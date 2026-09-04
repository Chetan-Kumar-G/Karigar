import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';
import '../services/api_service.dart';

/// Shared state for the end-to-end product-creation journey (spec §18) so the
/// Studio → Voice → Passport → Price → Publish screens all see the same draft.
/// Also persists a lightweight offline draft (spec §27).
class ProductFlow extends ChangeNotifier {
  ProductFlow(this._api);
  final ApiService _api;

  Product? product;
  ReadinessResult? readiness;
  CatalogResult? catalog;
  Passport? passport;
  PriceResult? price;

  bool busy = false;
  String? error;

  bool get hasDraft => product != null;
  String get step {
    if (product == null) return 'start';
    if (readiness == null) return 'photo';
    if (catalog == null) return 'voice';
    if (price == null) return 'price';
    if (product!.status != 'published') return 'publish';
    return 'done';
  }

  void reset() {
    product = null;
    readiness = null;
    catalog = null;
    passport = null;
    price = null;
    error = null;
    notifyListeners();
    _clearDraft();
  }

  void clearReadiness() {
    readiness = null;
    notifyListeners();
  }

  void clearCatalog() {
    catalog = null;
    notifyListeners();
  }

  Future<void> start({required String title, String? craftId, String? category}) async {
    await _guard(() async {
      product = await _api.createProduct(
          title: title, craftId: craftId, category: category);
      readiness = null;
      catalog = null;
      passport = null;
      price = null;
    });
    _saveDraft();
  }

  Future<void> loadExisting(String productId) async {
    await _guard(() async {
      product = await _api.product(productId);
      try {
        passport = await _api.passport(productId);
      } catch (_) {}
    });
  }

  Future<void> analyze(Uint8List bytes, {String filename = 'photo.jpg'}) async {
    if (product == null) return;
    await _guard(() async {
      readiness = await _api.analyzeImage(
        bytes: bytes,
        filename: filename,
        productId: product!.id,
        categoryHint: product!.category,
      );
      product = await _api.product(product!.id);
    });
    _saveDraft();
  }

  Future<void> runCatalog({
    Uint8List? audioBytes,
    String audioFilename = 'voice.m4a',
    String? typedTranscript,
    String languageHint = 'hi',
  }) async {
    if (product == null) return;
    await _guard(() async {
      final colours = <String>[];
      catalog = await _api.generateCatalog(
        audioBytes: audioBytes,
        audioFilename: audioFilename,
        typedTranscript: typedTranscript,
        languageHint: languageHint,
        craftId: product!.craftId,
        productId: product!.id,
        visualContext: {
          'detected_colors': colours,
          'segmentation_present': readiness?.maskUrl != null,
          'product_type_hint': '${product!.category ?? ''} ${product!.craftName ?? ''}',
        },
      );
      product = await _api.product(product!.id);
      passport = await _api.passport(product!.id);
    });
    _saveDraft();
  }

  Future<void> loadPassport() async {
    if (product == null) return;
    await _guard(() async {
      passport = await _api.passport(product!.id);
    });
  }

  Future<void> runPrice({
    required double materialCost,
    required double labourHours,
    required double labourRate,
    double packaging = 0,
    double logistics = 0,
  }) async {
    if (product == null) return;
    await _guard(() async {
      price = await _api.predictPrice(
        productId: product!.id,
        materialCost: materialCost,
        labourHours: labourHours,
        labourRate: labourRate,
        packaging: packaging,
        logistics: logistics,
        category: product!.category,
      );
      product = await _api.product(product!.id);
    });
    _saveDraft();
  }

  Future<Product> publish({double? priceOverride}) async {
    final p = await _api.publish(product!.id, price: priceOverride);
    product = p;
    notifyListeners();
    _clearDraft();
    return p;
  }

  Future<void> _guard(Future<void> Function() body) async {
    busy = true;
    error = null;
    notifyListeners();
    try {
      await body();
    } catch (e) {
      error = '$e';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  // ── offline draft ──────────────────────────────────────────────────
  static const _kDraft = 'sih_product_draft';

  Future<void> _saveDraft() async {
    if (product == null) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        _kDraft,
        jsonEncode({
          'product_id': product!.id,
          'title': product!.title,
          'status': product!.status,
          'readiness': readiness?.score,
          'has_catalog': catalog != null,
          'has_price': price != null,
        }));
  }

  Future<void> _clearDraft() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kDraft);
  }

  Future<Map<String, dynamic>?> peekDraft() async {
    final prefs = await SharedPreferences.getInstance();
    final s = prefs.getString(_kDraft);
    if (s == null) return null;
    try {
      return Map<String, dynamic>.from(jsonDecode(s) as Map);
    } catch (_) {
      return null;
    }
  }
}

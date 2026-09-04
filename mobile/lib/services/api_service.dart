import 'dart:convert';
import 'dart:typed_data';

import '../core/api_client.dart';
import '../core/json.dart';
import '../models/models.dart';

/// One typed method per backend endpoint (spec §12, §21, §29).
class ApiService {
  ApiService(this._c);
  final ApiClient _c;

  void setToken(String? t) => _c.setToken(t);

  // ── meta ──────────────────────────────────────────────────────────────
  Future<J> features() async => asMap(await _c.get('/meta/features'));
  Future<ReferenceData> reference() async =>
      ReferenceData.fromJson(asMap(await _c.get('/reference')));
  Future<J> health({Duration? timeout}) async =>
      asMap(await _c.get('/health', timeout: timeout));

  // ── auth ─────────────────────────────────────────────────────────────
  Future<J> requestOtp(String phone, String role) async =>
      asMap(await _c.postJson('/auth/otp/request', {'phone': phone, 'role': role}));

  Future<Session> verifyOtp(String phone, String otp, String role) async =>
      Session.fromJson(asMap(await _c.postJson(
          '/auth/otp/verify', {'phone': phone, 'otp': otp, 'role': role})));

  Future<J> demoAccounts() async => asMap(await _c.get('/auth/demo-accounts'));

  // ── demo mode ────────────────────────────────────────────────────────
  Future<J> demoScenario() async => asMap(await _c.get('/demo/scenario'));
  Future<J> demoReset() async => asMap(await _c.postJson('/demo/reset', {}));
  Future<J> demoLoad() async => asMap(await _c.postJson('/demo/load', {}));

  // ── products / F1 ────────────────────────────────────────────────────
  Future<List<Product>> myProducts() async =>
      asMapList(asMap(await _c.get('/products'))['products'])
          .map(Product.fromJson)
          .toList();

  Future<Product> product(String id) async =>
      Product.fromJson(asMap(await _c.get('/product/$id')));

  Future<Product> createProduct({
    required String title,
    String? craftId,
    String? category,
  }) async =>
      Product.fromJson(asMap(await _c.postForm('/product', {
        'title': title,
        if (craftId != null) 'craft_id': craftId,
        if (category != null) 'category': category,
      })));

  Future<ReadinessResult> analyzeImage({
    required Uint8List bytes,
    String filename = 'photo.jpg',
    String? productId,
    String? categoryHint,
  }) async =>
      ReadinessResult.fromJson(asMap(await _c.postMultipart(
        '/product/analyze',
        files: {'image': UploadPart(bytes, filename)},
        fields: {
          if (productId != null) 'product_id': productId,
          if (categoryHint != null) 'product_category_hint': categoryHint,
        },
      )));

  Future<Product> selectImage(String productId, String imageId,
          {bool useEnhanced = true}) async =>
      Product.fromJson(asMap(await _c.postForm('/product/$productId/select-image', {
        'image_id': imageId,
        'use_enhanced': '$useEnhanced',
      })));

  Future<J> inventory() async => asMap(await _c.get('/inventory'));

  Future<void> setInventory(String productId, int availableUnits) async {
    await _c.postForm('/product/$productId/inventory',
        {'available_units': '$availableUnits'});
  }

  Future<Product> publish(String productId, {double? price}) async =>
      Product.fromJson(asMap(await _c.postJson('/product/publish', {
        'product_id': productId,
        if (price != null) 'price_inr': price,
      })));

  // ── F2 catalog ───────────────────────────────────────────────────────
  Future<CatalogResult> generateCatalog({
    Uint8List? audioBytes,
    String audioFilename = 'voice.m4a',
    String? typedTranscript,
    String languageHint = 'hi',
    String? craftId,
    String? productId,
    Map<String, dynamic>? visualContext,
  }) async {
    final fields = <String, String>{
      'language_hint': languageHint,
      if (typedTranscript != null) 'typed_transcript': typedTranscript,
      if (craftId != null) 'craft_id': craftId,
      if (productId != null) 'product_id': productId,
      if (visualContext != null) 'visual_context': jsonEncode(visualContext),
    };
    final res = audioBytes != null
        ? await _c.postMultipart('/catalog/generate',
            files: {'voice_note': UploadPart(audioBytes, audioFilename)},
            fields: fields)
        : await _c.postForm('/catalog/generate', fields);
    return CatalogResult.fromJson(asMap(res));
  }

  // ── F3 craft / passport ─────────────────────────────────────────────
  Future<J> craft(String id) async => asMap(await _c.get('/craft/$id'));
  Future<Passport> passport(String productId) async =>
      Passport.fromJson(asMap(await _c.get('/passport/$productId')));

  // ── F4 pricing ─────────────────────────────────────────────────────
  Future<PriceResult> predictPrice({
    String? productId,
    required double materialCost,
    required double labourHours,
    required double labourRate,
    double packaging = 0,
    double logistics = 0,
    String? category,
    double? categoryMedian,
    double? minMargin,
  }) async =>
      PriceResult.fromJson(asMap(await _c.postJson('/price/predict', {
        if (productId != null) 'product_id': productId,
        'material_cost_inr': materialCost,
        'labour_hours': labourHours,
        'labour_rate_inr_per_hour': labourRate,
        'packaging_cost_inr': packaging,
        'logistics_cost_inr': logistics,
        if (category != null) 'category': category,
        if (categoryMedian != null) 'category_median_price_inr': categoryMedian,
        if (minMargin != null) 'min_margin': minMargin,
      })));

  // ── F5 demand ─────────────────────────────────────────────────────
  Future<DemandResult> demandForecast({
    required String category,
    String? regionId,
    int windowDays = 30,
    String? artisanId,
  }) async =>
      DemandResult.fromJson(asMap(await _c.get('/demand/forecast', query: {
        'category': category,
        'region_id': regionId,
        'window_days': windowDays,
        'artisan_id': artisanId,
      })));

  // ── F6 buyers / orders ────────────────────────────────────────────
  Future<List<Requirement>> requirements() async =>
      asMapList(asMap(await _c.get('/requirements'))['requirements'])
          .map(Requirement.fromJson)
          .toList();

  Future<Requirement> requirement(String id) async =>
      Requirement.fromJson(asMap(await _c.get('/requirement/$id')));

  Future<Requirement> createRequirement(J body) async =>
      Requirement.fromJson(asMap(await _c.postJson('/requirements', body)));

  Future<OrderResult> buyerMatch({
    String? requirementId,
    int? quantity,
    double? priceMin,
    double? priceMax,
    String? craftId,
    String? material,
    double fulfillmentMin = 1.0,
  }) async =>
      OrderResult.fromJson(asMap(await _c.postJson('/buyer/match', {
        if (requirementId != null) 'requirement_id': requirementId,
        if (quantity != null) 'quantity': quantity,
        if (priceMin != null) 'unit_price_min': priceMin,
        if (priceMax != null) 'unit_price_max': priceMax,
        if (craftId != null) 'required_craft_id': craftId,
        if (material != null) 'required_material': material,
        'fulfillment_min': fulfillmentMin,
      })));

  Future<OrderResult> allocateOrder(String orderId,
          {List<String>? declined}) async =>
      OrderResult.fromJson(asMap(await _c.postJson('/order/allocate', {
        'order_id': orderId,
        if (declined != null) 'declined_allocation_ids': declined,
      })));

  Future<List<J>> orders() async =>
      asMapList(asMap(await _c.get('/orders'))['orders']);

  Future<List<J>> artisanOrders(String artisanId) async =>
      asMapList(asMap(await _c.get('/artisan/$artisanId/orders'))['orders']);

  // ── F7 discovery / copilot / dashboard ───────────────────────────
  Future<SearchResult> search(String q,
          {String? category, String? regionId, bool fairness = true,
          String? sessionId}) async =>
      SearchResult.fromJson(asMap(await _c.get('/search', query: {
        'q': q,
        'category': category,
        'region_id': regionId,
        'fairness': fairness,
        'session_id': sessionId,
      })));

  Future<void> recordClick(String listingId, String sessionId) async {
    await _c.postForm('/search/click', {},
        query: {'listing_id': listingId, 'session_id': sessionId});
  }

  Future<J> searchCompare(String q) async =>
      asMap(await _c.get('/search/compare', query: {'q': q}));

  Future<List<CopilotCard>> insights(String artisanId) async =>
      asMapList(asMap(await _c.get('/artisan/$artisanId/insights'))['insights'])
          .map(CopilotCard.fromJson)
          .toList();

  Future<Dashboard> dashboard(String artisanId) async =>
      Dashboard.fromJson(asMap(await _c.get('/artisan/$artisanId/dashboard')));

  // ── judge screen ─────────────────────────────────────────────────
  Future<J> aiRunsSummary() async =>
      asMap(await _c.get('/debug/ai-runs/summary'));
  Future<List<AiRun>> aiRuns({String? feature}) async =>
      asMapList(asMap(await _c.get('/debug/ai-runs',
              query: {'feature': feature, 'limit': 60}))['runs'])
          .map(AiRun.fromJson)
          .toList();
  Future<J> f7Explain(String q) async =>
      asMap(await _c.get('/debug/f7-explain', query: {'q': q}));

  // ── Trust & Verification ─────────────────────────────────────────
  Future<VerifiedCard> artisanTrustCard(String artisanId) async =>
      VerifiedCard.fromJson(asMap(await _c.get('/trust/artisan/$artisanId')));

  Future<VerifiedCard> businessTrustCard(String buyerId) async =>
      VerifiedCard.fromJson(asMap(await _c.get('/trust/business/$buyerId')));

  Future<VerificationProfileM> trustProfile(String subjectId) async =>
      VerificationProfileM.fromJson(asMap(await _c.get('/trust/profile/$subjectId')));

  Future<VerificationProfileM> submitEvidence({
    required String subjectId,
    required String kind,
    String subjectType = 'artisan',
    String axis = 'identity',
    String? label,
    String? note,
  }) async {
    final res = asMap(await _c.postJson('/trust/verify/submit', {
      'subject_id': subjectId,
      'subject_type': subjectType,
      'kind': kind,
      'axis': axis,
      if (label != null) 'label': label,
      if (note != null) 'note': note,
    }));
    return VerificationProfileM.fromJson(asMap(res['profile']));
  }

  Future<J> reviewerQueue() async => asMap(await _c.get('/trust/reviewer/queue'));

  Future<VerificationProfileM> reviewerDetail(String profileId) async =>
      VerificationProfileM.fromJson(
          asMap(await _c.get('/trust/reviewer/$profileId')));

  Future<J> reviewerAction(String profileId, String action, {String? note}) async =>
      asMap(await _c.postJson('/trust/reviewer/$profileId/action', {
        'action': action,
        if (note != null) 'note': note,
      }));

  Future<J> complaints({String? subjectId, String? status}) async =>
      asMap(await _c.get('/trust/complaints',
          query: {'subject_id': subjectId, 'status': status}));

  Future<J> createComplaint({
    required String subjectId,
    required String category,
    String severity = 'medium',
    String? description,
    String? orderId,
  }) async =>
      asMap(await _c.postJson('/trust/complaints', {
        'subject_id': subjectId,
        'category': category,
        'severity': severity,
        if (description != null) 'description': description,
        if (orderId != null) 'order_id': orderId,
      }));

  Future<J> resolveComplaint(String complaintId,
          {required String resolution, String outcome = 'dismissed'}) async =>
      asMap(await _c.postJson('/trust/complaints/$complaintId/resolve',
          {'resolution': resolution, 'outcome': outcome}));

  Future<J> reliability(String artisanId) async =>
      asMap(await _c.get('/trust/reliability/$artisanId'));

  Future<J> trustScenario() async => asMap(await _c.get('/demo/trust'));

  // ── B2B order commitment (simulated milestone payments) ──────────
  Future<OrderCommitment> orderCommitment(String orderId) async =>
      OrderCommitment.fromJson(asMap(await _c.get('/order/$orderId/commitment')));

  Future<OrderCommitment> commitmentAdvancePayment(String orderId) async =>
      OrderCommitment.fromJson(
          asMap(await _c.postJson('/order/$orderId/commitment/advance', {})));

  Future<OrderCommitment> commitmentNextStage(String orderId) async =>
      OrderCommitment.fromJson(asMap(
          await _c.postJson('/order/$orderId/commitment/advance-stage', {})));

  Future<OrderCommitment> commitmentCancel(String orderId,
          {String by = 'buyer'}) async =>
      OrderCommitment.fromJson(asMap(
          await _c.postJson('/order/$orderId/commitment/cancel', {'by': by})));
}

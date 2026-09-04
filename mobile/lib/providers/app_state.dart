import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/app_config.dart';
import '../core/json.dart';
import '../models/models.dart';
import '../services/api_service.dart';

enum AuthStatus { unknown, signedOut, signedIn }

/// Result of the last backend health probe (spec: Phase 2).
enum ConnStatus { unknown, checking, online, offline }

/// App-wide session + reference data + demo-mode role switch (spec §6, §36).
class AppState extends ChangeNotifier {
  AppState() : api = ApiService(ApiClient());

  final ApiService api;

  AuthStatus status = AuthStatus.unknown;
  Session? session;
  ReferenceData? reference;
  J features = {};
  String? lastError;

  // ── backend connectivity (Phase 2) ──────────────────────────────────
  ConnStatus conn = ConnStatus.unknown;
  String? backendVersion;
  String? dbStatus; // 'ok' | 'error'
  String? connError; // human-readable reason the probe failed
  String get apiBaseUrl => AppConfig.apiBaseUrl;

  bool get backendOnline => conn == ConnStatus.online;

  /// Lightweight `/health` probe. Never throws. Returns true when the backend
  /// answered. Distinguishes *backend unreachable* (this returns false) from
  /// *invalid credentials* (a later 401 on a real request).
  ///
  /// Tries up to [attempts] times — a freshly started backend often misses the
  /// first probe while it loads its heavy libraries, then answers instantly.
  Future<bool> checkHealth({int attempts = 2}) async {
    conn = ConnStatus.checking;
    notifyListeners();
    for (var i = 0; i < attempts; i++) {
      try {
        final h = await api.health(timeout: AppConfig.healthTimeout);
        backendVersion = h['version']?.toString();
        dbStatus = h['database']?.toString();
        connError = null;
        conn = ConnStatus.online;
        notifyListeners();
        // Opportunistically refresh reference/feature data now that we're online.
        unawaited(_loadReference());
        unawaited(_loadFeatures());
        return true;
      } catch (e) {
        connError = e is ApiException ? e.message : '$e';
        if (i + 1 < attempts) {
          await Future<void>.delayed(const Duration(milliseconds: 800));
        }
      }
    }
    conn = ConnStatus.offline;
    notifyListeners();
    return false;
  }

  bool get isArtisan => session?.isArtisan ?? true;
  bool get signedIn => status == AuthStatus.signedIn && session != null;

  static const _kToken = 'sih_token';
  static const _kRole = 'sih_role';
  static const _kProfile = 'sih_profile';

  Future<void> bootstrap() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kToken);
    if (token != null) {
      api.setToken(token);
      session = Session(
        token: token,
        role: prefs.getString(_kRole) ?? 'artisan',
        profile: _decode(prefs.getString(_kProfile)),
      );
      status = AuthStatus.signedIn;
    } else {
      status = AuthStatus.signedOut;
    }
    notifyListeners();
    unawaited(checkHealth());
  }

  Future<void> _loadReference() async {
    try {
      reference = await api.reference();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> _loadFeatures() async {
    try {
      features = await api.features();
      notifyListeners();
    } catch (_) {}
  }

  Future<Session> signIn(String phone, String otp, String role) async {
    final s = await api.verifyOtp(phone, otp, role);
    await _persist(s);
    unawaited(_loadReference());
    unawaited(_loadFeatures());
    return s;
  }

  /// Demo-mode role switch — re-authenticates as the paired demo account.
  Future<void> switchRole(String toRole) async {
    final phone = toRole == 'buyer' ? '9900000001' : '9800000001';
    final s = await api.verifyOtp(phone, '123456', toRole);
    await _persist(s);
  }

  Future<J> loadDemo() async {
    final res = await api.demoLoad();
    final a = asMap(res['artisan']);
    await _persist(Session(
      token: asStr(a['token']),
      role: 'artisan',
      profile: {'artisan_id': a['artisan_id'], 'name': a['name']},
    ));
    return res;
  }

  Future<void> _persist(Session s) async {
    session = s;
    status = AuthStatus.signedIn;
    api.setToken(s.token);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kToken, s.token);
    await prefs.setString(_kRole, s.role);
    await prefs.setString(_kProfile, jsonEncode(s.profile));
    notifyListeners();
  }

  Future<void> signOut() async {
    session = null;
    status = AuthStatus.signedOut;
    api.setToken(null);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kToken);
    await prefs.remove(_kRole);
    await prefs.remove(_kProfile);
    notifyListeners();
  }

  static J _decode(String? s) {
    if (s == null || s.isEmpty) return {};
    try {
      return asMap(jsonDecode(s));
    } catch (_) {
      return {};
    }
  }
}

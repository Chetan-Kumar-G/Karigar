import 'package:shared_preferences/shared_preferences.dart';

/// Centralised backend configuration — the **single** place the app decides
/// which server to talk to. Nothing else in the app should hard-code a URL.
///
/// Resolution order (highest priority first):
///   1. A runtime override saved from the in-app "Server address" field
///      (`SharedPreferences` key [_overrideKey]) — lets a physical device point
///      at a laptop's LAN IP without rebuilding.
///   2. `--dart-define=API_BASE_URL=...` given at build/run time.
///   3. The built-in default below.
///
/// Typical values:
///   • Android emulator      → `http://10.0.2.2:8000/api`   (the default)
///   • Physical Android/iOS  → `http://<laptop-LAN-IP>:8000/api`
///   • Web / desktop / iOS simulator → `http://localhost:8000/api`
///   • Hosted demo build     → `https://<your-host>/api`
///
/// `MEDIA_HOST` no longer needs its own dart-define — it is derived from the
/// resolved base URL by stripping the trailing `/api`. An explicit
/// `--dart-define=MEDIA_HOST=...` still wins if supplied.
class AppConfig {
  AppConfig._();

  static const String _defaultBaseUrl = 'http://10.0.2.2:8000/api';

  static const String _dartDefineBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static const String _dartDefineMediaHost =
      String.fromEnvironment('MEDIA_HOST', defaultValue: '');

  static const String _overrideKey = 'sih_api_base_url_override';

  /// Set once at startup by [loadOverride]; mutated by [setOverride].
  static String? _override;

  static const String appName = 'Kārigar';
  static const String appTagline = 'Your AI business manager';

  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration aiTimeout = Duration(seconds: 60);

  /// Timeout for the startup / retry health probe. Generous because a freshly
  /// started Python backend loads OpenCV / LightGBM / OR-Tools on its first hit.
  static const Duration healthTimeout = Duration(seconds: 12);

  /// The effective API base URL, e.g. `http://10.0.2.2:8000/api`.
  static String get apiBaseUrl {
    final o = _override?.trim();
    if (o != null && o.isNotEmpty) return _normalise(o);
    // The dart-define value is a full URL supplied at build time (e.g. by CI) —
    // use it as-is rather than running it through the typed-address normaliser,
    // which would wrongly force a default :8000 port onto a standard-port host.
    if (_dartDefineBaseUrl.isNotEmpty) {
      return _stripTrailingSlash(_dartDefineBaseUrl.trim());
    }
    return _defaultBaseUrl;
  }

  /// Origin that serves `/media/...` files — derived from [apiBaseUrl].
  static String get mediaHost {
    if (_dartDefineMediaHost.isNotEmpty) {
      return _stripTrailingSlash(_dartDefineMediaHost);
    }
    final base = apiBaseUrl;
    final uri = Uri.tryParse(base);
    if (uri != null && uri.hasScheme) {
      return '${uri.scheme}://${uri.authority}';
    }
    // Fallback: chop a trailing `/api`.
    return base.endsWith('/api') ? base.substring(0, base.length - 4) : base;
  }

  /// Health endpoint for the startup connectivity probe.
  static String get healthUrl => '$apiBaseUrl/health';

  /// Whether the user has pinned a custom server address on this device.
  static bool get hasOverride =>
      (_override != null && _override!.trim().isNotEmpty);

  /// Load any saved override. Call once in `main()` before `runApp`.
  static Future<void> loadOverride() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _override = prefs.getString(_overrideKey);
    } catch (_) {
      _override = null;
    }
  }

  /// Persist (or clear, when [value] is null/empty) a custom server address.
  static Future<void> setOverride(String? value) async {
    final v = value?.trim() ?? '';
    _override = v.isEmpty ? null : _normalise(v);
    try {
      final prefs = await SharedPreferences.getInstance();
      if (_override == null) {
        await prefs.remove(_overrideKey);
      } else {
        await prefs.setString(_overrideKey, _override!);
      }
    } catch (_) {/* best-effort persistence */}
  }

  /// Accepts `192.168.1.5`, `192.168.1.5:8000`, `http://host:8000`,
  /// `http://host:8000/api` and normalises to `http://host:8000/api`.
  static String _normalise(String raw) {
    var s = raw.trim();
    if (!s.startsWith('http://') && !s.startsWith('https://')) {
      s = 'http://$s';
    }
    final uri = Uri.tryParse(s);
    if (uri == null || uri.host.isEmpty) return _defaultBaseUrl;
    final port = uri.hasPort ? uri.port : 8000;
    var path = _stripTrailingSlash(uri.path);
    if (path.isEmpty) path = '/api';
    return '${uri.scheme}://${uri.host}:$port$path';
  }

  static String _stripTrailingSlash(String s) =>
      s.endsWith('/') ? s.substring(0, s.length - 1) : s;

  /// Resolve a `/media/...` path returned by the backend to an absolute URL.
  static String media(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http')) return path;
    return '$mediaHost$path';
  }
}

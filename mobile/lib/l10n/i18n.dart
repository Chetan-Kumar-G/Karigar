import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'langs.dart';

/// Lightweight in-app localisation.
///
/// * The **key is the English source string** — `tr('Add product')`. A missing
///   translation falls back to the key, so the app is always readable.
/// * `LocaleProvider` holds the chosen language, persists it, and swaps the
///   active dictionary. The whole widget tree rebuilds on change (see
///   `main.dart`), so every `tr(...)` re-evaluates.
/// * Flutter's own Material/Cupertino text uses a *supported* base locale
///   (falling back to English) — decoupled from our dictionary so exotic
///   language codes never crash `GlobalMaterialLocalizations`.

/// The 22 Eighth-Schedule languages + English (23 total).
/// `filled: true` ⇒ a hand-written dictionary ships in `langs.dart`.
const List<({String code, String english, String native, bool filled, bool rtl})>
    kAppLanguages = [
  (code: 'en', english: 'English', native: 'English', filled: true, rtl: false),
  (code: 'hi', english: 'Hindi', native: 'हिन्दी', filled: true, rtl: false),
  (code: 'bn', english: 'Bengali', native: 'বাংলা', filled: true, rtl: false),
  (code: 'ta', english: 'Tamil', native: 'தமிழ்', filled: true, rtl: false),
  (code: 'te', english: 'Telugu', native: 'తెలుగు', filled: true, rtl: false),
  (code: 'mr', english: 'Marathi', native: 'मराठी', filled: true, rtl: false),
  (code: 'gu', english: 'Gujarati', native: 'ગુજરાતી', filled: true, rtl: false),
  (code: 'kn', english: 'Kannada', native: 'ಕನ್ನಡ', filled: true, rtl: false),
  (code: 'ml', english: 'Malayalam', native: 'മലയാളം', filled: true, rtl: false),
  (code: 'pa', english: 'Punjabi', native: 'ਪੰਜਾਬੀ', filled: true, rtl: false),
  (code: 'or', english: 'Odia', native: 'ଓଡ଼ିଆ', filled: true, rtl: false),
  (code: 'as', english: 'Assamese', native: 'অসমীয়া', filled: true, rtl: false),
  (code: 'ur', english: 'Urdu', native: 'اردو', filled: true, rtl: true),
  (code: 'brx', english: 'Bodo', native: 'बड़ो', filled: false, rtl: false),
  (code: 'doi', english: 'Dogri', native: 'डोगरी', filled: false, rtl: false),
  (code: 'kok', english: 'Konkani', native: 'कोंकणी', filled: false, rtl: false),
  (code: 'mai', english: 'Maithili', native: 'मैथिली', filled: false, rtl: false),
  (code: 'mni', english: 'Manipuri (Meitei)', native: 'মেইতেই', filled: false, rtl: false),
  (code: 'ne', english: 'Nepali', native: 'नेपाली', filled: false, rtl: false),
  (code: 'sa', english: 'Sanskrit', native: 'संस्कृतम्', filled: false, rtl: false),
  (code: 'sat', english: 'Santali', native: 'ᱥᱟᱱᱛᱟᱲᱤ', filled: false, rtl: false),
  (code: 'sd', english: 'Sindhi', native: 'سنڌي', filled: false, rtl: true),
  (code: 'ks', english: 'Kashmiri', native: 'کٲشُر', filled: false, rtl: true),
];

/// Locales Flutter's bundled `flutter_localizations` can actually render.
/// Anything else falls back to English for *Material* text only — our `tr()`
/// dictionary still uses the user's real choice.
const Set<String> _materialSafe = {
  'en', 'hi', 'bn', 'ta', 'te', 'mr', 'gu', 'kn', 'ml', 'pa', 'or', 'as',
  'ur', 'ne',
};

Map<String, String> _active = const {};

/// Translate an English source string. Unknown ⇒ returns [en] unchanged.
String tr(String en) => _active[en] ?? en;

/// `'Hello {name}'` → `tr` then `{name}` substitution.
String trp(String en, Map<String, String> params) {
  var s = tr(en);
  params.forEach((k, v) => s = s.replaceAll('{$k}', v));
  return s;
}

class LocaleProvider extends ChangeNotifier {
  static const _kKey = 'app_language_code';

  String _code = 'en';
  String get code => _code;

  bool get isRtl =>
      kAppLanguages.firstWhere((l) => l.code == _code,
          orElse: () => kAppLanguages.first).rtl;

  /// Locale handed to `MaterialApp` for its own widgets (safe subset only).
  Locale get materialLocale =>
      Locale(_materialSafe.contains(_code) ? _code : 'en');

  List<Locale> get supportedLocales =>
      _materialSafe.map((c) => Locale(c)).toList();

  Future<void> load() async {
    try {
      final p = await SharedPreferences.getInstance();
      _applyCode(p.getString(_kKey) ?? 'en');
    } catch (_) {
      _applyCode('en');
    }
    notifyListeners();
  }

  Future<void> setLanguage(String code) async {
    _applyCode(code);
    notifyListeners();
    try {
      final p = await SharedPreferences.getInstance();
      await p.setString(_kKey, code);
    } catch (_) {/* best-effort persistence */}
  }

  void _applyCode(String code) {
    final known = kAppLanguages.any((l) => l.code == code);
    _code = known ? code : 'en';
    _active = kTranslations[_code] ?? const {};
  }
}

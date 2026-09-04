import 'package:flutter/material.dart';

/// Heritage-inspired design system (spec §23): terracotta + indigo on a warm
/// cream ground. Large touch targets, high contrast, generous rounding.
class AppTheme {
  // ── palette ──────────────────────────────────────────────────────────
  static const Color terracotta = Color(0xFFB4552D);
  static const Color terracottaDark = Color(0xFF8C3E1F);
  static const Color indigo = Color(0xFF2E3A6E);
  static const Color indigoLight = Color(0xFF4A5BA6);
  static const Color ochre = Color(0xFFE0A73B);
  static const Color cream = Color(0xFFFBF6EE);
  static const Color sand = Color(0xFFF2E8D8);
  static const Color ink = Color(0xFF2A2320);
  static const Color inkSoft = Color(0xFF6B615A);
  static const Color leaf = Color(0xFF3F7D58);
  static const Color leafBg = Color(0xFFE3F0E7);
  static const Color amberBg = Color(0xFFFBEBD2);
  static const Color skyBg = Color(0xFFE2E9F5);
  static const Color danger = Color(0xFFB5372E);
  static const Color line = Color(0xFFE7DCC9);

  static ThemeData light() {
    const scheme = ColorScheme(
      brightness: Brightness.light,
      primary: terracotta,
      onPrimary: Colors.white,
      primaryContainer: Color(0xFFF6DFD1),
      onPrimaryContainer: terracottaDark,
      secondary: indigo,
      onSecondary: Colors.white,
      secondaryContainer: skyBg,
      onSecondaryContainer: indigo,
      tertiary: ochre,
      onTertiary: ink,
      error: danger,
      onError: Colors.white,
      errorContainer: Color(0xFFF7DAD6),
      onErrorContainer: Color(0xFF5F1712),
      surface: Colors.white,
      onSurface: ink,
      surfaceContainerLowest: Colors.white,
      surfaceContainerLow: cream,
      surfaceContainer: sand,
      surfaceContainerHigh: Color(0xFFEFE4D2),
      surfaceContainerHighest: Color(0xFFEADDC8),
      onSurfaceVariant: inkSoft,
      outline: Color(0xFFCBBCA2),
      outlineVariant: line,
      shadow: Color(0x22000000),
      scrim: Colors.black54,
      inverseSurface: ink,
      onInverseSurface: cream,
      inversePrimary: Color(0xFFF6DFD1),
    );

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: cream,
      fontFamily: 'Roboto',
      splashFactory: InkRipple.splashFactory,
    );

    return base.copyWith(
      textTheme: _text(base.textTheme),
      appBarTheme: const AppBarTheme(
        backgroundColor: cream,
        foregroundColor: ink,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: line),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: terracotta,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(54),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: indigo,
          minimumSize: const Size.fromHeight(52),
          side: const BorderSide(color: indigo, width: 1.5),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(54),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: sand,
        side: const BorderSide(color: line),
        labelStyle: const TextStyle(fontWeight: FontWeight.w600, color: ink),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: terracotta, width: 2),
        ),
      ),
      dividerTheme: const DividerThemeData(color: line, thickness: 1, space: 1),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: terracotta,
        unselectedItemColor: inkSoft,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: ink,
        contentTextStyle: const TextStyle(color: cream, fontSize: 15),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  static TextTheme _text(TextTheme t) => t.copyWith(
        displaySmall: t.displaySmall?.copyWith(fontWeight: FontWeight.w800, color: ink),
        headlineMedium: t.headlineMedium?.copyWith(fontWeight: FontWeight.w800, color: ink),
        headlineSmall: t.headlineSmall?.copyWith(fontWeight: FontWeight.w700, color: ink),
        titleLarge: t.titleLarge?.copyWith(fontWeight: FontWeight.w700, color: ink),
        titleMedium: t.titleMedium?.copyWith(fontWeight: FontWeight.w700, color: ink),
        bodyLarge: t.bodyLarge?.copyWith(fontSize: 16, color: ink, height: 1.4),
        bodyMedium: t.bodyMedium?.copyWith(fontSize: 15, color: inkSoft, height: 1.4),
        labelLarge: t.labelLarge?.copyWith(fontWeight: FontWeight.w700),
      );
}

/// Semantic colours for Business-Copilot / status chips.
class Accent {
  static const Map<String, Color> fg = {
    'blue': AppTheme.indigo,
    'green': AppTheme.leaf,
    'orange': AppTheme.terracotta,
    'amber': AppTheme.ochre,
  };
  static const Map<String, Color> bg = {
    'blue': AppTheme.skyBg,
    'green': AppTheme.leafBg,
    'orange': Color(0xFFF6E1D4),
    'amber': AppTheme.amberBg,
  };
}

import 'package:flutter/material.dart';

class AppTheme {
  static const primaryColor = Color(0xFF1565C0);
  static const betterColor = Color(0xFF2E7D32);
  static const worseColor = Color(0xFFC62828);
  static const sameColor = Color(0xFF757575);
  static const neutralColor = Color(0xFF424242);
  static const accentGold = Color(0xFFFF8F00);

  static const _fontFamily = 'PingFang TC, Heiti TC, Microsoft JhengHei, Noto Sans TC, sans-serif';

  static ThemeData get theme => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: primaryColor,
    scaffoldBackgroundColor: Colors.grey[50],
    textTheme: const TextTheme(
      bodyLarge: TextStyle(fontFamily: _fontFamily),
      bodyMedium: TextStyle(fontFamily: _fontFamily),
      bodySmall: TextStyle(fontFamily: _fontFamily),
      titleLarge: TextStyle(fontFamily: _fontFamily),
      titleMedium: TextStyle(fontFamily: _fontFamily),
      titleSmall: TextStyle(fontFamily: _fontFamily),
      labelLarge: TextStyle(fontFamily: _fontFamily),
      labelMedium: TextStyle(fontFamily: _fontFamily),
      labelSmall: TextStyle(fontFamily: _fontFamily),
      headlineLarge: TextStyle(fontFamily: _fontFamily),
      headlineMedium: TextStyle(fontFamily: _fontFamily),
      headlineSmall: TextStyle(fontFamily: _fontFamily),
      displayLarge: TextStyle(fontFamily: _fontFamily),
      displayMedium: TextStyle(fontFamily: _fontFamily),
      displaySmall: TextStyle(fontFamily: _fontFamily),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: primaryColor,
      foregroundColor: Colors.white,
      elevation: 0,
      titleTextStyle: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: Colors.white,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    ),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
  );
}

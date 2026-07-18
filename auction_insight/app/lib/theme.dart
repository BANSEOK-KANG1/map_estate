import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const ink = Color(0xFF1A2332);
  static const slate = Color(0xFF2C4A6E);
  static const amber = Color(0xFFC47B2B);
  static const mist = Color(0xFFF0F3F7);
  static const fog = Color(0xFFE2E8F0);
  static const line = Color(0xFFCBD5E1);

  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.light(
        primary: slate,
        secondary: amber,
        surface: mist,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: ink,
        outline: line,
      ),
      scaffoldBackgroundColor: mist,
    );

    return base.copyWith(
      textTheme: GoogleFonts.notoSansKrTextTheme(base.textTheme).apply(
        bodyColor: ink,
        displayColor: ink,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: mist.withValues(alpha: 0.94),
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.notoSansKr(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: fog,
        selectedColor: slate.withValues(alpha: 0.16),
        labelStyle: GoogleFonts.notoSansKr(fontSize: 13, color: ink),
        side: const BorderSide(color: line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: slate,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }
}

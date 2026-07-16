import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const ink = Color(0xFF1C2B2A);
  static const moss = Color(0xFF2F6F5E);
  static const clay = Color(0xFFC46B3A);
  static const sand = Color(0xFFE8E0D4);
  static const mist = Color(0xFFF3EFE8);
  static const line = Color(0xFFD5CFC4);

  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.light(
        primary: moss,
        secondary: clay,
        surface: mist,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: ink,
        outline: line,
      ),
      scaffoldBackgroundColor: mist,
    );

    return base.copyWith(
      textTheme: GoogleFonts.ibmPlexSansKrTextTheme(base.textTheme).apply(
        bodyColor: ink,
        displayColor: ink,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: mist.withValues(alpha: 0.92),
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.ibmPlexSansKr(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: sand,
        selectedColor: moss.withValues(alpha: 0.18),
        labelStyle: GoogleFonts.ibmPlexSansKr(fontSize: 13, color: ink),
        side: const BorderSide(color: line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: moss,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.7),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: line),
        ),
      ),
    );
  }
}

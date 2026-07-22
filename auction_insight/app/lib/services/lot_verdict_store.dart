import 'package:shared_preferences/shared_preferences.dart';

/// Local Pass / Watch notes for lots (device-only).
class LotVerdictStore {
  static String _key(String source, String externalId) =>
      'lot_verdict_${source}_$externalId';

  static Future<({String verdict, String note})> load(
    String source,
    String externalId,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key(source, externalId)) ?? '';
    if (raw.isEmpty) return (verdict: '', note: '');
    final parts = raw.split('\u001f');
    return (
      verdict: parts.isNotEmpty ? parts[0] : '',
      note: parts.length > 1 ? parts.sublist(1).join('\u001f') : '',
    );
  }

  static Future<void> save({
    required String source,
    required String externalId,
    required String verdict,
    String note = '',
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (verdict.isEmpty && note.isEmpty) {
      await prefs.remove(_key(source, externalId));
      return;
    }
    await prefs.setString(_key(source, externalId), '$verdict\u001f$note');
  }
}

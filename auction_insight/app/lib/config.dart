import 'package:flutter/foundation.dart' show kIsWeb;

class AppConfig {
  static String get apiBaseUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) {
      var url = fromEnv;
      if (kIsWeb) {
        url = url
            .replaceFirst('http://127.0.0.1', 'http://localhost')
            .replaceFirst('https://127.0.0.1', 'https://localhost');
      }
      return url;
    }
    if (kIsWeb) {
      return Uri.base.origin;
    }
    return 'http://127.0.0.1:8001';
  }
}

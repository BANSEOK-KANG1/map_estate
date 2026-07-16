import 'package:flutter/foundation.dart' show kIsWeb;

class AppConfig {
  /// Web same-origin (served from FastAPI :8000) avoids browser blocking cross-port calls.
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
      // When Flutter web is served by the API server, use same origin.
      return Uri.base.origin;
    }
    return 'http://127.0.0.1:8000';
  }

  static const kakaoNativeKey = String.fromEnvironment('KAKAO_NATIVE_KEY');
  static const kakaoJsKey = String.fromEnvironment('KAKAO_JS_KEY');

  static bool get hasKakaoMapKey =>
      kakaoNativeKey.isNotEmpty || kakaoJsKey.isNotEmpty;
}

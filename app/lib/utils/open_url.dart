import 'open_url_stub.dart'
    if (dart.library.html) 'open_url_web.dart'
    if (dart.library.io) 'open_url_io.dart'
    if (dart.library.js_interop) 'open_url_web.dart' as impl;

/// 외부 URL 열기 (웹은 window.open).
Future<bool> openExternalUrl(Uri uri) => impl.openExternalUrl(uri);

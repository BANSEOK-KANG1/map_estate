import 'package:web/web.dart' as web;

Future<bool> openExternalUrl(Uri uri) async {
  final url = uri.toString();
  // 1) 새 탭
  final popup = web.window.open(url, '_blank', 'noopener,noreferrer');
  if (popup != null) return true;
  // 2) 팝업 차단 시 같은 탭으로라도 이동
  web.window.location.assign(url);
  return true;
}

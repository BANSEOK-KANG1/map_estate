import 'package:web/web.dart' as web;

Future<bool> openExternalUrl(Uri uri) async {
  final url = uri.toString();
  // Prefer <a target=_blank>: reliable on Flutter web and does not navigate this tab.
  // Do NOT fall back to location.assign — that unloads the SPA ("앱이 초기화됨").
  // Also avoid relying on window.open's return value: with noopener it is often null
  // even when a new tab opened successfully.
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..target = '_blank'
    ..rel = 'noopener noreferrer';
  web.document.body?.append(anchor);
  anchor.click();
  anchor.remove();
  return true;
}

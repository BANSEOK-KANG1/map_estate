import 'package:intl/intl.dart';

final _manwon = NumberFormat('#,###');

String formatManwon(int? v) {
  if (v == null) return '—';
  if (v >= 10000) {
    final eok = v / 10000;
    if (eok == eok.roundToDouble()) {
      return '${eok.toInt()}억';
    }
    return '${eok.toStringAsFixed(1)}억';
  }
  return '${_manwon.format(v)}만';
}

String formatPct(double? ratio) {
  if (ratio == null) return '—';
  final pct = ratio * 100;
  final sign = pct >= 0 ? '-' : '+';
  // discount ratio: positive means cheaper → show as -XX%
  return '$sign${pct.abs().toStringAsFixed(0)}%';
}

String formatArea(double? m2) {
  if (m2 == null) return '—';
  final pyeong = m2 / 3.3058;
  return '${m2.toStringAsFixed(1)}㎡ (${pyeong.toStringAsFixed(1)}평)';
}

String formatDate(DateTime? dt) {
  if (dt == null) return '—';
  return DateFormat('yyyy.MM.dd').format(dt.toLocal());
}

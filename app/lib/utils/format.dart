import 'package:intl/intl.dart';

final _won = NumberFormat('#,###');

String formatManwon(int? manwon) {
  if (manwon == null) return '-';
  if (manwon >= 10000) {
    final eok = manwon / 10000;
    final rest = manwon % 10000;
    if (rest == 0) {
      return '${eok.toStringAsFixed(eok.truncateToDouble() == eok ? 0 : 1)}억';
    }
    return '${eok.floor()}억 ${_won.format(rest)}';
  }
  return '${_won.format(manwon)}만';
}

String formatRent(int? deposit, int? monthly) {
  if (deposit == null) return '-';
  if (monthly == null || monthly == 0) return '보 ${formatManwon(deposit)}';
  return '보 ${formatManwon(deposit)} / 월 ${_won.format(monthly)}';
}

String formatListingPrice({
  required String? dealKind,
  required int? price,
  required int? monthly,
}) {
  if (dealKind == 'rent') return formatRent(price, monthly);
  return formatManwon(price);
}

String formatTrend(double? pct) {
  if (pct == null) return '-';
  final sign = pct > 0 ? '+' : '';
  return '$sign${pct.toStringAsFixed(1)}%';
}

String formatArea(double? area) {
  if (area == null) return '-';
  return '${area.toStringAsFixed(1)}㎡';
}

String formatPyeong(double? pyeong) {
  if (pyeong == null) return '-';
  return '${pyeong.toStringAsFixed(1)}평';
}

String formatAreaPyeong(double? areaM2, double? pyeong) {
  if (areaM2 == null && pyeong == null) return '-';
  if (pyeong != null) {
    return '${formatArea(areaM2)} (${formatPyeong(pyeong)})';
  }
  if (areaM2 == null) return '-';
  return '${formatArea(areaM2)} (${(areaM2 / 3.3058).toStringAsFixed(1)}평)';
}

String formatLoan(int? loanManwon) {
  if (loanManwon == null) return '문의';
  if (loanManwon == 0) return '없음';
  return formatManwon(loanManwon);
}

String formatMoveIn(bool? ok) {
  if (ok == null) return '문의';
  return ok ? '가능' : '제한(문의)';
}

String formatYm(String? ym) {
  if (ym == null || ym.isEmpty) return '-';
  if (ym.length >= 7) return ym.substring(0, 7);
  return ym;
}

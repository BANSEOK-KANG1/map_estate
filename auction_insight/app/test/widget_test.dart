import 'package:flutter_test/flutter_test.dart';
import 'package:auction_insight_app/utils/format.dart';

void main() {
  test('formatManwon formats eok', () {
    expect(formatManwon(15000), '1.5억');
    expect(formatManwon(20000), '2억');
    expect(formatManwon(500), '500만');
  });

  test('formatPct shows discount', () {
    expect(formatPct(0.3), '-30%');
    expect(formatPct(-0.1), '+10%');
  });
}

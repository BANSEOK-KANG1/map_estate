import 'package:flutter/material.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/utils/format.dart';

/// Rough all-in cost helper for beginners (not tax advice).
class TotalCostCard extends StatefulWidget {
  const TotalCostCard({super.key, required this.lot});

  final LotDetail lot;

  @override
  State<TotalCostCard> createState() => _TotalCostCardState();
}

class _TotalCostCardState extends State<TotalCostCard> {
  double _repairManwon = 1000;
  double _taxRate = 0.022; // rough mid residential

  @override
  Widget build(BuildContext context) {
    final bid = (widget.lot.minBidManwon ?? 0).toDouble();
    final tax = bid * _taxRate;
    final total = bid + tax + _repairManwon;
    final market = widget.lot.market?.medianManwon?.toDouble();
    final margin = market != null && market > 0 ? (market - total) / market : null;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '총원가 감각 (러프)',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          ),
          const SizedBox(height: 4),
          Text(
            '취득세·수리비는 가정값입니다. 실제 세율·비용과 다를 수 있습니다.',
            style: TextStyle(
              fontSize: 11,
              color: AppTheme.ink.withValues(alpha: 0.45),
            ),
          ),
          const SizedBox(height: 12),
          _row('최저입찰', formatManwon(bid.round())),
          _row('취득세 가정 (${(_taxRate * 100).toStringAsFixed(1)}%)', formatManwon(tax.round())),
          _row('수리·명도 가정', formatManwon(_repairManwon.round())),
          const Divider(height: 20),
          _row('합산 총원가', formatManwon(total.round()), bold: true),
          if (market != null) ...[
            _row('인근 시세(중위)', formatManwon(market.round())),
            if (margin != null)
              _row(
                '시세 대비 여유',
                '${margin >= 0 ? '+' : ''}${(margin * 100).toStringAsFixed(0)}%p',
                bold: true,
              ),
          ],
          const SizedBox(height: 8),
          Text(
            '수리·명도 가정',
            style: TextStyle(
              fontSize: 12,
              color: AppTheme.ink.withValues(alpha: 0.55),
            ),
          ),
          Slider(
            value: _repairManwon.clamp(0, 10000),
            min: 0,
            max: 10000,
            divisions: 20,
            label: formatManwon(_repairManwon.round()),
            onChanged: (v) => setState(() => _repairManwon = v),
          ),
          Text(
            '취득세 가정',
            style: TextStyle(
              fontSize: 12,
              color: AppTheme.ink.withValues(alpha: 0.55),
            ),
          ),
          Slider(
            value: _taxRate.clamp(0.01, 0.045),
            min: 0.01,
            max: 0.045,
            divisions: 7,
            label: '${(_taxRate * 100).toStringAsFixed(1)}%',
            onChanged: (v) => setState(() => _taxRate = v),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 13,
                color: AppTheme.ink.withValues(alpha: 0.6),
              ),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

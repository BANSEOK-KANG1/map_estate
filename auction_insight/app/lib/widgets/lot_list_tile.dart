import 'package:flutter/material.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/utils/format.dart';

class LotListTile extends StatelessWidget {
  const LotListTile({super.key, required this.lot, this.onTap});

  final LotSummary lot;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final score = lot.scores?.total;
    final station = lot.nearestStation;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: lot.source == 'court'
                    ? AppTheme.slate.withValues(alpha: 0.12)
                    : const Color(0xFF3D6B4F).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                lot.source == 'court' ? Icons.gavel : Icons.storefront,
                color: lot.source == 'court'
                    ? AppTheme.slate
                    : const Color(0xFF3D6B4F),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      _miniChip(lot.sourceLabel),
                      _miniChip(lot.usage),
                      for (final h in lot.highlights.take(2)) _miniChip(h, accent: true),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    lot.title,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    [
                      if (lot.regionName != null) lot.regionName!,
                      if (lot.dong.isNotEmpty) lot.dong,
                      if (station != null && station.isNotEmpty)
                        '$station${lot.stationWalkMinutes != null ? " · 도보 ${lot.stationWalkMinutes}분" : ""}',
                    ].join(' · '),
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.ink.withValues(alpha: 0.55),
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Text(
                        '최저 ${formatManwon(lot.minBidManwon)}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '시세 ${formatPct(lot.scores?.discountVsMarket)}',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppTheme.ink.withValues(alpha: 0.65),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (score != null)
              Column(
                children: [
                  Text(
                    score.toStringAsFixed(0),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 18,
                      color: AppTheme.slate,
                    ),
                  ),
                  Text(
                    '점수',
                    style: TextStyle(
                      fontSize: 10,
                      color: AppTheme.ink.withValues(alpha: 0.45),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _miniChip(String text, {bool accent = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: accent ? AppTheme.amber.withValues(alpha: 0.14) : AppTheme.fog,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: accent ? FontWeight.w600 : FontWeight.w500,
          color: accent ? AppTheme.amber : AppTheme.ink,
        ),
      ),
    );
  }
}

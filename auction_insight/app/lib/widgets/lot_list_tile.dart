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
    final days = lot.daysLeft;
    final discApp = lot.scores?.discountVsAppraisal;
    final station = lot.nearestStation;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Thumb(lot: lot),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      if (days != null)
                        _miniChip(
                          days <= 0 ? '마감' : 'D-$days',
                          accent: days <= 3,
                          urgent: days <= 3,
                        ),
                      _miniChip(lot.sourceLabel),
                      if (lot.usage.isNotEmpty) _miniChip(lot.usage),
                      if (discApp != null && discApp >= 0.1)
                        _miniChip(
                          '감정 ${formatPct(discApp)}',
                          accent: true,
                        ),
                      for (final r in lot.riskFlags.take(2))
                        _miniChip(r, danger: true),
                      for (final h in lot.highlights
                          .where((e) => !e.startsWith('D-') && e != '마감')
                          .take(1))
                        _miniChip(h, accent: true),
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
                      if (lot.appraisalManwon != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          '감정 ${formatManwon(lot.appraisalManwon)}',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.ink.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                      if (lot.failCount > 0) ...[
                        const SizedBox(width: 8),
                        Text(
                          '유찰 ${lot.failCount}',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.ink.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            if (score != null)
              Padding(
                padding: const EdgeInsets.only(left: 6),
                child: Column(
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
              ),
          ],
        ),
      ),
    );
  }

  Widget _miniChip(
    String text, {
    bool accent = false,
    bool danger = false,
    bool urgent = false,
  }) {
    final Color bg;
    final Color fg;
    if (danger) {
      bg = const Color(0xFF8B4513).withValues(alpha: 0.12);
      fg = const Color(0xFF8B4513);
    } else if (urgent) {
      bg = AppTheme.amber.withValues(alpha: 0.2);
      fg = AppTheme.amber;
    } else if (accent) {
      bg = AppTheme.amber.withValues(alpha: 0.14);
      fg = AppTheme.amber;
    } else {
      bg = AppTheme.fog;
      fg = AppTheme.ink;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: fg,
        ),
      ),
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.lot});
  final LotSummary lot;

  @override
  Widget build(BuildContext context) {
    final url = lot.thumbnailUrl;
    final fallback = Container(
      width: 64,
      height: 64,
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
    );
    if (url == null || url.isEmpty) return fallback;
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: Image.network(
        url,
        width: 64,
        height: 64,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => fallback,
      ),
    );
  }
}

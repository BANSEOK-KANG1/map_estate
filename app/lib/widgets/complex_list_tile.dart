import 'package:flutter/material.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/theme.dart';
import 'package:map_estate_app/utils/format.dart';

class ComplexListTile extends StatelessWidget {
  const ComplexListTile({
    super.key,
    required this.item,
    required this.onTap,
  });

  final ComplexSummary item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final priceLabel = formatListingPrice(
      dealKind: item.dealKind,
      price: item.medianPriceManwon,
      monthly: item.medianMonthlyRentManwon,
    );
    final station = item.nearestStation == null
        ? null
        : '${item.nearestStation}역 도보 ${item.walkMinutes ?? '-'}분';

    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: AppTheme.line.withValues(alpha: 0.85)),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: 108,
                height: 108,
                child: item.thumbnailUrl == null
                    ? ColoredBox(
                        color: AppTheme.sand,
                        child: Icon(
                          Icons.home_work_outlined,
                          color: AppTheme.ink.withValues(alpha: 0.35),
                        ),
                      )
                    : Image.network(
                        item.thumbnailUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => ColoredBox(
                          color: AppTheme.sand,
                          child: Icon(
                            Icons.broken_image_outlined,
                            color: AppTheme.ink.withValues(alpha: 0.35),
                          ),
                        ),
                      ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          priceLabel,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -0.4,
                          ),
                        ),
                      ),
                      Text(
                        '${(item.scores?.total ?? 0).toStringAsFixed(0)}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          color: AppTheme.moss,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    item.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    [
                      item.housingTypeLabel,
                      if (item.facing != null) item.facing!,
                      formatAreaPyeong(
                        item.avgExclusiveArea,
                        item.avgExclusivePyeong,
                      ),
                    ].join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.62),
                      fontSize: 12,
                    ),
                  ),
                  if (station != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      station,
                      style: const TextStyle(
                        color: AppTheme.clay,
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 5,
                    runSpacing: 5,
                    children: [
                      _chip('전입 ${formatMoveIn(item.moveInOk)}'),
                      _chip('융자 ${formatLoan(item.loanManwon)}'),
                      if (item.roomCount != null)
                        _chip('${item.roomCount}룸'),
                      if (item.parking == true) _chip('주차'),
                      ...item.tags
                          .where((t) => t != item.facing)
                          .take(2)
                          .map(_chip),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: AppTheme.sand,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppTheme.line),
      ),
      child: Text(text, style: const TextStyle(fontSize: 11)),
    );
  }
}

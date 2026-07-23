import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/utils/format.dart';
import 'package:auction_insight_app/widgets/region_quick_bar.dart';
import 'package:auction_insight_app/widgets/segment_pills.dart';

class InsightsPanel extends ConsumerWidget {
  const InsightsPanel({super.key, required this.isDesktop});

  final bool isDesktop;

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insights = ref.watch(insightsProvider);
    final category = ref.watch(insightCategoryProvider);
    final filters = ref.watch(filtersProvider);
    final regions = ref.watch(regionsProvider).valueOrNull ?? [];
    final summary = regionSummaryLabel(regions, filters.regionCodes);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(
            isDesktop ? 14 : 16,
            0,
            isDesktop ? 14 : 16,
            8,
          ),
          child: SegmentPills(
            dense: true,
            selectedKey: category,
            options: const [
              ('전체', '전체'),
              ('재개발정비', '재개발·정비'),
              ('개발호재', '개발호재'),
            ],
            onSelected: (key) {
              ref.read(insightCategoryProvider.notifier).state = key;
            },
          ),
        ),
        Expanded(
          child: insights.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('불러오기 실패\n$e', textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () => ref.invalidate(insightsProvider),
                      child: const Text('다시 시도'),
                    ),
                  ],
                ),
              ),
            ),
            data: (result) {
              if (result.items.isEmpty) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '인사이트가 없습니다.\n설정에서 「호재 인사이트 갱신」을 눌러 주세요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppTheme.ink.withValues(alpha: 0.55),
                            height: 1.4,
                          ),
                        ),
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: () => ref.invalidate(insightsProvider),
                          child: const Text('다시 시도'),
                        ),
                      ],
                    ),
                  ),
                );
              }

              return DecoratedBox(
                decoration: BoxDecoration(
                  color: isDesktop
                      ? Colors.white.withValues(alpha: 0.55)
                      : Colors.transparent,
                  borderRadius:
                      isDesktop ? BorderRadius.circular(14) : null,
                  border: isDesktop
                      ? Border.all(color: AppTheme.line)
                      : null,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: EdgeInsets.fromLTRB(
                        isDesktop ? 14 : 16,
                        isDesktop ? 10 : 4,
                        isDesktop ? 14 : 16,
                        6,
                      ),
                      child: Row(
                        children: [
                          Text(
                            '${result.total}건',
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 15,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              summary,
                              textAlign: TextAlign.right,
                              style: TextStyle(
                                fontSize: 12,
                                color: AppTheme.ink.withValues(alpha: 0.45),
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        padding: EdgeInsets.fromLTRB(
                          isDesktop ? 12 : 16,
                          0,
                          isDesktop ? 12 : 16,
                          24,
                        ),
                        itemCount: result.items.length,
                        separatorBuilder: (_, _) => const Divider(height: 1),
                        itemBuilder: (context, i) {
                          final item = result.items[i];
                          return _InsightTile(
                            item: item,
                            onTap: item.sourceUrl.isEmpty
                                ? null
                                : () => _openUrl(item.sourceUrl),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _InsightTile extends StatelessWidget {
  const _InsightTile({required this.item, this.onTap});

  final MarketInsightItem item;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final loc = [
      item.sido,
      if (item.sgg.isNotEmpty) item.sgg,
    ].join(' · ');
    final dateLabel = formatDate(item.sortDate);
    final meta = [
      item.sourceLabel,
      if (item.publisher.isNotEmpty) item.publisher,
      if (dateLabel != '—') dateLabel,
    ].join(' · ');

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _CategoryChip(label: item.category),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    loc,
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.ink.withValues(alpha: 0.45),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (onTap != null)
                  Icon(
                    Icons.open_in_new,
                    size: 16,
                    color: AppTheme.ink.withValues(alpha: 0.35),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              item.title,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 15,
                height: 1.3,
              ),
            ),
            if (item.summary.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                item.summary,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 13,
                  height: 1.35,
                  color: AppTheme.ink.withValues(alpha: 0.65),
                ),
              ),
            ],
            const SizedBox(height: 6),
            Text(
              meta,
              style: TextStyle(
                fontSize: 11,
                color: AppTheme.ink.withValues(alpha: 0.4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final isRedevelop = label.contains('재개발');
    final color = isRedevelop ? AppTheme.slate : AppTheme.amber;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}

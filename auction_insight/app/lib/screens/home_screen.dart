import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/screens/filter_sheet.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/widgets/lot_list_tile.dart';
import 'package:auction_insight_app/widgets/lot_map.dart';
import 'package:auction_insight_app/widgets/region_quick_bar.dart';
import 'package:auction_insight_app/widgets/segment_pills.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  static const _desktopBreakpoint = 800.0;
  static const _listPanelWidth = 420.0;

  void _openLot(BuildContext context, LotSummary lot) {
    context.push(
      '/lot/${lot.id}?source=${Uri.encodeComponent(lot.source)}&ext=${Uri.encodeComponent(lot.externalId)}',
    );
  }

  Future<void> _setHomeMode(WidgetRef ref, String key) async {
    if (key == 'real') {
      final uri = Uri.parse('https://map-estate-uz70.onrender.com');
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      return;
    }
    ref.read(homeModeProvider.notifier).state = key;
    final cur = ref.read(filtersProvider);
    ref.read(filtersProvider.notifier).state = cur.copyWith(
      sources: key == 'court' ? ['court'] : ['onbid'],
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final search = ref.watch(searchProvider);
    final filters = ref.watch(filtersProvider);
    final regions = ref.watch(regionsProvider).valueOrNull ?? [];
    final activeSido = activeSidoFromFilters(regions, filters.regionCodes);
    final summary = regionSummaryLabel(regions, filters.regionCodes);
    final width = MediaQuery.sizeOf(context).width;
    final isDesktop = width >= _desktopBreakpoint;
    final homeMode = ref.watch(homeModeProvider);

    final extraFilters = <Widget>[
      for (final u in filters.usages)
        _ActiveFilterChip(label: usageChipLabel(u)),
      if (filters.minFailCount != null)
        _ActiveFilterChip(label: '유찰 ${filters.minFailCount}+'),
    ];

    return Scaffold(
      floatingActionButton: homeMode == 'real'
          ? null
          : FloatingActionButton.extended(
              onPressed: () => context.push('/analysis/new?source=$homeMode'),
              icon: const Icon(Icons.science_outlined),
              label: const Text('분석 등록'),
            ),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFF0F3F7),
              Color(0xFFE8EEF5),
              Color(0xFFF5F1EA),
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 4, 0),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        '경공매 인사이트',
                        style: TextStyle(
                          fontSize: isDesktop ? 20 : 18,
                          fontWeight: FontWeight.w800,
                          color: AppTheme.ink,
                          letterSpacing: -0.4,
                        ),
                      ),
                    ),
                    IconButton(
                      tooltip: '필터',
                      visualDensity: VisualDensity.compact,
                      onPressed: () => showFilterSheet(context, ref),
                      icon: Badge(
                        isLabelVisible: extraFilters.isNotEmpty,
                        smallSize: 8,
                        child: const Icon(Icons.tune, size: 22),
                      ),
                    ),
                    IconButton(
                      tooltip: '초보 가이드',
                      visualDensity: VisualDensity.compact,
                      onPressed: () => context.push('/guide'),
                      icon: const Icon(Icons.menu_book_outlined, size: 22),
                    ),
                    IconButton(
                      tooltip: '설정',
                      visualDensity: VisualDensity.compact,
                      onPressed: () => context.push('/settings'),
                      icon: const Icon(Icons.settings_outlined, size: 22),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (isDesktop)
                      Row(
                        children: [
                          SegmentPills(
                            selectedKey: homeMode,
                            options: const [
                              ('real', '실거래'),
                              ('court', '법원'),
                              ('onbid', '온비드'),
                            ],
                            onSelected: (k) => _setHomeMode(ref, k),
                          ),
                          Container(
                            width: 1,
                            height: 22,
                            margin: const EdgeInsets.symmetric(horizontal: 12),
                            color: AppTheme.line,
                          ),
                          const Expanded(
                            child: RegionQuickBar(sidoOnly: true),
                          ),
                        ],
                      )
                    else ...[
                      SegmentPills(
                        selectedKey: homeMode,
                        options: const [
                          ('real', '실거래'),
                          ('court', '법원'),
                          ('onbid', '온비드'),
                        ],
                        onSelected: (k) => _setHomeMode(ref, k),
                      ),
                      const SizedBox(height: 8),
                      const RegionQuickBar(sidoOnly: true),
                    ],
                    // District chips only when a sido is active
                    if (activeSido != null) ...[
                      const SizedBox(height: 8),
                      const RegionDistrictBar(),
                    ],
                  ],
                ),
              ),
              if (extraFilters.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: extraFilters,
                  ),
                ),
              const SizedBox(height: 10),
              Expanded(
                child: search.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('불러오기 실패\n$e', textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: () => ref.invalidate(searchProvider),
                            child: const Text('다시 시도'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  data: (result) {
                    final map = LotMap(
                      items: result.items,
                      height: isDesktop ? 320 : 300,
                      expand: isDesktop,
                      sidoPreset: activeSido,
                      onTapLot: (lot) => _openLot(context, lot),
                    );

                    final listHeader = Padding(
                      padding: EdgeInsets.fromLTRB(
                        isDesktop ? 14 : 16,
                        isDesktop ? 10 : 8,
                        isDesktop ? 14 : 16,
                        6,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
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
                          const SizedBox(height: 8),
                          SegmentPills(
                            dense: true,
                            selectedKey: filters.sort,
                            options: const [
                              ('score', '추천순'),
                              ('deadline', '마감임박'),
                              ('discount', '할인율'),
                            ],
                            onSelected: (key) {
                              ref.read(filtersProvider.notifier).state =
                                  filters.copyWith(sort: key);
                            },
                          ),
                        ],
                      ),
                    );

                    final list = ListView.separated(
                      padding: EdgeInsets.fromLTRB(
                        isDesktop ? 12 : 16,
                        0,
                        isDesktop ? 12 : 16,
                        24,
                      ),
                      itemCount: result.items.length,
                      separatorBuilder: (_, _) => const Divider(height: 1),
                      itemBuilder: (context, i) {
                        final lot = result.items[i];
                        return LotListTile(
                          lot: lot,
                          onTap: () => _openLot(context, lot),
                        );
                      },
                    );

                    if (isDesktop) {
                      return Padding(
                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              flex: 3,
                              child: DecoratedBox(
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: AppTheme.line),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(14),
                                  child: map,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            SizedBox(
                              width: _listPanelWidth,
                              child: DecoratedBox(
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.55),
                                  borderRadius: BorderRadius.circular(14),
                                  border: Border.all(color: AppTheme.line),
                                ),
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    listHeader,
                                    Expanded(child: list),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }

                    return Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: map,
                        ),
                        listHeader,
                        Expanded(child: list),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActiveFilterChip extends StatelessWidget {
  const _ActiveFilterChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppTheme.slate.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.slate.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: AppTheme.slate,
        ),
      ),
    );
  }
}

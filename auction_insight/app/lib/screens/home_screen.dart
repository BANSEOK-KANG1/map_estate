import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/screens/filter_sheet.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/widgets/lot_list_tile.dart';
import 'package:auction_insight_app/widgets/lot_map.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final search = ref.watch(searchProvider);
    final filters = ref.watch(filtersProvider);

    return Scaffold(
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
                padding: const EdgeInsets.fromLTRB(20, 12, 8, 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Auction Insight',
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                              color: AppTheme.ink,
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '경·공매 · 상권 · 시가 비교',
                            style: TextStyle(
                              fontSize: 13,
                              color: AppTheme.ink.withValues(alpha: 0.55),
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: '필터',
                      onPressed: () => showFilterSheet(context, ref),
                      icon: const Icon(Icons.tune),
                    ),
                    IconButton(
                      tooltip: '설정',
                      onPressed: () => context.push('/settings'),
                      icon: const Icon(Icons.settings_outlined),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Wrap(
                  spacing: 6,
                  children: [
                    for (final s in filters.sources)
                      Chip(
                        label: Text(s == 'court' ? '경매' : '공매'),
                        visualDensity: VisualDensity.compact,
                      ),
                    for (final u in filters.usages)
                      Chip(
                        label: Text(u),
                        visualDensity: VisualDensity.compact,
                      ),
                    if (filters.minFailCount != null)
                      Chip(
                        label: Text('유찰 ${filters.minFailCount}+'),
                        visualDensity: VisualDensity.compact,
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: search.when(
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
                            onPressed: () => ref.invalidate(searchProvider),
                            child: const Text('다시 시도'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  data: (result) {
                    return Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: LotMap(
                            items: result.items,
                            height: 240,
                            onTapLot: (lot) => context.push(
                              '/lot/${lot.id}?source=${Uri.encodeComponent(lot.source)}&ext=${Uri.encodeComponent(lot.externalId)}',
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
                          child: Row(
                            children: [
                              Text(
                                '${result.total}건',
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              const Spacer(),
                              Text(
                                '서울·경기·인천',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppTheme.ink.withValues(alpha: 0.45),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: ListView.separated(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                            itemCount: result.items.length,
                            separatorBuilder: (_, _) => const Divider(height: 1),
                            itemBuilder: (context, i) {
                              final lot = result.items[i];
                              return LotListTile(
                                lot: lot,
                                onTap: () => context.push(
                                  '/lot/${lot.id}?source=${Uri.encodeComponent(lot.source)}&ext=${Uri.encodeComponent(lot.externalId)}',
                                ),
                              );
                            },
                          ),
                        ),
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

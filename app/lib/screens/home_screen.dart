import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/providers/providers.dart';
import 'package:map_estate_app/screens/filter_sheet.dart';
import 'package:map_estate_app/theme.dart';
import 'package:map_estate_app/utils/format.dart';
import 'package:map_estate_app/widgets/complex_list_tile.dart';
import 'package:map_estate_app/widgets/complex_map.dart';
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final search = ref.watch(searchProvider);
    final prefs = ref.watch(prefsProvider);
    final filters = ref.watch(filtersProvider);

    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFF7F2E9),
              Color(0xFFE8EFEA),
              Color(0xFFF3EFE8),
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
                            'Map Estate',
                            style: Theme.of(context)
                                .textTheme
                                .headlineSmall
                                ?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: -0.5,
                                ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '원룸·다가구 · 실거래+호가 한눈에',
                            style: TextStyle(
                              color: AppTheme.ink.withValues(alpha: 0.62),
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: '조건',
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
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      ChoiceChip(
                        label: const Text('실거래'),
                        selected: true,
                        onSelected: (_) {},
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('법원경매'),
                        selected: false,
                        onSelected: (_) async {
                          await launchUrl(
                            Uri.parse('https://map.measuremkt.com'),
                            mode: LaunchMode.externalApplication,
                          );
                        },
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('온비드공매'),
                        selected: false,
                        onSelected: (_) async {
                          await launchUrl(
                            Uri.parse('https://map.measuremkt.com'),
                            mode: LaunchMode.externalApplication,
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(
                height: 42,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  children: [
                    _QuickChip(
                      label: '전월세',
                      selected: filters.dealKind == 'rent',
                      onTap: () => _patch(
                        ref,
                        filters.copyWith(dealKind: 'rent'),
                      ),
                    ),
                    _QuickChip(
                      label: '매매',
                      selected: filters.dealKind == 'sale',
                      onTap: () => _patch(
                        ref,
                        filters.copyWith(dealKind: 'sale'),
                      ),
                    ),
                    _QuickChip(
                      label: '역세권5분',
                      selected: filters.maxWalkMinutes == 5,
                      onTap: () => _patch(
                        ref,
                        filters.maxWalkMinutes == 5
                            ? filters.copyWith(clearMaxWalk: true)
                            : filters.copyWith(maxWalkMinutes: 5),
                      ),
                    ),
                    _QuickChip(
                      label: '보증금1천만↓',
                      selected: filters.priceMax == 1000,
                      onTap: () => _patch(
                        ref,
                        filters.copyWith(
                          priceMin: 0,
                          priceMax: filters.priceMax == 1000 ? 10000 : 1000,
                        ),
                      ),
                    ),
                    _QuickChip(
                      label: '월세60↓',
                      selected: filters.monthlyRentMax == 60,
                      onTap: () => _patch(
                        ref,
                        filters.monthlyRentMax == 60
                            ? filters.copyWith(clearMonthlyRentMax: true)
                            : filters.copyWith(monthlyRentMax: 60),
                      ),
                    ),
                    _QuickChip(
                      label: '신축2018↑',
                      selected: filters.buildYearMin == 2018,
                      onTap: () => _patch(
                        ref,
                        filters.buildYearMin == 2018
                            ? filters.copyWith(clearBuildYearMin: true)
                            : filters.copyWith(buildYearMin: 2018),
                      ),
                    ),
                    _QuickChip(
                      label: '오피스텔만',
                      selected: filters.housingTypes?.length == 1 &&
                          filters.housingTypes!.contains('officetel'),
                      onTap: () => _patch(
                        ref,
                        filters.copyWith(
                          housingTypes: filters.housingTypes?.length == 1
                              ? ['officetel', 'villa', 'multi']
                              : ['officetel'],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
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
                          Text('$e', textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(
                            onPressed: () => ref.invalidate(searchProvider),
                            child: const Text('다시 시도'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  data: (data) {
                    return LayoutBuilder(
                      builder: (context, constraints) {
                        final wide = constraints.maxWidth >= 960;
                        final map = ComplexMap(
                          items: data.items,
                          workLat: prefs.workLat,
                          workLng: prefs.workLng,
                          height: wide ? constraints.maxHeight : 220,
                          onTapComplex: (c) =>
                              context.push('/complex/${c.id}'),
                        );
                        final list = Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Padding(
                              padding:
                                  const EdgeInsets.fromLTRB(16, 8, 16, 4),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${data.total}개 매물',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w800,
                                      fontSize: 14,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 10,
                                      vertical: 8,
                                    ),
                                    decoration: BoxDecoration(
                                      color: (data.isMolit
                                              ? AppTheme.moss
                                              : AppTheme.clay)
                                          .withValues(alpha: 0.1),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      data.isMolit
                                          ? '국토부 실거래 기준 ${formatYm(data.dataAsOf)}'
                                              ' (${data.tradeFrom ?? '-'} ~ ${data.tradeTo ?? '-'})\n'
                                              '가격·면적·층·거래일은 신고 실거래. '
                                              '향·전입·융자·사진·연락처는 데모일 수 있음. '
                                              '공개 1~2개월 지연 가능.'
                                          : '지금은 데모 시드입니다 (국토부 원본 아님). '
                                              '기간 ${data.tradeFrom ?? '-'} ~ ${data.tradeTo ?? '-'}.\n'
                                              '진짜 실거래: 설정 → MOLIT 키 안내 후 실거래 수집.',
                                      style: TextStyle(
                                        fontSize: 11.5,
                                        height: 1.35,
                                        color: AppTheme.ink
                                            .withValues(alpha: 0.75),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Expanded(
                              child: ListView.builder(
                                itemCount: data.items.length,
                                itemBuilder: (context, i) {
                                  final item = data.items[i];
                                  return ComplexListTile(
                                    item: item,
                                    onTap: () =>
                                        context.push('/complex/${item.id}'),
                                  );
                                },
                              ),
                            ),
                          ],
                        );
                        if (wide) {
                          return Row(
                            children: [
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: map,
                                ),
                              ),
                              SizedBox(width: 440, child: list),
                            ],
                          );
                        }
                        return Column(
                          children: [
                            Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 12),
                              child: map,
                            ),
                            Expanded(child: list),
                          ],
                        );
                      },
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

  void _patch(WidgetRef ref, SearchFilters next) {
    ref.read(filtersProvider.notifier).state = next;
  }
}

class _QuickChip extends StatelessWidget {
  const _QuickChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
      ),
    );
  }
}

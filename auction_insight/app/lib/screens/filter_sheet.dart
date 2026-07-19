import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';

const kUsageOptions = <String>[
  '아파트',
  '오피스텔',
  '다가구',
  '다세대',
  '근린생활시설',
  '업무시설',
  '단독주택',
  '토지',
];

const kSidoOptions = <String>['서울특별시', '경기도', '인천광역시'];

Future<void> showFilterSheet(BuildContext context, WidgetRef ref) async {
  final current = ref.read(filtersProvider);
  var sources = List<String>.from(current.sources);
  var usages = List<String>.from(current.usages);
  var minFail = current.minFailCount;
  var maxPrice = current.maxPriceManwon;
  final regionsAsync = ref.read(regionsProvider);
  final regions = regionsAsync.valueOrNull ?? [];
  var selectedRegions = List<String>.from(current.regionCodes);

  // Infer sido tabs from already-selected districts; default Seoul first.
  var sidoFilter = <String>{};
  for (final code in selectedRegions) {
    final hit = regions.where((r) => r.code == code);
    if (hit.isNotEmpty) sidoFilter.add(hit.first.sido);
  }
  if (sidoFilter.isEmpty) sidoFilter = {'서울특별시'};

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppTheme.mist,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder: (ctx) {
      return StatefulBuilder(
        builder: (ctx, setState) {
          final visibleRegions = regions
              .where((r) => sidoFilter.contains(r.sido))
              .toList();

          return Padding(
            padding: EdgeInsets.only(
              left: 20,
              right: 20,
              top: 16,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
            ),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    '필터',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 16),
                  const Text('매각 구분', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      FilterChip(
                        label: const Text('경매'),
                        selected: sources.contains('court'),
                        onSelected: (v) {
                          setState(() {
                            if (v) {
                              sources = [...sources, 'court'];
                            } else {
                              sources = sources.where((e) => e != 'court').toList();
                            }
                            if (sources.isEmpty) sources = ['court', 'onbid'];
                          });
                        },
                      ),
                      FilterChip(
                        label: const Text('공매'),
                        selected: sources.contains('onbid'),
                        onSelected: (v) {
                          setState(() {
                            if (v) {
                              sources = [...sources, 'onbid'];
                            } else {
                              sources = sources.where((e) => e != 'onbid').toList();
                            }
                            if (sources.isEmpty) sources = ['court', 'onbid'];
                          });
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('건물 유형', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(
                    '여러 개 선택 가능 · 비우면 전체',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.ink.withValues(alpha: 0.45),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      for (final u in kUsageOptions)
                        FilterChip(
                          label: Text(u),
                          selected: usages.contains(u),
                          onSelected: (v) {
                            setState(() {
                              if (v) {
                                usages = [...usages, u];
                              } else {
                                usages = usages.where((e) => e != u).toList();
                              }
                            });
                          },
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('유찰', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('전체'),
                        selected: minFail == null,
                        onSelected: (_) => setState(() => minFail = null),
                      ),
                      ChoiceChip(
                        label: const Text('1회+'),
                        selected: minFail == 1,
                        onSelected: (_) => setState(() => minFail = 1),
                      ),
                      ChoiceChip(
                        label: const Text('2회+'),
                        selected: minFail == 2,
                        onSelected: (_) => setState(() => minFail = 2),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text('최고가 (만원)', style: TextStyle(fontWeight: FontWeight.w600)),
                  Slider(
                    value: (maxPrice ?? 300000).toDouble().clamp(5000, 300000),
                    min: 5000,
                    max: 300000,
                    divisions: 59,
                    label: '${((maxPrice ?? 300000) / 10000).toStringAsFixed(0)}억',
                    onChanged: (v) => setState(() => maxPrice = v.round()),
                  ),
                  if (regions.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    const Text('지역', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final sido in kSidoOptions)
                          FilterChip(
                            label: Text(
                              sido.replaceAll('특별시', '').replaceAll('광역시', '').replaceAll('도', ''),
                            ),
                            selected: sidoFilter.contains(sido),
                            onSelected: (v) {
                              setState(() {
                                final next = {...sidoFilter};
                                if (v) {
                                  next.add(sido);
                                } else {
                                  next.remove(sido);
                                  // Keep at least one sido tab visible
                                  if (next.isEmpty) next.add(sido);
                                  // Drop district selections outside visible sidos
                                  selectedRegions = selectedRegions
                                      .where((code) {
                                        final hit = regions.where((r) => r.code == code);
                                        return hit.isNotEmpty && next.contains(hit.first.sido);
                                      })
                                      .toList();
                                }
                                sidoFilter = next;
                              });
                            },
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Text(
                          '시·군·구 (${selectedRegions.length}개 선택)',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.ink.withValues(alpha: 0.55),
                          ),
                        ),
                        const Spacer(),
                        TextButton(
                          onPressed: () => setState(() => selectedRegions = []),
                          child: const Text('지역 초기화', style: TextStyle(fontSize: 12)),
                        ),
                      ],
                    ),
                    SizedBox(
                      height: 220,
                      child: ListView.builder(
                        itemCount: visibleRegions.length,
                        itemBuilder: (_, i) {
                          final r = visibleRegions[i];
                          final selected = selectedRegions.contains(r.code);
                          return CheckboxListTile(
                            dense: true,
                            title: Text(r.name, style: const TextStyle(fontSize: 13)),
                            value: selected,
                            onChanged: (v) {
                              setState(() {
                                if (v == true) {
                                  selectedRegions = [...selectedRegions, r.code];
                                } else {
                                  selectedRegions =
                                      selectedRegions.where((c) => c != r.code).toList();
                                }
                              });
                            },
                          );
                        },
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () {
                      ref.read(filtersProvider.notifier).state = SearchFilters(
                        sources: sources.toSet().toList(),
                        regionCodes: selectedRegions,
                        usages: usages.toSet().toList(),
                        minFailCount: minFail,
                        maxPriceManwon: maxPrice,
                        status: 'active',
                      );
                      Navigator.pop(ctx);
                    },
                    child: const Text('적용'),
                  ),
                ],
              ),
            ),
          );
        },
      );
    },
  );
}

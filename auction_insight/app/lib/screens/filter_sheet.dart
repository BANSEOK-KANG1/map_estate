import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';

Future<void> showFilterSheet(BuildContext context, WidgetRef ref) async {
  final current = ref.read(filtersProvider);
  var sources = List<String>.from(current.sources);
  var minFail = current.minFailCount;
  var maxPrice = current.maxPriceManwon;
  final regionsAsync = ref.read(regionsProvider);
  final regions = regionsAsync.valueOrNull ?? [];
  var selectedRegions = List<String>.from(current.regionCodes);

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
                  const Text('유형', style: TextStyle(fontWeight: FontWeight.w600)),
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
                    const Text('지역 (선택)', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 160,
                      child: ListView(
                        children: regions.take(40).map((r) {
                          final selected = selectedRegions.contains(r.code);
                          return CheckboxListTile(
                            dense: true,
                            title: Text('${r.sido} ${r.name}', style: const TextStyle(fontSize: 13)),
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
                        }).toList(),
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () {
                      ref.read(filtersProvider.notifier).state = SearchFilters(
                        sources: sources.toSet().toList(),
                        regionCodes: selectedRegions,
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

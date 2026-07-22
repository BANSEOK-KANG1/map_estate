import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';

const kSidoQuickOptions = <(String? code, String label)>[
  (null, '전체'),
  ('서울특별시', '서울'),
  ('경기도', '경기'),
  ('인천광역시', '인천'),
];

/// Infer which sido tab is active from selected region codes.
String? activeSidoFromFilters(List<Region> regions, List<String> regionCodes) {
  if (regionCodes.isEmpty) return null;
  final sidos = <String>{};
  for (final code in regionCodes) {
    for (final r in regions) {
      if (r.code == code) {
        sidos.add(r.sido);
        break;
      }
    }
  }
  if (sidos.length == 1) return sidos.first;
  return null;
}

String regionSummaryLabel(List<Region> regions, List<String> regionCodes) {
  if (regionCodes.isEmpty) return '서울·경기·인천';
  final selected = regions.where((r) => regionCodes.contains(r.code)).toList();
  if (selected.isEmpty) return '지역 선택';

  final bySido = <String, List<Region>>{};
  for (final r in selected) {
    bySido.putIfAbsent(r.sido, () => []).add(r);
  }

  String shortSido(String s) =>
      s.replaceAll('특별시', '').replaceAll('광역시', '').replaceAll('도', '');

  if (bySido.length == 1) {
    final entry = bySido.entries.first;
    final allInSido = regions.where((r) => r.sido == entry.key).length;
    if (entry.value.length >= allInSido) {
      return '${shortSido(entry.key)} 전체';
    }
    if (entry.value.length == 1) {
      return '${shortSido(entry.key)} · ${entry.value.first.name}';
    }
    if (entry.value.length <= 3) {
      return '${shortSido(entry.key)} · ${entry.value.map((e) => e.name).join(', ')}';
    }
    return '${shortSido(entry.key)} · ${entry.value.length}개 구·시';
  }
  return '${selected.length}개 지역';
}

class RegionQuickBar extends ConsumerWidget {
  const RegionQuickBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(filtersProvider);
    final regionsAsync = ref.watch(regionsProvider);
    final regions = regionsAsync.valueOrNull ?? [];
    final activeSido = activeSidoFromFilters(regions, filters.regionCodes);

    final districtPool = activeSido == null
        ? const <Region>[]
        : regions.where((r) => r.sido == activeSido).toList();

    final allCodesForSido = districtPool.map((r) => r.code).toSet();
    final selectedInSido =
        filters.regionCodes.where(allCodesForSido.contains).toSet();
    final wholeSidoSelected = activeSido != null &&
        selectedInSido.length == allCodesForSido.length &&
        allCodesForSido.isNotEmpty;

    void applyRegionCodes(List<String> codes) {
      ref.read(filtersProvider.notifier).state =
          filters.copyWith(regionCodes: codes);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
          child: Text(
            '지역 빠른 선택  ·  전체 / 서울 / 경기 / 인천',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: const Color(0xFFC47B2B),
              letterSpacing: 0.2,
            ),
          ),
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              for (final (code, label) in kSidoQuickOptions) ...[
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(label),
                    selected: activeSido == code,
                    onSelected: (_) {
                      if (code == null) {
                        applyRegionCodes([]);
                      } else {
                        final codes = regions
                            .where((r) => r.sido == code)
                            .map((r) => r.code)
                            .toList();
                        applyRegionCodes(codes);
                      }
                    },
                  ),
                ),
              ],
            ],
          ),
        ),
        if (districtPool.isNotEmpty) ...[
          const SizedBox(height: 8),
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: FilterChip(
                    label: const Text('구시 전체'),
                    selected: wholeSidoSelected,
                    visualDensity: VisualDensity.compact,
                    onSelected: (_) {
                      applyRegionCodes(
                        districtPool.map((r) => r.code).toList(),
                      );
                    },
                  ),
                ),
                for (final r in districtPool)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: FilterChip(
                      label: Text(r.name),
                      selected: !wholeSidoSelected &&
                          filters.regionCodes.contains(r.code),
                      visualDensity: VisualDensity.compact,
                      onSelected: (v) {
                        var next = List<String>.from(filters.regionCodes);
                        if (wholeSidoSelected) {
                          next = [];
                        }
                        next = next
                            .where((c) => allCodesForSido.contains(c))
                            .toList();
                        if (v) {
                          if (!next.contains(r.code)) next = [...next, r.code];
                        } else {
                          next = next.where((c) => c != r.code).toList();
                        }
                        if (next.isEmpty) {
                          next = districtPool.map((e) => e.code).toList();
                        }
                        applyRegionCodes(next);
                      },
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/widgets/segment_pills.dart';

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

String _shortDistrictName(String name) {
  return name
      .replaceFirst(RegExp(r'^수원시\s*'), '수원 ')
      .replaceFirst(RegExp(r'^성남시\s*'), '성남 ')
      .replaceFirst(RegExp(r'^안양시\s*'), '안양 ')
      .replaceFirst(RegExp(r'^부천시\s*'), '부천 ')
      .replaceFirst(RegExp(r'^안산시\s*'), '안산 ')
      .replaceFirst(RegExp(r'^고양시\s*'), '고양 ')
      .replaceFirst(RegExp(r'^용인시\s*'), '용인 ')
      .replaceFirst(RegExp(r'^화성시\s*'), '화성 ');
}

class RegionQuickBar extends ConsumerWidget {
  const RegionQuickBar({super.key, this.sidoOnly = false});

  /// Sido pills only (전체/서울/경기/인천). Pair with [RegionDistrictBar] for 구·시.
  final bool sidoOnly;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(filtersProvider);
    final regions = ref.watch(regionsProvider).valueOrNull ?? [];
    final activeSido = activeSidoFromFilters(regions, filters.regionCodes);

    void applyRegionCodes(List<String> codes) {
      ref.read(filtersProvider.notifier).state =
          filters.copyWith(regionCodes: codes);
    }

    final sidoPills = SegmentPills(
      dense: true,
      selectedKey: activeSido ?? 'all',
      options: [
        for (final (code, label) in kSidoQuickOptions) (code ?? 'all', label),
      ],
      onSelected: (key) {
        if (key == 'all') {
          applyRegionCodes([]);
          return;
        }
        final codes =
            regions.where((r) => r.sido == key).map((r) => r.code).toList();
        applyRegionCodes(codes);
      },
    );

    if (sidoOnly) return sidoPills;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        sidoPills,
        const SizedBox(height: 8),
        const RegionDistrictBar(),
      ],
    );
  }
}

/// Horizontal 구·시 chips for the active sido (hidden when 전체).
class RegionDistrictBar extends ConsumerWidget {
  const RegionDistrictBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(filtersProvider);
    final regions = ref.watch(regionsProvider).valueOrNull ?? [];
    final activeSido = activeSidoFromFilters(regions, filters.regionCodes);
    if (activeSido == null) return const SizedBox.shrink();

    final districtPool = regions.where((r) => r.sido == activeSido).toList();
    if (districtPool.isEmpty) return const SizedBox.shrink();

    final allCodesForSido = districtPool.map((r) => r.code).toSet();
    final selectedInSido =
        filters.regionCodes.where(allCodesForSido.contains).toSet();
    final wholeSidoSelected = selectedInSido.length == allCodesForSido.length &&
        allCodesForSido.isNotEmpty;

    void applyRegionCodes(List<String> codes) {
      ref.read(filtersProvider.notifier).state =
          filters.copyWith(regionCodes: codes);
    }

    return SizedBox(
      height: 32,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          _DistrictChip(
            label: '구·시 전체',
            selected: wholeSidoSelected,
            onTap: () {
              applyRegionCodes(districtPool.map((r) => r.code).toList());
            },
          ),
          for (final r in districtPool) ...[
            const SizedBox(width: 6),
            _DistrictChip(
              label: _shortDistrictName(r.name),
              selected:
                  !wholeSidoSelected && filters.regionCodes.contains(r.code),
              onTap: () {
                var next = List<String>.from(filters.regionCodes);
                if (wholeSidoSelected) {
                  next = [];
                }
                next =
                    next.where((c) => allCodesForSido.contains(c)).toList();
                final isOn = next.contains(r.code);
                if (isOn) {
                  next = next.where((c) => c != r.code).toList();
                } else {
                  next = [...next, r.code];
                }
                if (next.isEmpty) {
                  next = districtPool.map((e) => e.code).toList();
                }
                applyRegionCodes(next);
              },
            ),
          ],
        ],
      ),
    );
  }
}

class _DistrictChip extends StatelessWidget {
  const _DistrictChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected
          ? AppTheme.amber.withValues(alpha: 0.18)
          : Colors.white.withValues(alpha: 0.55),
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: selected
                  ? AppTheme.amber.withValues(alpha: 0.55)
                  : AppTheme.line.withValues(alpha: 0.8),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected
                  ? AppTheme.amber
                  : AppTheme.ink.withValues(alpha: 0.65),
            ),
          ),
        ),
      ),
    );
  }
}

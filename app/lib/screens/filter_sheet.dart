import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:map_estate_app/config.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/providers/providers.dart';
import 'package:map_estate_app/theme.dart';

Future<void> showFilterSheet(BuildContext context, WidgetRef ref) async {
  final regions = await ref.read(regionsProvider.future);
  final stations = await _fetchStations();
  if (!context.mounted) return;
  final current = ref.read(filtersProvider);

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppTheme.mist,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
    ),
    builder: (ctx) => _FilterBody(
      regions: regions,
      stations: stations,
      initial: current,
    ),
  );
}

Future<List<Map<String, dynamic>>> _fetchStations() async {
  try {
    final res = await Dio().get('${AppConfig.apiBaseUrl}/api/demo/stations');
    return (res.data as List).cast<Map<String, dynamic>>();
  } catch (_) {
    return [];
  }
}

const _housingOptions = [
  ('officetel', '오피스텔'),
  ('villa', '빌라·다세대'),
  ('multi', '단독·다가구'),
];

const _depositPresets = [
  (null, null, '전체'),
  (0, 500, '보 500만↓'),
  (0, 1000, '보 1천만↓'),
  (0, 3000, '보 3천만↓'),
  (0, 10000, '보 1억↓'),
];

const _monthlyPresets = [
  (null, '월세 전체'),
  (40, '월 40↓'),
  (60, '월 60↓'),
  (80, '월 80↓'),
  (100, '월 100↓'),
];

class _FilterBody extends ConsumerStatefulWidget {
  const _FilterBody({
    required this.regions,
    required this.stations,
    required this.initial,
  });

  final List<Region> regions;
  final List<Map<String, dynamic>> stations;
  final SearchFilters initial;

  @override
  ConsumerState<_FilterBody> createState() => _FilterBodyState();
}

class _FilterBodyState extends ConsumerState<_FilterBody> {
  String? regionCode;
  late final TextEditingController queryCtrl;
  late Set<String> housingTypes;
  String? dealKind;
  late RangeValues priceRange;
  late RangeValues areaRange;
  int? monthlyRentMax;
  int? buildYearMin;
  String? stationName;
  int? maxWalk;
  late String sortBy;
  late double maxCommute;
  late bool useCommute;

  @override
  void initState() {
    super.initState();
    final i = widget.initial;
    regionCode = i.regionCode;
    queryCtrl = TextEditingController(text: i.query ?? '');
    housingTypes = {...(i.housingTypes ?? ['officetel', 'villa', 'multi'])};
    dealKind = i.dealKind ?? 'rent';
    priceRange = RangeValues(
      (i.priceMin ?? 0).toDouble(),
      (i.priceMax ?? 10000).toDouble(),
    );
    areaRange = RangeValues(i.areaMin ?? 15, i.areaMax ?? 45);
    monthlyRentMax = i.monthlyRentMax;
    buildYearMin = i.buildYearMin;
    stationName = i.stationName;
    maxWalk = i.maxWalkMinutes;
    sortBy = i.sortBy;
    maxCommute = i.maxCommuteMinutes ?? 60;
    useCommute = i.maxCommuteMinutes != null;
  }

  @override
  void dispose() {
    queryCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.paddingOf(context).bottom;
    final isRent = dealKind != 'sale';
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 12, 20, 16 + bottom),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 4,
                decoration: BoxDecoration(
                  color: AppTheme.line,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
            ),
            const SizedBox(height: 14),
            const Text(
              '상세 조건',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 14),
            const Text('정렬', style: TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              children: [
                ('score', '추천순'),
                ('price_asc', '가격↑'),
                ('price_desc', '가격↓'),
                ('walk', '역가까운순'),
                ('recent', '거래활발'),
                ('area_desc', '넓은순'),
              ].map((e) {
                return ChoiceChip(
                  label: Text(e.$2),
                  selected: sortBy == e.$1,
                  onSelected: (_) => setState(() => sortBy = e.$1),
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'rent', label: Text('전월세')),
                ButtonSegment(value: 'sale', label: Text('매매')),
                ButtonSegment(value: 'all', label: Text('전체')),
              ],
              selected: {dealKind ?? 'all'},
              onSelectionChanged: (s) => setState(() {
                dealKind = s.first == 'all' ? null : s.first;
              }),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: _housingOptions.map((o) {
                final selected = housingTypes.contains(o.$1);
                return FilterChip(
                  label: Text(o.$2),
                  selected: selected,
                  onSelected: (v) => setState(() {
                    if (v) {
                      housingTypes.add(o.$1);
                    } else if (housingTypes.length > 1) {
                      housingTypes.remove(o.$1);
                    }
                  }),
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String?>(
              // ignore: deprecated_member_use
              value: regionCode,
              decoration: const InputDecoration(labelText: '구'),
              items: [
                const DropdownMenuItem(value: null, child: Text('전체 서울')),
                ...widget.regions.map(
                  (r) => DropdownMenuItem(value: r.code, child: Text(r.name)),
                ),
              ],
              onChanged: (v) => setState(() => regionCode = v),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String?>(
              // ignore: deprecated_member_use
              value: stationName,
              decoration: const InputDecoration(labelText: '지하철역'),
              items: [
                const DropdownMenuItem(value: null, child: Text('역 전체')),
                ...widget.stations.map(
                  (s) => DropdownMenuItem(
                    value: s['name'] as String,
                    child: Text('${s['name']} (${s['line']})'),
                  ),
                ),
              ],
              onChanged: (v) => setState(() => stationName = v),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: queryCtrl,
              decoration: const InputDecoration(
                labelText: '건물명 검색',
                hintText: '예: 스테이, 원룸',
              ),
            ),
            const SizedBox(height: 12),
            if (isRent) ...[
              const Text('보증금 빠른선택', style: TextStyle(fontWeight: FontWeight.w700)),
              Wrap(
                spacing: 8,
                children: _depositPresets.map((p) {
                  final sel = priceRange.start.round() == (p.$1 ?? 0) &&
                      priceRange.end.round() == (p.$2 ?? 10000);
                  return ChoiceChip(
                    label: Text(p.$3),
                    selected: sel,
                    onSelected: (_) => setState(() {
                      priceRange = RangeValues(
                        (p.$1 ?? 0).toDouble(),
                        (p.$2 ?? 10000).toDouble(),
                      );
                    }),
                  );
                }).toList(),
              ),
              const SizedBox(height: 8),
              const Text('월세 상한', style: TextStyle(fontWeight: FontWeight.w700)),
              Wrap(
                spacing: 8,
                children: _monthlyPresets.map((p) {
                  return ChoiceChip(
                    label: Text(p.$2),
                    selected: monthlyRentMax == p.$1,
                    onSelected: (_) => setState(() => monthlyRentMax = p.$1),
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              isRent
                  ? '보증금 ${priceRange.start.round()}~${priceRange.end.round()}만'
                  : '매매가 범위',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            RangeSlider(
              values: priceRange,
              min: 0,
              max: isRent ? 20000 : 80000,
              divisions: 40,
              onChanged: (v) => setState(() => priceRange = v),
            ),
            Text(
              '전용 ${areaRange.start.round()}~${areaRange.end.round()}㎡',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            RangeSlider(
              values: areaRange,
              min: 10,
              max: 80,
              divisions: 35,
              onChanged: (v) => setState(() => areaRange = v),
            ),
            const Text('도보거리', style: TextStyle(fontWeight: FontWeight.w700)),
            Wrap(
              spacing: 8,
              children: [
                (null, '전체'),
                (5, '5분↓'),
                (10, '10분↓'),
                (15, '15분↓'),
              ].map((e) {
                return ChoiceChip(
                  label: Text(e.$2),
                  selected: maxWalk == e.$1,
                  onSelected: (_) => setState(() => maxWalk = e.$1),
                );
              }).toList(),
            ),
            const SizedBox(height: 8),
            const Text('건축년도', style: TextStyle(fontWeight: FontWeight.w700)),
            Wrap(
              spacing: 8,
              children: [
                (null, '전체'),
                (2015, '2015↑'),
                (2018, '2018↑'),
                (2020, '2020↑'),
              ].map((e) {
                return ChoiceChip(
                  label: Text(e.$2),
                  selected: buildYearMin == e.$1,
                  onSelected: (_) => setState(() => buildYearMin = e.$1),
                );
              }).toList(),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('출퇴근 시간 제한'),
              subtitle: Text('최대 ${maxCommute.round()}분 (설정 출근지 기준)'),
              value: useCommute,
              onChanged: (v) => setState(() => useCommute = v),
            ),
            if (useCommute)
              Slider(
                value: maxCommute,
                min: 20,
                max: 90,
                divisions: 14,
                onChanged: (v) => setState(() => maxCommute = v),
              ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: () {
                ref.read(filtersProvider.notifier).state = SearchFilters(
                  regionCode: regionCode,
                  query: queryCtrl.text.trim().isEmpty
                      ? null
                      : queryCtrl.text.trim(),
                  housingTypes: housingTypes.toList(),
                  dealKind: dealKind,
                  priceMin: priceRange.start.round(),
                  priceMax: priceRange.end.round(),
                  monthlyRentMax: isRent ? monthlyRentMax : null,
                  areaMin: areaRange.start,
                  areaMax: areaRange.end,
                  buildYearMin: buildYearMin,
                  stationName: stationName,
                  maxWalkMinutes: maxWalk,
                  maxCommuteMinutes: useCommute ? maxCommute : null,
                  sortBy: sortBy,
                );
                Navigator.pop(context);
              },
              child: const Text('이 조건으로 보기'),
            ),
          ],
        ),
      ),
    );
  }
}

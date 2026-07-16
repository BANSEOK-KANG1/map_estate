import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import 'package:map_estate_app/providers/providers.dart';
import 'package:map_estate_app/theme.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late double wPrice;
  late double wInfra;
  late double wCommute;
  LatLng? pick;

  @override
  void initState() {
    super.initState();
    final p = ref.read(prefsProvider);
    wPrice = p.weightPrice;
    wInfra = p.weightInfra;
    wCommute = p.weightCommute;
    if (p.workLat != null && p.workLng != null) {
      pick = LatLng(p.workLat!, p.workLng!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final prefs = ref.watch(prefsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            '출근지',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 6),
          Text(
            prefs.workLabel.isEmpty
                ? '지도를 탭해 출근지를 지정하세요.'
                : prefs.workLabel,
            style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.65)),
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: SizedBox(
              height: 260,
              child: FlutterMap(
                options: MapOptions(
                  initialCenter:
                      pick ?? const LatLng(37.5665, 126.9780),
                  initialZoom: 12,
                  onTap: (tap, latLng) {
                    setState(() => pick = latLng);
                  },
                ),
                children: [
                  TileLayer(
                    urlTemplate:
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.mapestate.app',
                  ),
                  if (pick != null)
                    MarkerLayer(
                      markers: [
                        Marker(
                          point: pick!,
                          width: 40,
                          height: 40,
                          child: const Icon(
                            Icons.work,
                            color: AppTheme.clay,
                            size: 34,
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: pick == null
                ? null
                : () async {
                    await ref.read(prefsProvider.notifier).setWork(
                          lat: pick!.latitude,
                          lng: pick!.longitude,
                          label:
                              '출근지 (${pick!.latitude.toStringAsFixed(4)}, ${pick!.longitude.toStringAsFixed(4)})',
                        );
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('출근지를 저장했습니다.')),
                      );
                    }
                  },
            child: const Text('출근지 저장'),
          ),
          const SizedBox(height: 28),
          const Text(
            '점수 가중치',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          _slider('가격 매력', wPrice, (v) => setState(() => wPrice = v)),
          _slider('인프라', wInfra, (v) => setState(() => wInfra = v)),
          _slider('출퇴근', wCommute, (v) => setState(() => wCommute = v)),
          FilledButton.tonal(
            onPressed: () async {
              await ref.read(prefsProvider.notifier).setWeights(
                    price: wPrice,
                    infra: wInfra,
                    commute: wCommute,
                  );
              ref.invalidate(searchProvider);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('가중치를 저장했습니다.')),
                );
              }
            },
            child: const Text('가중치 저장'),
          ),
          const SizedBox(height: 28),
          const Text(
            '데이터 (실거래 기준)',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          FutureBuilder(
            future: ref.read(apiProvider).health(),
            builder: (context, snap) {
              final h = snap.data;
              if (h == null) {
                return Text(
                  '상태 확인 중…',
                  style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.55)),
                );
              }
              final molit = h['molit_configured'] == true;
              final source = h['data_source'] as String? ?? 'demo';
              final asOf = h['data_as_of'] as String? ?? '-';
              final from = h['trade_from'] as String? ?? '-';
              final to = h['trade_to'] as String? ?? '-';
              return Text(
                '출처: ${source == 'molit' ? '국토부 실거래(MOLIT)' : '데모 시드'}\n'
                '거래 기간: $from ~ $to (기준월 $asOf)\n'
                '매물 ${h['complex_count']} · 거래 ${h['trade_count']}\n'
                'MOLIT 키: ${molit ? '설정됨' : '없음 (backend/.env)'}\n'
                '가격·면적·층·거래일만 실거래/시드 거래값. '
                '향·전입·융자·사진·연락처는 데모일 수 있음.',
                style: TextStyle(
                  height: 1.45,
                  color: AppTheme.ink.withValues(alpha: 0.72),
                  fontSize: 13,
                ),
              );
            },
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () async {
              try {
                final res = await ref.read(apiProvider).triggerIngest(
                      months: 6,
                      regionCodes: [
                        '11680', // 강남
                        '11740', // 강동
                        '11620', // 관악
                        '11440', // 마포
                        '11200', // 성동
                        '11710', // 송파
                        '11650', // 서초
                        '11470', // 양천
                        '11560', // 영등포
                        '11380', // 은평
                        '11140', // 중구
                        '11110', // 종로
                      ],
                    );
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        res['message']?.toString() ??
                            '실거래 수집을 시작했습니다. 수 분 후 새로고침하세요.',
                      ),
                    ),
                  );
                }
                await Future<void>.delayed(const Duration(seconds: 2));
                ref.invalidate(searchProvider);
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        '수집 실패: $e\n'
                        'backend/.env 에 MOLIT_SERVICE_KEY 를 넣고 서버를 재시작하세요.',
                      ),
                    ),
                  );
                }
              }
            },
            child: const Text('국토부 실거래 수집 시작'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: () async {
              await ref.read(apiProvider).seedDemo();
              ref.invalidate(searchProvider);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('데모 시드로 교체했습니다 (국토부 원본 아님).'),
                  ),
                );
              }
            },
            child: const Text('데모 시드로 되돌리기'),
          ),
        ],
      ),
    );
  }

  Widget _slider(String label, double value, ValueChanged<double> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$label ${(value * 100).round()}%'),
        Slider(
          value: value,
          min: 0.05,
          max: 0.8,
          divisions: 15,
          onChanged: onChanged,
        ),
      ],
    );
  }
}

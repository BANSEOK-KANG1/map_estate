import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/config.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(healthProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'API',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Base URL'),
            subtitle: Text(AppConfig.apiBaseUrl),
          ),
          const Divider(),
          const Text(
            '데이터 상태',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 8),
          health.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => Text('$e'),
            data: (h) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('모드: ${h.mode} · 물건 ${h.lotCount}건 (데모 ${h.demoLotCount})'),
                const SizedBox(height: 8),
                Text(
                  '키  · 온비드 ${h.keys['onbid'] == true ? "✓" : "✗"}'
                  '  · 국토부 ${h.keys['molit'] == true ? "✓" : "✗"}'
                  '  · 카카오 ${h.keys['kakao'] == true ? "✓" : "✗"}',
                ),
                const SizedBox(height: 12),
                if (h.keys['onbid'] != true)
                  Text(
                    'ONBID_SERVICE_KEY는 설정됨/미설정과 별개로, 온비드 서버 연결이 필요합니다.\n'
                    '지금은 국토부 시세 enrich는 가능합니다. docs/REAL_DATA.md 참고.',
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.55),
                      height: 1.4,
                    ),
                  ),
                const SizedBox(height: 8),
                if (h.keys['kakao'] == true) ...[
                  const SizedBox(height: 8),
                  FilledButton.tonal(
                    onPressed: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      messenger.showSnackBar(
                        const SnackBar(content: Text('지도 좌표 붙이는 중… (1~2분)')),
                      );
                      try {
                        final res = await ref.read(apiProvider).enrichLots(
                              limit: 180,
                              fetchMarket: false,
                              fetchPois: false,
                              fetchDetail: false,
                              missingCoordsOnly: true,
                              balanceBySido: true,
                            );
                        ref.invalidate(searchProvider);
                        ref.invalidate(healthProvider);
                        messenger.showSnackBar(
                          SnackBar(
                            content: Text(
                              '좌표 enrich ${res['enriched']}건 · ${res['message'] ?? res['status']}',
                            ),
                          ),
                        );
                      } catch (e) {
                        messenger.showSnackBar(
                          SnackBar(content: Text('실패: $e')),
                        );
                      }
                    },
                    child: const Text('지도 좌표 붙이기 (카카오)'),
                  ),
                ],
                if (h.keys['molit'] == true) ...[
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      messenger.showSnackBar(
                        const SnackBar(content: Text('국토부 시세 enrich 중…')),
                      );
                      try {
                        final res = await ref.read(apiProvider).enrichLots();
                        ref.invalidate(searchProvider);
                        ref.invalidate(healthProvider);
                        messenger.showSnackBar(
                          SnackBar(
                            content: Text(
                              'enrich ${res['enriched']}건 · ${res['status']}',
                            ),
                          ),
                        );
                      } catch (e) {
                        messenger.showSnackBar(
                          SnackBar(content: Text('실패: $e')),
                        );
                      }
                    },
                    child: const Text('시세 다시 계산 (국토부)'),
                  ),
                ],
                if (h.keys['onbid'] == true) ...[
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      messenger.showSnackBar(
                        const SnackBar(content: Text('온비드 권리 상세 enrich 중…')),
                      );
                      try {
                        final res = await ref.read(apiProvider).enrichLots(
                              limit: 40,
                              fetchMarket: false,
                              fetchPois: false,
                              fetchDetail: true,
                              missingCoordsOnly: false,
                              balanceBySido: true,
                            );
                        ref.invalidate(searchProvider);
                        ref.invalidate(healthProvider);
                        messenger.showSnackBar(
                          SnackBar(
                            content: Text(
                              '권리 detail ${res['enriched']}건 · ${res['message'] ?? res['status']}',
                            ),
                          ),
                        );
                      } catch (e) {
                        messenger.showSnackBar(
                          SnackBar(content: Text('실패: $e')),
                        );
                      }
                    },
                    child: const Text('권리·등기 요약 채우기 (온비드 상세)'),
                  ),
                ],
                if (h.keys['onbid'] == true) ...[
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: () async {
                      final messenger = ScaffoldMessenger.of(context);
                      messenger.showSnackBar(
                        const SnackBar(content: Text('온비드 수집 중…')),
                      );
                      try {
                        final res = await ref.read(apiProvider).ingestOnbid();
                        ref.invalidate(searchProvider);
                        ref.invalidate(healthProvider);
                        messenger.showSnackBar(
                          SnackBar(
                            content: Text(
                              '수집 ${res['lot_count']}건 · enrich ${res['enriched']} · '
                              '${res['status']}',
                            ),
                          ),
                        );
                      } catch (e) {
                        messenger.showSnackBar(
                          SnackBar(content: Text('실패: $e')),
                        );
                      }
                    },
                    child: const Text('실데이터 수집 (온비드)'),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            '데이터 소스',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 8),
          Text(
            '공매: 캠코 온비드 OpenAPI\n'
            '경매: 공식 API 없음 (어댑터/데모)\n'
            '시세: 국토부 실거래 · 상권: 카카오 Local',
            style: TextStyle(
              color: AppTheme.ink.withValues(alpha: 0.55),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

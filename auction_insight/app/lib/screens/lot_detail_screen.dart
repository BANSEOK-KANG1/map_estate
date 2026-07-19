import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/utils/format.dart';
import 'package:auction_insight_app/widgets/lot_map.dart';

class LotDetailScreen extends ConsumerWidget {
  const LotDetailScreen({
    super.key,
    required this.lotId,
    this.source,
    this.externalId,
  });

  final int lotId;
  final String? source;
  final String? externalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(
      _lotProvider((
        id: lotId,
        source: source,
        externalId: externalId,
      )),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('물건 상세')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _DetailError(
          error: e,
          onRetry: () {
            ref.invalidate(searchProvider);
            ref.invalidate(
              _lotProvider((
                id: lotId,
                source: source,
                externalId: externalId,
              )),
            );
          },
          onBack: () {
            ref.invalidate(searchProvider);
            context.go('/');
          },
        ),
        data: (lot) => _DetailBody(lot: lot),
      ),
    );
  }
}

typedef _LotKey = ({int id, String? source, String? externalId});

final _lotProvider =
    FutureProvider.autoDispose.family<LotDetail, _LotKey>((ref, key) async {
  return ref.watch(apiProvider).fetchLot(
        key.id,
        source: key.source,
        externalId: key.externalId,
      );
});

class _DetailError extends StatelessWidget {
  const _DetailError({
    required this.error,
    required this.onRetry,
    required this.onBack,
  });

  final Object error;
  final VoidCallback onRetry;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final is404 = error is DioException &&
        (error as DioException).response?.statusCode == 404;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              is404 ? Icons.refresh : Icons.error_outline,
              size: 40,
              color: AppTheme.ink.withValues(alpha: 0.45),
            ),
            const SizedBox(height: 16),
            Text(
              is404
                  ? '물건 정보가 갱신되었습니다'
                  : '상세를 불러오지 못했습니다',
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              is404
                  ? '서버가 잠들었다 깨면 목록이 다시 만들어집니다.\n목록으로 돌아가 새로고침해 주세요.'
                  : '$error',
              textAlign: TextAlign.center,
              style: TextStyle(
                height: 1.4,
                color: AppTheme.ink.withValues(alpha: 0.55),
              ),
            ),
            const SizedBox(height: 20),
            FilledButton(onPressed: onBack, child: const Text('목록으로')),
            const SizedBox(height: 8),
            TextButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({required this.lot});

  final LotDetail lot;

  @override
  Widget build(BuildContext context) {
    final scores = lot.scores;
    final market = lot.market;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
      children: [
        // Header
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            _chip(lot.sourceLabel),
            _chip(lot.usage),
            for (final h in lot.highlights) _chip(h, accent: true),
          ],
        ),
        const SizedBox(height: 10),
        Text(
          lot.title,
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 4),
        Text(
          lot.address,
          style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.6)),
        ),
        if (lot.courtName.isNotEmpty || lot.caseNo.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            [
              if (lot.courtName.isNotEmpty) lot.courtName,
              if (lot.caseNo.isNotEmpty) lot.caseNo,
            ].join(' · '),
            style: TextStyle(
              fontSize: 13,
              color: AppTheme.ink.withValues(alpha: 0.45),
            ),
          ),
        ],
        const SizedBox(height: 14),
        LotMap(items: [lot], focus: lot, height: 190),
        const SizedBox(height: 18),

        // Key facts
        _section('기본 정보'),
        _factGrid([
          ('면적', formatArea(lot.exclusiveArea)),
          if (lot.landArea != null) ('토지', formatArea(lot.landArea)),
          if (lot.buildYear != null) ('건축', '${lot.buildYear}년'),
          if (lot.floorInfo.isNotEmpty) ('층', lot.floorInfo),
          if (lot.nearestStation != null)
            (
              '역세권',
              '${lot.nearestStation}'
                  '${lot.stationLine != null ? " (${lot.stationLine})" : ""}'
                  '${lot.stationWalkMinutes != null ? " · 도보 ${lot.stationWalkMinutes}분" : ""}'
            ),
          ('매각기일', formatDate(lot.saleDate)),
          if (lot.daysLeft != null) ('남은 일수', 'D-${lot.daysLeft}'),
        ]),
        if (lot.description.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text(
            lot.description,
            style: TextStyle(
              height: 1.45,
              color: AppTheme.ink.withValues(alpha: 0.75),
            ),
          ),
        ],

        const SizedBox(height: 22),
        _section('가격 비교'),
        _PriceRow(label: '감정가', value: formatManwon(lot.appraisalManwon)),
        _PriceRow(
          label: '최저가',
          value: formatManwon(lot.minBidManwon),
          emphasize: true,
        ),
        _PriceRow(
          label: '인근 시세',
          value: formatManwon(market?.medianManwon),
          subtitle: [
            if (market != null && market.pyeongManwon != null)
              '평단 ${formatManwon(market.pyeongManwon!.round())}',
            if (market != null) '표본 ${market.sampleCount}건',
            if (market != null) '신뢰도 ${_confidenceLabel(market.confidence)}',
          ].join(' · '),
        ),
        if (market?.note.isNotEmpty == true) ...[
          const SizedBox(height: 6),
          Text(
            market!.note,
            style: TextStyle(
              fontSize: 12,
              height: 1.35,
              color: AppTheme.ink.withValues(alpha: 0.5),
            ),
          ),
        ],
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _MetricCard(
                label: '감정 대비',
                value: formatPct(scores?.discountVsAppraisal),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                label: '시세 대비',
                value: formatPct(scores?.discountVsMarket),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                label: '종합점수',
                value: scores?.total?.toStringAsFixed(0) ?? '—',
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _MetricCard(
                label: '상권',
                value: scores?.infra?.toStringAsFixed(0) ?? '—',
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                label: '마감임박',
                value: scores?.urgency?.toStringAsFixed(0) ?? '—',
              ),
            ),
            const SizedBox(width: 8),
            const Expanded(child: SizedBox()),
          ],
        ),

        const SizedBox(height: 22),
        _section('입찰 · 유찰 이력'),
        Text(
          '유찰 ${lot.failCount}회'
          '${lot.legal?.bidRounds.isNotEmpty == true ? " · 회차 상세 있음" : " · 회차별 최저가·입찰팀 수는 별도 API 신청 후 표시"}',
          style: TextStyle(
            fontSize: 13,
            color: AppTheme.ink.withValues(alpha: 0.65),
          ),
        ),
        const SizedBox(height: 8),
        if (lot.legal?.bidRounds.isNotEmpty == true)
          ...lot.legal!.bidRounds.map((r) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                '${r['round_no'] ?? "-"}회 · 최저 ${r['min_bid'] ?? "-"} · 입찰 ${r['bidder_count'] ?? "?"}팀 · ${r['result'] ?? ""}',
                style: const TextStyle(fontSize: 13),
              ),
            );
          })
        else if (lot.schedules.isEmpty)
          Text('마감 ${formatDate(lot.bidEndAt)}')
        else
          ...lot.schedules.map((s) {
            final active = s.result == '진행';
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: active
                    ? AppTheme.slate.withValues(alpha: 0.08)
                    : Colors.white.withValues(alpha: 0.65),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.line),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 14,
                    backgroundColor: active ? AppTheme.slate : AppTheme.fog,
                    foregroundColor: active ? Colors.white : AppTheme.ink,
                    child: Text('${s.roundNo}', style: const TextStyle(fontSize: 12)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${s.roundNo}회차 · ${s.result}',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        Text(
                          '${formatDate(s.saleDate)} · 최저 ${formatManwon(s.minBidManwon)}',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.ink.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }),

        const SizedBox(height: 22),
        _section('권리 · 법적 리스크 (참고)'),
        if (lot.legal == null)
          Text(
            '상세 권리 정보 없음 — 설정에서 enrich(detail) 후 다시 확인',
            style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.55)),
          )
        else ...[
          if (lot.legal!.riskFlags.isNotEmpty) ...[
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final f in lot.legal!.riskFlags) _chip(f, accent: true),
              ],
            ),
            const SizedBox(height: 10),
          ],
          _factGrid([
            if (lot.legal!.orgName.isNotEmpty) ('공고기관', lot.legal!.orgName),
            if (lot.legal!.evictionTarget.isNotEmpty)
              ('명도책임', lot.legal!.evictionTarget),
            ('임대차', '${lot.legal!.leaseCount}건'),
            ('점유관계', '${lot.legal!.occupyCount}건'),
            ('등기관련', '${lot.legal!.registryCount}건'),
          ]),
          const SizedBox(height: 10),
          ...lot.legal!.notes.take(8).map(
                (n) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    '· $n',
                    style: TextStyle(
                      fontSize: 13,
                      height: 1.4,
                      color: AppTheme.ink.withValues(alpha: 0.7),
                    ),
                  ),
                ),
              ),
          if (lot.legal!.appraisals.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...lot.legal!.appraisals.map((a) {
              final url = a['url'] as String?;
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: InkWell(
                  onTap: url == null || url.isEmpty
                      ? null
                      : () async {
                          await launchUrl(
                            Uri.parse(url),
                            mode: LaunchMode.externalApplication,
                          );
                        },
                  child: Text(
                    '감정평가서 ${a['org'] ?? ""} ${a['date'] ?? ""}',
                    style: const TextStyle(
                      color: AppTheme.slate,
                      decoration: TextDecoration.underline,
                      fontSize: 13,
                    ),
                  ),
                ),
              );
            }),
          ],
          if (lot.legal!.gaps.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...lot.legal!.gaps.map(
              (g) => Text(
                '⚠ $g',
                style: TextStyle(
                  fontSize: 12,
                  color: AppTheme.amber.withValues(alpha: 0.9),
                ),
              ),
            ),
          ],
        ],

        const SizedBox(height: 18),
        _section('주변 상권 (반경 약 800m)'),
        if (lot.pois.isEmpty)
          Text(
            '상권 데이터 없음',
            style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.55)),
          )
        else
          ...lot.pois.where((p) => p.count > 0).map((p) {
            final nearest = p.places.isNotEmpty
                ? '${p.places.first['name']} ${p.places.first['distance']}m'
                : (p.nearestDistanceM != null
                    ? '${p.nearestDistanceM!.round()}m'
                    : '');
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 72,
                    child: Text(
                      p.categoryLabel,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${p.count}곳${nearest.isNotEmpty ? " · 최근접 $nearest" : ""}',
                      style: TextStyle(
                        color: AppTheme.ink.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),

        const SizedBox(height: 20),
        if (lot.sourceUrl.isNotEmpty)
          OutlinedButton.icon(
            onPressed: () async {
              final uri = Uri.parse(lot.sourceUrl);
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            },
            icon: const Icon(Icons.open_in_new),
            label: const Text('원문 보기'),
          ),
        if (lot.disclaimer.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(
            lot.disclaimer,
            style: TextStyle(
              fontSize: 11,
              height: 1.4,
              color: AppTheme.ink.withValues(alpha: 0.4),
            ),
          ),
        ],
      ],
    );
  }

  Widget _section(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(
          t,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      );

  Widget _chip(String text, {bool accent = false}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: accent ? AppTheme.amber.withValues(alpha: 0.14) : AppTheme.fog,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: accent ? AppTheme.amber : AppTheme.ink,
        ),
      ),
    );
  }

  Widget _factGrid(List<(String, String)> items) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: items
          .map(
            (e) => SizedBox(
              width: 150,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    e.$1,
                    style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.ink.withValues(alpha: 0.45),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    e.$2,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }

  String _confidenceLabel(String c) => switch (c) {
        'high' => '높음',
        'medium' => '보통',
        _ => '낮음',
      };
}

class _PriceRow extends StatelessWidget {
  const _PriceRow({
    required this.label,
    required this.value,
    this.subtitle,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final String? subtitle;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(
              label,
              style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.55)),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontWeight: emphasize ? FontWeight.w800 : FontWeight.w600,
                    fontSize: emphasize ? 18 : 15,
                  ),
                ),
                if (subtitle != null && subtitle!.isNotEmpty)
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.ink.withValues(alpha: 0.45),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.w800,
              fontSize: 17,
              color: AppTheme.slate,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: AppTheme.ink.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }
}

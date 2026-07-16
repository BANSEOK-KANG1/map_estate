import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/providers/providers.dart';
import 'package:map_estate_app/theme.dart';
import 'package:map_estate_app/utils/format.dart';
import 'package:map_estate_app/utils/listing_links.dart';
import 'package:map_estate_app/utils/open_url.dart';
import 'package:map_estate_app/widgets/complex_map.dart';
import 'package:map_estate_app/widgets/price_trend_chart.dart';
import 'package:url_launcher/url_launcher.dart';

class ComplexDetailScreen extends ConsumerStatefulWidget {
  const ComplexDetailScreen({super.key, required this.complexId});

  final int complexId;

  @override
  ConsumerState<ComplexDetailScreen> createState() =>
      _ComplexDetailScreenState();
}

class _ComplexDetailScreenState extends ConsumerState<ComplexDetailScreen> {
  AreaBucket? selectedBucket;
  int _photoIndex = 0;
  ComplexDetail? _detail;
  TrendResponse? _trends;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load({bool trendsOnly = false}) async {
    final prefs = ref.read(prefsProvider);
    final api = ref.read(apiProvider);
    setState(() {
      if (!trendsOnly) {
        _loading = true;
        _error = null;
      }
    });
    try {
      final trendsFut = api.fetchTrends(
        widget.complexId,
        areaMin: selectedBucket?.minArea,
        areaMax: selectedBucket?.maxArea == 9999
            ? null
            : selectedBucket?.maxArea,
      );
      if (trendsOnly && _detail != null) {
        final trends = await trendsFut;
        if (!mounted) return;
        setState(() => _trends = trends);
        return;
      }
      final results = await Future.wait([
        api.fetchComplex(widget.complexId, prefs: prefs),
        trendsFut,
      ]);
      if (!mounted) return;
      setState(() {
        _detail = results[0] as ComplexDetail;
        _trends = results[1] as TrendResponse;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _detail == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null && _detail == null) {
      return Scaffold(
        appBar: AppBar(),
        body: Center(child: Text('오류: $_error')),
      );
    }
    final detail = _detail!;
    final trends = _trends ??
        const TrendResponse(complexId: 0, points: []);
    final photos = detail.photoUrls;
    final prefs = ref.watch(prefsProvider);

    return Scaffold(
      backgroundColor: AppTheme.mist,
      appBar: AppBar(title: Text(detail.name)),
      bottomNavigationBar: detail.agentPhone.isEmpty
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _call(detail.agentPhone),
                        icon: const Icon(Icons.phone_outlined),
                        label: Text(detail.agentPhone),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: () => _call(detail.agentPhone),
                        icon: const Icon(Icons.chat_bubble_outline),
                        label: const Text('연락하기'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          if (photos.isNotEmpty)
            SizedBox(
              height: 240,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  PageView.builder(
                    itemCount: photos.length,
                    onPageChanged: (i) => setState(() => _photoIndex = i),
                    itemBuilder: (context, i) => Image.network(
                      photos[i],
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => ColoredBox(
                        color: AppTheme.sand,
                        child: Icon(
                          Icons.broken_image_outlined,
                          size: 48,
                          color: AppTheme.ink.withValues(alpha: 0.35),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    right: 12,
                    bottom: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.55),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '${_photoIndex + 1}/${photos.length}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            )
          else
            Container(
              height: 160,
              color: AppTheme.sand,
              alignment: Alignment.center,
              child: Text(
                '내부 사진 없음',
                style: TextStyle(
                  color: AppTheme.ink.withValues(alpha: 0.45),
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  formatListingPrice(
                    dealKind: detail.dealKind,
                    price: detail.medianPriceManwon,
                    monthly: detail.medianMonthlyRentManwon,
                  ),
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.6,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  [
                    if (detail.nearestStation != null)
                      '${detail.nearestStation}역 도보 ${detail.walkMinutes}분',
                    detail.housingTypeLabel,
                    '${detail.regionName} ${detail.dong}',
                  ].where((e) => e.isNotEmpty).join(' · '),
                  style: TextStyle(
                    color: AppTheme.ink.withValues(alpha: 0.65),
                  ),
                ),
                if (detail.description.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    detail.description,
                    style: TextStyle(
                      height: 1.45,
                      color: AppTheme.ink.withValues(alpha: 0.82),
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                _DataAsOfBanner(detail: detail),
                const SizedBox(height: 18),
                _sectionTitle('실시간 매물 교차확인'),
                const SizedBox(height: 6),
                Text(
                  '실거래는 이 앱, 호가는 네이버·직방입니다. '
                  '네이버는 PC에서도 월세(B2)·원룸·오피스텔로 엽니다.',
                  style: TextStyle(
                    fontSize: 12.5,
                    height: 1.4,
                    color: AppTheme.ink.withValues(alpha: 0.62),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  '검색: ${ListingLinks.queryFor(detail)}',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.moss,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton.icon(
                      onPressed: () =>
                          _openExternal(ListingLinks.naver(detail)),
                      icon: const Icon(Icons.map_outlined, size: 18),
                      label: Text(
                        detail.dealKind == 'sale' ? '네이버 매매' : '네이버 월세',
                      ),
                    ),
                    FilledButton.tonalIcon(
                      onPressed: () =>
                          _openExternal(ListingLinks.zigbang(detail)),
                      icon: const Icon(Icons.home_work_outlined, size: 18),
                      label: const Text('직방'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () =>
                          _openExternal(ListingLinks.naverMobile(detail)),
                      icon: const Icon(Icons.phone_iphone, size: 18),
                      label: const Text('네이버(모바일)'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () =>
                          _openExternal(ListingLinks.naverSearch(detail)),
                      icon: const Icon(Icons.search, size: 18),
                      label: const Text('네이버 검색'),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SelectableText(
                  ListingLinks.naver(detail).toString(),
                  style: TextStyle(
                    fontSize: 11,
                    color: AppTheme.ink.withValues(alpha: 0.45),
                  ),
                ),
                const SizedBox(height: 22),
                _sectionTitle('매물 정보'),
                const SizedBox(height: 10),
                _InfoGrid(
                  entries: [
                    ('방향', detail.facing ?? '문의'),
                    ('전입신고', formatMoveIn(detail.moveInOk)),
                    ('융자', formatLoan(detail.loanManwon)),
                    (
                      '면적',
                      formatAreaPyeong(
                        detail.avgExclusiveArea,
                        detail.avgExclusivePyeong,
                      ),
                    ),
                    (
                      '구조',
                      [
                        if (detail.roomCount != null) '${detail.roomCount}룸',
                        if (detail.bathCount != null)
                          '${detail.bathCount}욕실',
                      ].join(' · ').ifEmpty('문의'),
                    ),
                    (
                      '주차',
                      detail.parking == null
                          ? '문의'
                          : (detail.parking! ? '가능' : '협의'),
                    ),
                    (
                      '층',
                      detail.floorMin == null
                          ? '-'
                          : '${detail.floorMin}-${detail.floorMax}층',
                    ),
                    ('건축', '${detail.buildYear ?? '-'}년'),
                  ],
                ),
                const SizedBox(height: 22),
                _sectionTitle('연락처'),
                const SizedBox(height: 8),
                if (detail.agentPhone.isEmpty)
                  Text(
                    '등록된 연락처 없음',
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.55),
                    ),
                  )
                else
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.7),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppTheme.line),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          detail.agentOffice,
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 15,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${detail.agentName} · ${detail.agentPhone}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '전화 · 문자로 임장 일정 조율 가능 (데모 연락처)',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.ink.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 22),
                if (detail.lat != null && detail.lng != null) ...[
                  _sectionTitle('위치'),
                  const SizedBox(height: 8),
                  ComplexMap(
                    items: [detail],
                    focus: detail,
                    workLat: prefs.workLat,
                    workLng: prefs.workLng,
                    height: 200,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    detail.roadName.isNotEmpty
                        ? detail.roadName
                        : '${detail.dong} ${detail.jibun}',
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.65),
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 22),
                ],
                _ScoreRow(scores: detail.scores),
                const SizedBox(height: 22),
                _sectionTitle('실거래 추이'),
                const SizedBox(height: 6),
                Text(
                  detail.dealKind == 'rent'
                      ? '전월세 지표(보증금+월세×100 환산) · 신고 기준'
                      : '매매가 추이 · 신고 기준',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppTheme.ink.withValues(alpha: 0.55),
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: const Text('전체'),
                      selected: selectedBucket == null,
                      onSelected: (_) {
                        setState(() => selectedBucket = null);
                        _load(trendsOnly: true);
                      },
                    ),
                    ...detail.areaBuckets
                        .where((b) => b.tradeCount > 0)
                        .map(
                          (b) => ChoiceChip(
                            label: Text(b.label),
                            selected: selectedBucket?.label == b.label,
                            onSelected: (_) {
                              setState(() => selectedBucket = b);
                              _load(trendsOnly: true);
                            },
                          ),
                        ),
                  ],
                ),
                const SizedBox(height: 12),
                PriceTrendChart(points: trends.points),
                const SizedBox(height: 22),
                _sectionTitle('요약'),
                const SizedBox(height: 8),
                _kv(
                  detail.dealKind == 'rent' ? '중위 보증금' : '중위 거래가',
                  formatManwon(detail.medianPriceManwon),
                ),
                if (detail.dealKind == 'rent')
                  _kv(
                    '중위 월세',
                    formatManwon(detail.medianMonthlyRentManwon),
                  ),
                _kv(
                  '평당(중위)',
                  detail.medianPyeongManwon == null
                      ? '-'
                      : '${detail.medianPyeongManwon!.toStringAsFixed(0)}만',
                ),
                _kv('추이', formatTrend(detail.priceTrendPct)),
                _kv('6개월 거래', '${detail.recentDealCount6m}건'),
                const SizedBox(height: 22),
                _sectionTitle('주변 인프라 (반경 800m)'),
                const SizedBox(height: 8),
                if (detail.poiSummary.isEmpty)
                  Text(
                    '카카오 REST 키를 설정하면 상권·인프라를 불러옵니다.',
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.55),
                    ),
                  )
                else
                  ...detail.poiSummary.map(
                    (p) => _kv(
                      p.label,
                      '${p.count}곳 · 최단 ${p.nearestDistanceM?.round() ?? '-'}m',
                    ),
                  ),
                const SizedBox(height: 22),
                _sectionTitle('출퇴근'),
                const SizedBox(height: 8),
                if (detail.commute?.durationMinutes == null)
                  Text(
                    prefs.workLat == null
                        ? '설정에서 출근지를 지정하세요.'
                        : '경로 계산 불가 (좌표/키 확인)',
                    style: TextStyle(
                      color: AppTheme.ink.withValues(alpha: 0.55),
                    ),
                  )
                else
                  _kv(
                    '예상 소요',
                    '${detail.commute!.durationMinutes!.toStringAsFixed(0)}분'
                        ' · 점수 ${detail.commute!.score.toStringAsFixed(0)}'
                        ' (${detail.commute!.source})',
                  ),
                const SizedBox(height: 22),
                _sectionTitle('최근 거래'),
                const SizedBox(height: 8),
                ...detail.recentTrades.take(12).map(
                      (t) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 96,
                              child: Text(
                                t.dealDate.toIso8601String().substring(0, 10),
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                '${t.dealKind == 'rent' ? '전월세' : '매매'} · '
                                '${t.exclusiveArea.toStringAsFixed(1)}㎡'
                                '${t.floor != null ? ' · ${t.floor}층' : ''}',
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                            Text(
                              formatListingPrice(
                                dealKind: t.dealKind,
                                price: t.priceManwon,
                                monthly: t.monthlyRentManwon,
                              ),
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone.replaceAll('-', ''));
    await _openExternal(uri);
  }

  Future<void> _openExternal(Uri uri) async {
    var launched = false;
    try {
      launched = await openExternalUrl(uri);
    } catch (_) {
      launched = false;
    }
    if (!launched) {
      try {
        launched = await launchUrl(
          uri,
          mode: LaunchMode.platformDefault,
          webOnlyWindowName: '_blank',
        );
      } catch (_) {
        launched = false;
      }
    }
    if (!launched && mounted) {
      await Clipboard.setData(ClipboardData(text: uri.toString()));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('새 탭이 막혀 링크를 복사했습니다.\n$uri'),
          duration: const Duration(seconds: 4),
        ),
      );
    }
  }

  Widget _sectionTitle(String t) => Text(
        t,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
      );

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
              width: 110,
              child: Text(
                k,
                style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.55)),
              ),
            ),
            Expanded(
              child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      );
}

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}

class _DataAsOfBanner extends StatelessWidget {
  const _DataAsOfBanner({required this.detail});

  final ComplexDetail detail;

  @override
  Widget build(BuildContext context) {
    final deal = detail.latestDealDate;
    final listed = detail.listedAt;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.moss.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppTheme.moss.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            [
              if (deal != null)
                '실거래 최근 ${deal.toIso8601String().substring(0, 10)}',
              if (listed != null)
                '매물게시 ${listed.toIso8601String().substring(0, 10)}',
            ].join(' · '),
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 13,
              color: AppTheme.moss,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            detail.dataNote.isNotEmpty
                ? detail.dataNote
                : '실거래는 신고 기준(1~2개월 지연 가능). 향·전입·융자·사진·연락처는 데모 호가정보입니다.',
            style: TextStyle(
              fontSize: 12,
              height: 1.35,
              color: AppTheme.ink.withValues(alpha: 0.65),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoGrid extends StatelessWidget {
  const _InfoGrid({required this.entries});

  final List<(String, String)> entries;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final cols = constraints.maxWidth >= 520 ? 4 : 2;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: entries.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: cols,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 1.85,
          ),
          itemBuilder: (context, i) {
            final e = entries[i];
            return Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.65),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.line),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    e.$1,
                    style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.ink.withValues(alpha: 0.55),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    e.$2,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _ScoreRow extends StatelessWidget {
  const _ScoreRow({required this.scores});

  final ScoreBreakdown? scores;

  @override
  Widget build(BuildContext context) {
    final s = scores;
    return Row(
      children: [
        _chip('총점', s?.total ?? 0, AppTheme.moss),
        _chip('가격', s?.price ?? 0, AppTheme.ink),
        _chip('인프라', s?.infrastructure ?? 0, AppTheme.clay),
        _chip('출퇴근', s?.commute ?? 0, AppTheme.moss),
      ].map((w) => Expanded(child: w)).toList(),
    );
  }

  Widget _chip(String label, double value, Color color) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4),
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        children: [
          Text(
            value.toStringAsFixed(0),
            style: TextStyle(
              fontWeight: FontWeight.w900,
              fontSize: 20,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 11)),
        ],
      ),
    );
  }
}

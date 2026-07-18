import 'package:dio/dio.dart';
import 'package:auction_insight_app/config.dart';
import 'package:auction_insight_app/models/models.dart';

class HealthInfo {
  final String status;
  final String mode;
  final int lotCount;
  final int demoLotCount;
  final Map<String, bool> keys;

  const HealthInfo({
    required this.status,
    required this.mode,
    required this.lotCount,
    required this.demoLotCount,
    required this.keys,
  });

  factory HealthInfo.fromJson(Map<String, dynamic> json) => HealthInfo(
        status: json['status'] as String? ?? 'ok',
        mode: json['mode'] as String? ?? 'demo',
        lotCount: json['lot_count'] as int? ?? 0,
        demoLotCount: json['demo_lot_count'] as int? ?? 0,
        keys: {
          for (final e in (json['keys'] as Map? ?? {}).entries)
            e.key.toString(): e.value == true,
        },
      );

  bool get hasRealKeys =>
      (keys['onbid'] == true) || (keys['molit'] == true) || (keys['kakao'] == true);
}

class AuctionApi {
  AuctionApi({Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: AppConfig.apiBaseUrl,
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 120),
                headers: {'Content-Type': 'application/json'},
              ),
            );

  final Dio _dio;

  Future<HealthInfo> health() async {
    final res = await _dio.get('/api/health');
    return HealthInfo.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<List<Region>> fetchRegions() async {
    final res = await _dio.get('/api/regions');
    return (res.data as List)
        .map((e) => Region.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SearchResult> search(SearchFilters filters) async {
    final res = await _dio.post('/api/search', data: filters.toJson());
    final data = res.data as Map<String, dynamic>;
    return SearchResult(
      total: data['total'] as int? ?? 0,
      items: (data['items'] as List? ?? [])
          .map((e) => LotSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<LotDetail> fetchLot(int id, {bool enrich = false}) async {
    final res = await _dio.get(
      '/api/lots/$id',
      queryParameters: {if (enrich) 'enrich': true},
    );
    return LotDetail.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> seedDemo() async {
    await _dio.post('/api/demo/seed');
  }

  Future<Map<String, dynamic>> ingestOnbid({
    int maxPages = 5,
    bool clearDemo = true,
    bool enrich = true,
  }) async {
    final res = await _dio.post(
      '/api/ingest/onbid',
      data: {
        'max_pages': maxPages,
        'page_size': 20,
        'clear_demo': clearDemo,
        'enrich': enrich,
        'enrich_limit': 40,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> enrichLots({
    int limit = 50,
    bool fetchMarket = true,
    bool fetchPois = false,
  }) async {
    final res = await _dio.post(
      '/api/enrich',
      data: {
        'limit': limit,
        'fetch_market': fetchMarket,
        'fetch_pois': fetchPois,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }
}

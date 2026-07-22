import 'package:dio/dio.dart';
import 'package:auction_insight_app/analysis/analysis_models.dart';
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

  Future<LotDetail> fetchLot(
    int id, {
    bool enrich = false,
    bool fetchDetail = false,
    String? source,
    String? externalId,
  }) async {
    // Prefer stable key when available (DB wipe changes numeric ids).
    if (source != null &&
        source.isNotEmpty &&
        externalId != null &&
        externalId.isNotEmpty) {
      try {
        final res = await _dio.get(
          '/api/lots/by-key',
          queryParameters: {
            'source': source,
            'external_id': externalId,
            if (enrich) 'enrich': true,
            if (fetchDetail) 'fetch_detail': true,
          },
        );
        return LotDetail.fromJson(res.data as Map<String, dynamic>);
      } on DioException catch (e) {
        if (e.response?.statusCode != 404) rethrow;
        // Fall through to numeric id for older clients / edge cases.
      }
    }
    final res = await _dio.get(
      '/api/lots/$id',
      queryParameters: {
        if (enrich) 'enrich': true,
        if (fetchDetail) 'fetch_detail': true,
      },
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
    bool fetchDetail = false,
    bool missingCoordsOnly = false,
    bool balanceBySido = false,
    List<String> regionCodes = const [],
  }) async {
    final res = await _dio.post(
      '/api/enrich',
      data: {
        'limit': limit,
        'fetch_market': fetchMarket,
        'fetch_pois': fetchPois,
        'fetch_detail': fetchDetail,
        'missing_coords_only': missingCoordsOnly,
        'balance_by_sido': balanceBySido,
        if (regionCodes.isNotEmpty) 'region_codes': regionCodes,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<AnalysisItemSummary>> listAnalysisItems({String? source}) async {
    final res = await _dio.get(
      '/api/analysis/items',
      queryParameters: {if (source != null) 'source': source},
    );
    final list = res.data as List;
    return list
        .map((e) => AnalysisItemSummary.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<AnalysisItemDetail> fetchAnalysisItem(int id) async {
    final res = await _dio.get('/api/analysis/items/$id');
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<AnalysisItemDetail> createAnalysisItem(Map<String, dynamic> body) async {
    final res = await _dio.post('/api/analysis/items', data: body);
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<AnalysisItemDetail> createAnalysisItemFromLot(
    int lotId, {
    bool forceNew = false,
  }) async {
    final res = await _dio.post(
      '/api/analysis/items/from-lot/$lotId',
      queryParameters: {if (forceNew) 'force_new': true},
    );
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<AnalysisItemDetail> patchAnalysisFinance(
    int id,
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.patch('/api/analysis/items/$id/finance', data: body);
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<Map<String, dynamic>> uploadAnalysisDocument(
    int itemId, {
    required List<int> bytes,
    required String filename,
    String? docType,
  }) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
      if (docType != null) 'doc_type': docType,
    });
    final res = await _dio.post('/api/analysis/items/$itemId/documents', data: form);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> fetchAnalysisDocument(int docId) async {
    final res = await _dio.get('/api/analysis/documents/$docId');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> correctAnalysisDocument(
    int docId, {
    String? docType,
    String? extractedText,
    bool confirm = false,
  }) async {
    final res = await _dio.patch(
      '/api/analysis/documents/$docId',
      data: {
        if (docType != null) 'doc_type': docType,
        if (extractedText != null) 'extracted_text': extractedText,
        'confirm': confirm,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> documentEvidence(
    int docId, {
    int page = 1,
    String query = '',
  }) async {
    final res = await _dio.post(
      '/api/analysis/documents/$docId/evidence',
      data: {'page': page, 'query': query},
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> rightFromEvidence(
    int itemId, {
    required int docId,
    int page = 1,
    String label = '',
    String kind = 'other',
    String query = '',
  }) async {
    final res = await _dio.post(
      '/api/analysis/items/$itemId/rights/from-evidence',
      data: {
        'doc_id': docId,
        'page': page,
        'label': label,
        'kind': kind,
        'query': query,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> createAnalysisRight(
    int itemId,
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.post('/api/analysis/items/$itemId/rights', data: body);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> patchAnalysisRight(
    int rightId,
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.patch('/api/analysis/rights/$rightId', data: body);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> deleteAnalysisRight(int rightId) async {
    await _dio.delete('/api/analysis/rights/$rightId');
  }

  Future<Map<String, dynamic>> createAnalysisOccupancy(
    int itemId,
    Map<String, dynamic> body,
  ) async {
    final res =
        await _dio.post('/api/analysis/items/$itemId/occupancies', data: body);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> patchAnalysisOccupancy(
    int occId,
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.patch('/api/analysis/occupancies/$occId', data: body);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> deleteAnalysisOccupancy(int occId) async {
    await _dio.delete('/api/analysis/occupancies/$occId');
  }

  Future<AnalysisItemDetail> evaluateAnalysisTimeline(
    int itemId, {
    bool applyFinanceSuggest = false,
  }) async {
    final res = await _dio.post(
      '/api/analysis/items/$itemId/timeline/evaluate',
      data: {'apply_finance_suggest': applyFinanceSuggest},
    );
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<AnalysisItemDetail> applyAnalysisTaxFromRules(int itemId) async {
    final res = await _dio.post('/api/analysis/items/$itemId/finance/apply-tax');
    return AnalysisItemDetail.fromJson(Map<String, dynamic>.from(res.data as Map));
  }

  Future<Map<String, dynamic>> previewAnalysisWhatIf(
    int itemId, {
    double assumeDepositFactor = 1.0,
    int evictionExtraWon = 0,
    int loanHaircutWon = 0,
    double exitDropRatio = 0.0,
  }) async {
    final res = await _dio.post(
      '/api/analysis/items/$itemId/what-if',
      data: {
        'assume_deposit_factor': assumeDepositFactor,
        'eviction_extra_won': evictionExtraWon,
        'loan_haircut_won': loanHaircutWon,
        'exit_drop_ratio': exitDropRatio,
      },
    );
    return Map<String, dynamic>.from(res.data as Map);
  }
}

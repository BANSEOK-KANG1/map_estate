import 'package:dio/dio.dart';
import 'package:map_estate_app/config.dart';
import 'package:map_estate_app/models/models.dart';

class EstateApi {
  EstateApi({Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: AppConfig.apiBaseUrl,
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 30),
                headers: {'Content-Type': 'application/json'},
              ),
            );

  final Dio _dio;

  Future<List<Region>> fetchRegions() async {
    final res = await _dio.get('/api/regions');
    return (res.data as List)
        .map((e) => Region.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SearchResult> search(
    SearchFilters filters, {
    required UserPrefs prefs,
  }) async {
    final res = await _dio.post(
      '/api/search',
      data: filters.toJson(
        workLat: prefs.workLat,
        workLng: prefs.workLng,
        weightPrice: prefs.weightPrice,
        weightInfra: prefs.weightInfra,
        weightCommute: prefs.weightCommute,
      ),
    );
    final data = res.data as Map<String, dynamic>;
    return SearchResult(
      total: data['total'] as int,
      items: (data['items'] as List)
          .map((e) => ComplexSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
      note: data['note'] as String? ?? '',
      dataAsOf: data['data_as_of'] as String?,
      tradeFrom: data['trade_from'] as String?,
      tradeTo: data['trade_to'] as String?,
      dataSource: data['data_source'] as String? ?? 'demo',
      listedAsOf: data['listed_as_of'] as String?,
    );
  }

  Future<ComplexDetail> fetchComplex(
    int id, {
    required UserPrefs prefs,
  }) async {
    final res = await _dio.get(
      '/api/complexes/$id',
      queryParameters: {
        if (prefs.workLat != null) 'work_lat': prefs.workLat,
        if (prefs.workLng != null) 'work_lng': prefs.workLng,
        'weight_price': prefs.weightPrice,
        'weight_infra': prefs.weightInfra,
        'weight_commute': prefs.weightCommute,
      },
    );
    return ComplexDetail.fromJson(res.data as Map<String, dynamic>);
  }

  Future<TrendResponse> fetchTrends(
    int id, {
    double? areaMin,
    double? areaMax,
  }) async {
    final res = await _dio.get(
      '/api/complexes/$id/trends',
      queryParameters: {
        if (areaMin != null) 'area_min': areaMin,
        if (areaMax != null) 'area_max': areaMax,
      },
    );
    return TrendResponse.fromJson(res.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> health() async {
    final res = await _dio.get('/api/health');
    return res.data as Map<String, dynamic>;
  }

  Future<void> seedDemo() async {
    await _dio.post('/api/demo/seed');
  }

  Future<Map<String, dynamic>> triggerIngest({
    int months = 6,
    List<String>? regionCodes,
    List<String>? sources,
  }) async {
    final res = await _dio.post(
      '/api/ingest',
      data: {
        'months': months,
        if (regionCodes != null) 'region_codes': regionCodes,
        'sources': sources ?? ['officetel:rent', 'officetel:sale'],
        'force': false,
      },
    );
    return res.data as Map<String, dynamic>;
  }
}

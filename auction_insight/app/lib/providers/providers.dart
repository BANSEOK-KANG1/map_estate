import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:auction_insight_app/api/auction_api.dart';
import 'package:auction_insight_app/models/models.dart';

final apiProvider = Provider<AuctionApi>((ref) => AuctionApi());

final regionsProvider = FutureProvider<List<Region>>((ref) async {
  return ref.watch(apiProvider).fetchRegions();
});

final filtersProvider = StateProvider<SearchFilters>(
  (ref) => const SearchFilters(),
);

/// Home product mode: real-tx link | court | onbid | market insights.
final homeModeProvider = StateProvider<String>((ref) => 'onbid');

/// Insight category chip: 전체 | 재개발정비 | 개발호재
final insightCategoryProvider = StateProvider<String>((ref) => '전체');

final healthProvider = FutureProvider.autoDispose<HealthInfo>((ref) async {
  return ref.watch(apiProvider).health();
});

final searchProvider = FutureProvider.autoDispose<SearchResult>((ref) async {
  final api = ref.watch(apiProvider);
  final filters = ref.watch(filtersProvider);
  final health = await api.health();
  final result = await api.search(filters);

  // 실데이터 키(특히 온비드)가 있으면 데모를 자동 시드하지 않음
  if (result.total == 0 && !health.hasRealKeys) {
    await api.seedDemo();
    return api.search(filters);
  }
  return result;
});

String? _activeSido(List<Region> regions, List<String> regionCodes) {
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

final insightsProvider = FutureProvider.autoDispose<InsightsResult>((ref) async {
  final api = ref.watch(apiProvider);
  final filters = ref.watch(filtersProvider);
  final category = ref.watch(insightCategoryProvider);
  final regions = await ref.watch(regionsProvider.future);
  final activeSido = _activeSido(regions, filters.regionCodes);
  final result = await api.fetchInsights(
    sido: activeSido,
    category: category,
  );
  if (result.total == 0) {
    try {
      await api.ingestInsights();
    } catch (_) {
      // fall through — may still be empty
    }
    return api.fetchInsights(sido: activeSido, category: category);
  }
  return result;
});

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

/// Home product mode: real-tx link | court screening | onbid screening.
final homeModeProvider = StateProvider<String>((ref) => 'onbid');

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

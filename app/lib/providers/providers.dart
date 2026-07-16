import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:map_estate_app/api/estate_api.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:shared_preferences/shared_preferences.dart';

final apiProvider = Provider<EstateApi>((ref) => EstateApi());

final regionsProvider = FutureProvider<List<Region>>((ref) async {
  return ref.watch(apiProvider).fetchRegions();
});

final prefsProvider =
    StateNotifierProvider<PrefsNotifier, UserPrefs>((ref) => PrefsNotifier());

class PrefsNotifier extends StateNotifier<UserPrefs> {
  PrefsNotifier() : super(const UserPrefs()) {
    _load();
  }

  Future<void> _load() async {
    final sp = await SharedPreferences.getInstance();
    state = UserPrefs(
      workLat: sp.getDouble('work_lat'),
      workLng: sp.getDouble('work_lng'),
      workLabel: sp.getString('work_label') ?? '',
      weightPrice: sp.getDouble('w_price') ?? 0.4,
      weightInfra: sp.getDouble('w_infra') ?? 0.3,
      weightCommute: sp.getDouble('w_commute') ?? 0.3,
    );
  }

  Future<void> setWork({
    required double lat,
    required double lng,
    required String label,
  }) async {
    final sp = await SharedPreferences.getInstance();
    await sp.setDouble('work_lat', lat);
    await sp.setDouble('work_lng', lng);
    await sp.setString('work_label', label);
    state = state.copyWith(workLat: lat, workLng: lng, workLabel: label);
  }

  Future<void> setWeights({
    required double price,
    required double infra,
    required double commute,
  }) async {
    final sp = await SharedPreferences.getInstance();
    await sp.setDouble('w_price', price);
    await sp.setDouble('w_infra', infra);
    await sp.setDouble('w_commute', commute);
    state = state.copyWith(
      weightPrice: price,
      weightInfra: infra,
      weightCommute: commute,
    );
  }
}

final filtersProvider = StateProvider<SearchFilters>(
  (ref) => const SearchFilters(
    housingTypes: ['officetel'],
    dealKind: 'rent',
    priceMin: 0,
    priceMax: 30000,
    areaMin: 12,
    areaMax: 50,
    sortBy: 'score',
  ),
);

final searchProvider = FutureProvider.autoDispose<SearchResult>((ref) async {
  final api = ref.watch(apiProvider);
  final filters = ref.watch(filtersProvider);
  final prefs = ref.watch(prefsProvider);
  final health = await api.health();
  final count = health['complex_count'] as int? ?? 0;
  final molit = health['molit_configured'] as bool? ?? false;
  // 실거래 키가 있으면 데모 자동시드하지 않음. 키 없을 때만 빈 DB 시드.
  if (count == 0 && !molit) {
    await api.seedDemo();
  }
  return api.search(filters, prefs: prefs);
});

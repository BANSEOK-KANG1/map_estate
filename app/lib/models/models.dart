class Region {
  final String code;
  final String name;
  final String sido;

  const Region({required this.code, required this.name, required this.sido});

  factory Region.fromJson(Map<String, dynamic> json) => Region(
        code: json['code'] as String,
        name: json['name'] as String,
        sido: json['sido'] as String? ?? '',
      );
}

class ScoreBreakdown {
  final double price;
  final double infrastructure;
  final double commute;
  final double total;

  const ScoreBreakdown({
    required this.price,
    required this.infrastructure,
    required this.commute,
    required this.total,
  });

  factory ScoreBreakdown.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return const ScoreBreakdown(
        price: 0,
        infrastructure: 0,
        commute: 0,
        total: 0,
      );
    }
    return ScoreBreakdown(
      price: (json['price'] as num?)?.toDouble() ?? 0,
      infrastructure: (json['infrastructure'] as num?)?.toDouble() ?? 0,
      commute: (json['commute'] as num?)?.toDouble() ?? 0,
      total: (json['total'] as num?)?.toDouble() ?? 0,
    );
  }
}

class ComplexSummary {
  final int id;
  final String name;
  final String housingType;
  final String housingTypeLabel;
  final String regionCode;
  final String regionName;
  final String dong;
  final String jibun;
  final String roadName;
  final int? buildYear;
  final double? lat;
  final double? lng;
  final int tradeCount;
  final String? dealKind;
  final int? latestPriceManwon;
  final int? latestMonthlyRentManwon;
  final int? medianPriceManwon;
  final int? medianMonthlyRentManwon;
  final double? medianPyeongManwon;
  final double? avgExclusiveArea;
  final double? avgExclusivePyeong;
  final double? priceTrendPct;
  final ScoreBreakdown? scores;
  final String? nearestStation;
  final String? stationLine;
  final int? walkMinutes;
  final int? floorMin;
  final int? floorMax;
  final List<String> tags;
  final int recentDealCount6m;
  final String? facing;
  final bool? moveInOk;
  final int? loanManwon;
  final int? roomCount;
  final int? bathCount;
  final bool? parking;
  final String? thumbnailUrl;
  final DateTime? latestDealDate;
  final DateTime? listedAt;

  const ComplexSummary({
    required this.id,
    required this.name,
    required this.housingType,
    required this.housingTypeLabel,
    required this.regionCode,
    required this.regionName,
    required this.dong,
    required this.jibun,
    required this.roadName,
    required this.buildYear,
    required this.lat,
    required this.lng,
    required this.tradeCount,
    required this.dealKind,
    required this.latestPriceManwon,
    required this.latestMonthlyRentManwon,
    required this.medianPriceManwon,
    required this.medianMonthlyRentManwon,
    required this.medianPyeongManwon,
    required this.avgExclusiveArea,
    this.avgExclusivePyeong,
    required this.priceTrendPct,
    required this.scores,
    this.nearestStation,
    this.stationLine,
    this.walkMinutes,
    this.floorMin,
    this.floorMax,
    this.tags = const [],
    this.recentDealCount6m = 0,
    this.facing,
    this.moveInOk,
    this.loanManwon,
    this.roomCount,
    this.bathCount,
    this.parking,
    this.thumbnailUrl,
    this.latestDealDate,
    this.listedAt,
  });

  factory ComplexSummary.fromJson(Map<String, dynamic> json) => ComplexSummary(
        id: json['id'] as int,
        name: json['name'] as String,
        housingType: json['housing_type'] as String? ?? 'officetel',
        housingTypeLabel: json['housing_type_label'] as String? ?? '',
        regionCode: json['region_code'] as String,
        regionName: json['region_name'] as String? ?? '',
        dong: json['dong'] as String? ?? '',
        jibun: json['jibun'] as String? ?? '',
        roadName: json['road_name'] as String? ?? '',
        buildYear: json['build_year'] as int?,
        lat: (json['lat'] as num?)?.toDouble(),
        lng: (json['lng'] as num?)?.toDouble(),
        tradeCount: json['trade_count'] as int? ?? 0,
        dealKind: json['deal_kind'] as String?,
        latestPriceManwon: json['latest_price_manwon'] as int?,
        latestMonthlyRentManwon: json['latest_monthly_rent_manwon'] as int?,
        medianPriceManwon: json['median_price_manwon'] as int?,
        medianMonthlyRentManwon: json['median_monthly_rent_manwon'] as int?,
        medianPyeongManwon: (json['median_pyeong_manwon'] as num?)?.toDouble(),
        avgExclusiveArea: (json['avg_exclusive_area'] as num?)?.toDouble(),
        avgExclusivePyeong: (json['avg_exclusive_pyeong'] as num?)?.toDouble(),
        priceTrendPct: (json['price_trend_pct'] as num?)?.toDouble(),
        scores: ScoreBreakdown.fromJson(json['scores'] as Map<String, dynamic>?),
        nearestStation: json['nearest_station'] as String?,
        stationLine: json['station_line'] as String?,
        walkMinutes: json['walk_minutes'] as int?,
        floorMin: json['floor_min'] as int?,
        floorMax: json['floor_max'] as int?,
        tags: (json['tags'] as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
        recentDealCount6m: json['recent_deal_count_6m'] as int? ?? 0,
        facing: json['facing'] as String?,
        moveInOk: json['move_in_ok'] as bool?,
        loanManwon: json['loan_manwon'] as int?,
        roomCount: json['room_count'] as int?,
        bathCount: json['bath_count'] as int?,
        parking: json['parking'] as bool?,
        thumbnailUrl: json['thumbnail_url'] as String?,
        latestDealDate: json['latest_deal_date'] == null
            ? null
            : DateTime.tryParse(json['latest_deal_date'] as String),
        listedAt: json['listed_at'] == null
            ? null
            : DateTime.tryParse(json['listed_at'] as String),
      );
}

class TradeOut {
  final DateTime dealDate;
  final String dealKind;
  final double exclusiveArea;
  final int priceManwon;
  final int monthlyRentManwon;
  final int? floor;
  final double pricePerSqmManwon;

  const TradeOut({
    required this.dealDate,
    required this.dealKind,
    required this.exclusiveArea,
    required this.priceManwon,
    required this.monthlyRentManwon,
    required this.floor,
    required this.pricePerSqmManwon,
  });

  factory TradeOut.fromJson(Map<String, dynamic> json) => TradeOut(
        dealDate: DateTime.parse(json['deal_date'] as String),
        dealKind: json['deal_kind'] as String? ?? 'sale',
        exclusiveArea: (json['exclusive_area'] as num).toDouble(),
        priceManwon: json['price_manwon'] as int,
        monthlyRentManwon: json['monthly_rent_manwon'] as int? ?? 0,
        floor: json['floor'] as int?,
        pricePerSqmManwon: (json['price_per_sqm_manwon'] as num).toDouble(),
      );
}

class AreaBucket {
  final String label;
  final double minArea;
  final double maxArea;
  final int tradeCount;
  final int? medianPriceManwon;

  const AreaBucket({
    required this.label,
    required this.minArea,
    required this.maxArea,
    required this.tradeCount,
    required this.medianPriceManwon,
  });

  factory AreaBucket.fromJson(Map<String, dynamic> json) => AreaBucket(
        label: json['label'] as String,
        minArea: (json['min_area'] as num).toDouble(),
        maxArea: (json['max_area'] as num).toDouble(),
        tradeCount: json['trade_count'] as int,
        medianPriceManwon: json['median_price_manwon'] as int?,
      );
}

class PoiSummary {
  final String category;
  final String label;
  final int count;
  final double? nearestDistanceM;

  const PoiSummary({
    required this.category,
    required this.label,
    required this.count,
    required this.nearestDistanceM,
  });

  factory PoiSummary.fromJson(Map<String, dynamic> json) => PoiSummary(
        category: json['category'] as String,
        label: json['label'] as String,
        count: json['count'] as int,
        nearestDistanceM: (json['nearest_distance_m'] as num?)?.toDouble(),
      );
}

class CommuteOut {
  final String mode;
  final double? durationMinutes;
  final double? distanceMeters;
  final double score;
  final String source;

  const CommuteOut({
    required this.mode,
    required this.durationMinutes,
    required this.distanceMeters,
    required this.score,
    required this.source,
  });

  factory CommuteOut.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return const CommuteOut(
        mode: 'none',
        durationMinutes: null,
        distanceMeters: null,
        score: 0,
        source: '',
      );
    }
    return CommuteOut(
      mode: json['mode'] as String? ?? 'driving',
      durationMinutes: (json['duration_minutes'] as num?)?.toDouble(),
      distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
      score: (json['score'] as num?)?.toDouble() ?? 0,
      source: json['source'] as String? ?? '',
    );
  }
}

class ComplexDetail extends ComplexSummary {
  final List<TradeOut> recentTrades;
  final List<AreaBucket> areaBuckets;
  final List<PoiSummary> poiSummary;
  final CommuteOut? commute;
  final List<String> photoUrls;
  final String description;
  final String agentName;
  final String agentPhone;
  final String agentOffice;
  final String dataNote;

  ComplexDetail({
    required super.id,
    required super.name,
    required super.housingType,
    required super.housingTypeLabel,
    required super.regionCode,
    required super.regionName,
    required super.dong,
    required super.jibun,
    required super.roadName,
    required super.buildYear,
    required super.lat,
    required super.lng,
    required super.tradeCount,
    required super.dealKind,
    required super.latestPriceManwon,
    required super.latestMonthlyRentManwon,
    required super.medianPriceManwon,
    required super.medianMonthlyRentManwon,
    required super.medianPyeongManwon,
    required super.avgExclusiveArea,
    super.avgExclusivePyeong,
    required super.priceTrendPct,
    required super.scores,
    super.nearestStation,
    super.stationLine,
    super.walkMinutes,
    super.floorMin,
    super.floorMax,
    super.tags,
    super.recentDealCount6m,
    super.facing,
    super.moveInOk,
    super.loanManwon,
    super.roomCount,
    super.bathCount,
    super.parking,
    super.thumbnailUrl,
    super.latestDealDate,
    super.listedAt,
    required this.recentTrades,
    required this.areaBuckets,
    required this.poiSummary,
    required this.commute,
    this.photoUrls = const [],
    this.description = '',
    this.agentName = '',
    this.agentPhone = '',
    this.agentOffice = '',
    this.dataNote = '',
  });

  factory ComplexDetail.fromJson(Map<String, dynamic> json) {
    final base = ComplexSummary.fromJson(json);
    return ComplexDetail(
      id: base.id,
      name: base.name,
      housingType: base.housingType,
      housingTypeLabel: base.housingTypeLabel,
      regionCode: base.regionCode,
      regionName: base.regionName,
      dong: base.dong,
      jibun: base.jibun,
      roadName: base.roadName,
      buildYear: base.buildYear,
      lat: base.lat,
      lng: base.lng,
      tradeCount: base.tradeCount,
      dealKind: base.dealKind,
      latestPriceManwon: base.latestPriceManwon,
      latestMonthlyRentManwon: base.latestMonthlyRentManwon,
      medianPriceManwon: base.medianPriceManwon,
      medianMonthlyRentManwon: base.medianMonthlyRentManwon,
      medianPyeongManwon: base.medianPyeongManwon,
      avgExclusiveArea: base.avgExclusiveArea,
      avgExclusivePyeong: base.avgExclusivePyeong,
      priceTrendPct: base.priceTrendPct,
      scores: base.scores,
      nearestStation: base.nearestStation,
      stationLine: base.stationLine,
      walkMinutes: base.walkMinutes,
      floorMin: base.floorMin,
      floorMax: base.floorMax,
      tags: base.tags,
      recentDealCount6m: base.recentDealCount6m,
      facing: base.facing,
      moveInOk: base.moveInOk,
      loanManwon: base.loanManwon,
      roomCount: base.roomCount,
      bathCount: base.bathCount,
      parking: base.parking,
      thumbnailUrl: base.thumbnailUrl,
      latestDealDate: base.latestDealDate,
      listedAt: base.listedAt,
      recentTrades: (json['recent_trades'] as List<dynamic>? ?? [])
          .map((e) => TradeOut.fromJson(e as Map<String, dynamic>))
          .toList(),
      areaBuckets: (json['area_buckets'] as List<dynamic>? ?? [])
          .map((e) => AreaBucket.fromJson(e as Map<String, dynamic>))
          .toList(),
      poiSummary: (json['poi_summary'] as List<dynamic>? ?? [])
          .map((e) => PoiSummary.fromJson(e as Map<String, dynamic>))
          .toList(),
      commute: json['commute'] == null
          ? null
          : CommuteOut.fromJson(json['commute'] as Map<String, dynamic>),
      photoUrls: (json['photo_urls'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      description: json['description'] as String? ?? '',
      agentName: json['agent_name'] as String? ?? '',
      agentPhone: json['agent_phone'] as String? ?? '',
      agentOffice: json['agent_office'] as String? ?? '',
      dataNote: json['data_note'] as String? ?? '',
    );
  }
}

class TrendPoint {
  final String yearMonth;
  final double medianPriceManwon;
  final double medianPerSqmManwon;
  final int tradeCount;

  const TrendPoint({
    required this.yearMonth,
    required this.medianPriceManwon,
    required this.medianPerSqmManwon,
    required this.tradeCount,
  });

  factory TrendPoint.fromJson(Map<String, dynamic> json) => TrendPoint(
        yearMonth: json['year_month'] as String,
        medianPriceManwon: (json['median_price_manwon'] as num).toDouble(),
        medianPerSqmManwon: (json['median_per_sqm_manwon'] as num).toDouble(),
        tradeCount: json['trade_count'] as int,
      );
}

class TrendResponse {
  final int complexId;
  final List<TrendPoint> points;

  const TrendResponse({required this.complexId, required this.points});

  factory TrendResponse.fromJson(Map<String, dynamic> json) => TrendResponse(
        complexId: json['complex_id'] as int,
        points: (json['points'] as List<dynamic>)
            .map((e) => TrendPoint.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class SearchResult {
  final int total;
  final List<ComplexSummary> items;
  final String note;
  final String? dataAsOf;
  final String? tradeFrom;
  final String? tradeTo;
  final String dataSource;
  final String? listedAsOf;

  const SearchResult({
    required this.total,
    required this.items,
    required this.note,
    this.dataAsOf,
    this.tradeFrom,
    this.tradeTo,
    this.dataSource = 'demo',
    this.listedAsOf,
  });

  bool get isMolit => dataSource == 'molit';
}

class SearchFilters {
  final String? regionCode;
  final String? query;
  final List<String>? housingTypes;
  final String? dealKind;
  final int? priceMin;
  final int? priceMax;
  final int? monthlyRentMin;
  final int? monthlyRentMax;
  final double? areaMin;
  final double? areaMax;
  final int? buildYearMin;
  final String? stationName;
  final int? maxWalkMinutes;
  final double? maxCommuteMinutes;
  final double? minInfraScore;
  final String sortBy;

  const SearchFilters({
    this.regionCode,
    this.query,
    this.housingTypes,
    this.dealKind,
    this.priceMin,
    this.priceMax,
    this.monthlyRentMin,
    this.monthlyRentMax,
    this.areaMin,
    this.areaMax,
    this.buildYearMin,
    this.stationName,
    this.maxWalkMinutes,
    this.maxCommuteMinutes,
    this.minInfraScore,
    this.sortBy = 'score',
  });

  SearchFilters copyWith({
    String? regionCode,
    String? query,
    List<String>? housingTypes,
    String? dealKind,
    int? priceMin,
    int? priceMax,
    int? monthlyRentMin,
    int? monthlyRentMax,
    double? areaMin,
    double? areaMax,
    int? buildYearMin,
    String? stationName,
    int? maxWalkMinutes,
    double? maxCommuteMinutes,
    double? minInfraScore,
    String? sortBy,
    bool clearRegion = false,
    bool clearQuery = false,
    bool clearStation = false,
    bool clearMaxWalk = false,
    bool clearMonthlyRentMax = false,
    bool clearBuildYearMin = false,
  }) {
    return SearchFilters(
      regionCode: clearRegion ? null : (regionCode ?? this.regionCode),
      query: clearQuery ? null : (query ?? this.query),
      housingTypes: housingTypes ?? this.housingTypes,
      dealKind: dealKind ?? this.dealKind,
      priceMin: priceMin ?? this.priceMin,
      priceMax: priceMax ?? this.priceMax,
      monthlyRentMin: monthlyRentMin ?? this.monthlyRentMin,
      monthlyRentMax:
          clearMonthlyRentMax ? null : (monthlyRentMax ?? this.monthlyRentMax),
      areaMin: areaMin ?? this.areaMin,
      areaMax: areaMax ?? this.areaMax,
      buildYearMin:
          clearBuildYearMin ? null : (buildYearMin ?? this.buildYearMin),
      stationName: clearStation ? null : (stationName ?? this.stationName),
      maxWalkMinutes: clearMaxWalk ? null : (maxWalkMinutes ?? this.maxWalkMinutes),
      maxCommuteMinutes: maxCommuteMinutes ?? this.maxCommuteMinutes,
      minInfraScore: minInfraScore ?? this.minInfraScore,
      sortBy: sortBy ?? this.sortBy,
    );
  }

  Map<String, dynamic> toJson({
    double? workLat,
    double? workLng,
    double weightPrice = 0.35,
    double weightInfra = 0.25,
    double weightCommute = 0.4,
  }) {
    return {
      if (regionCode != null) 'region_code': regionCode,
      if (query != null && query!.isNotEmpty) 'query': query,
      if (housingTypes != null && housingTypes!.isNotEmpty)
        'housing_types': housingTypes,
      if (dealKind != null) 'deal_kind': dealKind,
      if (priceMin != null) 'price_min': priceMin,
      if (priceMax != null) 'price_max': priceMax,
      if (monthlyRentMin != null) 'monthly_rent_min': monthlyRentMin,
      if (monthlyRentMax != null) 'monthly_rent_max': monthlyRentMax,
      if (areaMin != null) 'area_min': areaMin,
      if (areaMax != null) 'area_max': areaMax,
      if (buildYearMin != null) 'build_year_min': buildYearMin,
      if (stationName != null) 'station_name': stationName,
      if (maxWalkMinutes != null) 'max_walk_minutes': maxWalkMinutes,
      if (maxCommuteMinutes != null) 'max_commute_minutes': maxCommuteMinutes,
      if (minInfraScore != null) 'min_infra_score': minInfraScore,
      if (workLat != null) 'work_lat': workLat,
      if (workLng != null) 'work_lng': workLng,
      'sort_by': sortBy,
      'weight_price': weightPrice,
      'weight_infra': weightInfra,
      'weight_commute': weightCommute,
      'limit': 120,
    };
  }
}

class UserPrefs {
  final double? workLat;
  final double? workLng;
  final String workLabel;
  final double weightPrice;
  final double weightInfra;
  final double weightCommute;

  const UserPrefs({
    this.workLat,
    this.workLng,
    this.workLabel = '',
    this.weightPrice = 0.4,
    this.weightInfra = 0.3,
    this.weightCommute = 0.3,
  });

  UserPrefs copyWith({
    double? workLat,
    double? workLng,
    String? workLabel,
    double? weightPrice,
    double? weightInfra,
    double? weightCommute,
  }) {
    return UserPrefs(
      workLat: workLat ?? this.workLat,
      workLng: workLng ?? this.workLng,
      workLabel: workLabel ?? this.workLabel,
      weightPrice: weightPrice ?? this.weightPrice,
      weightInfra: weightInfra ?? this.weightInfra,
      weightCommute: weightCommute ?? this.weightCommute,
    );
  }
}

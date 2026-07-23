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

class InsightScore {
  final double? discountVsAppraisal;
  final double? discountVsMarket;
  final double? infra;
  final double? urgency;
  final double? fail;
  final double? total;

  const InsightScore({
    this.discountVsAppraisal,
    this.discountVsMarket,
    this.infra,
    this.urgency,
    this.fail,
    this.total,
  });

  factory InsightScore.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const InsightScore();
    return InsightScore(
      discountVsAppraisal: (json['discount_vs_appraisal'] as num?)?.toDouble(),
      discountVsMarket: (json['discount_vs_market'] as num?)?.toDouble(),
      infra: (json['infra'] as num?)?.toDouble(),
      urgency: (json['urgency'] as num?)?.toDouble(),
      fail: (json['fail'] as num?)?.toDouble(),
      total: (json['total'] as num?)?.toDouble(),
    );
  }
}

class MarketCompare {
  final int? medianManwon;
  final double? pyeongManwon;
  final int sampleCount;
  final String note;
  final String confidence;

  const MarketCompare({
    this.medianManwon,
    this.pyeongManwon,
    this.sampleCount = 0,
    this.note = '',
    this.confidence = 'low',
  });

  factory MarketCompare.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const MarketCompare();
    return MarketCompare(
      medianManwon: json['median_manwon'] as int?,
      pyeongManwon: (json['pyeong_manwon'] as num?)?.toDouble(),
      sampleCount: json['sample_count'] as int? ?? 0,
      note: json['note'] as String? ?? '',
      confidence: json['confidence'] as String? ?? 'low',
    );
  }
}

class LotSummary {
  final int id;
  final String source;
  final String sourceLabel;
  final String externalId;
  final String caseNo;
  final String courtName;
  final String title;
  final String usage;
  final String address;
  final String? regionCode;
  final String? regionName;
  final String dong;
  final double? exclusiveArea;
  final int? buildYear;
  final String floorInfo;
  final int? appraisalManwon;
  final int? minBidManwon;
  final int failCount;
  final String status;
  final DateTime? bidEndAt;
  final DateTime? saleDate;
  final int? daysLeft;
  final double? lat;
  final double? lng;
  final String sourceUrl;
  final String? thumbnailUrl;
  final String? nearestStation;
  final String? stationLine;
  final int? stationWalkMinutes;
  final InsightScore? scores;
  final MarketCompare? market;
  final List<String> highlights;
  final List<String> riskFlags;

  const LotSummary({
    required this.id,
    required this.source,
    required this.sourceLabel,
    required this.externalId,
    required this.caseNo,
    this.courtName = '',
    required this.title,
    required this.usage,
    required this.address,
    this.regionCode,
    this.regionName,
    required this.dong,
    this.exclusiveArea,
    this.buildYear,
    this.floorInfo = '',
    this.appraisalManwon,
    this.minBidManwon,
    required this.failCount,
    required this.status,
    this.bidEndAt,
    this.saleDate,
    this.daysLeft,
    this.lat,
    this.lng,
    required this.sourceUrl,
    this.thumbnailUrl,
    this.nearestStation,
    this.stationLine,
    this.stationWalkMinutes,
    this.scores,
    this.market,
    this.highlights = const [],
    this.riskFlags = const [],
  });

  factory LotSummary.fromJson(Map<String, dynamic> json) => LotSummary(
        id: json['id'] as int,
        source: json['source'] as String? ?? '',
        sourceLabel: json['source_label'] as String? ?? '',
        externalId: json['external_id'] as String? ?? '',
        caseNo: json['case_no'] as String? ?? '',
        courtName: json['court_name'] as String? ?? '',
        title: json['title'] as String? ?? '',
        usage: json['usage'] as String? ?? '',
        address: json['address'] as String? ?? '',
        regionCode: json['region_code'] as String?,
        regionName: json['region_name'] as String?,
        dong: json['dong'] as String? ?? '',
        exclusiveArea: (json['exclusive_area'] as num?)?.toDouble(),
        buildYear: json['build_year'] as int?,
        floorInfo: json['floor_info'] as String? ?? '',
        appraisalManwon: json['appraisal_manwon'] as int?,
        minBidManwon: json['min_bid_manwon'] as int?,
        failCount: json['fail_count'] as int? ?? 0,
        status: json['status'] as String? ?? '',
        bidEndAt: _parseDt(json['bid_end_at']),
        saleDate: _parseDt(json['sale_date']),
        daysLeft: json['days_left'] as int?,
        lat: (json['lat'] as num?)?.toDouble(),
        lng: (json['lng'] as num?)?.toDouble(),
        sourceUrl: json['source_url'] as String? ?? '',
        thumbnailUrl: json['thumbnail_url'] as String?,
        nearestStation: json['nearest_station'] as String?,
        stationLine: json['station_line'] as String?,
        stationWalkMinutes: json['station_walk_minutes'] as int?,
        scores: InsightScore.fromJson(json['scores'] as Map<String, dynamic>?),
        market: MarketCompare.fromJson(json['market'] as Map<String, dynamic>?),
        highlights: (json['highlights'] as List? ?? []).cast<String>(),
        riskFlags: (json['risk_flags'] as List? ?? []).cast<String>(),
      );
}

class ScheduleItem {
  final int roundNo;
  final DateTime? saleDate;
  final int? minBidManwon;
  final String result;
  final String note;

  const ScheduleItem({
    required this.roundNo,
    this.saleDate,
    this.minBidManwon,
    required this.result,
    this.note = '',
  });

  factory ScheduleItem.fromJson(Map<String, dynamic> json) => ScheduleItem(
        roundNo: json['round_no'] as int? ?? 0,
        saleDate: _parseDt(json['sale_date']),
        minBidManwon: json['min_bid_manwon'] as int?,
        result: json['result'] as String? ?? '',
        note: json['note'] as String? ?? '',
      );
}

class PoiItem {
  final String category;
  final String categoryLabel;
  final int count;
  final double? nearestDistanceM;
  final List<Map<String, dynamic>> places;

  const PoiItem({
    required this.category,
    required this.categoryLabel,
    required this.count,
    this.nearestDistanceM,
    this.places = const [],
  });

  factory PoiItem.fromJson(Map<String, dynamic> json) => PoiItem(
        category: json['category'] as String? ?? '',
        categoryLabel: json['category_label'] as String? ?? '',
        count: json['count'] as int? ?? 0,
        nearestDistanceM: (json['nearest_distance_m'] as num?)?.toDouble(),
        places: (json['places'] as List? ?? [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList(),
      );
}

class LotDetail extends LotSummary {
  final double? landArea;
  final String description;
  final List<String> photoUrls;
  final List<ScheduleItem> schedules;
  final List<PoiItem> pois;
  final LegalRisk? legal;
  final DateTime? bidStartAt;
  final String disclaimer;

  LotDetail({
    required super.id,
    required super.source,
    required super.sourceLabel,
    required super.externalId,
    required super.caseNo,
    super.courtName,
    required super.title,
    required super.usage,
    required super.address,
    super.regionCode,
    super.regionName,
    required super.dong,
    super.exclusiveArea,
    super.buildYear,
    super.floorInfo,
    super.appraisalManwon,
    super.minBidManwon,
    required super.failCount,
    required super.status,
    super.bidEndAt,
    super.saleDate,
    super.daysLeft,
    super.lat,
    super.lng,
    required super.sourceUrl,
    super.thumbnailUrl,
    super.nearestStation,
    super.stationLine,
    super.stationWalkMinutes,
    super.scores,
    super.market,
    super.highlights,
    super.riskFlags,
    this.landArea,
    this.description = '',
    this.photoUrls = const [],
    this.schedules = const [],
    this.pois = const [],
    this.legal,
    this.bidStartAt,
    this.disclaimer = '',
  });

  factory LotDetail.fromJson(Map<String, dynamic> json) {
    final base = LotSummary.fromJson(json);
    return LotDetail(
      id: base.id,
      source: base.source,
      sourceLabel: base.sourceLabel,
      externalId: base.externalId,
      caseNo: base.caseNo,
      courtName: base.courtName,
      title: base.title,
      usage: base.usage,
      address: base.address,
      regionCode: base.regionCode,
      regionName: base.regionName,
      dong: base.dong,
      exclusiveArea: base.exclusiveArea,
      buildYear: base.buildYear,
      floorInfo: base.floorInfo,
      appraisalManwon: base.appraisalManwon,
      minBidManwon: base.minBidManwon,
      failCount: base.failCount,
      status: base.status,
      bidEndAt: base.bidEndAt,
      saleDate: base.saleDate,
      daysLeft: base.daysLeft,
      lat: base.lat,
      lng: base.lng,
      sourceUrl: base.sourceUrl,
      thumbnailUrl: base.thumbnailUrl,
      nearestStation: base.nearestStation,
      stationLine: base.stationLine,
      stationWalkMinutes: base.stationWalkMinutes,
      scores: base.scores,
      market: base.market,
      highlights: base.highlights,
      riskFlags: base.riskFlags,
      landArea: (json['land_area'] as num?)?.toDouble(),
      description: json['description'] as String? ?? '',
      photoUrls: (json['photo_urls'] as List? ?? []).cast<String>(),
      schedules: (json['schedules'] as List? ?? [])
          .map((e) => ScheduleItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      pois: (json['pois'] as List? ?? [])
          .map((e) => PoiItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      legal: LegalRisk.fromJson(json['legal'] as Map<String, dynamic>?),
      bidStartAt: _parseDt(json['bid_start_at']),
      disclaimer: json['disclaimer'] as String? ?? '',
    );
  }
}

class LegalRisk {
  final String orgName;
  final String evictionTarget;
  final String etcNote;
  final String utilizationNote;
  final String locationNote;
  final List<String> riskFlags;
  final List<String> notes;
  final int leaseCount;
  final int occupyCount;
  final int registryCount;
  final List<Map<String, dynamic>> appraisals;
  final List<Map<String, dynamic>> bidRounds;
  final List<String> gaps;
  final String? bidInfoStatus;
  final List<LegalInfoRow> leaseRows;
  final List<LegalInfoRow> occupyRows;
  final List<LegalInfoRow> registryRows;
  final List<ChecklistItem> checklist;
  final List<String> strategyTips;
  final String irosUrl;
  final String irosAddress;
  final String bidHistorySummary;
  final List<String> bidHistoryNotes;
  final String onbidNotice;

  const LegalRisk({
    this.orgName = '',
    this.evictionTarget = '',
    this.etcNote = '',
    this.utilizationNote = '',
    this.locationNote = '',
    this.riskFlags = const [],
    this.notes = const [],
    this.leaseCount = 0,
    this.occupyCount = 0,
    this.registryCount = 0,
    this.appraisals = const [],
    this.bidRounds = const [],
    this.gaps = const [],
    this.bidInfoStatus,
    this.leaseRows = const [],
    this.occupyRows = const [],
    this.registryRows = const [],
    this.checklist = const [],
    this.strategyTips = const [],
    this.irosUrl = 'https://www.iros.go.kr',
    this.irosAddress = '',
    this.bidHistorySummary = '',
    this.bidHistoryNotes = const [],
    this.onbidNotice = '',
  });

  factory LegalRisk.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const LegalRisk();
    return LegalRisk(
      orgName: json['org_name'] as String? ?? '',
      evictionTarget: json['eviction_target'] as String? ?? '',
      etcNote: json['etc_note'] as String? ?? '',
      utilizationNote: json['utilization_note'] as String? ?? '',
      locationNote: json['location_note'] as String? ?? '',
      riskFlags: (json['risk_flags'] as List? ?? []).cast<String>(),
      notes: (json['notes'] as List? ?? []).cast<String>(),
      leaseCount: json['lease_count'] as int? ?? 0,
      occupyCount: json['occupy_count'] as int? ?? 0,
      registryCount: json['registry_count'] as int? ?? 0,
      appraisals: (json['appraisals'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
      bidRounds: (json['bid_rounds'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
      gaps: (json['gaps'] as List? ?? []).cast<String>(),
      bidInfoStatus: json['bid_info_status'] as String?,
      leaseRows: (json['lease_rows'] as List? ?? [])
          .map((e) => LegalInfoRow.fromJson(e as Map<String, dynamic>))
          .toList(),
      occupyRows: (json['occupy_rows'] as List? ?? [])
          .map((e) => LegalInfoRow.fromJson(e as Map<String, dynamic>))
          .toList(),
      registryRows: (json['registry_rows'] as List? ?? [])
          .map((e) => LegalInfoRow.fromJson(e as Map<String, dynamic>))
          .toList(),
      checklist: (json['checklist'] as List? ?? [])
          .map((e) => ChecklistItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      strategyTips: (json['strategy_tips'] as List? ?? []).cast<String>(),
      irosUrl: json['iros_url'] as String? ?? 'https://www.iros.go.kr',
      irosAddress: json['iros_address'] as String? ?? '',
      bidHistorySummary: json['bid_history_summary'] as String? ?? '',
      bidHistoryNotes:
          (json['bid_history_notes'] as List? ?? []).cast<String>(),
      onbidNotice: json['onbid_notice'] as String? ?? '',
    );
  }
}

class LegalInfoRow {
  final String title;
  final String subtitle;
  final List<LegalRowField> fields;

  const LegalInfoRow({
    this.title = '',
    this.subtitle = '',
    this.fields = const [],
  });

  factory LegalInfoRow.fromJson(Map<String, dynamic> json) => LegalInfoRow(
        title: json['title'] as String? ?? '',
        subtitle: json['subtitle'] as String? ?? '',
        fields: (json['fields'] as List? ?? [])
            .map((e) => LegalRowField.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class LegalRowField {
  final String key;
  final String label;
  final String value;

  const LegalRowField({this.key = '', this.label = '', this.value = ''});

  factory LegalRowField.fromJson(Map<String, dynamic> json) => LegalRowField(
        key: json['key'] as String? ?? '',
        label: json['label'] as String? ?? '',
        value: json['value'] as String? ?? '',
      );
}

class ChecklistItem {
  final String id;
  final String title;
  final String detail;
  final int priority;
  final String status;
  final String? link;

  const ChecklistItem({
    required this.id,
    required this.title,
    this.detail = '',
    this.priority = 2,
    this.status = 'todo',
    this.link,
  });

  factory ChecklistItem.fromJson(Map<String, dynamic> json) => ChecklistItem(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        detail: json['detail'] as String? ?? '',
        priority: json['priority'] as int? ?? 2,
        status: json['status'] as String? ?? 'todo',
        link: json['link'] as String?,
      );
}

class SearchFilters {
  final List<String> sources;
  final List<String> regionCodes;
  final List<String> usages;
  final int? minPriceManwon;
  final int? maxPriceManwon;
  final int? minFailCount;
  final String? status;
  final String? q;
  final String sort;

  const SearchFilters({
    this.sources = const ['onbid', 'court'],
    this.regionCodes = const [],
    this.usages = const [],
    this.minPriceManwon,
    this.maxPriceManwon,
    this.minFailCount,
    this.status = 'active',
    this.q,
    this.sort = 'score',
  });

  SearchFilters copyWith({
    List<String>? sources,
    List<String>? regionCodes,
    List<String>? usages,
    int? minPriceManwon,
    int? maxPriceManwon,
    int? minFailCount,
    String? status,
    String? q,
    String? sort,
  }) =>
      SearchFilters(
        sources: sources ?? this.sources,
        regionCodes: regionCodes ?? this.regionCodes,
        usages: usages ?? this.usages,
        minPriceManwon: minPriceManwon ?? this.minPriceManwon,
        maxPriceManwon: maxPriceManwon ?? this.maxPriceManwon,
        minFailCount: minFailCount ?? this.minFailCount,
        status: status ?? this.status,
        q: q ?? this.q,
        sort: sort ?? this.sort,
      );

  Map<String, dynamic> toJson() => {
        'sources': sources,
        if (regionCodes.isNotEmpty) 'region_codes': regionCodes,
        if (usages.isNotEmpty) 'usages': usages,
        if (minPriceManwon != null) 'min_price_manwon': minPriceManwon,
        if (maxPriceManwon != null) 'max_price_manwon': maxPriceManwon,
        if (minFailCount != null) 'min_fail_count': minFailCount,
        if (status != null) 'status': status,
        if (q != null && q!.isNotEmpty) 'q': q,
        'sort': sort,
        'limit': 100,
      };
}

class SearchResult {
  final int total;
  final List<LotSummary> items;

  const SearchResult({required this.total, required this.items});
}

DateTime? _parseDt(dynamic v) {
  if (v == null) return null;
  if (v is String && v.isNotEmpty) {
    return DateTime.tryParse(v);
  }
  return null;
}

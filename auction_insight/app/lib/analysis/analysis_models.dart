class MoneyTriple {
  final int won;
  final double manwon;
  final double eok;
  final String labelWon;
  final String labelManwon;
  final String labelEok;

  const MoneyTriple({
    required this.won,
    required this.manwon,
    required this.eok,
    required this.labelWon,
    required this.labelManwon,
    required this.labelEok,
  });

  factory MoneyTriple.fromJson(Map<String, dynamic> json) => MoneyTriple(
        won: json['won'] as int? ?? 0,
        manwon: (json['manwon'] as num?)?.toDouble() ?? 0,
        eok: (json['eok'] as num?)?.toDouble() ?? 0,
        labelWon: json['label_won'] as String? ?? '',
        labelManwon: json['label_manwon'] as String? ?? '',
        labelEok: json['label_eok'] as String? ?? '',
      );

  static MoneyTriple? maybe(dynamic json) {
    if (json is! Map) return null;
    return MoneyTriple.fromJson(Map<String, dynamic>.from(json));
  }

  String get multiLine => '$labelWon\n$labelManwon\n$labelEok';
}

class AnalysisItemSummary {
  final int id;
  final String source;
  final String title;
  final String address;
  final String usage;
  final String caseNo;
  final MoneyTriple? appraisal;
  final MoneyTriple? minBid;
  final MoneyTriple? plannedPrice;
  final List<Map<String, dynamic>> digitWarnings;
  final String verdict;
  final double? lat;
  final double? lng;

  const AnalysisItemSummary({
    required this.id,
    required this.source,
    required this.title,
    required this.address,
    this.usage = '',
    this.caseNo = '',
    this.appraisal,
    this.minBid,
    this.plannedPrice,
    this.digitWarnings = const [],
    this.verdict = 'HOLD',
    this.lat,
    this.lng,
  });

  factory AnalysisItemSummary.fromJson(Map<String, dynamic> json) =>
      AnalysisItemSummary(
        id: json['id'] as int,
        source: json['source'] as String? ?? '',
        title: json['title'] as String? ?? '',
        address: json['address'] as String? ?? '',
        usage: json['usage'] as String? ?? '',
        caseNo: json['case_no'] as String? ?? '',
        appraisal: MoneyTriple.maybe(json['appraisal']),
        minBid: MoneyTriple.maybe(json['min_bid']),
        plannedPrice: MoneyTriple.maybe(json['planned_price']),
        digitWarnings: (json['digit_warnings'] as List? ?? [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList(),
        verdict: json['verdict'] as String? ?? 'HOLD',
        lat: (json['lat'] as num?)?.toDouble(),
        lng: (json['lng'] as num?)?.toDouble(),
      );
}

class AnalysisItemDetail extends AnalysisItemSummary {
  final String courtOrOrg;
  final String sourceUrl;
  final String notes;
  final Map<String, dynamic> finance;
  final Map<String, dynamic> costBreakdown;
  final Map<String, dynamic>? bidCeiling;
  final List<Map<String, dynamic>> loanScenarios;
  final Map<String, dynamic> whatIf;
  final List<String> missingDocs;
  final bool beginnerBan;
  final List<String> checkNext;
  final String rightsStatusNote;
  final List<Map<String, dynamic>> documents;

  AnalysisItemDetail({
    required super.id,
    required super.source,
    required super.title,
    required super.address,
    super.usage,
    super.caseNo,
    super.appraisal,
    super.minBid,
    super.plannedPrice,
    super.digitWarnings,
    super.verdict,
    super.lat,
    super.lng,
    this.courtOrOrg = '',
    this.sourceUrl = '',
    this.notes = '',
    this.finance = const {},
    this.costBreakdown = const {},
    this.bidCeiling,
    this.loanScenarios = const [],
    this.whatIf = const {},
    this.missingDocs = const [],
    this.beginnerBan = true,
    this.checkNext = const [],
    this.rightsStatusNote = '',
    this.documents = const [],
  });

  factory AnalysisItemDetail.fromJson(Map<String, dynamic> json) {
    final base = AnalysisItemSummary.fromJson(json);
    return AnalysisItemDetail(
      id: base.id,
      source: base.source,
      title: base.title,
      address: base.address,
      usage: base.usage,
      caseNo: base.caseNo,
      appraisal: base.appraisal,
      minBid: base.minBid,
      plannedPrice: base.plannedPrice,
      digitWarnings: base.digitWarnings,
      verdict: base.verdict,
      lat: base.lat,
      lng: base.lng,
      courtOrOrg: json['court_or_org'] as String? ?? '',
      sourceUrl: json['source_url'] as String? ?? '',
      notes: json['notes'] as String? ?? '',
      finance: Map<String, dynamic>.from(json['finance'] as Map? ?? {}),
      costBreakdown:
          Map<String, dynamic>.from(json['cost_breakdown'] as Map? ?? {}),
      bidCeiling: json['bid_ceiling'] is Map
          ? Map<String, dynamic>.from(json['bid_ceiling'] as Map)
          : null,
      loanScenarios: (json['loan_scenarios'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
      whatIf: Map<String, dynamic>.from(json['what_if'] as Map? ?? {}),
      missingDocs: (json['missing_docs'] as List? ?? []).cast<String>(),
      beginnerBan: json['beginner_ban'] as bool? ?? true,
      checkNext: (json['check_next'] as List? ?? []).cast<String>(),
      rightsStatusNote: json['rights_status_note'] as String? ?? '',
      documents: (json['documents'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
    );
  }
}

String verdictLabelKo(String v) => switch (v) {
      'REVIEW_OK' => '검토 가능',
      'REVIEW_CONDITIONAL' => '조건부 검토',
      'HOLD' => '입찰 보류',
      'BEGINNER_BAN' => '초보자 입찰 금지',
      _ => v,
    };

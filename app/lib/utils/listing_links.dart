import 'package:map_estate_app/models/models.dart';

/// 실시간 호가 포털 딥링크 (스크래핑 없음).
///
/// 네이버 PC(fin.land) 쿼리:
/// - tradeTypes: A1 매매 / B1 전세 / B2 월세 (구분자 `-`)
/// - realEstateTypes: A01 아파트 / A02 오피스텔 / A04 재건축 /
///   C01 원룸 / C02 빌라 / C03 단독다가구 (구분자 `-`)
///
/// ※ fin.land 기본값이 매매+전세 / 아파트+재건축이라,
///    쿼리 없이 열면 월세·원룸이 아님.
class ListingLinks {
  ListingLinks._();

  static const _regionCenter = <String, (double, double)>{
    '강남구': (37.5172, 127.0473),
    '강동구': (37.5301, 127.1238),
    '강북구': (37.6396, 127.0257),
    '강서구': (37.5509, 126.8495),
    '관악구': (37.4784, 126.9516),
    '광진구': (37.5384, 127.0822),
    '구로구': (37.4954, 126.8874),
    '금천구': (37.4563, 126.8955),
    '노원구': (37.6542, 127.0568),
    '도봉구': (37.6688, 127.0471),
    '동대문구': (37.5744, 127.0396),
    '동작구': (37.5124, 126.9393),
    '마포구': (37.5663, 126.9019),
    '서대문구': (37.5791, 126.9368),
    '서초구': (37.4837, 127.0324),
    '성동구': (37.5633, 127.0366),
    '성북구': (37.5894, 127.0167),
    '송파구': (37.5145, 127.1059),
    '양천구': (37.5170, 126.8664),
    '영등포구': (37.5264, 126.8962),
    '용산구': (37.5326, 126.9900),
    '은평구': (37.6027, 126.9291),
    '종로구': (37.5735, 126.9788),
    '중구': (37.5636, 126.9970),
    '중랑구': (37.6063, 127.0925),
  };

  static const _cortarNo = <String, String>{
    '강남구': '1168000000',
    '강동구': '1174000000',
    '강북구': '1130500000',
    '강서구': '1150000000',
    '관악구': '1162000000',
    '광진구': '1121500000',
    '구로구': '1153000000',
    '금천구': '1154500000',
    '노원구': '1135000000',
    '도봉구': '1132000000',
    '동대문구': '1123000000',
    '동작구': '1159000000',
    '마포구': '1144000000',
    '서대문구': '1141000000',
    '서초구': '1165000000',
    '성동구': '1120000000',
    '성북구': '1129000000',
    '송파구': '1171000000',
    '양천구': '1147000000',
    '영등포구': '1156000000',
    '용산구': '1117000000',
    '은평구': '1138000000',
    '종로구': '1111000000',
    '중구': '1114000000',
    '중랑구': '1126000000',
  };

  static String queryFor(ComplexSummary c) {
    final parts = <String>[
      '서울',
      if (c.regionName.isNotEmpty) c.regionName,
      if (c.dong.isNotEmpty) c.dong,
      c.name,
      if (c.dealKind != 'sale') '월세',
      '원룸',
      '오피스텔',
    ];
    return parts.join(' ').trim();
  }

  static (double, double)? _coords(ComplexSummary c) {
    if (c.lat != null && c.lng != null) return (c.lat!, c.lng!);
    return _regionCenter[c.regionName];
  }

  /// fin.land realEstateTypes (아파트/재건축 제외)
  static String _finPropertyTypes(ComplexSummary c) {
    switch (c.housingType) {
      case 'officetel':
        return 'A02-C01'; // 오피스텔-원룸
      case 'villa':
        return 'C02-C01'; // 빌라-원룸
      case 'multi':
        return 'C03-C01-C02'; // 단독다가구-원룸-빌라
      default:
        return 'C01-A02'; // 원룸-오피스텔
    }
  }

  /// m.land path 유형 코드
  static String _mPropertyTypes(ComplexSummary c) {
    switch (c.housingType) {
      case 'officetel':
        return 'OPST:OR';
      case 'villa':
        return 'VL:OR';
      case 'multi':
        return 'DDDGG:OR:VL';
      default:
        return 'OR:OPST';
    }
  }

  static String _tradeCode(ComplexSummary c) {
    // 매매 / 월세(전월세 필터의 호가 교차 기본)
    return c.dealKind == 'sale' ? 'A1' : 'B2';
  }

  /// 네이버 부동산 — PC(fin.land)에 월세·원룸·오피 쿼리 고정
  static Uri naver(ComplexSummary c) {
    final coords = _coords(c);
    final trade = _tradeCode(c);
    final types = _finPropertyTypes(c);
    if (coords != null) {
      final (lat, lng) = coords;
      return Uri.https('fin.land.naver.com', '/map', {
        'lat': lat.toString(),
        'lon': lng.toString(),
        'zoom': '17',
        'tradeTypes': trade, // B2=월세
        'realEstateTypes': types, // C01=원룸, A02=오피스텔
      });
    }
    return naverSearch(c);
  }

  /// 모바일 m.land (백업) — path에 OR/B2 고정
  static Uri naverMobile(ComplexSummary c) {
    final coords = _coords(c);
    if (coords == null) return naverSearch(c);
    final (lat, lng) = coords;
    final cortar = _cortarNo[c.regionName];
    final loc = cortar == null ? '$lat:$lng:17' : '$lat:$lng:17:$cortar';
    return Uri.parse(
      'https://m.land.naver.com/map/$loc/${_mPropertyTypes(c)}/${_tradeCode(c)}',
    );
  }

  static Uri naverSearch(ComplexSummary c) {
    final q = Uri.encodeComponent(queryFor(c));
    return Uri.parse('https://m.land.naver.com/search/result/$q');
  }

  static Uri zigbang(ComplexSummary c) {
    final coords = _coords(c);
    if (coords != null) {
      final (lat, lng) = coords;
      return Uri.parse(
        'https://www.zigbang.com/home/oneroom/map'
        '?lat=$lat&lng=$lng&zoom=3',
      );
    }
    return Uri.https('www.zigbang.com', '/search/map', {
      'keyword': queryFor(c),
    });
  }
}

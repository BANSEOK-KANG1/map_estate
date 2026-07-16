# API 키 가이드

## 1. 국토교통부 실거래가 (원룸·다가구)

1. [공공데이터포털](https://www.data.go.kr) 가입
2. 아래 API 활용 신청
   - 오피스텔 매매 / 전월세
   - 연립다세대 매매 / 전월세
   - 단독다가구 매매 / 전월세
3. 마이페이지 → 일반 인증키(Decoding) 복사
4. `backend/.env`에 설정:

```
MOLIT_SERVICE_KEY=발급키
```

실거래는 신고일 기준으로 **1~2개월 지연**될 수 있습니다.

## 2. 카카오 (상권·출퇴근·지오코딩)

1. [Kakao Developers](https://developers.kakao.com) 앱 생성
2. **REST API 키** 발급
3. 앱 설정에서 **Kakao Map / Local** 관련 서비스 활성화
4. `backend/.env`:

```
KAKAO_REST_KEY=REST_API_키
```

사용 API:

- Local Address / Keyword — 단지 좌표
- Local Category — 지하철·학교·병원·마트·카페 등
- Mobility Directions — 차량 ETA (실패 시 직선거리 휴리스틱)

### Flutter 지도 (선택)

현재 클라이언트 지도는 OpenStreetMap 타일(`flutter_map`)입니다.  
카카오 지도 SDK를 쓰려면 Native/JavaScript 키를 발급하고 도메인을 등록한 뒤
`kakao_maps_flutter`로 교체하면 됩니다.

```
flutter run --dart-define=KAKAO_NATIVE_KEY=... --dart-define=KAKAO_JS_KEY=...
```

## 3. CORS / 로컬 URL

`CORS_ORIGINS`에 Flutter Web 오리진을 추가하세요.

```
CORS_ORIGINS=http://localhost:*,http://127.0.0.1:*,http://localhost:8080
```

FastAPI 예시는 쉼표 구분 목록입니다. 필요 시 `backend/app/config.py`의 기본값을 수정하세요.

# API 키 가이드

## 1. 캠코 온비드 (공매)

1. [공공데이터포털](https://www.data.go.kr) 가입
2. [온비드 캠코공매물건조회서비스](https://www.data.go.kr/data/15000851/openapi.do) 등 활용 신청
3. 일반 인증키(Decoding) 복사
4. `auction_insight/backend/.env`:

```
ONBID_SERVICE_KEY=발급키
```

### 호출 제한·주의

- 일부 온비드 엔드포인트는 **파이썬 클라이언트 요청을 제한**한다고 안내합니다.  
  수집기는 Browser-like `User-Agent`와 페이지 간 delay(약 0.35s)를 사용합니다.
- 개발 계정 트래픽은 일일 한도가 있습니다. `max_pages`를 작게 두고 캐시/DB에 적재하세요.
- MVP는 **서울·경기·인천 주소**만 upsert합니다.

## 2. 국토교통부 실거래가 (시세 비교)

1. 공공데이터포털에서 아파트/오피스텔/연립다세대 매매 API 신청
2. `.env`:

```
MOLIT_SERVICE_KEY=발급키
```

물건 용도에 따라 아파트·오피스텔·연립 엔드포인트를 골라 인근 중위가를 추정합니다.  
표본이 3건 미만이면 상세에 안내 문구를 표시합니다.

## 3. 카카오 (지오코딩·상권)

1. [Kakao Developers](https://developers.kakao.com) 앱 생성
2. REST API 키 + Local 서비스 활성화
3. `.env`:

```
KAKAO_REST_KEY=REST_API_키
```

사용: 주소 지오코딩, 지하철·학교·병원·마트·카페·음식점 POI.

## 4. 재개발·정비사업 / 호재 뉴스 (홈 「호재」)

### 정비사업

**추가 키 발급 없음.** `auction_insight/backend/.env`의 기존 `MOLIT_SERVICE_KEY`를 재사용합니다.

수집 순서 (`POST /api/ingest/insights`):

1. [전국재개발재건축정비사업표준데이터](https://www.data.go.kr/data/15155703/standard.do) OpenAPI  
   - 동일 포털 키로 호출. 해당 데이터셋에 **활용신청이 안 되어 있으면** 포털에서 한 번만 신청(자동승인)하면 됩니다.
2. OpenAPI가 0건/미등록이면 → **로그인·키 없이** 내려받는 지자체 CSV 폴백  
   (서울 성북·서초·강남, 경기 부천·고양·안양·남양주, 인천 정비·도시개발 등)

조회: `GET /api/insights?sido=&category=`

### 뉴스 RSS (링크만)

- Google News RSS로 `재개발` / `정비구역` / `도시개발` × 지역 검색
- **제목·URL·출처·일시만** 저장 (본문 미수집)
- 별도 API 키 불필요

설정 화면 **「호재 인사이트 갱신」**으로 수동 최신화합니다.

## 5. CORS / 포트

백엔드 기본 포트는 **8001** (map_estate 8000과 분리).

```
CORS_ORIGINS=http://localhost:*,http://127.0.0.1:*,*
```

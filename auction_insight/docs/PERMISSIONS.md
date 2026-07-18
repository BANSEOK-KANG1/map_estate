# 사용자 권한이 필요한 항목 (체크리스트)

아래는 **본인 계정 로그인 후 활용신청/키 발급**이 필요합니다.  
에이전트가 대신 로그인·신청할 수 없습니다.

## A. 국토부 실거래 API (시세 정확도)

이미 오피스텔 매매는 동작합니다. 아래를 **추가 활용신청**하세요.  
(같은 일반 인증키로 여러 API를 묶을 수 있는 경우가 많습니다.)

| 우선 | API | 신청 페이지 |
|------|-----|-------------|
| 1 | 아파트 매매 실거래 | https://www.data.go.kr/data/15126469/openapi.do |
| 2 | 연립다세대 매매 실거래 | https://www.data.go.kr/data/15126467/openapi.do |
| 3 | (선택) 단독/다가구 매매 | 공공데이터포털에서 `RTMSDataSvcSHTrade` 검색 |

신청 후 승인되면 알려주세요. 서버 재시작 없이 enrich만 다시 돌리면 됩니다.

```bash
curl -X POST http://127.0.0.1:8001/api/enrich \
  -H 'Content-Type: application/json' \
  -d '{"limit":50,"fetch_market":true,"fetch_pois":false}'
```

## B. 카카오 REST 키 (지오코딩·상권)

1. https://developers.kakao.com 로그인
2. 내 애플리케이션 → 앱 선택/생성
3. 앱 키 → **REST API 키** 복사
4. **제품 설정**에서 **카카오맵**(또는 OPEN_MAP_AND_LOCAL / 로컬) **활성화**  
   - 키만 넣고 제품을 안 켜면 `NotAuthorizedError: disabled OPEN_MAP_AND_LOCAL` 발생
5. `auction_insight/backend/.env` 에:

```
KAKAO_REST_KEY=여기에_REST키
```

6. API 서버 재시작 후:

```bash
curl -X POST http://127.0.0.1:8001/api/enrich \
  -H 'Content-Type: application/json' \
  -d '{"limit":50,"fetch_market":true,"fetch_pois":true}'
```

또는 채팅에 REST 키만 보내 주시면 `.env`에 넣어 드리겠습니다. (커밋하지 않음)

## C. 온비드 / 차세대 온비드

| 항목 | 상태 | 할 일 |
|------|------|--------|
| 부동산 물건목록 | 동작 중 (`apis.data.go.kr`) | — |
| 부동산 물건상세 | 동작 중 (권리·특약·감정평가 요약) | enrich `fetch_detail` |
| 물건상세 입찰정보 (회차별 최저가·입찰팀) | **403 — 활용신청 필요** | https://www.data.go.kr/data/15157251/openapi.do |
| 물건 입찰결과목록 | **403 — 활용신청 필요** | https://www.data.go.kr/data/15157252/openapi.do |
| 물건 입찰결과상세 | 엔드포인트는 열림, 진행중 물건은 NODATA | https://www.data.go.kr/data/15157254/openapi.do |

유치권·법정지상권 등은 OpenAPI에 전용 필드가 거의 없습니다.  
물건상세의 기타사항/임대차/점유/등기 목록 + **감정평가서·등기부등본**으로 확인해야 합니다.

## D. 에이전트가 지금 한 것

- 온비드 연결 **재시도** → 여전히 ConnectTimeout
- 국토부 오피스텔 시세로 **14건 중 13건 enrich** 완료
- 이 체크리스트·신청 링크 정리

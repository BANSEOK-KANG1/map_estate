# 실데이터 전환 가이드

데모 → 실데이터는 **캠코 온비드(공매)** 가 1차 소스입니다.  
법원 경매는 공식 OpenAPI가 없어 당분간 데모/수동·제휴만 가능합니다.

## 1. API 키

`auction_insight/backend/.env`:

| 키 | 용도 | 필수 |
|----|------|------|
| `ONBID_SERVICE_KEY` | 공매 물건 수집 | **필수** |
| `MOLIT_SERVICE_KEY` | 인근 실거래 시세 | 권장 |
| `KAKAO_REST_KEY` | 지오코딩·상권 | 권장 |

발급: [docs/API_KEYS.md](API_KEYS.md)

## 2. 서버 재시작

`.env` 변경 후:

```bash
cd auction_insight/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## 3. 수집 / enrich

```bash
# 온비드 실공매 (서버 연결 가능 시)
bash auction_insight/backend/scripts/ingest_real.sh

# 국토부 시세만 다시 계산
curl -X POST http://127.0.0.1:8001/api/enrich \
  -H 'Content-Type: application/json' \
  -d '{"limit":50,"fetch_market":true,"fetch_pois":false}'
```

## 4. 상태 확인

```bash
curl -s http://127.0.0.1:8001/api/health | python3 -m json.tool
```

## 5. 온비드 수집 경로 (우회)

| 경로 | 호스트 | 비고 |
|------|--------|------|
| **1순위 (현재 사용)** | `apis.data.go.kr` 차세대 부동산 목록 | 레거시 장애와 무관하게 동작 |
| 2순위 폴백 | `openapi.onbid.co.kr` 레거시 | 종종 ConnectTimeout |

차세대 목록: [부동산 물건목록](https://www.data.go.kr/data/15157207/openapi.do)  
입찰결과 상세 등은 별도 활용신청: [입찰결과상세](https://www.data.go.kr/data/15157254/openapi.do)

## 6. 기타 제약

- 국토부 실거래: 아파트/연립/오피스텔 승인 상태에 따라 enrich 소스 달라짐
- 카카오 키 없음 → 실지오코딩/상권 불가 (데모 POI 유지)

## 7. 법원 경매

공식 API 없음 → [COURT_ADAPTER.md](COURT_ADAPTER.md)

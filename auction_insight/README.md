# Auction Insight — 경·공매 인사이트

Flutter + FastAPI로 **법원 경매·캠코 공매** 물건을 지도에서 보고,  
주변 상권·인근 실거래 시가와 비교하는 MVP입니다. (서울·경기·인천)

기존 `map_estate`(원룸 실거래)와는 독립 앱입니다. 같은 저장소에만 공존합니다.

## 경·공매 분석 랩 (Phase 1–6)

심층 분석 도메인은 기존 `AuctionLot` 스크리닝과 분리된 모듈입니다.

- 설계: [docs/ANALYSIS_MODULE.md](docs/ANALYSIS_MODULE.md)
- 보안·배포: [docs/PHASE6_SECURITY_DEPLOY.md](docs/PHASE6_SECURITY_DEPLOY.md)
- API: `/api/analysis/*` (등록 · 문서함 · 권리·점유 · 대출 · lot 연동)
- UI: 홈 모드 [실거래|법원경매|온비드공매] · 물건상세「심층 분석」· `/analysis/:id` 7탭

AI는 입찰을 결정하지 않으며, 필수문서 부족 시 권리 확정 금지·초보자 입찰 금지를 표시합니다.

### 옵시디언 — 스크리닝 점수·가중치

정보 enrich 시 쓰는 할인·POI·마감·종합점수 공식 정리:

- 볼트 폴더: [docs/obsidian-vault](docs/obsidian-vault)  
- Obsidian에서 **Open folder as vault** → 해당 폴더  
- 시작 노트: `00-스크리닝-점수-MOC.md`

## 구조

```
auction_insight/
  app/          Flutter 클라이언트
  backend/      FastAPI (수집·점수·API)
  docs/         API 키·어댑터 가이드
```

## 빠른 시작

### 1) 백엔드

```bash
cd auction_insight/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

데모 시드:

```bash
curl -X POST http://127.0.0.1:8001/api/demo/seed
```

API 문서: http://127.0.0.1:8001/docs

### 2) Flutter

```bash
cd auction_insight/app
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8001
```

## 배포

### Render (예전에 map_estate에 쓰신 방식 · 추천)

PC 켤 필요 없음. 무료 플랜은 **안 쓰면 잠들고**, 링크 열면 다시 켜집니다.

```bash
bash scripts/deploy_auction_render.sh
```

1. GitHub에 push  
2. [Render Dashboard](https://dashboard.render.com) → New → Blueprint → `auction_insight/render.yaml`  
3. Environment: `ONBID_SERVICE_KEY`, `MOLIT_SERVICE_KEY`, `KAKAO_REST_KEY`  
4. 배포 URL 예: `https://auction-insight.onrender.com`  
5. 첫 접속 후 설정에서 **온비드 수집** 한 번 (무료 플랜은 DB가 재시작 시 비워질 수 있음)

### Fly.io (선택)

카드 등록 필요. 개인용 auto-stop 설정 있음: `bash scripts/deploy_auction_fly.sh`

## 실데이터 연동

키 발급: [docs/API_KEYS.md](docs/API_KEYS.md)  
전환 절차: [docs/REAL_DATA.md](docs/REAL_DATA.md)

```
ONBID_SERVICE_KEY=...   # 필수 (공매)
MOLIT_SERVICE_KEY=...   # 권장 (시세)
KAKAO_REST_KEY=...      # 권장 (지도·상권)
```

```bash
bash auction_insight/backend/scripts/ingest_real.sh
```

## 주요 화면

- 홈: 실거래 | 법원 | 온비드 | **호재** + 지역 필터 + 지도/목록(또는 인사이트 목록)
- 호재: 재개발·정비사업(공공) + 개발호재 뉴스 링크 (본문 미수집)
- 상세: 감정가·최저가·시세 비교, 유찰 이력, 상권, 원문 링크
- 설정: API Base URL · 호재 인사이트 갱신

## API 요약

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/health` | 상태 |
| GET | `/api/regions` | 서울·경기·인천 시군구 |
| POST | `/api/search` | 조건 검색 |
| GET | `/api/lots/{id}` | 물건 상세 |
| GET | `/api/insights` | 호재 인사이트 목록 |
| POST | `/api/ingest/insights` | 정비사업·뉴스 링크 갱신 |
| POST | `/api/ingest/onbid` | 온비드 수집 |
| POST | `/api/demo/seed` | 데모 시드 |

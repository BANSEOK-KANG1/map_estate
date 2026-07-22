# 경·공매 분석 모듈 (Auction Analysis Lab)

> AI는 입찰 여부를 결정하지 않는다.  
> 공식 문서 → 권리 → 점유 → 대출 → 필요현금 → 총투입액 → 적정 입찰 상한 → 현장조사  
> 순서로 **사용자 판단을 돕는** 모듈이다.

## 0. 현재 코드베이스 요약 (감사)

### 루트 `map_estate` (실거래)
| 경로 | 역할 |
|------|------|
| `app/` | Flutter · Complex 지도/목록/상세(`complex_detail_screen`) |
| `backend/app/` | FastAPI · `Complex`/`Deal` · 국토부 실거래 ingest |
| `render.yaml` | `map-estate` Docker 서비스 |

### `auction_insight/` (기존 경공매 MVP)
| 경로 | 역할 |
|------|------|
| `app/` | Flutter · 온비드 목록/지도/권리요약/초보가이드 |
| `backend/app/` | `AuctionLot` · 온비드 ingest · enrich · 검색 |
| `render.yaml` | `auction-insight` · map.measuremkt.com |

**원칙:** 실거래 앱/API는 삭제·전면 재작성하지 않는다.  
분석 도메인은 `auction_insight/backend/app/analysis/` · `auction_insight/app/lib/analysis/` 로 **추가**한다.  
기존 `AuctionLot`는 수집·지도 스크리닝용으로 유지하고, 심층 분석은 `AuctionItem`으로 연결(선택 FK)한다.

---

## 1. 변경·신규 파일

### Backend (신규)
- `app/analysis/models.py` — AuctionItem, AuctionDocument, RightEntry, OccupancyClaim, AnalysisRun, FinanceProfile, LoanScenario, RuleConfig
- `app/analysis/money.py` — 원/만원/억 표시 · 자릿수 오류 감지
- `app/analysis/calculator.py` — 총투입액 · 입찰상한 · 시나리오
- `app/analysis/rules.py` — RuleConfig 시드/조회 (LTV·DSR·취득세)
- `app/analysis/storage.py` — DocumentStore 추상화 (local → S3 교체)
- `app/analysis/service.py` · `schemas.py` · `router.py`
- `tests/test_money.py` · `tests/test_calculator.py`

### Backend (수정)
- `app/main.py` — analysis router include
- `app/db.py` — analysis 모델 import (create_all)

### Flutter (신규)
- `lib/analysis/*` — models, money UI, calculator, detail tabs, manual form
- 모드: 실거래 / 법원경매 / 온비드공매

### Flutter (수정)
- `lib/screens/home_screen.dart` — 모드 세그먼트
- `lib/main.dart` — 라우트
- 루트 `app/lib/screens/home_screen.dart` — 모드 칩(실거래 유지, 경공매는 URL/딥링크)

---

## 2. DB 모델 (요약)

| 모델 | 핵심 |
|------|------|
| **AuctionItem** | source=`court`\|`onbid`, 주소, 감정가/최저가/예정가(**원 단위 정수**), lot_id FK optional |
| **AuctionDocument** | type, storage_key, page_count, extracted_text, masked, confirmed_at |
| **RightEntry** | kind, priority, amount_won, status=`UNKNOWN`\|`HOLD`\|…, evidence_* |
| **OccupancyClaim** | housing\|commercial 분리 필드, 대항력 입력, status |
| **AnalysisRun** | verdict, missing_docs[], notes, created_at |
| **FinanceProfile** | 목표마진, 보수적처분가, 비용 항목들(원) |
| **LoanScenario** | conservative/base/optimistic 한도, rule_ids |
| **RuleConfig** | key, effective_from, region, usage, value_json, source_url |

문서 없으면 권리 **확정 금지** → `UNKNOWN` / `HOLD`.

---

## 3. API 설계 (Phase 1)

```
POST /api/analysis/items              # 수동 등록
GET  /api/analysis/items              # 목록 (?source=court|onbid)
GET  /api/analysis/items/{id}         # 상세+계산 스냅샷
PATCH /api/analysis/items/{id}/finance
POST /api/analysis/items/{id}/recompute
POST /api/analysis/money/validate     # 자릿수 검수
GET  /api/analysis/rules              # RuleConfig
```

Phase 2+: documents upload, rights CRUD, occupancy, LLM summarize (설명 only).

---

## 4. 판정 · 공식

**판정:** `REVIEW_OK` | `REVIEW_CONDITIONAL` | `HOLD` | `BEGINNER_BAN`

**총투입액** = 낙찰가 + 인수보증금·권리 + 취득세 + 부가세 + 등기법무 + 체납관리비 + 수리 + 명도 + 대출이자 + 매각비용 + 예비비

**적정 입찰 상한** = 보수적 처분가 − 목표 안전마진 − (낙찰가 외 비용) − 인수예상액 − 금융비용

---

## 5. 단계

| Phase | 내용 |
|-------|------|
| 0 | 감사·설계 (본 문서) |
| **1** | 수동 등록, 지도·목록·상세 탭 골격, 금액 안전장치, 계산기, 모드 전환 |
| 2 | PDF·근거 추적·마스킹·Object Storage |
| 3 | 권리·점유 타임라인 (court vs onbid 로직 분리) |
| 4 | 대출 시나리오 (RuleConfig) |
| 5 | 공식 데이터 연동 (기존 AuctionLot 링크) |
| 6 | 테스트·보안·배포 |

LLM: 요약/설명만. 날짜·금액·선후순위는 결정론 코드.

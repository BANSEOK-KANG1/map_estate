---
tags:
  - moc
  - map-estate
  - auction-insight
aliases:
  - 스크리닝 점수 목차
  - 가중치 MOC
created: 2026-07-23
source: auction_insight/backend/app/services/score.py
---

# 경·공매 스크리닝 점수 · 가중치

정보를 **끌어올 때(enrich)** 계산해 목록·지도 **추천순**에 쓰는 점수 체계입니다.  
심층 분석 랩(권리·대출)과 별개이며, **입찰 여부를 결정하지 않습니다.**

## 한 장 요약

| 구성 | 필드 | 가중치 | 역할 |
|------|------|--------|------|
| 시세 할인 | `discount_vs_market` → 점수화 | **35%** | 최저가 vs 인근 실거래 중위 |
| 감정 할인 | `discount_vs_appraisal` → 점수화 | **25%** | 최저가 vs 감정가 |
| 상권·인프라 | `infra_score` | **25%** | 카카오 POI (역·학교 등) |
| 마감 긴급도 | `urgency_score` | **15%** | 입찰 마감까지 남은 일수 |
| **종합** | `total_score` | 100% | 위 네 가지 가중합 |

> 유찰 횟수(`fail_count`)는 **점수에 들어가지 않습니다.** 필터·칩·문구용입니다.

## 노트 목차

1. [[01-데이터-유입-enrich|데이터 유입 파이프라인 (enrich)]]
2. [[02-할인율|할인율 (감정·시세)]]
3. [[03-인프라-POI|인프라·상권 점수 (POI 가중치)]]
4. [[04-마감-긴급도|마감 긴급도]]
5. [[05-종합점수|종합점수 combine_insight]]
6. [[06-정렬-UI|검색 정렬 · 앱 표시]]
7. [[07-임계값-치트시트|임계값 · 치트시트]]

## 코드 위치

- 공식·가중치: `auction_insight/backend/app/services/score.py`
- 적용 시점: `…/services/enrich.py` → `enrich_lot`
- 검색 정렬: `…/services/lots.py` → `search_lots`
- POI: `…/services/kakao.py`
- 시세: `…/ingest/molit_market.py`

## 옵시디언에서 열기

1. Obsidian → **Open folder as vault**
2. 폴더 선택:  
   `map_estate/auction_insight/docs/obsidian-vault`
3. 그래프 뷰에서 `스크리닝` 태그로 연결 확인

또는 이 폴더를 기존 볼트에 복사·심링크해도 됩니다.

---
tags:
  - map-estate
  - auction-insight
  - POI
  - 인프라
  - 가중치
  - 스크리닝
aliases:
  - infra_score
  - 상권점수
created: 2026-07-23
---

# 인프라 · 상권 점수 (POI 가중치)

← [[00-스크리닝-점수-MOC|목차]] · [[01-데이터-유입-enrich|enrich]]

카카오 로컬에서 **반경 800m** POI를 카테고리별로 모아 `infra_score`(0~100)를 만듭니다.

## 카테고리 가중치 (합 = 1.0)

| category | 가중치 | 의미 |
|----------|--------|------|
| `subway` | **0.30** | 지하철 |
| `school` | 0.15 | 학교 |
| `hospital` | 0.15 | 병원 |
| `mart` | 0.15 | 마트 |
| `convenience` | 0.10 | 편의점 |
| `cafe` | 0.08 | 카페 |
| `food` | 0.07 | 음식 |

## 카테고리별 세부 점수 (가중 전, 최대 100)

한 카테고리 안에서:

$$
\text{cat} = \underbrace{\min(\tfrac{\text{count}}{5},\,1)\times 60}_{\text{개수}} + \underbrace{\max(0,\,1-\tfrac{d}{800})\times 40}_{\text{거리}}
$$

- `count`: 해당 카테고리 POI 개수 (5개면 개수항 만점)
- `d`: 최근접까지 미터 (`nearest_distance_m`)
- 800m 밖이면 거리항 0

그다음:

$$
\text{infra} = \min\left(100,\ \sum_c w_c \cdot \text{cat}_c\right)
$$

POI가 하나도 없으면 **0** (enrich 시 기존 값 유지 가능).

## 부가 표시 (점수식 밖)

- 최근접 지하철 이름 → `nearest_station`
- 도보분 ≈ `max(1, 거리m / 80)`

## 종합 비중

- `infra_score` → **25%** → [[05-종합점수]]

## 코드

`infrastructure_score()` — `backend/app/services/score.py`

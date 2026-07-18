# 법원 경매 어댑터 확장 가이드

법원 경매(courtauction.go.kr 등)는 **공식 OpenAPI가 없습니다.**  
MVP는 데모 데이터와 교체 가능한 인터페이스만 제공합니다.

## 인터페이스

`backend/app/providers/court.py`:

```python
class CourtAuctionProvider(ABC):
    async def fetch_lots(self, *, region_hint: str | None = None) -> list[CourtLotDraft]:
        ...
```

`DemoCourtAuctionProvider`가 서울·경기·인천 샘플을 반환합니다.  
`POST /api/demo/seed`가 이 구현을 호출합니다.

## 확장 방법

1. **수동 CSV/JSON 업로드**  
   - `CourtLotDraft` 필드로 매핑하는 `CsvCourtAuctionProvider` 추가  
   - 관리용 `POST /api/ingest/court`에서 파일 파싱

2. **제휴·상용 API**  
   - 동일 인터페이스로 HTTP 클라이언트 구현  
   - rate limit·약관·저작권 준수

3. **합법적 공개 피드가 생기면**  
   - `DemoCourtAuctionProvider` 대신 새 클래스를 기본으로 등록

## 최소 필드 매핑

| CourtLotDraft | 의미 |
|---------------|------|
| external_id | 고유 키 (사건번호 등) |
| case_no | 표시용 사건번호 |
| address | 지오코딩·지역 매칭용 |
| appraisal_manwon / min_bid_manwon | 만원 단위 |
| fail_count | 유찰 횟수 |
| bid_end_at / sale_date | 마감·매각기일 |
| schedules | 회차별 최저가·결과 |

## 하지 말 것

- 법원 사이트 ToS를 위반하는 무단 대량 스크래핑
- 권리분석·법률 자문을 앱이 대신한다고 표시하는 UX

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

## 4. CORS / 포트

백엔드 기본 포트는 **8001** (map_estate 8000과 분리).

```
CORS_ORIGINS=http://localhost:*,http://127.0.0.1:*,*
```

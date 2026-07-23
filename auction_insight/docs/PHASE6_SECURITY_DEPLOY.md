# Phase 6 — 테스트 · 보안 · 배포

## 보안 체크리스트

- [x] 업로드: PDF/TXT만, 25MB 제한, 파일명 sanitize, PDF magic 검사
- [x] DocumentStore: storage key path traversal 차단 (`safe_path`)
- [x] API 응답에서 `storage_key` 미노출
- [x] 주민번호·연락처 저장 전 마스킹 (`pii.mask_pii`)
- [x] 보안 헤더: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- [x] `/api/*` `Cache-Control: no-store`
- [x] DocumentStore 추상화 (local ↔ s3). 운영은 `ANALYSIS_DOC_STORE=s3|r2` + bucket/creds
- [x] S3/R2 put/get/delete (`boto3`, `ANALYSIS_S3_ENDPOINT_URL`로 R2/MinIO)
- [x] 선택적 `ANALYSIS_API_KEY` → 분석 쓰기 API에 `X-API-Key` 요구
- [ ] 사용자 로그인/인가 (공개 MVP — 추후)

## 테스트

```bash
cd auction_insight/backend
python -m pytest tests/ -q

cd auction_insight/app
flutter analyze lib/

# 루트 실거래 회귀
cd app && flutter test
```

## 배포 (Render)

1. `auction_insight/backend/scripts/sync_web.sh` 로 웹 빌드 동기화
2. `git push` → Render auto-deploy
3. 확인:
   - `GET https://map.measuremkt.com/api/health` → `analysis.item_count`, `analysis.doc_store`
   - 물건 상세 → **심층 분석 열기**
   - 문서함 TXT 업로드 → 마스킹·분류
4. 환경변수 (권장):
   - `ANALYSIS_DOC_STORE=local` (기본) → 운영 `s3` 또는 `r2`
   - `ANALYSIS_DOC_ROOT` (local 경로)
   - `ANALYSIS_S3_BUCKET` / `ANALYSIS_S3_PREFIX` / `ANALYSIS_S3_REGION`
   - `ANALYSIS_S3_ENDPOINT_URL` (R2·MinIO)
   - `ANALYSIS_S3_ACCESS_KEY` / `ANALYSIS_S3_SECRET_KEY`
   - `ANALYSIS_API_KEY` (설정 시 분석 쓰기 API에 `X-API-Key` 필수)

## 제품 원칙 (회귀 금지)

- AI는 입찰을 결정하지 않는다.
- 필수문서 없으면 권리 확정 금지 (UNKNOWN/HOLD).
- LTV/취득세는 RuleConfig (하드코딩 금지).
- 실거래 앱(`app/` / 루트 backend)은 분석 모듈과 분리 유지.

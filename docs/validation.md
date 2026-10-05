# 재현 가능한 검증 결과

검증일은 2026-10-06입니다. “통과”는 표에 적힌 범위에만 적용되며 원본 전체나 운영 상태로 확대 해석하지 않습니다.

## 새 공개 사례집

| 검사 | 명령 | 결과 | 증명 범위 |
| --- | --- | --- | --- |
| 개인정보·비밀정보 guard | `python scripts/privacy_guard.py .` | 통과 | allowlist, 파일 크기, 위험 경로·문자열 검사 |
| Markdown link | `python scripts/check_markdown_links.py .` | 통과 | 저장소 내부 상대 링크의 대상 존재 여부 |
| Rust format | `cargo fmt --check` | 통과 | 독립 예제 포맷 |
| Rust lint | `cargo clippy --all-targets -- -D warnings` | 통과, 경고 0 | 독립 예제와 테스트의 lint |
| Rust test | `cargo test` | 4 passed, 0 failed | 성공·실패·빈 실행·중복 이름 식별의 수명주기 계약 |
| PostgreSQL 16 test | `psql -f sql/test-weekly-aggregation.sql` | 통과 | ISO 주차 경계, OHLCV, 반복 실행 |
| GitHub Actions | `safety.yml` | [최신 상태](https://github.com/cheolgyu/stockbot-engineering-case-study/actions/workflows/safety.yml) | 게시 시점에는 GitHub-hosted runner 장애로 queued; 로컬 동일 계열 검사는 통과 |

로컬 검사는 [`scripts/verify.ps1`](../scripts/verify.ps1)로 묶었습니다. SQL 검사는 임시 PostgreSQL 16 container를 사용하고 종료 시 제거합니다.

도구 버전과 기계 판독 가능한 결과는 [`evidence/verification.json`](../evidence/verification.json)에 함께 기록합니다.

## 비공개 원본의 읽기 전용 감사

| 검사 | 결과 | 한계 |
| --- | --- | --- |
| 현재 개발 workspace `cargo check --workspace` | exit 0, 경고 147개 | 테스트 통과나 품질 보증이 아님 |
| 역사적 `site-yew` release build | exit 0, 경고 99개 | 브라우저 E2E·배포·현재 UI를 검증하지 않음 |
| batch lib-test compile | 31개 test 열거·binary compile | 실제 실행 안 함; placeholder·외부 환경 의존 포함 |
| Git 활동 집계 | 2022~2025 1,388 commits, 201 active days | author metadata는 독립적인 저작권 증명이 아님 |

원본 저장소의 부족한 테스트를 새 사례집의 테스트 통과로 덮어쓰지 않습니다. 서로 다른 검증 대상입니다.

## 수동 검토 항목

- 원본 저장소와 이 사례집의 Git 이력이 연결되지 않았는가
- 원본 비공개 저장소들이 계속 private인가
- 새 공개 저장소만 새 remote로 설정됐는가
- 공개 tree에 환경 파일, 키, dump, 로그, 원자료가 없는가
- 2026년 에이전트 보조 변경이 역사적 직접 개발 주장에 섞이지 않았는가
- Yew/WASM이 역사적 구현이며 2026-05-05 감사 스냅샷의 UI는 React 19라고 명시했는가

## 남는 한계

정적 패턴 검사는 알려지지 않은 형태의 민감 정보를 모두 찾을 수 없습니다. 또한 합성 예제의 통과는 원본 비공개 시스템의 운영 안정성, 데이터 정확성, 투자 성과를 증명하지 않습니다.

SQL 테스트는 ISO 주차 경계와 변경 없는 upsert를 검증하지만 두 세션의 실제 lock 경쟁은 검증하지 않습니다. 집계 SQL은 원천 행이 추가·수정되는 append/upsert 모델을 전제로 하며, 원천의 마지막 행이 삭제됐을 때 이미 생성된 주간 행을 지우는 reconciliation은 범위 밖입니다.

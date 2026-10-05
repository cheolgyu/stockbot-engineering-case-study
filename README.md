# Stockbot Engineering Case Study

[![safety](https://github.com/cheolgyu/stockbot-engineering-case-study/actions/workflows/safety.yml/badge.svg)](https://github.com/cheolgyu/stockbot-engineering-case-study/actions/workflows/safety.yml)

[English](README.en.md) · [검증 근거](docs/validation.md) · [주장 범위](docs/claims-boundary.md)

비공개 시장 데이터 프로젝트에서 직접 설계하고 구현한 내용을, 공개 가능한 합성 데이터와 독립 예제로 다시 검증한 기술 사례집입니다. 원본 저장소의 소스나 Git 이력을 복제한 저장소가 아닙니다.

> 이 공개 사례집의 문서·합성 SQL·독립 Rust 예제·검증 자동화는 2026-10에 사용자가 공개 범위를 결정하고 AI 에이전트와 함께 재구성했습니다. 2022~2025년 원본 코드나 당시의 단독 저작 증거로 동일시하지 않습니다.

## 한눈에 보기

2021년 인프라 실험 뒤 2022-05~08 Go 프로토타입을 진행했고, 2022-07 Rust 주 구현을 시작해 잠시 병행했습니다. Rust 개발 도중인 2023~2024년에는 별도 Spring 기반 구현도 실험했습니다. 2022~2025년 주 Rust 구현은 수집·집계·API·웹 계층으로 확장됐습니다.

| 영역 | 당시 구현 | 이 사례집의 공개 증거 |
| --- | --- | --- |
| 배치 | Rust로 `Batch → Job → Step` 실행 모델 설계 | 실패 경로까지 종료 상태를 남기는 [독립 실행 예제](examples/resilient-batch/)와 테스트 |
| 데이터 | PostgreSQL 기반 일별 데이터 집계 | ISO 연도 경계를 다루는 [주간 집계 SQL](sql/weekly-aggregation.sql)과 회귀 테스트 |
| API | Actix Web, SQLx, PostgreSQL | 비공개 소스의 manifest·구조를 로컬 감사한 [아키텍처 기록](docs/architecture.md) |
| 웹 | 당시 Yew 기반 Rust/WASM 클라이언트 | 과거 WASM 빌드 확인 결과와 현재 상태를 구분한 [검증표](docs/validation.md) |
| 오픈소스 | `tb_row` 배포, Actix 예제 기여 | 제3자가 확인 가능한 [공개 링크와 수치](docs/open-source.md) |

> Rust를 선택한 이유는 처리 성능과 메모리 사용량을 더 세밀하게 통제하기 위해서였습니다. 다만 당시 Go·Spring 버전과 동일 조건의 벤치마크가 남아 있지 않으므로, “Rust로 몇 배 빨라졌다”는 주장은 하지 않습니다.

## 외부 확인 가능한 근거

- Actix 공식 examples 저장소에 multipart·object-storage 예제 [PR #250](https://github.com/actix/examples/pull/250)과 후속 async 수정 [PR #252](https://github.com/actix/examples/pull/252)가 병합됐습니다. 첫 PR은 9개 파일, 357 additions입니다.
- Rust crate [`tb_row` 1.0.0](https://crates.io/crates/tb_row)을 배포했으며, 2026-10-06 확인 기준 누적 다운로드는 1,544회입니다. 다운로드를 고유 사용자 수로 해석하지 않습니다.
- 비공개 기록상 2025-09-25 두 이력 테이블에 합계 34,968,331행이 저장돼 있었습니다. 이는 현재 운영량이나 처리량이 아닌 당시 스냅샷 기록입니다.

## 검토 과정에서 바로잡은 두 가지

### 1. 성공과 실패가 모두 끝나는 배치 수명주기

초기 구현은 Spring Batch에서 착안해 실행 단위를 `Batch`, `Job`, `Step`으로 나눴지만, 오류가 발생하면 일부 `run_after` 경로와 종료 상태 기록이 생략될 수 있었습니다. 공개 예제는 이를 그대로 미화하거나 복사하지 않았습니다.

- `Step::run`이 panic 없이 `Result`를 반환한 모든 경로에서 시작 범위는 `Started`와 `Finished` 이벤트를 가집니다.
- 실패한 단계·작업·배치가 모두 `Failed`로 종결됩니다.
- 실패 뒤의 단계와 작업은 실행하지 않는 fail-fast 정책을 테스트합니다.
- 반환 오류 경로에서 panic을 일으키지 않고 오류 문맥을 결과에 보존합니다.

구현은 [examples/resilient-batch/src/lib.rs](examples/resilient-batch/src/lib.rs), 동작 계약은 [테스트](examples/resilient-batch/tests/lifecycle.rs)에서 확인할 수 있습니다.

### 2. 달력 연도와 ISO 주차 연도의 경계

주간 집계에서 달력 연도와 ISO 주차 번호를 섞으면, 예를 들어 2021년 1월 1일이 `2021-W53`처럼 잘못 분류될 수 있습니다. 공개 SQL은 다음 원칙을 적용합니다.

- `date_trunc('week', observed_on)`을 주 식별자의 기준으로 사용
- `EXTRACT(ISOYEAR ...)`와 `EXTRACT(WEEK ...)`를 함께 저장
- transaction-scoped advisory lock으로 중복 실행 직렬화
- upsert로 같은 원천 데이터에 대해 멱등 갱신
- 2020년 12월 28일과 2021년 1월 1일이 모두 `2020-W53`에 포함되는 합성 회귀 테스트

## 프로젝트 이력의 경계

로컬 Git 감사로 주 Rust 저장소의 2022~2025년 개발 구간과 연도별 활동을 확인했습니다. 비공개 이력의 집계 수치는 작업 지속성을 설명할 뿐 외부 검증 가능한 품질이나 사업 성과를 대신하지 않으므로 [프로젝트 계보](docs/lineage.md)에만 상세히 기록합니다.

2026년에는 React 전환을 포함한 에이전트 보조 현대화가 별도로 진행됐습니다. 그 구간은 이 사례집의 “원래 직접 개발한 시스템” 근거에서 제외했습니다. 따라서 이 문서가 말하는 Yew/WASM은 과거 구현이며, 2026-05-05 감사 스냅샷의 비공개 UI는 React 19입니다. 상세 구간과 산정법은 [프로젝트 계보](docs/lineage.md)에 있습니다.

## 검증

Windows PowerShell에서 한 번에 실행하려면 다음 명령을 사용합니다. PostgreSQL SQL 검증에는 Docker가 필요합니다.

```powershell
./scripts/verify.ps1
```

개별 검증 명령과 현재 결과는 [docs/validation.md](docs/validation.md)에 기록합니다. GitHub Actions도 같은 개인정보·Rust·PostgreSQL 검사를 수행합니다.

## 이 사례집이 증명하지 않는 것

- 투자 수익률, 예측 정확도 또는 자동매매 성과
- 현재 운영 중인 서비스, 사용자 수 또는 트래픽 규모
- 동일 조건 벤치마크가 없는 언어 간 성능 우위
- 비공개 원본 전체의 무결점 또는 프로덕션 준비 상태
- 2026년 에이전트 보조 변경을 과거 본인 단독 개발로 소급한 주장

면접·이력서에서 사용할 수 있는 문장과 피해야 할 문장은 [주장 범위](docs/claims-boundary.md)에 분리했습니다.

## 공개 원칙

원본에는 공개할 수 없는 설정과 운영 자료가 있어 fresh Git 이력으로 다시 작성했습니다. 원본 코드, 환경 파일, 로그, DB dump, 시장 원자료, 클라우드 식별자는 포함하지 않습니다. 자세한 기준은 [PRIVACY.md](PRIVACY.md)와 [SECURITY.md](SECURITY.md)를 참고하세요.

## 문서 지도

- [프로젝트 계보와 기여 구간](docs/lineage.md)
- [역사적 시스템 아키텍처](docs/architecture.md)
- [배치 실행 모델과 실패 처리](docs/batch-runtime.md)
- [WASM 및 오픈소스 근거](docs/open-source.md)
- [재현 가능한 검증 결과](docs/validation.md)
- [이력서·면접 주장 범위](docs/claims-boundary.md)

## License

새로 작성한 문서와 예제 코드는 [MIT License](LICENSE)로 공개합니다. 비공개 원본 코드에 대한 라이선스나 접근 권한을 부여하지 않습니다.

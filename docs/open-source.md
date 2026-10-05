# WASM 및 오픈소스 근거

## 역사적 Yew/WASM 빌드

2026-10-06에 비공개 개발 브랜치가 보관하고 있는 과거 `site-yew` 스냅샷을 격리해 release build를 다시 실행했습니다.

| 항목 | 결과 |
| --- | --- |
| target | `wasm32-unknown-unknown` |
| 도구 | Trunk 0.21.14 |
| 종료 코드 | 0 |
| 산출물 | 6개, 합계 1,508,507 bytes |
| WASM | 1,434,345 bytes |

이 결과는 “과거 Yew/WASM 프런트가 실제로 release build된다”는 점만 확인합니다. 브라우저 기능의 종단 간 동작, 운영 배포, 성능, 2026-05-05 감사 스냅샷의 UI가 WASM이라는 주장은 증명하지 않습니다. 컴파일 경고 수는 [검증 문서](validation.md)에 별도로 기록합니다.

## Actix 생태계 기여

- [actix/examples PR #250](https://github.com/actix/examples/pull/250): multipart 업로드와 object storage 연동 예제, 2020-02-10 병합
- [actix/examples PR #252](https://github.com/actix/examples/pull/252): async 동작 후속 수정, 2020-02-13 병합

PR #250은 9개 파일, 357 additions 규모로 확인됐습니다. 병합 여부와 diff가 외부 저장소에 남아 있어, 비공개 프로젝트 설명보다 독립적으로 검증하기 쉬운 근거입니다.

## `tb_row`

[`tb_row` 1.0.0](https://crates.io/crates/tb_row)은 구조체 직렬화 결과를 순서가 정해진 tuple로 바꾸는 용도의 Rust crate입니다. crates.io에서 2023-07-16 게시와 2026-10-06 기준 누적 다운로드 1,544회를 확인했습니다.

다운로드 수는 사용자 수나 품질을 뜻하지 않습니다. 이 사례집에서는 “crate를 설계·배포한 경험”의 보조 근거로만 사용합니다.

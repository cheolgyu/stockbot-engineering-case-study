# Stockbot Engineering Case Study

[한국어](README.md) · [Validation](docs/validation.md) · [Claims boundary](docs/claims-boundary.md)

This repository reconstructs selected engineering decisions from a private market-data project using public, synthetic data and independently written examples. It is not a source dump or a copy of the original Git history.

> The documentation, synthetic SQL, independent Rust example, and validation automation in this public case study were reconstructed in October 2026 through a user-directed, AI-assisted review. They are not presented as the original 2022–2025 source or as evidence of unaided authorship at that time.

## At a glance

After infrastructure experiments in 2021, a Go prototype ran from May to August 2022. The main Rust implementation began in July 2022, briefly overlapping it, and a separate Spring-based implementation was explored in 2023–2024. The main 2022–2025 Rust codebase expanded across data collection, aggregation, API, and web layers.

| Area | Historical implementation | Public evidence in this repository |
| --- | --- | --- |
| Batch | A Rust `Batch → Job → Step` execution model | A tested [standalone runner](examples/resilient-batch/) that finalizes both success and failure paths |
| Data | PostgreSQL daily-to-weekly aggregation | [SQL](sql/weekly-aggregation.sql) and a synthetic ISO-week boundary regression test |
| API | Actix Web, SQLx, and PostgreSQL | A locally audited [architecture record](docs/architecture.md) |
| Web | A Yew-based Rust/WASM client at the historical cutoff | A build result that is explicitly separated from the current React UI |
| Open source | The `tb_row` crate and contributions to Actix examples | Third-party-verifiable [links and metrics](docs/open-source.md) |

Rust was chosen to gain tighter control over runtime and memory costs. No equivalent-condition benchmark survives across the Go, Spring, and Rust versions, so this case study does not claim a measured language-level speedup.

## Externally verifiable evidence

- Actix merged upstream [PR #250](https://github.com/actix/examples/pull/250), a 9-file and 357-addition multipart/object-storage example, and its async follow-up [PR #252](https://github.com/actix/examples/pull/252).
- The published Rust crate [`tb_row` 1.0.0](https://crates.io/crates/tb_row) had 1,544 lifetime downloads when checked on 2026-10-06. Downloads are not unique users.
- A private record captured 34,968,331 rows across two history tables on 2025-09-25. This is a historical storage snapshot, not current traffic or throughput.

## What the review improved

The historical batch abstraction had a useful shape but did not consistently finalize every scope on failure. For steps that return a `Result` without panicking, the public reconstruction guarantees that every started batch, job, and step receives a terminal event, preserves failure context, and stops subsequent work under an explicit fail-fast policy.

The SQL example also corrects a calendar-year/ISO-week mismatch. It keys weeks by their Monday start date, records ISO year and week together, serializes concurrent refreshes with a transaction-scoped advisory lock, and tests the 2020/2021 boundary using synthetic rows.

## Authorship boundary

A local Git audit confirmed the main Rust repository's 2022–2025 development window and yearly activity. Because the private history is not independently verifiable, its detailed counts are kept in [lineage](docs/lineage.md) and are not used as a headline quality or productivity score.

Agent-assisted modernization took place separately in 2026, including a move to React. That work is excluded from claims about the original implementation. The Yew/WASM material here describes the historical UI; the private UI in the 2026-05-05 audit snapshot used React 19. See [lineage](docs/lineage.md) for the method and dates.

## Verify

On Windows PowerShell, run:

```powershell
./scripts/verify.ps1
```

Docker is required for the PostgreSQL test. The same privacy, Rust, and SQL checks run in GitHub Actions. Exact results and limitations are recorded in [validation](docs/validation.md).

## This repository does not prove

- investment returns, forecast accuracy, or automated-trading performance;
- a currently operating service, user count, or traffic scale;
- a Rust performance advantage without a controlled benchmark;
- that the complete private source is defect-free or production-ready; or
- that agent-assisted 2026 work was part of the original solo implementation.

## License

The newly written documentation and examples are available under the [MIT License](LICENSE). This grants no rights or access to the private original source.

use std::cell::RefCell;
use std::rc::Rc;

use resilient_batch::{Batch, FnStep, Job, Phase, RunStatus, Scope, StepError};

#[test]
fn successful_run_preserves_order_and_finalizes_every_scope() {
    let calls = Rc::new(RefCell::new(Vec::new()));
    let first_calls = Rc::clone(&calls);
    let second_calls = Rc::clone(&calls);

    let mut batch = Batch::new("daily-refresh").job(
        Job::new("collect-and-aggregate")
            .step(FnStep::new("collect", move || {
                first_calls.borrow_mut().push("collect");
                Ok(())
            }))
            .step(FnStep::new("aggregate", move || {
                second_calls.borrow_mut().push("aggregate");
                Ok(())
            })),
    );

    let report = batch.run();

    assert_eq!(report.status, RunStatus::Succeeded);
    assert_eq!(*calls.borrow(), ["collect", "aggregate"]);
    assert!(report.failure.is_none());
    assert_started_scopes_are_finished_once(&report.events);
    assert_eq!(report.events.last().unwrap().scope, Scope::Batch);
    assert_eq!(
        report.events.last().unwrap().status,
        Some(RunStatus::Succeeded)
    );
}

#[test]
fn failure_finalizes_step_job_and_batch_then_stops() {
    let calls = Rc::new(RefCell::new(Vec::new()));
    let failing_calls = Rc::clone(&calls);
    let skipped_step_calls = Rc::clone(&calls);
    let skipped_job_calls = Rc::clone(&calls);

    let mut batch = Batch::new("daily-refresh")
        .job(
            Job::new("collect")
                .step(FnStep::new("download", move || {
                    failing_calls.borrow_mut().push("download");
                    Err(StepError::new("source unavailable"))
                }))
                .step(FnStep::new("normalize", move || {
                    skipped_step_calls.borrow_mut().push("normalize");
                    Ok(())
                })),
        )
        .job(Job::new("aggregate").step(FnStep::new("weekly", move || {
            skipped_job_calls.borrow_mut().push("weekly");
            Ok(())
        })));

    let report = batch.run();

    assert_eq!(report.status, RunStatus::Failed);
    assert_eq!(*calls.borrow(), ["download"]);
    assert_eq!(
        report.failure.as_ref().map(|failure| (
            failure.job_index,
            failure.job.as_str(),
            failure.step_index,
            failure.step.as_str(),
            failure.message.as_str(),
        )),
        Some((0, "collect", 0, "download", "source unavailable"))
    );
    assert_started_scopes_are_finished_once(&report.events);

    let terminal_statuses: Vec<_> = report
        .events
        .iter()
        .filter(|event| event.phase == Phase::Finished)
        .map(|event| {
            (
                event.scope,
                event.name.as_str(),
                event.job_index,
                event.step_index,
                event.status,
            )
        })
        .collect();

    assert_eq!(
        terminal_statuses,
        [
            (
                Scope::Step,
                "download",
                Some(0),
                Some(0),
                Some(RunStatus::Failed)
            ),
            (
                Scope::Job,
                "collect",
                Some(0),
                None,
                Some(RunStatus::Failed)
            ),
            (
                Scope::Batch,
                "daily-refresh",
                None,
                None,
                Some(RunStatus::Failed)
            ),
        ]
    );
}

#[test]
fn duplicate_names_remain_distinguishable_by_position() {
    let mut batch = Batch::new("batch")
        .job(Job::new("same-job").step(FnStep::new("same-step", || Ok(()))))
        .job(Job::new("same-job").step(FnStep::new("same-step", || Ok(()))));

    let report = batch.run();
    let step_starts: Vec<_> = report
        .events
        .iter()
        .filter(|event| event.scope == Scope::Step && event.phase == Phase::Started)
        .map(|event| (event.name.as_str(), event.job_index, event.step_index))
        .collect();

    assert_eq!(
        step_starts,
        [
            ("same-step", Some(0), Some(0)),
            ("same-step", Some(1), Some(0)),
        ]
    );
    assert_started_scopes_are_finished_once(&report.events);
}

#[test]
fn empty_batch_and_empty_job_finish_successfully() {
    let mut empty_batch = Batch::new("empty");
    let empty_report = empty_batch.run();
    assert_eq!(empty_report.status, RunStatus::Succeeded);
    assert_started_scopes_are_finished_once(&empty_report.events);

    let mut batch_with_empty_job = Batch::new("batch").job(Job::new("empty-job"));
    let report = batch_with_empty_job.run();
    assert_eq!(report.status, RunStatus::Succeeded);
    assert_started_scopes_are_finished_once(&report.events);
}

fn assert_started_scopes_are_finished_once(events: &[resilient_batch::Event]) {
    for started in events.iter().filter(|event| event.phase == Phase::Started) {
        let matching_finishes = events
            .iter()
            .filter(|event| {
                event.phase == Phase::Finished
                    && event.scope == started.scope
                    && event.name == started.name
                    && event.job_index == started.job_index
                    && event.step_index == started.step_index
            })
            .count();

        assert_eq!(
            matching_finishes, 1,
            "{} {:?} must finish exactly once",
            started.name, started.scope
        );
    }
}

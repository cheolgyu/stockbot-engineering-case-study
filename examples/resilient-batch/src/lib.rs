#![forbid(unsafe_code)]

use std::error::Error;
use std::fmt::{self, Display, Formatter};

/// The terminal status of an execution scope.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RunStatus {
    Succeeded,
    Failed,
}

/// The level at which a lifecycle event occurred.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Scope {
    Batch,
    Job,
    Step,
}

/// Whether a scope started or finished.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Phase {
    Started,
    Finished,
}

/// An auditable lifecycle event.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Event {
    pub scope: Scope,
    pub name: String,
    pub job_index: Option<usize>,
    pub step_index: Option<usize>,
    pub phase: Phase,
    pub status: Option<RunStatus>,
}

impl Event {
    fn started(
        scope: Scope,
        name: impl Into<String>,
        job_index: Option<usize>,
        step_index: Option<usize>,
    ) -> Self {
        Self {
            scope,
            name: name.into(),
            job_index,
            step_index,
            phase: Phase::Started,
            status: None,
        }
    }

    fn finished(
        scope: Scope,
        name: impl Into<String>,
        job_index: Option<usize>,
        step_index: Option<usize>,
        status: RunStatus,
    ) -> Self {
        Self {
            scope,
            name: name.into(),
            job_index,
            step_index,
            phase: Phase::Finished,
            status: Some(status),
        }
    }
}

/// A step-level error without infrastructure-specific details.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StepError {
    message: String,
}

impl StepError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl Display for StepError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl Error for StepError {}

/// A callable unit of work.
///
/// Expected failures must be returned as [`StepError`]. Panics and hangs are
/// outside the lifecycle guarantee provided by this small example.
pub trait Step {
    fn name(&self) -> &str;
    fn run(&mut self) -> Result<(), StepError>;
}

/// Adapts a closure to [`Step`].
pub struct FnStep<F>
where
    F: FnMut() -> Result<(), StepError>,
{
    name: String,
    action: F,
}

impl<F> FnStep<F>
where
    F: FnMut() -> Result<(), StepError>,
{
    pub fn new(name: impl Into<String>, action: F) -> Self {
        Self {
            name: name.into(),
            action,
        }
    }
}

impl<F> Step for FnStep<F>
where
    F: FnMut() -> Result<(), StepError>,
{
    fn name(&self) -> &str {
        &self.name
    }

    fn run(&mut self) -> Result<(), StepError> {
        (self.action)()
    }
}

/// A sequential group of steps.
pub struct Job {
    name: String,
    steps: Vec<Box<dyn Step>>,
}

impl Job {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            steps: Vec::new(),
        }
    }

    pub fn step(mut self, step: impl Step + 'static) -> Self {
        self.steps.push(Box::new(step));
        self
    }
}

/// A fail-fast sequence of jobs.
pub struct Batch {
    name: String,
    jobs: Vec<Job>,
}

impl Batch {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            jobs: Vec::new(),
        }
    }

    pub fn job(mut self, job: Job) -> Self {
        self.jobs.push(job);
        self
    }

    /// Runs jobs and steps sequentially.
    ///
    /// When every step returns a `Result`, each started scope receives exactly
    /// one terminal event. A failed step finalizes its step, job, and batch as
    /// failed before the report returns.
    pub fn run(&mut self) -> RunReport {
        let mut events = vec![Event::started(Scope::Batch, &self.name, None, None)];

        for (job_index, job) in self.jobs.iter_mut().enumerate() {
            events.push(Event::started(Scope::Job, &job.name, Some(job_index), None));

            for (step_index, step) in job.steps.iter_mut().enumerate() {
                let step_name = step.name().to_owned();
                events.push(Event::started(
                    Scope::Step,
                    &step_name,
                    Some(job_index),
                    Some(step_index),
                ));

                if let Err(error) = step.run() {
                    events.push(Event::finished(
                        Scope::Step,
                        &step_name,
                        Some(job_index),
                        Some(step_index),
                        RunStatus::Failed,
                    ));
                    events.push(Event::finished(
                        Scope::Job,
                        &job.name,
                        Some(job_index),
                        None,
                        RunStatus::Failed,
                    ));
                    events.push(Event::finished(
                        Scope::Batch,
                        &self.name,
                        None,
                        None,
                        RunStatus::Failed,
                    ));

                    return RunReport {
                        batch_name: self.name.clone(),
                        status: RunStatus::Failed,
                        failure: Some(Failure {
                            job_index,
                            job: job.name.clone(),
                            step_index,
                            step: step_name,
                            message: error.to_string(),
                        }),
                        events,
                    };
                }

                events.push(Event::finished(
                    Scope::Step,
                    step_name,
                    Some(job_index),
                    Some(step_index),
                    RunStatus::Succeeded,
                ));
            }

            events.push(Event::finished(
                Scope::Job,
                &job.name,
                Some(job_index),
                None,
                RunStatus::Succeeded,
            ));
        }

        events.push(Event::finished(
            Scope::Batch,
            &self.name,
            None,
            None,
            RunStatus::Succeeded,
        ));

        RunReport {
            batch_name: self.name.clone(),
            status: RunStatus::Succeeded,
            failure: None,
            events,
        }
    }
}

/// Failure context preserved without a panic.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Failure {
    pub job_index: usize,
    pub job: String,
    pub step_index: usize,
    pub step: String,
    pub message: String,
}

/// The complete, terminal result of one batch run.
#[must_use = "inspect the batch status and failure before discarding the report"]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RunReport {
    pub batch_name: String,
    pub status: RunStatus,
    pub failure: Option<Failure>,
    pub events: Vec<Event>,
}

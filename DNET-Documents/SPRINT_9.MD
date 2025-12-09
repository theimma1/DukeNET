# Sprint 9 – DukeNet AINS API

## Sprint overview

- Sprint number: 9  
- Duration: 1 week (adjust if needed)  
- Context: Sprint 8 delivered Prometheus-based observability for HTTP and business metrics and stabilized the SQLite database (ains.db with init_db.py). Sprint 9 focuses on validating task/agent flows end-to-end, exercising trust/reputation, and making metrics actionable via dashboards. [51][54][63]  

## Sprint goal

Deliver an end-to-end–validated AINS task/agent pipeline with at least one sample agent, plus initial Grafana dashboards wired to Prometheus metrics, so that task routing, trust scoring, and system health can be observed and verified in real time. [52][55][58][61][64]  

## Success criteria

The sprint is successful if all of the following are true:

- End-to-end task/agent flows:
  - A task can be created via the API, routed to an agent, processed, and completed with a result stored in the DB.
  - Failures and retries are recorded correctly in both the database and metrics.
  - Trust/reputation fields on agents update as expected after successful and failed tasks. [52][55]  

- Sample agent:
  - A sample agent service (can be a simple Python process) can:
    - Register with the AINS API.
    - Send periodic heartbeats.
    - Poll for tasks, execute them (mocked business logic), and report completion or failure.
  - The sample agent surfaces all key behaviors needed to exercise routing and trust logic. [55]  

- Metrics and dashboards:
  - Prometheus scrapes /metrics from the AINS API without errors.
  - At least one Grafana dashboard exists with:
    - HTTP-level metrics (requests rate, latency, error rate).
    - Task and agent metrics (task throughput, failure rate, queue depth, trust score distribution, heartbeats). [51][54][57][63][65]  

- Quality and automation:
  - End-to-end tests cover the primary happy path and at least one major failure path (e.g., agent offline, task failure and retry).
  - Tests run via a single command (e.g., `make e2e` or `pytest e2e`) and pass reliably on a clean environment. [52][55]  

## In-scope work

1. End-to-end task/agent tests
   - Design test scenarios:
     - Happy path: create task → routed to agent → agent completes task → trust score increases or remains stable.
     - Failure path: agent fails task → failure recorded → retry logic exercised if implemented → trust score adjusts.
     - Agent unavailable: create task when no agents are available or agent stops heartbeating. [52][55]  
   - Implement tests:
     - Add automated tests (pytest or similar) that:
       - Spin up the AINS API server (test mode or local instance).
       - Use the HTTP API to create agents, tasks, and query results.
       - Assert on DB state (tasks, agents, trust_records) and on key metrics (HTTP and business counters). [52][55]  
     - Integrate into existing test suite and CI path if available.

2. Sample agent implementation
   - Implement a minimal agent client:
     - Language: Python (reusing project venv).
     - Responsibilities:
       - Register with the AINS API on startup.
       - Send heartbeat requests on a fixed interval.
       - Poll for tasks assigned to it (simple pull-based protocol).
       - Execute a stubbed task handler (e.g., echo or basic transformation).
       - Report completion or failure back to the API. [55]  
   - Configuration:
     - Read API base URL and API key (if required) from environment variables.
     - Provide a simple CLI entry point (e.g., `python sample_agent.py`).  
   - Observability:
     - Ensure agent-related metrics (registrations, heartbeats, tasks handled, failures) are updated by the API as the sample agent runs. [51][63]  

3. Trust and routing validation
   - Define small test matrix:
     - Vary agent trust scores and simulate:
       - High-trust vs low-trust agent routing behavior.
       - Agents with high failure rates.
     - Observe which agent gets tasks and how scores evolve.  
   - Implement assertions:
     - For given input conditions (e.g., two agents with different trust scores), verify that the routing logic selects the expected agent.
     - Confirm `trust_scores` and related counters update according to the spec after each test run.  

4. Grafana + Prometheus integration
   - Environment setup:
     - Run Prometheus configured to scrape the AINS API `/metrics` endpoint.
     - Run Grafana connected to Prometheus as a data source. [46][47][51][57][63][65]  
   - Dashboards:
     - Create an “AINS – HTTP & Core” dashboard:
       - Panels for:
         - HTTP request rate (by route and status code).
         - HTTP latency (p95/p99).
         - Error rate (5xx, 4xx). [51][54][57][63][65]  
     - Create an “AINS – Tasks & Agents” dashboard:
       - Panels for:
         - Task creation and completion rate.
         - Task failure/retry rate.
         - Queue depth over time.
         - Agent heartbeats and offline agents.
         - Trust score distribution (e.g., histogram or time series for selected agents). [51][54][63]  
   - Documentation:
     - Capture basic dashboard usage notes (what each panel means, which metrics it uses).

5. Developer and runbook documentation
   - Add/update Markdown docs:
     - `sprint-9.md` (this file) with:
       - Goals, scope, and acceptance criteria.
       - Links or commands for running E2E tests, sample agent, Prometheus, and Grafana.
     - A short “Monitoring & Dashboards” doc:
       - How to start Prometheus and Grafana in dev.
       - How to import or open the AINS dashboards.
       - Key queries or metrics to look at when debugging. [51][54][63]  

## Out-of-scope work

- Major schema changes or new database tables (beyond small additions strictly needed to support tests).  
- New large features unrelated to task/agent flows or observability (e.g., multi-tenant auth, billing, or complex workflow orchestration).  
- Production-grade deployment tooling (Kubernetes manifests, cloud infra) beyond what is necessary for local testing.  

## Milestones and breakdown

- Day 1–2:
  - Finalize E2E scenarios.
  - Implement initial happy-path E2E tests.
  - Implement basic sample agent and verify it can register and complete one task end-to-end.  

- Day 3–4:
  - Add failure-path E2E tests (agent failure, retries, agent offline).
  - Flesh out trust/routing validation logic and assertions.
  - Wire Prometheus to `/metrics` and verify metrics presence for all core flows. [51][54][63]  

- Day 5:
  - Create Grafana dashboards for HTTP and task/agent metrics.
  - Polish docs (test instructions, agent usage, monitoring guide).
  - Buffer for bug fixes and stabilization. [46][47][58][61][64]  

## Risks and assumptions

- Risks:
  - Trust and routing behavior may not match the original spec, requiring refactors that could expand the scope.
  - Flaky E2E tests if test harness depends on timing-sensitive heartbeats or async processing. [52][55]  
  - Complexity configuring Prometheus and Grafana across different environments. [51][57][63][65]  

- Assumptions:
  - AINS API remains stable enough for E2E tests (no major breaking changes mid-sprint).
  - Local dev environment can run API server, sample agent, Prometheus, and Grafana concurrently.
  - Existing metrics are sufficient to build useful dashboards without major refactoring.  

## Definition of done

A story or task in Sprint 9 is “done” when:

- Code:
  - Is implemented, passes unit and E2E tests, and integrates with existing modules.
- Tests:
  - Include automated coverage where applicable (unit or E2E) and run green locally. [52][55]  
- Observability:
  - Adds or updates metrics using existing Prometheus conventions where needed and appears correctly in `/metrics`. [51][54][63]  
- Documentation:
  - Includes any CLI commands, configuration options, and dashboard usage notes relevant to the change, and `sprint-9.md` is updated if the work changes scope.

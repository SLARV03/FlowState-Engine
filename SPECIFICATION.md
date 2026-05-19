# FlowState-Engine — Functional & Non-Functional Requirements Specification

> **Document Type:** Software Requirements Specification (SRS)  
> **Version:** 0.1.0-alpha  
> **Last Updated:** 2026-05-19  
> **Status:** Draft

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [System Constraints](#5-system-constraints)
6. [Data Requirements](#6-data-requirements)
7. [Interface Requirements](#7-interface-requirements)
8. [Acceptance Criteria](#8-acceptance-criteria)
9. [Risk Assessment](#9-risk-assessment)
10. [Glossary](#10-glossary)

---

## 1. Introduction

### 1.1 Purpose

This document defines the complete set of functional and non-functional requirements for the **FlowState-Engine**, a high-performance multi-agent orchestration engine that autonomously generates, tests, and iterates on software projects using specialized AI agents and containerized sandboxed execution.

### 1.2 Scope

FlowState-Engine encompasses:
- A **backend orchestration server** (Python/FastAPI) managing a LangGraph-based state machine
- A **sandbox execution layer** (Docker) for secure, isolated code execution
- A **frontend dashboard** (React/Vite) providing real-time visibility into the autonomous workflow
- A **WebSocket communication layer** bridging backend events to the frontend in real time

### 1.3 Intended Audience

| Audience              | Interest Area                                     |
| --------------------- | ------------------------------------------------- |
| Core developers       | Implementation details, API contracts, data flow  |
| DevOps / Infra        | Docker, deployment, security constraints          |
| Product stakeholders  | Feature scope, UX expectations, acceptance criteria|
| QA / Testing          | Testability, edge cases, safety mechanisms        |

### 1.4 Definitions & Conventions

- **SHALL** — Mandatory requirement (must be implemented for release)
- **SHOULD** — Strongly recommended (implement unless technically infeasible)
- **MAY** — Optional (nice-to-have, implement if time permits)
- Requirements are prefixed: `FR-XXX` (functional), `NFR-XXX` (non-functional)

---

## 2. System Overview

### 2.1 Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FlowState-Engine                         │
│                                                                 │
│  ┌─────────┐    ┌───────────────────────┐    ┌──────────────┐  │
│  │ Frontend │◄──►│  Backend API Server   │◄──►│ Docker Engine│  │
│  │ (React)  │ WS │  (FastAPI/LangGraph)  │    │ (Sandbox)    │  │
│  └─────────┘    └───────────┬───────────┘    └──────────────┘  │
│                             │                                   │
│                     ┌───────▼───────┐                           │
│                     │  LLM Provider │                           │
│                     │ (OpenAI/etc.) │                           │
│                     └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │ HTTP / WebSocket
         ▼
    ┌──────────┐
    │   User   │
    └──────────┘
```

### 2.2 Core Actors

| Actor          | Description                                                       |
| -------------- | ----------------------------------------------------------------- |
| User           | Human operator who submits prompts and monitors execution          |
| PM Agent       | AI agent that generates technical specifications                   |
| SWE Agent      | AI agent that writes and patches source code                       |
| QA Agent       | AI agent that writes tests and triggers sandbox execution          |
| Sandbox Runner | Docker-based isolated execution environment for running tests      |
| LLM Provider   | External API providing language model inference (OpenAI, Anthropic)|

---

## 3. Functional Requirements

### 3.1 Session Management

| ID       | Requirement                                                                                   | Priority |
| -------- | --------------------------------------------------------------------------------------------- | -------- |
| FR-001   | The system SHALL allow users to create a new orchestration session via API call.               | HIGH     |
| FR-002   | The system SHALL assign a unique UUID to each session upon creation.                           | HIGH     |
| FR-003   | The system SHALL accept a natural-language user prompt as the starting input for a session.    | HIGH     |
| FR-004   | The system SHALL support concurrent sessions (minimum 5 simultaneous sessions).               | MEDIUM   |
| FR-005   | The system SHALL allow users to terminate a running session at any point.                      | HIGH     |
| FR-006   | The system SHALL clean up all resources (temp dirs, containers) when a session is terminated.  | HIGH     |
| FR-007   | The system SHALL expose a REST endpoint to retrieve the current state snapshot of any session. | MEDIUM   |

### 3.2 State Machine & Orchestration

| ID       | Requirement                                                                                          | Priority |
| -------- | ---------------------------------------------------------------------------------------------------- | -------- |
| FR-010   | The system SHALL implement a directed graph-based state machine using LangGraph.                     | HIGH     |
| FR-011   | The global state object SHALL conform to the `SquadState` TypedDict schema.                          | HIGH     |
| FR-012   | The state SHALL be passed mutable-by-reference through all graph nodes.                              | HIGH     |
| FR-013   | The system SHALL route execution through nodes in order: PM → SWE → QA → Conditional Branch.        | HIGH     |
| FR-014   | The system SHALL implement conditional routing after QA based on `test_status` and `iteration_count`.| HIGH     |
| FR-015   | On `test_status == "PASSED"`, the system SHALL route to the Deployment Node and terminate.           | HIGH     |
| FR-016   | On `test_status == "FAILED"` and `iteration_count < MAX_ITERATIONS`, the system SHALL route back to SWE. | HIGH |
| FR-017   | On `iteration_count >= MAX_ITERATIONS`, the system SHALL route to the Human Intervention Node.       | HIGH     |
| FR-018   | The system SHALL track and update `current_agent` in the state on every node transition.             | MEDIUM   |
| FR-019   | The system SHALL append to `chat_history` every agent input/output interaction.                       | MEDIUM   |

### 3.3 Agent — Product Manager (PM)

| ID       | Requirement                                                                                    | Priority |
| -------- | ---------------------------------------------------------------------------------------------- | -------- |
| FR-020   | The PM agent SHALL receive the `user_requirement` from the global state.                       | HIGH     |
| FR-021   | The PM agent SHALL generate a structured markdown technical specification.                     | HIGH     |
| FR-022   | The specification SHALL include: project overview, module breakdown, API contracts, edge cases, file structure, and acceptance criteria. | HIGH |
| FR-023   | The PM agent SHALL call `submit_spec(markdown_string)` to commit the spec to state.            | HIGH     |
| FR-024   | The PM agent SHALL NOT have access to code-writing or test-execution tools.                    | HIGH     |
| FR-025   | The PM agent SHALL default to Python as the implementation language if not specified by user.   | MEDIUM   |

### 3.4 Agent — Software Engineer (SWE)

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-030   | The SWE agent SHALL read `technical_spec` to understand implementation requirements.             | HIGH     |
| FR-031   | The SWE agent SHALL write source files using `write_file(path, content)`.                        | HIGH     |
| FR-032   | The SWE agent SHALL support patching existing files using `patch_file(path, search, replace)`.   | HIGH     |
| FR-033   | The SWE agent SHALL call `submit_to_qa()` to advance the graph to the QA node.                  | HIGH     |
| FR-034   | On bug-fix iterations, the SWE agent SHALL analyze `latest_test_logs` for failure root causes.   | HIGH     |
| FR-035   | The SWE agent SHALL NOT write or modify test files.                                              | HIGH     |
| FR-036   | The SWE agent SHALL NOT use mocks unless the specification explicitly permits it.                | MEDIUM   |
| FR-037   | The SWE agent SHALL include docstrings and type hints in all public functions.                   | MEDIUM   |
| FR-038   | The SWE agent SHALL prefer `patch_file` over `write_file` for bug fixes to minimize regression.  | MEDIUM   |

### 3.5 Agent — QA Engineer (QA)

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-040   | The QA agent SHALL read both `technical_spec` and `file_system` from the global state.           | HIGH     |
| FR-041   | The QA agent SHALL write test files using `write_test_file(path, content)`.                      | HIGH     |
| FR-042   | Tests SHALL cover: happy path, edge cases, input validation, error handling.                     | HIGH     |
| FR-043   | The QA agent SHALL select the test framework based on project language (pytest/Jest/testing).     | MEDIUM   |
| FR-044   | The QA agent SHALL call `run_test_sandbox()` to trigger isolated Docker execution.               | HIGH     |
| FR-045   | The QA agent SHALL NOT modify any source code files.                                             | HIGH     |
| FR-046   | On re-iterations, the QA agent SHALL add new test cases but NOT remove existing ones.            | MEDIUM   |
| FR-047   | All test functions SHALL use descriptive names: `test_<feature>_<scenario>`.                     | LOW      |

### 3.6 Sandbox Execution

| ID       | Requirement                                                                                             | Priority |
| -------- | ------------------------------------------------------------------------------------------------------- | -------- |
| FR-050   | The system SHALL create a unique temporary directory per sandbox invocation.                             | HIGH     |
| FR-051   | The system SHALL dump all `file_system` and `test_suite` entries into the temporary directory.           | HIGH     |
| FR-052   | The system SHALL select a Docker base image based on detected project language.                          | HIGH     |
| FR-053   | The system SHALL mount the temporary directory as a volume inside the container.                         | HIGH     |
| FR-054   | The system SHALL execute the appropriate test runner command inside the container.                       | HIGH     |
| FR-055   | The system SHALL capture combined stdout and stderr from the container execution.                        | HIGH     |
| FR-056   | The system SHALL parse the exit code (0 = PASSED, non-zero = FAILED) and update `test_status`.          | HIGH     |
| FR-057   | The system SHALL inject captured output into `latest_test_logs`.                                        | HIGH     |
| FR-058   | The system SHALL increment `iteration_count` after each sandbox execution.                              | HIGH     |
| FR-059   | The system SHALL automatically remove the temporary directory after execution.                           | HIGH     |
| FR-060   | The system SHALL auto-generate `requirements.txt` or `package.json` from detected imports.              | MEDIUM   |
| FR-061   | The system SHALL install detected dependencies inside the container before running tests.               | MEDIUM   |

### 3.7 Human Intervention

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-070   | The Human Intervention Node SHALL halt all automated execution.                                  | HIGH     |
| FR-071   | The system SHALL present accumulated logs, file states, and failure history to the user.         | HIGH     |
| FR-072   | The user SHALL be able to modify the original prompt and restart execution.                       | MEDIUM   |
| FR-073   | The user SHALL be able to manually edit files in the virtual workspace and resume.                | MEDIUM   |
| FR-074   | The user SHALL be able to abort the session entirely from the intervention node.                  | HIGH     |

### 3.8 Deployment Node

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-080   | The Deployment Node SHALL be reached only when `test_status == "PASSED"`.                        | HIGH     |
| FR-081   | The system SHALL make all generated files available for download as a ZIP archive.                | HIGH     |
| FR-082   | The system SHALL display a success summary including iteration count and test results.           | MEDIUM   |
| FR-083   | The system MAY support optional deployment to a target (e.g., GitHub repo, S3 bucket).           | LOW      |

### 3.9 Real-Time Communication (WebSocket)

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-090   | The system SHALL expose a WebSocket endpoint at `/ws/session/{session_id}`.                       | HIGH     |
| FR-091   | The system SHALL broadcast `agent_message` events when agents produce output.                    | HIGH     |
| FR-092   | The system SHALL broadcast `file_created` events when `write_file` or `write_test_file` is called.| HIGH    |
| FR-093   | The system SHALL broadcast `file_modified` events when `patch_file` is called.                   | HIGH     |
| FR-094   | The system SHALL broadcast `state_transition` events on every graph node change.                 | HIGH     |
| FR-095   | The system SHALL broadcast `test_result` events when sandbox execution completes.                | HIGH     |
| FR-096   | The system SHALL broadcast `error` events on unrecoverable failures.                             | HIGH     |
| FR-097   | All WebSocket events SHALL conform to the defined event schema with `event_type`, `timestamp`, and `payload`. | HIGH |

### 3.10 REST API

| ID       | Requirement                                                                                      | Priority |
| -------- | ------------------------------------------------------------------------------------------------ | -------- |
| FR-100   | `POST /api/session/create` SHALL create a new session and return a session ID.                   | HIGH     |
| FR-101   | `POST /api/session/{id}/start` SHALL accept a user prompt and begin orchestration.               | HIGH     |
| FR-102   | `GET /api/session/{id}/state` SHALL return the current `SquadState` snapshot.                    | MEDIUM   |
| FR-103   | `GET /api/session/{id}/files` SHALL list all files in the virtual workspace.                     | MEDIUM   |
| FR-104   | `GET /api/session/{id}/files/{path}` SHALL return the content of a specific file.                | MEDIUM   |
| FR-105   | `POST /api/session/{id}/intervene` SHALL accept human feedback during intervention.              | MEDIUM   |
| FR-106   | `DELETE /api/session/{id}` SHALL terminate and clean up a session.                               | HIGH     |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-001   | The system SHALL respond to REST API requests within 200ms (excluding LLM calls).              | HIGH     |
| NFR-002   | WebSocket event delivery latency SHALL be under 100ms from event generation to client receipt.  | HIGH     |
| NFR-003   | Sandbox container spin-up time SHALL be under 5 seconds.                                       | MEDIUM   |
| NFR-004   | The system SHALL support a minimum of 5 concurrent sessions without performance degradation.    | MEDIUM   |
| NFR-005   | Frontend UI SHALL render at 60fps during normal operation.                                      | MEDIUM   |
| NFR-006   | File tree and code viewer updates SHALL reflect within 500ms of the corresponding event.        | MEDIUM   |

### 4.2 Security

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-010   | Sandbox containers SHALL run with no network access (`--network none`).                        | HIGH     |
| NFR-011   | Sandbox containers SHALL enforce a memory limit of 256MB.                                      | HIGH     |
| NFR-012   | Sandbox containers SHALL enforce a CPU limit of 0.5 cores.                                     | HIGH     |
| NFR-013   | Sandbox containers SHALL run with a read-only root filesystem.                                 | HIGH     |
| NFR-014   | Sandbox containers SHALL drop all Linux capabilities (`--cap-drop ALL`).                       | HIGH     |
| NFR-015   | Sandbox containers SHALL enforce a PID limit of 64 processes.                                  | HIGH     |
| NFR-016   | Sandbox execution SHALL enforce a hard timeout (default 30 seconds, configurable).             | HIGH     |
| NFR-017   | The system SHALL NOT pass API keys or secrets into sandbox containers.                         | HIGH     |
| NFR-018   | LLM API keys SHALL be stored as environment variables, never hardcoded.                        | HIGH     |
| NFR-019   | The system SHOULD implement rate limiting on public-facing API endpoints.                      | MEDIUM   |
| NFR-020   | WebSocket connections SHOULD be authenticated per session.                                     | MEDIUM   |

### 4.3 Reliability

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-030   | The system SHALL implement exponential backoff with jitter for LLM API rate limits (max 3 retries). | HIGH |
| NFR-031   | The system SHALL gracefully handle LLM token limit exceeded errors by truncating chat history.  | HIGH     |
| NFR-032   | The system SHALL re-prompt agents on malformed tool calls with error context and schema.        | HIGH     |
| NFR-033   | The system SHALL kill and clean up sandbox containers that exceed the timeout threshold.        | HIGH     |
| NFR-034   | The system SHALL NOT crash on individual session failures; other sessions SHALL continue.       | HIGH     |
| NFR-035   | The system SHOULD persist session state to enable recovery after server restarts.               | LOW      |

### 4.4 Scalability

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-040   | The architecture SHALL support horizontal scaling of the backend via stateless API design.      | MEDIUM   |
| NFR-041   | Session state SHOULD be externalizable to Redis for multi-instance deployments.                 | LOW      |
| NFR-042   | The system SHALL support pluggable LLM providers without code changes to the orchestration layer.| MEDIUM  |

### 4.5 Usability (Frontend)

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-050   | The UI SHALL provide a dark-themed terminal-style chat rail for agent communications.          | HIGH     |
| NFR-051   | Agent messages SHALL be color-coded by agent type (PM=blue, SWE=green, QA=amber, RUNTIME=red/green). | HIGH |
| NFR-052   | The UI SHALL display a reactive file tree that updates in real-time as files are created.       | HIGH     |
| NFR-053   | The file tree SHALL animate new file entries with a "pop-in" effect.                           | MEDIUM   |
| NFR-054   | The UI SHALL display a visual state machine graph with the active node highlighted.            | HIGH     |
| NFR-055   | The active node in the pipeline graph SHALL have a pulsing green glow animation.               | MEDIUM   |
| NFR-056   | The UI SHALL support click-to-expand file viewing with syntax highlighting.                    | MEDIUM   |
| NFR-057   | The chat rail SHALL support auto-scrolling with a scroll-lock toggle.                          | MEDIUM   |
| NFR-058   | The UI SHALL display a running cost tracker (token usage + estimated USD) in the sidebar.      | LOW      |
| NFR-059   | The UI SHALL use premium typography (e.g., Inter for UI, JetBrains Mono for code).             | MEDIUM   |
| NFR-060   | The UI SHALL be responsive and functional on viewport widths ≥ 1024px.                         | MEDIUM   |

### 4.6 Maintainability

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-070   | The backend codebase SHALL follow a modular architecture with clear separation of concerns.    | HIGH     |
| NFR-071   | All agent system prompts SHALL be externalized into configuration files, not hardcoded.        | MEDIUM   |
| NFR-072   | The tool definitions SHALL be implemented as a pluggable registry pattern.                     | MEDIUM   |
| NFR-073   | The project SHALL include a `README.md` with setup instructions and architecture overview.     | HIGH     |
| NFR-074   | The project SHALL use type hints throughout the Python codebase.                               | MEDIUM   |
| NFR-075   | The project SHOULD include inline documentation for all public functions.                      | MEDIUM   |

### 4.7 Observability

| ID        | Requirement                                                                                    | Priority |
| --------- | ---------------------------------------------------------------------------------------------- | -------- |
| NFR-080   | The system SHALL log all agent invocations with timestamps, token usage, and duration.         | HIGH     |
| NFR-081   | The system SHALL log all sandbox executions with container ID, duration, and exit status.      | HIGH     |
| NFR-082   | The system SHOULD expose a health check endpoint at `GET /api/health`.                         | MEDIUM   |
| NFR-083   | The system SHOULD track cumulative token usage per session (input + output per agent).         | MEDIUM   |

---

## 5. System Constraints

| ID       | Constraint                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------- |
| SC-001   | Docker Engine MUST be installed and running on the host machine.                                |
| SC-002   | Python 3.11+ MUST be available for the backend server.                                          |
| SC-003   | Node.js 18+ MUST be available for the frontend build toolchain.                                 |
| SC-004   | A valid LLM API key (OpenAI or Anthropic) MUST be configured.                                  |
| SC-005   | The host machine MUST have at least 4GB RAM and 2 CPU cores available.                          |
| SC-006   | The maximum iteration count is capped at 5 by default (configurable via `MAX_ITERATIONS`).      |
| SC-007   | The system is designed for single-user local deployment in v0.1 (multi-tenant is out of scope). |

---

## 6. Data Requirements

### 6.1 State Lifecycle

```
Session Created → State Initialized → PM Mutates → SWE Mutates → QA Mutates
    → Sandbox Mutates → [Loop or Terminate] → State Archived/Discarded
```

### 6.2 Data Retention

| Data Type         | Retention Policy                                    |
| ----------------- | --------------------------------------------------- |
| Session State     | In-memory during execution; discarded on terminate  |
| Generated Files   | Available for download until session termination     |
| Chat History      | Part of session state; follows same lifecycle        |
| Test Logs         | Part of session state; follows same lifecycle        |
| Sandbox Temp Dirs | Deleted immediately after sandbox execution          |

### 6.3 Data Sensitivity

| Data Element    | Sensitivity | Handling                                         |
| --------------- | ----------- | ------------------------------------------------ |
| LLM API Keys    | HIGH        | Environment variables only, never logged          |
| User Prompts    | MEDIUM      | Stored in session state, not persisted to disk    |
| Generated Code  | LOW         | Ephemeral, user-downloadable                      |
| Test Logs       | LOW         | Ephemeral, displayed in UI                        |

---

## 7. Interface Requirements

### 7.1 Frontend Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: FlowState-Engine Logo + Session ID + Cost Tracker      │
├───────────────┬───────────────────────────────┬─────────────────┤
│               │                               │                 │
│  File Tree    │   Main Content Area           │  Pipeline Graph │
│  (Left Panel) │   (Agent Chat Rail)           │  (Right Panel)  │
│               │                               │                 │
│  - Reactive   │   - Terminal-style log        │  - Node graph   │
│  - Animated   │   - Color-coded agents        │  - Active glow  │
│  - Clickable  │   - Auto-scroll + lock        │  - Iteration #  │
│               │   - Expandable entries        │                 │
├───────────────┴───────────────────────────────┴─────────────────┤
│  Footer: Status Bar (current agent, iteration, test status)     │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 External Interfaces

| Interface       | Protocol    | Direction  | Description                          |
| --------------- | ----------- | ---------- | ------------------------------------ |
| LLM Provider    | HTTPS       | Outbound   | Agent LLM inference calls            |
| Docker Engine   | Unix Socket | Local      | Container lifecycle management       |
| Frontend ↔ API  | HTTP/WS     | Bidirectional | REST + WebSocket communication   |

---

## 8. Acceptance Criteria

### 8.1 End-to-End Workflow

| AC ID   | Criterion                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------ |
| AC-001  | A user submits a prompt → PM generates a spec → SWE writes code → QA writes tests → tests pass → files are downloadable. |
| AC-002  | When tests fail, the SWE receives logs, patches code, and QA re-runs tests (at least 1 successful retry cycle). |
| AC-003  | After 5 failed iterations, the system halts and presents the Human Intervention UI.              |
| AC-004  | All agent activity is visible in the real-time chat rail via WebSocket.                           |
| AC-005  | The file tree updates dynamically as agents create or modify files.                              |
| AC-006  | The pipeline graph correctly highlights the active node at each stage.                           |

### 8.2 Sandbox Security

| AC ID   | Criterion                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------ |
| AC-010  | A generated script containing `while True: pass` is killed within the timeout period.            |
| AC-011  | A generated script attempting network access (e.g., `requests.get`) fails silently.              |
| AC-012  | A fork bomb script (`os.fork()` loop) is contained by the PID limit.                             |
| AC-013  | Container execution does not persist any files on the host after completion.                      |

### 8.3 Error Recovery

| AC ID   | Criterion                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------ |
| AC-020  | The system recovers from a 429 rate limit response and retries the LLM call.                     |
| AC-021  | The system handles a malformed tool call by re-prompting the agent with the error.               |
| AC-022  | Terminating a session while sandbox is running cleans up the container and temp directory.        |

---

## 9. Risk Assessment

| Risk ID | Risk Description                                       | Likelihood | Impact | Mitigation Strategy                                |
| ------- | ------------------------------------------------------ | ---------- | ------ | -------------------------------------------------- |
| R-001   | LLM generates unsafe code that escapes sandbox         | Low        | High   | Network isolation, read-only FS, capability drops  |
| R-002   | Infinite iteration loop drains API credits              | Medium     | High   | Hard iteration cap (MAX_ITERATIONS = 5)            |
| R-003   | LLM hallucinates non-existent APIs or libraries        | High       | Medium | Dependency installation + clear error logs to SWE  |
| R-004   | Docker Engine unavailable on host                      | Low        | High   | Startup health check, clear error messaging        |
| R-005   | WebSocket connection drops during long execution        | Medium     | Medium | Auto-reconnect with state replay on client side    |
| R-006   | Large codebases exceed LLM context window              | Medium     | High   | Summarize chat_history, selective file inclusion    |
| R-007   | Agent produces malformed tool calls repeatedly          | Medium     | Medium | Max retry limit per agent invocation (3 attempts)  |

---

## 10. Glossary

| Term                | Definition                                                                  |
| ------------------- | --------------------------------------------------------------------------- |
| FSM                 | Finite State Machine — the execution model for the orchestration graph      |
| LangGraph           | Python framework for building stateful, multi-actor LLM applications        |
| SquadState          | The global TypedDict state object passed through all graph nodes            |
| Sandbox             | An ephemeral Docker container for isolated code execution                   |
| Agent               | An independent LLM instantiation with role-specific prompts and tools       |
| Node                | A vertex in the LangGraph state machine representing an agent or action     |
| Conditional Edge    | A graph edge whose target is determined by a routing function               |
| Human Intervention  | A safety mechanism that halts automation and requests user input            |
| Tool                | A programmatic function that an agent can invoke to mutate state            |
| Iteration           | One complete cycle of SWE coding → QA testing → sandbox execution           |

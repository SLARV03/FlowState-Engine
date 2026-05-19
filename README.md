# FlowState-Engine

> High-Performance Multi-Agent Orchestration Engine for Autonomous Software Engineering

FlowState-Engine is a stateful, graph-based workspace where specialized AI agents (Product Manager, Software Engineer, QA Engineer) collaborate to autonomously write code, execute tests inside ephemeral Docker sandboxes, and iteratively fix bugs until your project passes QA.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  User Prompt │────▶│  PM Agent    │────▶│  SWE Agent   │────▶│  QA Agent    │
└─────────────┘     │  (Spec Gen)  │     │  (Code Gen)  │     │  (Test Gen)  │
                    └──────────────┘     └──────────────┘     └──────┬───────┘
                                              ▲                      │
                                              │  FAILED (retry)      │
                                              └──────────────────────┤
                                                                     ├── PASSED → END
                                                                     └── MAX_ITER → HUMAN
```

## Tech Stack

| Layer           | Technology                          |
| --------------- | ----------------------------------- |
| Orchestration   | Python 3.11+, LangGraph             |
| Backend API     | FastAPI + WebSockets + Uvicorn      |
| Sandbox         | Docker (ephemeral containers)       |
| Frontend        | React 18 + Vite                     |
| LLM             | OpenAI / Anthropic (pluggable)      |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Engine (running)
- An OpenAI or Anthropic API key

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/FlowState-Engine.git
cd FlowState-Engine
cp .env.example .env
# Edit .env and set your LLM_API_KEY
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run

**Terminal 1 — Backend:**
```bash
cd FlowState-Engine
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Project Structure

```
FlowState-Engine/
├── PROMPT.md                    # Agent system prompts & definitions
├── SPECIFICATION.md             # Functional & non-functional requirements
├── README.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Pydantic settings
│   ├── models/
│   │   └── state.py             # SquadState + WebSocket events
│   ├── agents/
│   │   ├── base.py              # Abstract agent with tool-calling loop
│   │   ├── pm_agent.py          # Product Manager
│   │   ├── swe_agent.py         # Software Engineer
│   │   └── qa_agent.py          # QA Engineer
│   ├── tools/
│   │   ├── registry.py          # Pluggable tool registry
│   │   ├── pm_tools.py          # submit_spec
│   │   ├── swe_tools.py         # write_file, patch_file, submit_to_qa
│   │   └── qa_tools.py          # write_test_file, run_test_sandbox
│   ├── graph/
│   │   └── orchestrator.py      # LangGraph state machine
│   ├── sandbox/
│   │   └── runner.py            # Docker sandbox execution
│   ├── api/
│   │   ├── routes.py            # REST endpoints
│   │   └── websocket.py         # WebSocket manager
│   └── session/
│       └── manager.py           # Session lifecycle
└── frontend/
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── App.jsx              # Root component
        ├── index.css            # Design system
        ├── hooks/
        │   └── useWebSocket.js  # WebSocket hook
        └── components/
            ├── Header.jsx
            ├── PromptInput.jsx
            ├── ChatRail.jsx
            ├── FileTree.jsx
            ├── PipelineGraph.jsx
            ├── CodeViewer.jsx
            └── StatusBar.jsx
```

## API Endpoints

| Method   | Endpoint                          | Description                   |
| -------- | --------------------------------- | ----------------------------- |
| `GET`    | `/api/health`                     | Health check                  |
| `POST`   | `/api/session/create`             | Create new session            |
| `POST`   | `/api/session/{id}/start`         | Start orchestration           |
| `GET`    | `/api/session/{id}/state`         | Get session state             |
| `GET`    | `/api/session/{id}/files`         | List workspace files          |
| `GET`    | `/api/session/{id}/files/{path}`  | Get file content              |
| `GET`    | `/api/session/{id}/download`      | Download files as ZIP         |
| `POST`   | `/api/session/{id}/intervene`     | Human intervention            |
| `DELETE` | `/api/session/{id}`               | Terminate session             |
| `WS`     | `/ws/session/{id}`                | Real-time event stream        |

## Security

All sandbox containers run with:
- `--network none` — No network access
- `--memory 256m` — Memory cap
- `--cpus 0.5` — CPU throttle
- `--read-only` — Immutable filesystem
- `--cap-drop ALL` — No kernel capabilities
- `--pids-limit 64` — Fork bomb protection
- `30s timeout` — Infinite loop protection

## License

MIT

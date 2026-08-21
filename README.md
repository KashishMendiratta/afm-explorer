# AFM Explorer

[![CI](https://github.com/KashishMendiratta/afm-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/KashishMendiratta/afm-explorer/actions/workflows/ci.yml)

**Live demo:** https://afm.kashishmendiratta.com

AFM Explorer is a full-stack platform for analyzing Atomic Force Microscopy (AFM) force-distance data. It started as a university programming assignment and was rebuilt into a tested, containerized, cloud-deployed application with a REST API, interactive visualizations, machine-learning-based contact-point estimation, CI/CD, and an MCP interface for AI-assisted analysis.

## What does AFM Explorer do?

Atomic Force Microscopy uses a very small probe to press against many points on a surface. Each interaction produces a force-distance curve that describes how the material responds. AFM Explorer turns those raw measurements into interactive maps and plots, estimates where the probe first makes contact with the surface, and uses the fitted response to compare stiffness across a scan.

For a non-technical user, the workflow is simple: upload an AFM scan, explore the generated maps, click into individual measurement locations, inspect their force curves, and compare classical and machine-learning estimates. For developers and researchers, the same functionality is exposed through a REST API and an MCP tool layer.

## Full-stack ML system

The original project came from the **Algorithmic Bioinformatics / Programming with Python for Bioinformatics** course at Universität des Saarlandes.

The coursework was developed in three stages:

1. Parse the block-based AFM text export and plot individual force-distance curves.
2. Estimate the approximately linear contact region and report its slope.
3. Build a Streamlit interface for exploring height and stiffness maps and selecting individual curves.

The original submissions are preserved under [`legacy_scripts/`](legacy_scripts) for provenance and comparison.

The coursework version consisted of standalone scripts with duplicated parsing logic and several different approaches to finding the contact region. AFM Explorer refactors that work into reusable packages and extends it with:

- a shared and tested AFM analysis library
- a FastAPI REST backend
- a thin Streamlit frontend
- supervised ML contact-point estimation
- unsupervised curve quality control
- model evaluation against a classical heuristic baseline
- Docker and Docker Compose
- nginx reverse proxying
- AWS EC2 deployment
- HTTPS through Cloudflare Tunnel
- GitHub Actions CI/CD
- an MCP server exposing AFM functionality as AI-callable tools

## Architecture

```mermaid
flowchart LR
    Browser["Browser"] --> CF["Cloudflare"]
    CF --> Tunnel["Cloudflare Tunnel"]
    Tunnel --> NGINX["nginx"]

    NGINX --> FE["Streamlit frontend"]
    NGINX --> API["FastAPI backend"]

    FE -->|HTTP / JSON| API

    API --> Core["afm_core"]
    API --> ML["ML package"]
    API --> Storage[("filesystem storage")]

    AI["MCP-compatible AI client"] --> MCP["AFM MCP server"]
    MCP -->|HTTP| API

    Core --> Parse["Parsing"]
    Core --> Heuristic["Classical heuristic"]
    Core --> Features["Feature engineering"]

    ML --> Train["Training"]
    ML --> Infer["Inference"]
    ML --> QC["Isolation Forest QC"]
```

### Main components

- **`packages/afm_core`** — parsing, schemas, preprocessing, feature engineering, and the classical contact-region heuristic.
- **`packages/ml`** — training-data generation, supervised contact-point modeling, inference, evaluation, and unsupervised quality control.
- **`backend`** — FastAPI application exposing scan, curve, map, labeling, training, model, and health endpoints.
- **`frontend`** — Streamlit application that communicates with the backend over HTTP rather than reading data directly from disk.
- **`packages/mcp_server`** — Model Context Protocol server exposing the REST API as tools for an AI client.
- **`docker/nginx`** — production reverse-proxy configuration.
- **`.github/workflows`** — continuous integration and deployment workflows.

## Core AFM analysis

The central analysis task is to identify where a force-distance curve transitions into the approximately linear contact region.

The original coursework implemented this using hand-written heuristics. AFM Explorer consolidates that logic into a reusable baseline and represents the result consistently so that the same downstream API and UI can work with either the classical or ML estimator.

For each scan, the application can provide:

- parsed force-distance curves
- per-location contact-region estimates
- stiffness-related slope estimates
- height-map approximation
- stiffness maps
- individual curve inspection

## Machine-learning feature

AFM Explorer adds a supervised alternative to the classical contact-region heuristic.

### 1. Human labeling

A user selects the contact point of a real force curve in the frontend. The stored label identifies:

```text
scan_id
series
i
j
contact_index
```

### 2. Training-data expansion

Each labeled curve is expanded into multiple sliding-window training examples. Shared feature engineering computes quantities such as:

- slope
- R²
- local variance
- curvature
- force statistics
- normalized position along the curve

Windows containing the human-selected contact point become positive examples; the remaining windows become negative examples.

This allows a relatively small number of labeled curves to produce a larger window-level training set.

### 3. Supervised contact-point model

The current supervised estimator uses:

`HistGradientBoostingClassifier`

A tree-based model was chosen deliberately because the realistic label budget is relatively small. Training and evaluation are split at the **curve level**, rather than randomly at the window level, so windows from the same curve cannot leak into both training and evaluation sets.

### 4. Unsupervised quality control

An `IsolationForest` operates on whole-curve features to provide anomaly and quality-control signals without requiring labels.

### 5. Evaluation

The ML estimator is evaluated against the classical heuristic on held-out labeled curves. The key question is not simply whether a model can be trained, but whether it reduces contact-index error relative to the original heuristic.

## AI-assisted analysis with MCP

AFM Explorer includes an MCP server under [`packages/mcp_server/`](packages/mcp_server).

The Model Context Protocol layer converts the REST API into tools that an MCP-compatible AI client can call. This lets an AI assistant inspect AFM data through controlled application interfaces rather than by reading internal files or manipulating Python objects directly.

Example questions and workflows include:

- "Which location in this scan has the highest estimated stiffness?"
- "Show me the curve at that location."
- "Which curves look anomalous and may need review?"
- "How many human labels are available?"
- "What model is currently active?"
- "Did the trained estimator outperform the classical heuristic?"

### Read tools

The MCP server exposes read-oriented tools including:

- `list_scans`
- `get_scan`
- `get_height_map`
- `get_stiffness_map`
- `get_curve`
- `get_contact_point_estimate`
- `list_labels`
- `get_active_model`
- `get_training_status`

Map responses include compact summaries such as minimum, maximum, mean, missing-value count, and extrema locations so an AI client does not need to reason token-by-token over an entire grid.

### Write tools

The MCP layer can also expose:

- `upload_scan`
- `submit_label`
- `train_model`

Write tools can be removed entirely from the exposed MCP tool set by setting:

```bash
AFM_MCP_READONLY=true
```

This is the preferred mode for read-only or shared AI access.

The MCP integration provides the tool layer for AI-assisted analysis. A dedicated autonomous multi-step agent that independently plans and chains several AFM operations is intentionally left as future work.

## Repository layout

```text
packages/
├── afm_core/       Shared parsing, schemas, heuristics and feature engineering
├── ml/             Dataset generation, training, inference and evaluation
└── mcp_server/     MCP tools wrapping the REST API

backend/            FastAPI application, storage and orchestration
frontend/           Streamlit frontend
docker/nginx/       Production reverse-proxy configuration
deploy/             Deployment/bootstrap helpers
data/samples/       Small AFM sample data used by tests and demos
legacy_scripts/     Original university-assignment scripts
.github/workflows/  CI and CD workflows

README.md           Project overview
DEPLOY.md           Production deployment documentation
```

## Tech stack

| Area | Technology |
|---|---|
| Language | Python |
| Scientific computing | NumPy, SciPy |
| Machine learning | scikit-learn |
| Backend | FastAPI, Pydantic, Uvicorn |
| Frontend | Streamlit, Plotly |
| API communication | HTTP / JSON |
| AI tool interface | MCP / FastMCP |
| Containerization | Docker, Docker Compose |
| Reverse proxy | nginx |
| Cloud | AWS EC2 |
| HTTPS / public routing | Cloudflare Tunnel |
| CI/CD | GitHub Actions |
| Cloud authentication | GitHub OIDC → AWS IAM |
| Testing | pytest |
| Linting | Ruff |

## Running locally

### Prerequisites

- Python 3.11+
- Git
- Docker and Docker Compose if using the containerized setup

Clone the repository:

```bash
git clone https://github.com/KashishMendiratta/afm-explorer.git
cd afm-explorer
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install the internal AFM and ML packages:

```bash
pip install -e packages/afm_core -e packages/ml
```

Install backend dependencies from inside `backend/` because the development requirements contain relative editable-package paths:

```bash
cd backend
pip install -r requirements-dev.txt
cd ..
```

Install frontend dependencies:

```bash
pip install -r frontend/requirements.txt
```

Install the MCP package if you want the AI/MCP interface:

```bash
pip install -e packages/mcp_server -e "packages/mcp_server[dev]"
```

### Start the backend

Terminal 1:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

Backend:

`http://localhost:8000`

Interactive FastAPI / Swagger documentation:

`http://localhost:8000/docs`

### Start the frontend

Terminal 2:

```bash
source .venv/bin/activate
export BACKEND_URL=http://localhost:8000
cd frontend/streamlit_app
streamlit run Home.py
```

Open:

`http://localhost:8501`

Upload:

`data/samples/sample.txt`

to explore the demo scan.

## Running with Docker

### Development

```bash
docker compose config
docker compose up --build
```

The development override exposes the backend and frontend directly and enables development-oriented behavior such as source mounts and reload.

### Production-shaped local stack

Validate the merged configuration:

```bash
docker compose   -f docker-compose.yml   -f docker-compose.prod.yml   config
```

Run it:

```bash
docker compose   -f docker-compose.yml   -f docker-compose.prod.yml   up -d --build
```

In production, nginx is the entry point and routes `/` to Streamlit and `/api/` to FastAPI.

## Testing

Run the package suites separately:

```bash
pytest packages/afm_core/tests -q
pytest packages/ml/tests -q
pytest packages/mcp_server/tests -q
```

Backend tests:

```bash
cd backend
pytest tests -q
cd ..
```

Lint:

```bash
ruff check packages backend frontend
```

Frontend syntax check:

```bash
python -m compileall -q frontend
```

Validate production Compose:

```bash
docker compose   -f docker-compose.yml   -f docker-compose.prod.yml   config
```

## API overview

FastAPI exposes the main application functionality through a REST API.

| Endpoint | Purpose |
|---|---|
| `POST /api/scans` | Upload and parse a raw AFM text export |
| `GET /api/scans` | List scans |
| `GET /api/scans/{id}` | Read scan metadata |
| `GET /api/scans/{id}/heightmap` | Get the height map |
| `GET /api/scans/{id}/stiffnessmap` | Get the stiffness map |
| `GET /api/scans/{id}/curves/{s}/{i}/{j}` | Get one raw force curve |
| `GET /api/scans/{id}/curves/{s}/{i}/{j}/estimate` | Estimate the contact region |
| `POST /api/labels` | Save a human contact-point label |
| `POST /api/train` | Start model training |
| `GET /api/train/{job_id}` | Poll training status |
| `GET /api/models/active` | Read active model metadata and metrics |
| `GET /api/health` | Health check |

Write endpoints support optional API-key protection through `AFM_API_KEY`.

When an API key is configured, write requests must provide the matching `X-API-Key` header.

## Using the MCP server

Install the MCP package:

```bash
pip install -e packages/mcp_server -e "packages/mcp_server[dev]"
```

The installed console command is:

```bash
afm-mcp-server
```

### Example MCP client configuration

For Claude Desktop, add the following to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "afm-explorer": {
      "command": "afm-mcp-server",
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "AFM_API_KEY": "",
        "AFM_MCP_READONLY": "false"
      }
    }
  }
}
```

The JSON block contains no comments, so it can be copied directly into a JSON configuration file.

`BACKEND_URL` can also point to the deployed application:

```text
https://afm.kashishmendiratta.com
```

For shared or untrusted access, prefer:

```text
AFM_MCP_READONLY=true
```

unless backend API-key authentication has also been configured appropriately.

The MCP server speaks stdio by default. Other supported transports can be selected through the corresponding MCP environment variables.

## Production deployment

AFM Explorer is currently deployed at:

**https://afm.kashishmendiratta.com**

The production stack uses:

- Ubuntu Server 26.04 LTS on AWS EC2
- Docker Compose
- nginx as the internal reverse proxy
- Cloudflare Tunnel for HTTPS and public routing
- no direct public exposure of the FastAPI or Streamlit ports

The application is reached through:

```text
Browser
   |
   | HTTPS
   v
Cloudflare
   |
   | outbound tunnel
   v
cloudflared on EC2
   |
   v
nginx
  /  /   Streamlit   FastAPI
```

Full setup, security, recovery, and deployment details are documented in [`DEPLOY.md`](DEPLOY.md).

## Continuous Integration and Deployment

### Continuous Integration

`.github/workflows/ci.yml` runs automatically on pushes and pull requests.

The CI pipeline performs:

1. dependency installation
2. Ruff linting
3. `afm_core` tests
4. ML tests
5. backend tests
6. MCP tests
7. frontend syntax checks
8. production Compose validation
9. Docker build checks

### Continuous Deployment

After CI succeeds on `main`, `.github/workflows/cd.yml` deploys the updated application to AWS EC2.

The deployment uses:

- GitHub OIDC rather than long-lived AWS access keys
- a least-privilege AWS IAM role
- temporary SSH access restricted to the current GitHub Actions runner IP
- a dedicated deployment SSH key
- Docker Compose rebuild/restart
- a live health check after deployment
- automatic removal of the temporary SSH rule

The deployment flow is:

```text
git push origin main
        |
        v
GitHub Actions CI
        |
        | success
        v
GitHub Actions CD
        |
        | OIDC
        v
AWS IAM
        |
        | short-lived credentials
        v
temporary runner-specific SSH rule
        |
        v
EC2
        |
        v
Docker Compose rebuild
        |
        v
health check
        |
        v
live application
```

See [`DEPLOY.md`](DEPLOY.md) for the full deployment configuration.

## Known limitations

### Height map is currently an approximation

`ScanCache.height_map()` currently approximates topography using the distance at the estimated contact point.

The original course dataset also included `afm.heights.npy`, containing independently measured topography. A sample copy exists under `data/samples/`, but the backend does not yet ingest it.

### Full preprocessed pickle is not included

The original `afm.data.pickled` contained the complete 32,768-curve preprocessed dataset and is not included in the repository.

The modern backend also intentionally avoids unpickling arbitrary client-supplied files.

### Filesystem-backed storage

Scans, labels, and models currently use filesystem storage.

This is appropriate for the current single-instance deployment. A multi-instance or multi-user production system would benefit from a database and object storage.

### In-process model training

Training currently runs through FastAPI background tasks.

This is sufficient for the current data/model scale. Larger workloads would justify a dedicated worker or task queue.

### MCP provides tools, not autonomous orchestration

The MCP integration allows an AI client to call AFM Explorer tools, but the repository does not currently contain a dedicated autonomous agent that independently plans and executes long chains of operations.

## Future work

The next extensions are intentionally focused on adding capability rather than expanding the stack for its own sake:

1. **Autonomous AI agent over the MCP tool layer**  
   Add a bounded agent orchestration layer that can plan multi-step AFM analyses, call several MCP tools, and return a grounded explanation. This should include strict turn limits, read-only-by-default behavior, and evaluation of tool-use reliability before being exposed publicly.

2. **Use real height measurements**  
   Add optional ingestion of `afm.heights.npy` and prefer independently measured topography when available, while preserving the current contact-position approximation as a fallback.

3. **Larger real labeling and ML evaluation cycle**  
   Label a substantially larger set of real curves and report robust heuristic-vs-ML contact-point error on held-out curves.


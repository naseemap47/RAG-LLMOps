# RAG-LLMOps — MultiDocChat

A production-ready **Retrieval-Augmented Generation (RAG)** application with a complete **LLMOps** pipeline: automated testing, Docker packaging, and zero-downtime deployment to **AWS EKS** via Jenkins CI/CD.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Local Development](#local-development)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Running the App](#running-the-app)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [CI/CD Pipelines](#cicd-pipelines)
  - [Jenkinsfile.test — Test Pipeline](#jenkinsfiletest--test-pipeline)
  - [Jenkinsfile.infra — Infrastructure Pipeline](#jenkinsfileinfra--infrastructure-pipeline)
  - [Jenkinsfile.deploy — Deploy Pipeline](#jenkinsfiledeploy--deploy-pipeline)
- [AWS Infrastructure](#aws-infrastructure)
- [Kubernetes Manifests](#kubernetes-manifests)
- [Git Branches](#git-branches)

---

## Overview

**MultiDocChat** lets users upload multiple documents (PDF, DOCX, TXT) and have a conversational Q&A session over them. Under the hood it uses:

- **LangChain LCEL** for a modular, composable RAG pipeline.
- **FAISS** as the local vector store (persisted per session).
- **MMR (Maximal Marginal Relevance)** retrieval for diverse, high-quality context chunks.
- A configurable LLM backend (Groq, Google Gemini, or Ollama).
- A configurable embedding backend (Google `gemini-embedding-001` or Ollama `nomic-embed-text`).

The whole application is containerised with Docker, traced with **LangSmith**, and deployed to AWS EKS through a three-stage Jenkins pipeline.

---

## Architecture

```
Browser / API Client
        │
        ▼
┌─────────────────────────────────────────┐
│         FastAPI  (main.py)              │
│  GET /          → Jinja2 HTML UI        │
│  POST /upload   → Document ingestion    │
│  POST /chat     → Conversational RAG    │
│  GET  /health   → Health check          │
└──────────┬──────────────────────────────┘
           │
  ┌────────▼────────┐       ┌──────────────────┐
  │  ChatIngestor   │       │ ConversationalRAG │
  │  (ingestion)    │       │  (retrieval)      │
  │                 │       │                  │
  │ save files      │       │ load FAISS index  │
  │ load & split    │       │ rewrite question  │
  │ embed → FAISS   │       │ retrieve chunks   │
  │ persist index   │       │ LLM → answer      │
  └────────┬────────┘       └──────┬───────────┘
           │                       │
           └───────────┬───────────┘
                       │
             ┌─────────▼──────────┐
             │  FAISS Vector Store│
             │  (faiss_index/<id>)│
             └────────────────────┘
```

Each upload creates a **unique session ID** and persists a FAISS index under `faiss_index/<session_id>/`. Subsequent `/chat` calls load that index for context-aware, multi-turn conversation.

---

## Project Structure

```
RAG-LLMOps/
├── main.py                        # FastAPI app — routes & session management
├── Dockerfile                     # Application container image
├── Dockerfile.jenkins             # Jenkins agent with Docker + AWS CLI
├── docker-compose.jenkins.yml     # Local Jenkins bootstrap
├── pyproject.toml                 # Python dependencies (managed by uv)
│
├── multi_doc_chat/                # Core application package
│   ├── config/
│   │   └── config.yaml            # LLM & embedding model configuration
│   ├── model/
│   │   └── models.py              # Pydantic request/response schemas
│   ├── prompts/
│   │   └── prompt.py              # Prompt templates (contextualize + QA)
│   ├── src/
│   │   ├── document_ingestion/
│   │   │   └── data_ingestion.py  # ChatIngestor + FaissManager
│   │   └── document_chat/
│   │       └── retrieval.py       # ConversationalRAG (LCEL chain)
│   ├── utils/
│   │   ├── model_loader.py        # LLM & embedding factory (Groq/Google/Ollama)
│   │   ├── config_loader.py       # YAML config reader
│   │   ├── document_ops.py        # File loading helpers
│   │   └── file_io.py             # File save utilities
│   ├── exception/
│   │   └── exception.py           # DocumentPortalException
│   └── logger/                    # structlog-based global logger
│
├── templates/                     # Jinja2 HTML templates
├── static/                        # Static assets (CSS, JS)
├── data/                          # Uploaded file staging area (per session)
├── faiss_index/                   # Persisted FAISS indexes (per session)
│
├── infra/
│   └── eks-with-ecr.yaml          # CloudFormation: VPC + EKS + ECR
├── k8/
│   ├── deployment.yaml            # Kubernetes Deployment (2 replicas, rolling update)
│   └── service.yaml               # Kubernetes Service
│
├── Jenkinsfile.test               # CI: test-only pipeline
├── Jenkinsfile.infra              # CI: one-shot infrastructure provisioning
├── Jenkinsfile.deploy             # CI: build → push ECR → deploy EKS
│
└── test/                          # pytest test suite
```

---

## Features

- 📄 **Multi-document upload** — PDF, DOCX, and TXT support (powered by `pypdf`, `docx2txt`, `rapidocr-onnxruntime`).
- 🧠 **Conversational RAG** — question rewriting with chat history context via a two-step LCEL chain.
- 🔎 **MMR retrieval** — diverse chunk selection to avoid repetitive context.
- 💾 **Idempotent FAISS indexing** — deduplication via content fingerprinting; re-uploads do not create duplicate vectors.
- 🔄 **Session isolation** — each upload gets a unique session ID; multiple users can chat simultaneously.
- 🔌 **Pluggable LLM & embeddings** — swap between Groq, Google Gemini, or local Ollama via a single env var.
- 🔭 **LangSmith tracing** — full observability of every RAG chain invocation.
- 🐳 **Containerised** — single Dockerfile with `uv` for fast, reproducible builds.
- 🚀 **EKS deployment** — production-grade Kubernetes with rolling updates and health probes.
- 🔁 **Automated CI/CD** — three Jenkins pipelines covering test, infra, and deploy.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Templating | Jinja2 |
| RAG framework | LangChain (LCEL) |
| Vector store | FAISS (CPU) |
| Embedding models | Google `gemini-embedding-001` / Ollama `nomic-embed-text` |
| LLM providers | Groq (`openai/gpt-oss-20b`) / Google Gemini / Ollama |
| Observability | LangSmith |
| Logging | structlog |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Containerisation | Docker |
| Cloud | AWS (EKS, ECR, CloudFormation) |
| Orchestration | Kubernetes |
| CI/CD | Jenkins |
| Python | 3.12+ |

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Groq or Google API key (or a running Ollama instance)

### Environment Variables

Copy `.env` and fill in your own keys:

```dotenv
# LLM provider: "groq" | "google" | "ollama"
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key

# Embedding provider: "google" | "ollama"
EMBEDDING_PROVIDER=google
GOOGLE_API_KEY=your_google_api_key

# LangSmith (optional but recommended)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=RAG-LLMOps

# Server
IP_ADDRESS=0.0.0.0
PORT=8000
```

> **Note:** Keep your real `.env` out of version control. It is already listed in `.gitignore`.

### Running the App

```bash
# 1. Install dependencies
uv sync

# 2. Start the server
uv run python main.py
# or
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The UI is available at `http://localhost:8000`.

### Running with Docker

```bash
docker build -t multi-doc-chat .
docker run -p 8080:8080 --env-file .env multi-doc-chat
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve the chat UI (HTML) |
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/upload` | Upload one or more files; returns `session_id` |
| `POST` | `/chat` | Send a message with `session_id`; returns LLM answer |

**POST `/upload`** — multipart form data

```
files: <file1>, <file2>, ...
```

Response:
```json
{
  "session_id": "session_20241014_123456_abcd1234",
  "indexed": true,
  "message": "Indexing complete with MMR"
}
```

**POST `/chat`** — JSON body

```json
{
  "session_id": "session_20241014_123456_abcd1234",
  "message": "What are the key findings in the report?"
}
```

Response:
```json
{
  "answer": "The key findings are ..."
}
```

---

## Configuration

The model configuration lives in `multi_doc_chat/config/config.yaml`:

```yaml
embedding_model:
  ollama:
    model_name: "nomic-embed-text:latest"
  google:
    model_name: "gemini-embedding-001"

retriever:
  top_k: 10
  search_type: "mmr"   # similarity | mmr | similarity_score_threshold
  fetch_k: 20          # candidates fetched before MMR re-ranking
  lambda_mult: 0.5     # 0 = max diversity, 1 = max relevance

llm:
  groq:
    model_name: "openai/gpt-oss-20b"
    temperature: 0
    max_output_tokens: 2048
  google:
    model_name: "gemini-3.6-flash"
    temperature: 0
  ollama:
    model_name: "qwen3.5:4b"
    temperature: 0
```

Switch providers at runtime via `LLM_PROVIDER` and `EMBEDDING_PROVIDER` environment variables — no code changes required.

---

## CI/CD Pipelines

The project ships three declarative Jenkins pipelines.

### `Jenkinsfile.test` — Test Pipeline

**Trigger:** SCM polling every minute (suitable for local Jenkins without a public webhook).

**Stages:**
1. **Checkout** — clone the repo.
2. **Setup Python Environment** — install `uv`, create a per-build venv at `/tmp/venv-<build>`.
3. **Install Dependencies** — install from `requirements.txt` (strips Windows-only packages).
4. **Run Tests** — `pytest` with JUnit XML and HTML/XML coverage reports.

**Artifacts:** `test-results/`, `coverage.xml`, `htmlcov/`

---

### `Jenkinsfile.infra` — Infrastructure Pipeline

**Trigger:** Manual only — run **once** to provision AWS infrastructure (~20–30 min).

**Stages:**
1. **Checkout**
2. **Validate CloudFormation Template** — `aws cloudformation validate-template`
3. **Check Existing Stack** — detects `NOT_FOUND`, `ROLLBACK_COMPLETE`, or existing stack and sets create/update action accordingly.
4. **Deploy CloudFormation Stack** — `aws cloudformation deploy` with parameterised EKS cluster and ECR repo.
5. **Wait for Stack Completion**
6. **Verify Infrastructure** — confirms EKS cluster is ACTIVE, ECR repo exists, node group is healthy.
7. **Display Stack Outputs** — prints ARNs and URIs needed by the deploy pipeline.

**Required Jenkins environment variables:**

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | Target region (default: `ap-southeast-2`) |

---

### `Jenkinsfile.deploy` — Deploy Pipeline

**Trigger:** SCM polling every 5 minutes (automatic on push).

**Stages:**
1. **Checkout**
2. **Verify Prerequisites** — checks Docker daemon and AWS CLI availability.
3. **Build Docker Image** — tags with a Unix timestamp for immutable image tags.
4. **Push to ECR** — authenticates with ECR and pushes the image.
5. **Configure kubectl** — updates `~/.kube/config` for the EKS cluster.
6. **Create/Update Kubernetes Secrets** — injects `GROQ_API_KEY` and `GOOGLE_API_KEY` as a K8s Secret.
7. **Deploy to EKS** — patches the image tag in `k8/deployment.yaml` and applies the manifests.
8. **Verify Deployment** — waits for rollout to complete and checks pod health.

**Required Jenkins environment variables:**

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | Target region |
| `ECR_REGISTRY` | `<account-id>.dkr.ecr.<region>.amazonaws.com` |
| `ECR_REPOSITORY` | ECR repo name (default: `multi-doc-chat`) |
| `EKS_CLUSTER_NAME` | EKS cluster name (default: `multi-doc-chat-cluster`) |
| `GROQ_API_KEY` | Groq API key (injected as K8s secret) |
| `GOOGLE_API_KEY` | Google API key (injected as K8s secret) |

---

## AWS Infrastructure

The CloudFormation template at `infra/eks-with-ecr.yaml` provisions:

| Resource | Details |
|---|---|
| VPC | Custom VPC with 2 public subnets across AZs |
| Internet Gateway | For outbound internet access |
| EKS Cluster | `multi-doc-chat-cluster` (configurable) |
| EKS Node Group | Auto-scaling: min 1, desired 2, max 3 × `t3.small` |
| ECR Repository | `multi-doc-chat` — stores Docker images |
| IAM Roles | EKS cluster role + node instance role with required policies |
| Security Groups | Cluster communication and node access |

**Default region:** `ap-southeast-2` (Sydney) — override via `AWS_REGION`.

---

## Kubernetes Manifests

### `k8/deployment.yaml`

- **2 replicas** with a **RollingUpdate** strategy (`maxSurge: 1`, `maxUnavailable: 0`) for zero-downtime deploys.
- Image pulled from ECR using the `ecr-registry-secret` pull secret (created by the deploy pipeline).
- Resource requests: `250m` CPU / `512Mi` RAM; limits: `1000m` CPU / `2Gi` RAM.
- Liveness and readiness probes on `GET /health` (port 8080).
- Environment injects `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `GROQ_API_KEY`, and `GOOGLE_API_KEY` (latter two from a K8s Secret).

### `k8/service.yaml`

Exposes the deployment as a Kubernetes Service to route traffic to the pods.

---

## Git Branches

| Branch | Purpose |
|---|---|
| `master` | Stable baseline |
| `eks_deploy` | **Current** — EKS deployment wiring & Kubernetes manifests |
| `deployonAWS` | AWS deployment experiments |
| `jenkins` | Jenkins pipeline development |
| `test` | Test pipeline experiments |
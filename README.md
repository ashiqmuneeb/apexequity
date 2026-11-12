# 📈 ApexEquity — Institutional Financial Stock Analysis Engine

An automated institutional financial research and competitive equity analysis platform built with **LlamaIndex RAG**, **Groq AI Acceleration**, **local HuggingFace embeddings (`BAAI/bge-small-en-v1.5`)**, and a decoupled **React 19** executive terminal.

Designed with **Enterprise Clean Layered Architecture** on the backend and **Feature-Sliced Component Architecture** on the frontend.

---

## 🏗️ Architecture Design & Standards

### 1. Backend Architecture (`backend/app/`)
Organized following strict separation of concerns, dependency injection, and PEP 8 standards:

```
backend/
├── app/
│   ├── main.py                     # App factory & route inclusions (thin entry point)
│   ├── core/                       # Core configuration, settings, logger
│   │   ├── config.py               # Pydantic Settings, paths, and environment
│   │   └── logger.py               # Structured logging configuration
│   ├── schemas/                    # Pydantic DTOs & data validation contracts
│   │   ├── analysis.py             # SingleStockRequest, CompareStockRequest, CustomQuery
│   │   ├── article.py              # ArticlePayload, ArticleItem, ArticleListResponse, LiveStockFetchRequest
│   │   └── system.py               # SystemStatusResponse, KeyConfigPayload
│   ├── services/                   # Business logic layer (decoupled from HTTP)
│   │   ├── rag_engine.py           # LlamaIndex query engine lifecycle & Groq integration
│   │   ├── analysis_service.py     # Prompt orchestration & report synthesis
│   │   └── article_service.py      # Article file storage, Yahoo Finance ingestion, CRUD, index persistence
│   └── api/                        # HTTP Presentation layer (APIRouter endpoints)
│       ├── deps.py                 # Dependency injection providers
│       └── v1/
│           ├── api.py              # Aggregated v1 API Router
│           └── endpoints/
│               ├── analysis.py     # POST /analyze/single, /analyze/compare, /analyze/custom
│               ├── articles.py     # GET /articles, POST /articles, POST /articles/fetch-live, DELETE /{ticker}
│               └── system.py       # GET /status, POST /config/key, POST /index/rebuild
├── articles/                       # Document corpus (audited filings, 10-K notes, earnings)
│   ├── AAPL.txt
│   ├── GOOGL.txt
│   ├── MSFT.txt
│   └── NVDA.txt
├── storage/                        # Vector persistence (BAAI/bge-small-en-v1.5 embeddings)
├── tests/                          # Automated Pytest test suite (9 passing unit & integration tests)
├── .env                            # Environment variables (GROQ_API_KEY, PORT, etc.)
├── .env.example
├── .gitignore
├── pytest.ini                      # Pytest runner configuration
├── ruff.toml                       # PEP 8 & Ruff linting configuration
└── requirements.txt
```

### 2. Frontend Architecture (`frontend/src/`)
Organized following React/Airbnb clean component standards and decoupled API services:

```
frontend/
├── src/
│   ├── main.jsx                    # React entrypoint
│   ├── App.jsx                     # Root application coordinator with dynamic market background
│   ├── index.css                   # Global Tailwind CSS styles, animations, grid background & print CSS
│   ├── api/                        # Centralized API service layer (no direct fetch in UI)
│   │   ├── client.js               # Unified fetch wrapper with error handling
│   │   ├── analysisApi.js          # singleStock, compareStocks, customQuery
│   │   ├── articlesApi.js          # listArticles, saveArticle, fetchLiveStock, deleteArticle, rebuildIndex
│   │   └── systemApi.js            # getStatus, saveGroqKey
│   ├── hooks/                      # Custom reusable React hooks
│   │   ├── useSystemStatus.js      # Status polling & Groq key checks
│   │   ├── useArticles.js          # Articles state & CRUD handlers
│   ├── components/                 # Shared UI components
│   │   ├── common/
│   │   │   ├── Header.jsx              # ApexEquity institutional navigation bar
│   │   │   ├── FinancialBackground.jsx # Animated financial chart waves, glow orbs & candlestick silhouettes
│   │   │   ├── TickerTape.jsx          # Live financial market ribbon with dynamic indices
│   │   │   ├── MetricsScorecard.jsx    # KPI financial indicators, revenue & sentiment scorecard
│   │   │   ├── ComparisonChart.jsx     # Recharts dual-bar comparative visual benchmarking
│   │   │   ├── StatusBanner.jsx        # System warnings & prompts
│   │   │   ├── MarkdownView.jsx        # Clean GFM markdown renderer with math formatting
│   │   │   ├── ApiKeyModal.jsx         # Secure API key modal
│   │   │   ├── LoadingSkeleton.jsx     # Polished animated loading state
│   │   │   └── ErrorCard.jsx           # Standardized error presentation
│   │   └── layout/
│   │       ├── TabNavigation.jsx       # Institutional tab switcher
│   │       └── Footer.jsx              # Bottom system info & compliance notes
│   ├── features/                   # Business domain feature views
│   │   ├── singleStock/            # SingleStockView.jsx (Equity Research Dossier)
│   │   ├── comparison/             # ComparisonView.jsx (Peer & Moat Benchmark)
│   │   ├── customQuery/            # CustomQueryView.jsx (Market Intelligence Terminal)
│   │   └── articles/               # ArticleManager.jsx (SEC Disclosures & Yahoo Finance Ingestion)
│   └── constants/                  # Configuration & constant values
│       └── stockTickers.js         # Default ticker suggestions & inquiries
├── .prettierrc                     # Prettier code formatting rules
├── .gitignore
├── package.json
└── vite.config.js
```

---

## ⚡ Prerequisites

1. **Python 3.10+** (Configured in `backend/venv`)
2. **Node.js 18+** & **npm** (Configured in `frontend/node_modules`)
3. **Groq API Key** (from [console.groq.com/keys](https://console.groq.com/keys))

---

## 🚀 Running the Application

### ⚡ 1-Click All-in-One Launch (Recommended)

Simply double-click **`run.bat`** in the project root:
- Automatically verifies backend virtual environment & installs dependencies if needed.
- Automatically verifies vector storage index and embeds documents if uninitialized.
- Automatically runs `npm install` for frontend if needed.
- Concurrently launches the **FastAPI Backend Server** on `http://127.0.0.1:8000`.
- Concurrently launches the **React Vite Frontend** on `http://localhost:5173`.
- Automatically opens **`http://localhost:5173`** in your default web browser!

---

### Manual Launch (Optional)

If you prefer starting each service manually in your own terminal:
- **Backend:**
  ```powershell
  cd backend
  .\venv\Scripts\activate
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **Frontend:**
  ```powershell
  cd frontend
  npm run dev
  ```

---

## 🧪 Automated Testing

Execute the backend automated test suite:
```powershell
cd backend
.\venv\Scripts\pytest -v
```
All 9 unit and integration tests validate request models, CRUD persistence, live market fetching, and system health checks.

---

## 🛠️ API Reference

All endpoints are available under both `/api/v1` and `/api`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/status` | System readiness, Groq key status, indexed article count |
| `POST` | `/api/v1/config/key` | Update and persist Groq API key at runtime |
| `GET` | `/api/v1/articles` | List all indexed stock filing summaries |
| `POST` | `/api/v1/articles` | Add or update a stock filing document |
| `POST` | `/api/v1/articles/fetch-live` | Fetch real-time financials via Yahoo Finance and auto-index |
| `DELETE` | `/api/v1/articles/{ticker}` | Delete a stock filing document |
| `POST` | `/api/v1/index/rebuild` | Trigger vector embedding computation and persistence |
| `POST` | `/api/v1/analyze/single` | Run single-stock deep-dive report |
| `POST` | `/api/v1/analyze/compare` | Run side-by-side comparative analysis |
| `POST` | `/api/v1/analyze/custom` | Natural language search across the financial corpus |

---
description: ApexEquity project rules (truthfulness, architecture, security, design system)
---

# Project
ApexEquity is an SEC-filing analysis platform.
- backend/: Python 3.11+, FastAPI, Pydantic v2, LlamaIndex, Groq LLM, local HuggingFace embeddings (BAAI/bge-small-en-v1.5). Layers: app/core, app/schemas, app/services, app/api/v1/endpoints.
- frontend/: React 19, Vite, Tailwind CSS v4, Recharts, lucide-react, react-markdown. Structure: src/api, src/hooks, src/components, src/features.

# Truthfulness rules (highest priority)
1. Never hard-code financial figures, prices, ratings, sentiment, scores or "consensus" values in production code. Test fixtures are allowed and must live in tests/fixtures.
2. Every number shown in the UI or a report must come from (a) SEC XBRL company facts, (b) retrieved filing text with a citation, or (c) a dataset explicitly labeled "Sample data".
3. If data is missing, show "N/A" or "Not disclosed in the retrieved filings". Never invent defaults (no default "Bullish").
4. Do not write accuracy or performance claims in README or docs unless they come from `python -m eval.run` and link to the results file.
5. Use "SEC 10-K" only for real filings that were ingested from SEC EDGAR.
6. Show a "Not investment advice" disclaimer in the footer and on every exported report.

# Backend rules
- Pydantic v2 models for all request and response bodies. Type hints everywhere. Ruff must pass.
- Configuration via pydantic-settings and environment variables. No secrets in the repo.
- Blocking LLM or embedding calls must not block the event loop (use threadpool or background jobs).
- Map upstream failures: Groq rate limit -> HTTP 429 with Retry-After; model not found -> 502 with a clear message.
- Unit tests never call the network. Use fake LLM and fake embeddings. Record SEC responses as fixtures.
- Never commit: .env, storage/, data/, dist/, __pycache__/, *.db.
- No absolute local paths in document metadata.

# Security rules
- CORS: explicit allowlist from env. Never "*" together with credentials.
- Admin endpoints (ingest, delete, rebuild) require an `X-API-Key` header. Do not add endpoints that write secrets to disk.
- SEC requests: send User-Agent from env, max 5 requests/second, cache responses on disk.

# Frontend rules
- No fetch calls inside components: use src/api and hooks.
- Use design tokens (Tailwind @theme variables), never raw hex values inside className.
- Every async view needs loading, empty, error and success states.
- Text contrast >= 4.5:1. Visible focus rings. Keyboard accessible. Responsive from 360px.
- No fake "live" data. Anything not from the API must show a "Sample data" badge.
- Respect prefers-reduced-motion. Animations must pause when the tab is hidden.

# Design system (keep the current identity: light, institutional, navy + cyan)
- Fonts: Inter (UI), JetBrains Mono (tickers, numbers, kbd, badges).
- Colors: see tokens in frontend/src/index.css (@theme). Navy = primary, cyan = accent graphics, emerald = positive, rose = negative/risk, amber = warning.
- Cards: white at ~94% opacity, 1px slate-200 border, soft navy-tinted shadow, rounded-xl/2xl, hover = navy border + faint cyan glow.
- Labels: 10-11px uppercase, tracking-wider, bold, slate-600.
- Icons: lucide-react only.

# Workflow rules
- Plan first (Implementation Plan artifact), then implement.
- Before finishing any task run: ruff, pytest, `npm run build`. Report results honestly.
- For UI changes, verify in the browser and attach screenshots to the Walkthrough.
- Small commits with conventional messages (feat:, fix:, test:, docs:).
- Ask before adding paid services, deleting user data, or changing the tech stack.
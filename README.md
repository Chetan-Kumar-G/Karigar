# Kārigar — AI-Driven Market Linkage & Smart Cataloging for Marginalized Artisans

**SIH 2026 · Problem Statement 26090** · Ministry of Social Justice & Empowerment

A demo-ready mobile prototype that turns *one phone photo* and *one voice note* into a
trustworthy, fairly-priced, fairly-discoverable, bulk-order-ready product listing — an
**AI business manager** for artisans with low digital literacy, limited English, and a
low-end Android phone.

The build implements all seven features (F1–F7) from the project's Master Technical
Feature Specification. Where a production model needs unavailable data or heavy compute,
there is a clearly-labelled prototype fallback behind the same interface — see
[**Honesty report**](#honesty-report--what-is-real).

---

## Live demo

- **App:** <https://chetan-kumar-g.github.io/Karigar/>
- **API:** <https://karigar-backend-4n9v.onrender.com> (hosted via [render.yaml](render.yaml); frontend auto-deploys via [.github/workflows/deploy-web.yml](.github/workflows/deploy-web.yml))

Login as artisan `9800000001` / OTP `123456`, or tap **Open SIH Demo Mode**. See
[Demo mode & test credentials](#demo-mode--test-credentials) for the full cast.

Both are on free hosting tiers, so:
- **Cold start:** the backend spins down after ~15 min idle; the first request after
  that can take 30–60s (and may time out once) while it wakes back up. Reload if a
  screen seems stuck loading right after opening the link cold.
- **Data resets on restart:** the backend's SQLite database lives on ephemeral disk, so
  every spin-down/restart reseeds it back to the fixed demo dataset. Anything created
  during a session (new products, orders) won't survive an idle restart — expected
  behaviour, not a bug, given the auto-seed-on-empty-DB design below.
- **Voice recording uses the labelled demo fallback** — the deployed backend doesn't
  bundle a speech-to-text engine (see [F2 live voice](#f2-live-voice-real-speech-to-text)),
  so recorded audio shows an honest "not enabled on this server" banner and a sample
  transcript. Typed descriptions still produce a fully real F2 catalog.

---

## Table of contents

1. [Architecture](#architecture)
2. [Feature map (F1–F7)](#feature-map-f1f7)
3. [Technology stack](#technology-stack)
4. [Prerequisites](#prerequisites)
5. [Quick start (backend)](#quick-start-backend)
6. [Quick start (mobile)](#quick-start-mobile)
7. [Docker](#docker)
8. [Environment variables](#environment-variables)
9. [Demo mode & test credentials](#demo-mode--test-credentials)
10. [Running the demo (judge script)](#running-the-demo-judge-script)
11. [API reference](#api-reference)
12. [Tests](#tests)
13. [Honesty report — what is real](#honesty-report--what-is-real)
14. [Judge technical explanation (per feature)](#judge-technical-explanation-per-feature)
15. [Known limitations](#known-limitations)
16. [Production upgrade path](#production-upgrade-path)
17. [Project layout](#project-layout)
18. [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  MOBILE (Flutter)  — camera · mic · low-literacy UI          │
│  offline draft cache · demo-mode role switch                 │
└───────────────────────────┬────────────────────────────────┘
                            │  REST / JSON over HTTP
┌───────────────────────────▼────────────────────────────────┐
│  FastAPI BFF   — phone-OTP → JWT · validation · error shaping│
├────────────────────────────────────────────────────────────┤
│  AI services (swappable, each logs an AiRun metadata row)    │
│   F1 OpenCV studio   F2 grounded cataloger   F3 craft graph  │
│   F4 LightGBM pricing  F5 LightGBM demand   F6 OR-Tools MILP  │
│                        F7 fair re-ranking                    │
├────────────────────────────────────────────────────────────┤
│  SQLAlchemy · 27 tables · SQLite (default) or Postgres+pgvector│
└────────────────────────────────────────────────────────────┘
```

Every AI call returns a **technical-metadata object** (`feature`, `model`, `mode`,
`latency_ms`, `inputs`) that the app's *AI System Insights* screen renders for the
technical judging round.

---

## Feature map (F1–F7)

| # | Feature | Endpoint(s) | Engine | Mode |
|---|---|---|---|---|
| F1 | AI Product Studio + Readiness Gate | `POST /product/analyze` | OpenCV — GrabCut segmentation, Laplacian-variance sharpness, histogram exposure, mask-bbox framing, background variance; CLAHE + gamma auto-enhance; composite score & 3-way gate (spec §3.I) | **REAL** |
| F2 | Multilingual Grounded Auto-Cataloger | `POST /catalog/generate` | ASR (pluggable) → KG-seeded slot NER → **Fact-Grounding Guard** → cross-modal heuristic → EN/HI generation | **REAL** grounding · **PROTOTYPE** cross-modal · optional **LLM** phrasing |
| F3 | Craft Knowledge Graph + Digital Passport | `GET /craft/{id}`, `GET /passport/{product_id}` | Relational graph + recursive-CTE traversal; provenance-confidence formula (spec §5.I) | **REAL** |
| F4 | Fair Cost-Aware Pricing | `POST /price/predict` | Cost-floor formula + **LightGBM** regressor + native tree-SHAP; recommendation **clipped at floor by construction** (spec §6.I / §30) | **REAL** (formula fallback if model absent) |
| F5 | Demand & Opportunity Intelligence | `GET /demand/forecast` | **LightGBM** quantile regression (0.1/0.5/0.9) + prediction→action translation | **REAL model · SIMULATED history** |
| F6 | B2B Matching + Cluster Order Pooling | `POST /buyer/match`, `POST /order/allocate` | **OR-Tools CP-SAT MILP** allocation (spec §8.I) + **exact Shapley-value** payment split (spec §8.I.5) + greedy baseline | **REAL** |
| F7 | Fair Market Discovery + Business Copilot | `GET /search`, `GET /artisan/{id}/insights` | TF-IDF cosine retrieval + `α·Rel + β·NewSeller + γ·Region − δ·Exposure` re-rank, weights configurable, exposure persisted per impression (spec §9.I) | **REAL** |

---

## Technology stack

| Layer | Choice |
|---|---|
| Mobile | **Flutter** (`provider`, `go_router`, `http`, `image_picker`, `record`, `fl_chart`) |
| Backend | **Python 3.12–3.14 · FastAPI · SQLAlchemy 2** |
| Database | **SQLite** (zero-config default) or **PostgreSQL + pgvector** (docker-compose) |
| CV | **OpenCV** (headless) |
| ML | **LightGBM**, scikit-learn, NumPy |
| Optimisation | **Google OR-Tools** (CP-SAT), PuLP/CBC fallback |
| Auth | mock phone-OTP → **JWT** (PyJWT) |

> Verified on **CPython 3.14.3 (Windows)** — every dependency above installs from a
> binary wheel, no build tools required.

---

## Prerequisites

- **Python 3.12+** (3.14 works). `pip`.
- **Flutter 3.27+** (built & analysed on Flutter 3.47 / Dart 3.13).
- Optional: **Docker** (for the Postgres path), an Android emulator or device.

---

## Quick start (backend)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Git Bash / macOS / Linux:
source .venv/Scripts/activate        # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

# train the two tiny ML models (writes data/models/*.txt) — ~5 seconds
python -m app.ai.f4_pricing.train
python -m app.ai.f5_demand.train

# seed the demo database (SQLite at backend/data/sih.db)
python -m app.db.seed

# run (localhost only)
uvicorn app.main:app --reload --port 8000

# …or, to also reach it from a phone on the same Wi-Fi (binds 0.0.0.0 and
# prints the exact LAN URL + dart-define line to use):
python -m scripts.serve
```

- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/health> (also <http://localhost:8000/health>).
  Returns `{"status","database","version",...}`; `database` is `"ok"` / `"error"`,
  and the endpoint stays **200 even if the DB is down** so the app can tell
  *backend unreachable* from *DB down* from *bad credentials*.
- The server **auto-seeds** on first boot if the DB is empty, so `python -m app.db.seed`
  is optional but recommended.

### F2 live voice (real speech-to-text)

The default `.venv` (Python 3.14) has **no ASR engine** — recorded audio falls back to a
clearly-labelled demo transcript (typed descriptions are always real). For **real,
offline** voice, run the backend from the bundled Python 3.12 venv:

```bash
cd backend
py -3.12 -m venv .venv312
.venv312\Scripts\python.exe -m pip install -r requirements.txt faster-whisper
.venv312\Scripts\python.exe -m scripts.check_asr          # verify (downloads the model once)
.venv312\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

On boot you'll see `F2 voice: REAL speech-to-text ACTIVE via faster-whisper`.
Config lives in `backend/.env` (`SIH_WHISPER_MODEL`, `SIH_WHISPER_LANGUAGE`).
Cloud alternative: put an OpenAI-compatible key in `SIH_LLM_API_KEY` and use the
normal `.venv` — it uses the `/audio/transcriptions` API automatically.
Status any time: `GET /api/catalog/asr-status`.

## Quick start (mobile)

```bash
cd mobile
flutter pub get
# generate android/ (and web/) platform folders if missing:
flutter create --platforms=android,web --project-name artisan_market --org com.sih26090 .

# Android emulator reaches your host at 10.0.2.2 — this is the built-in default,
# so `flutter run` with no defines just works.
flutter run

# Override the backend for any other target (MEDIA_HOST is derived automatically):
flutter run --dart-define=API_BASE_URL=http://192.168.1.50:8000/api   # physical device
flutter run --dart-define=API_BASE_URL=http://localhost:8000/api      # web / desktop
```

All backend-URL logic lives in **one file** — `mobile/lib/core/app_config.dart`.
On a physical device you can also skip the rebuild: open the app, and on the
"Can't reach the server" screen tap **Change server address** and type your
laptop's `IP:8000` (run `python -m scripts.serve` on the laptop to print it).
The address is saved on the device.

Start uvicorn with `--host 0.0.0.0` (or use `python -m scripts.serve`) when
testing from a physical device.

---

## Docker

Brings up **Postgres 16 + pgvector** and the backend, pre-trained and seeded:

```bash
cp .env.example .env
docker compose up --build
# backend on http://localhost:8000 ; then point the app at it:
#   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
```

---

## Environment variables

Copy `.env.example` → `.env`. Everything is optional. Highlights:

| Var | Default | Effect |
|---|---|---|
| `SIH_DATABASE_URL` | SQLite file | set to `postgresql+psycopg://sih:sih@localhost:5432/sih` for Postgres |
| `SIH_MOCK_OTP` | `123456` | OTP accepted for every phone number |
| `SIH_ASR_BACKEND` | `auto` | `whisper` (needs `faster-whisper`), `api`, or `fallback` |
| `SIH_LLM_ENABLED` / `SIH_LLM_API_KEY` | off | when set, an OpenAI-compatible endpoint *rephrases* F2/Copilot text — it never invents facts |
| `SIH_PRICING_MIN_MARGIN` | `0.18` | F4 sustainable-margin floor |
| `SIH_F6_LAMBDA` | `40` | F6 cost-vs-quality/reliability trade-off |
| `SIH_F7_ALPHA/BETA/GAMMA/DELTA` | `1 / 0.35 / 0.25 / 0.30` | F7 fairness weights |

No secrets are committed. `SIH_JWT_SECRET` must be changed for any non-demo use.

---

## Demo mode & test credentials

| Role | Phone | OTP |
|---|---|---|
| Artisan (Meera Devi, Madhubani) | `9800000001` | `123456` |
| Buyer (Meridian Hotels procurement) | `9900000001` | `123456` |

**Named cast for the buyer→artisan walkthrough** (OTP `123456` for all; see `GET /api/demo/cast`):

| Buyers | Phone | | Artisans (Thanjavur art-plate cluster) | Phone | Capacity |
|---|---|---|---|---|---|
| Agneay (B2B) | `9600000001` | | Chetan | `9700000001` | 900 |
| Cynthiya (boutique) | `9600000002` | | Prasannaa | `9700000002` | 1500 |
| Prarthana (government) | `9600000003` | | Deeraj | `9700000003` | 700 |

Walkthrough: log in as **Agneay** → open the *"2,900 Thanjavur art plates"* requirement
→ **Find Artisan Cluster** → F6 splits it **Prasannaa 1500 + Chetan 900 + Deeraj 500**
with a Shapley payment split (each share explained) → **Confirm** → log in as
**Prasannaa** (`9700000002`) → **Orders** shows the pooled order with her units + share.
**Cynthiya**'s *"60 plates"* requirement goes to a single maker (small-order shape).

In-app: **Login → "Open SIH Demo Mode"**, or **Profile → SIH Demo Mode**.

| Action | Endpoint | What it does |
|---|---|---|
| **Load demo** | `POST /api/demo/load` | rebuilds the full dataset **and** returns ready artisan + buyer JWTs |
| **Reset demo** | `POST /api/demo/reset` | rebuilds the dataset only |
| Scenario | `GET /api/demo/scenario` | the script below, machine-readable |

Everything is repeatable — **no manual DB edits and no source changes during the demo.**

---

## Running the demo (judge script)

1. **Login** as artisan `9800000001 / 123456` (or tap *Load demo*).
2. **Dashboard** — "Your business today", 3 things need attention.
3. **＋ Add product** → name it, pick *Madhubani painting*.
4. **Studio** → pick the dim demo photo → **F1** scores it (~55–60/100) → tap through
   the auto-enhanced **Before → After** and the five component bars.
5. **Add voice** → *Use the demo recording* → **F2** shows the transcript, the
   structured attributes, the **AI verification** panel (origin claim **flagged** —
   *"needs GI documentation"*), and the EN/HI catalog with SEO keywords.
6. **Craft Passport** → **F3**: provenance confidence ≈ 0.74–0.84 with the weighted
   breakdown, related crafts (via recursive CTE), sample verification record.
7. **Fair price** → enter ₹180 / 6h / ₹60 / ₹40 / ₹30 → **F4**: floor, competitive
   range, recommended, *"Why this price?"* + expandable tree-SHAP for judges.
   *Ask "what if the market is below cost?"* → re-run with `category_median` 150 → the
   recommendation clamps to the floor.
8. **Review & publish** → listing created.
9. **Market** tab → search **"handwoven cotton dupatta"** → the brand-new artisan
   ranks above established sellers; tap **Compare** for fairness ON vs OFF and the
   exposure-gap metric.
10. **Business Copilot** → "demand rising" / "you may be underpricing" cards, each
    tagged with the feature that produced it.
11. **Profile → Switch to Buyer mode** (or login `9900000001`).
12. Open **"5,000 bamboo welcome baskets"** → **Find artisan cluster**.
13. **F6** runs the CP-SAT MILP live → **5,000 / 5,000** across 3 artisans in
    ~40–90 ms → **Optimization** panel (objective value, solve time, capacity
    utilisation) → **Fair payment distribution**: Shapley bar vs by-units bar,
    visibly different → **vs. naive greedy baseline**.
14. **Confirm allocation.**
15. **AI System Insights** (dashboard top-right or Profile) → per-feature model /
    mode / latency, the full **F7 ranking breakdown table**, recent AI runs.

---

## API reference

Interactive docs at `/docs`. Core endpoints (all under `/api`):

| Method | Path | Feature |
|---|---|---|
| `POST` | `/auth/otp/request` · `/auth/otp/verify` | mock OTP → JWT |
| `POST` | `/product` · `/product/publish` | product lifecycle |
| `POST` | `/product/analyze` | **F1** |
| `POST` | `/catalog/generate` | **F2** |
| `GET`  | `/craft/{id}` · `/passport/{product_id}` | **F3** |
| `POST` | `/price/predict` | **F4** |
| `GET`  | `/demand/forecast` | **F5** |
| `GET`  | `/requirements` · `POST /requirements` | B2B requirements |
| `POST` | `/buyer/match` · `/order/allocate` | **F6** |
| `GET`  | `/search` · `/search/compare` | **F7** discovery |
| `GET`  | `/artisan/{id}/insights` · `/artisan/{id}/dashboard` | **F7** copilot / home |
| `GET`  | `/debug/ai-runs` · `/debug/ai-runs/summary` · `/debug/f7-explain` | judge screen |
| `POST` | `/demo/load` · `/demo/reset` | demo mode |

Validation via Pydantic; errors return a human-readable `detail` (never a raw stack
trace). Unhandled exceptions become a friendly 500: *"Your work is safe — please try
again."*

---

## Tests

**Backend** (`cd backend`):

```bash
python -m pytest -q            # 27 tests
python scripts/smoke.py        # 43-check end-to-end journey via TestClient
```

Covers: F4 floor invariant (400 randomised cases — recommendation never below floor),
F6 allocation feasibility / capacity / price-ceiling / Shapley-sums-to-payment /
solve-time, F7 ordering & boost decay & exposure-gap, API validation, and the full
create → catalog → price → publish → search → match flow.

**Mobile** (`cd mobile`):

```bash
flutter analyze     # 0 issues
flutter test        # model-parsing tests
flutter build web   # full-tree compile check
```

---

## Honesty report — what is real

Internal labels used throughout the code and surfaced on the *AI System Insights*
screen: **REAL · PROTOTYPE · SIMULATED_DATA · FALLBACK**.

| Component | Status | Notes |
|---|---|---|
| F1 segmentation + 5-dim scoring + gate | **REAL** | OpenCV on the actual pixels. GrabCut stands in for SAM (SAM is the documented production upgrade). |
| F1 auto-enhance (CLAHE + gamma + studio bg) | **REAL** | Zero-DCE-style tone curve approximated with a measured-mean gamma. |
| F2 ASR | **REAL if** `faster-whisper` installed or an API key is set; otherwise **FALLBACK** to typed text or a deterministic demo transcript. IndicWav2Vec/IndicTrans2 = production upgrade. |
| F2 slot extraction + **Fact-Grounding Guard** | **REAL** | Deterministic rule engine over the transcript + Craft-KG vocabulary. This is the feature's core contribution and it runs live. |
| F2 Cross-Modal Authenticity Verifier | **PROTOTYPE** | Colour/category heuristic. A CLIP-class visual-entailment scorer is the documented upgrade. |
| F2 copy generation | **REAL** template; **LLM** only if `SIH_LLM_ENABLED` — and only to rephrase validated slots. |
| F3 craft graph + recursive-CTE + passport confidence | **REAL** | Seeded from realistic GI/ODOP/cluster data. |
| F3 certifications | **SIMULATED_DATA** | Every record is labelled *"Sample Verification Record — not a real GI certificate"*. No government certification is fabricated. |
| F4 cost-floor formula | **REAL** | `base / (1 − margin)`, unit-tested to bind. |
| F4 price model | **REAL** LightGBM + native tree-SHAP, trained at setup on a synthetic-but-realistic generator; **FALLBACK** to a deterministic cost-plus-market formula if the booster file is missing. |
| F5 forecast model | **REAL** LightGBM quantile regression; **SIMULATED_DATA** history (~200 days per category, generated — openly flagged in the UI per the cold-start rule). |
| F5 prediction→action translation | **REAL** | Scales the forecast delta to the artisan's capacity + a deadline. |
| F6 allocation | **REAL** | OR-Tools CP-SAT MILP, live, objective value + solve time shown. |
| F6 Shapley payment split | **REAL** | Exact enumeration of all `2^N` sub-coalitions (tractable for the N ≤ 8 a pooled order reaches). Monte-Carlo sampling is the stated production path for large N. |
| F7 retrieval + fairness re-rank | **REAL** | TF-IDF cosine + the spec §9.I formula; weights configurable; one impression persisted per shown listing. |
| F7 interaction / exposure history | **SIMULATED_DATA** | Seeded with a deliberately skewed popular-vs-new distribution so the effect is demonstrable. |
| F7 Business Copilot | **REAL** | Cards are built from structured F1/F4/F5/F6 output; the LLM (if enabled) only phrases them. |

**NOT IMPLEMENTED** (out of prototype scope, no fake stand-in): real IndicWav2Vec/
IndicTrans2 checkpoints, a fine-tuned visual-entailment model, live market-price
scraping, ONDC/GeM adapters, on-device offline AI inference, SMS OTP delivery.

---

## Judge technical explanation (per feature)

- **F1** — The uploaded JPEG is EXIF-oriented and decoded with OpenCV. GrabCut produces
  a foreground mask; five dimensions are measured directly (variance-of-Laplacian for
  focus, luminance-histogram mean + tail clipping for exposure, mask bounding-box ratio
  and centroid for framing, LAB colour-std + Canny edge density in the mask *complement*
  for background, pixel count for resolution). They combine with the fixed spec weights
  into a 0–100 score that routes to accept ≥ 80 / auto-enhance 50–79 / retake < 50. Auto-
  enhance applies a mean-derived gamma, CLAHE on the L channel, grey-world white balance
  and a masked studio-gradient background, then re-scores.

- **F2** — Audio (or typed text, or a demo transcript) is transcribed, then a rule-based
  slot extractor seeded with the Craft-KG vocabulary pulls material/technique/region/
  colours/effort. The **Fact-Grounding Guard** marks each attribute `confirmed_from_voice`
  only if its token is in the transcript; any origin/GI claim is always `flagged` because
  F2 cannot verify documentation. A colour/category heuristic gives a visual-consistency
  label per visually-checkable claim. An LLM is used *only* to phrase already-validated
  slots — never to add facts.

- **F3** — Artisan → Cluster → Craft → {Technique, Material, Region} → Passport →
  Certification are relational tables; "related crafts" come from a genuine recursive CTE
  over a typed `craft_relation` edge table (runs identically on SQLite and Postgres).
  `provenance_confidence = 0.40·gov + 0.25·grounding + 0.20·visual + 0.15·self-report`,
  persisted with its component breakdown.

- **F4** — `P_floor = base_cost / (1 − m_min)`. A LightGBM regressor (trained on a
  synthetic generator that encodes the intended economics) predicts a market price; the
  recommendation is `max(P_floor, clip(model, P_floor, P_market_max))` — so it is
  **structurally impossible** to recommend below the floor (400 randomised unit tests
  confirm). Native tree-SHAP gives the per-prediction factor contributions.

- **F5** — Three LightGBM quantile models (α = 0.1 / 0.5 / 0.9) roll a daily forecast
  forward over the window; the point forecast is the 0.5 sum, the interval the 0.1/0.9
  sums. A separate decision layer converts the forecast delta into "make N more units by
  DATE", capped at the artisan's own monthly capacity. The history is generated and the
  UI says so.

- **F6** — Eligible artisans are filtered by craft compatibility (via F3), capacity and
  price band. A CP-SAT model minimises `Σ(cost+logistics)·xᵢ − λ·Σ(quality+reliability)·xᵢ`
  subject to demand, per-artisan capacity, min-lot and max-artisans constraints; if total
  capacity < demand it switches to maximise-fill and reports the shortfall. The buyer's
  total payment is then split by the **exact Shapley value** over the coalition of
  selected artisans (characteristic function = coalition surplus, computed for all `2^N`
  subsets), normalised to the payment total. A greedy cheapest-first baseline is computed
  alongside for comparison.

- **F7** — Candidates are retrieved by TF-IDF (1–2 gram) cosine + keyword overlap, then
  re-scored as `α·relevance + 0.15·quality + β·newSellerBoost + γ·regionBoost −
  δ·exposurePenalty`. `newSellerBoost` decays linearly to 0 as verified-sales approach a
  threshold (bootstrap, not a permanent thumb). Each shown listing gets one persisted
  impression, so exposure state actually evolves. A position-weighted exposure-gap metric
  and a fairness-ON-vs-OFF comparison are exposed for judges.

---

## Known limitations

- **Flutter build verified for web + static analysis**; an Android APK build additionally
  needs the Android SDK + accepted licenses on the build machine (`flutter doctor`).
- ASR quality in the fallback path is a deterministic demo transcript, not live regional-
  language recognition (install `faster-whisper` or set an API key for real ASR).
- F5 history and F7 interaction logs are synthetic — this is inherent to a pre-launch
  platform (cold start) and is labelled in the UI.
- The cross-modal authenticity check (F2) is a heuristic, not a trained model.
- pgvector is available via Docker but embeddings are stored as JSON arrays at this scale;
  the semantic-search path uses TF-IDF, not dense vectors.
- Single-instance app; no horizontal scaling, no rate limiting beyond FastAPI defaults.

---

## Production upgrade path

Each AI service sits behind a narrow interface, so upgrading is a drop-in replacement:

| Feature | Prototype now | Production |
|---|---|---|
| F1 | GrabCut + classical scoring | MobileSAM/SAM2 on-device, NIMA-class IQA, quantised Zero-DCE |
| F2 | pluggable ASR + rules | IndicWav2Vec + IndicTrans2, fine-tuned NER, CLIP visual-entailment, moderation queue UI |
| F3 | recursive CTE | Neo4j only if query complexity outgrows CTEs; learned link-prediction for GI candidacy |
| F4 | synthetic-trained LightGBM | LightGBM on real cost/sale data + live market-price scraping |
| F5 | simulated history | retrain on 3–6 months of real transactions; MASE monitoring |
| F6 | exact Shapley (N ≤ 8) | Monte-Carlo Shapley sampling; real-time re-solve on decline at SLA |
| F7 | TF-IDF + static weights | click-log-driven learned relevance; doubly-stochastic fairness LP |
| Infra | monolith + SQLite | split services, Postgres+pgvector, ONDC seller-app + GeM catalogue adapters |

---

## Project layout

```
SIHps090/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app factory, static /media, error shaping
│   │   ├── core/                   config · logging · JWT
│   │   ├── db/                     base · session · seed_data · seed
│   │   ├── models/                 27 SQLAlchemy tables (spec §11)
│   │   ├── schemas/                Pydantic request/response models
│   │   ├── services/               cross-route orchestration helpers
│   │   ├── ai/
│   │   │   ├── base.py             AiResult envelope + AiRun logging + timer
│   │   │   ├── f1_studio/          OpenCV readiness pipeline
│   │   │   ├── f2_catalog/         asr.py · cataloger.py (grounding guard)
│   │   │   ├── f3_graph/           graph.py (recursive CTE + passport formula)
│   │   │   ├── f4_pricing/         features · train · pricing (floor + LightGBM + SHAP)
│   │   │   ├── f5_demand/          train · forecast (quantile LightGBM + action layer)
│   │   │   ├── f6_matching/        allocation.py (CP-SAT MILP + exact Shapley)
│   │   │   └── f7_ranking/         ranking.py (fair re-rank + exposure gap)
│   │   └── api/routes/             auth·products·catalog·craft·pricing·demand·
│   │                               buyers·orders·discovery·debug·demo·meta
│   ├── tests/                      pytest suite
│   ├── scripts/smoke.py           43-check end-to-end journey
│   ├── requirements.txt
│   └── Dockerfile
├── mobile/
│   └── lib/
│       ├── main.dart
│       ├── core/                   app_config · theme · api_client · json
│       ├── models/models.dart      typed API models
│       ├── services/api_service.dart
│       ├── providers/              app_state · product_flow (offline draft)
│       ├── navigation/             app_router (go_router) · app_shell (bottom nav)
│       ├── widgets/                common · score_bar · ai_progress
│       └── features/               auth · dashboard · product_studio · craft_passport ·
│                                   pricing · demand · buyers · orders · marketplace ·
│                                   copilot · insights · profile · demo
├── docker-compose.yml             Postgres+pgvector + backend
├── .env.example
└── README.md
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| App shows the *"Can't reach the server"* screen | Backend not running, or wrong address. The screen shows the address it tried and the reason. Tap **Try again**, or **Change server address**. Emulator → `10.0.2.2:8000`; physical device → laptop LAN IP (run `python -m scripts.serve`); web/desktop → `localhost:8000`. |
| Images don't load in the app | `MEDIA_HOST` is now derived from `API_BASE_URL` automatically — no separate define needed. Only override it if media is served from a different origin. |
| Emulator camera shows the fake 3D "VirtualScene" room | That is the emulator's built-in camera. In Android Studio → **Device Manager → Edit → Show Advanced Settings → Camera → Back** choose **Webcam0** (uses your laptop webcam) or **Emulated**. F1's **Gallery** button works the same and needs no camera — push a JPG with `adb push photo.jpg /sdcard/Download/` first. |
| "Camera not available" dialog in F1 | Expected when the emulator has no camera configured. Tap **Choose from gallery** — F1 runs identically on a gallery image. |
| `flutter run` can't find android/ | `flutter create --platforms=android,web --project-name artisan_market --org com.sih26090 .` |
| F4 shows mode `FALLBACK` | Run `python -m app.ai.f4_pricing.train` (and `...f5_demand.train`). |
| `pip install` fails on a package | You're likely on Python < 3.12 with an old pip — `pip install --upgrade pip`, or use Python 3.12+. |
| Postgres: `pgvector` extension error | Use the `pgvector/pgvector:pg16` image from `docker-compose.yml`; the app does not require the extension at prototype scale. |
| Reset everything | `POST /api/demo/reset`, or delete `backend/data/sih.db*` and restart. |
```

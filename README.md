# SkillGap — Intelligent Resume-Job Alignment & Skill Roadmapping Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-teal.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

SkillGap is a production-grade web application designed for students, data scientists, and engineers to diagnose skill gaps between their resumes and target job descriptions. Built using explainable NLP heuristics, TF-IDF vectorization, topological prerequisite graphs, and unsupervised role clustering, it delivers an actionable, transparent roadmap to employment readiness without black-box hallucination.

---

## 1. Quick Start (Local Setup)

### Prerequisites
- Python 3.11, 3.12, or 3.13 installed
- Git

### Installation Steps

1. **Clone or navigate to the repository:**
   ```bash
   cd SkillGap_v2
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install pinned dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   *(Or edit `.env` to configure your `SECRET_KEY` and `DATABASE_URL`)*

5. **Start the Development Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 2. Seeded Demo Account

The application automatically seeds a demo account upon startup if it does not already exist:
- **Email:** `demo@skillgap.app`
- **Password:** `Demo@1234`
- **One-Click Demo:** Click the **"Try the demo"** button on the landing page to log in instantly.
- **Pre-loaded Data:** Includes 3 realistic historical analyses (Data Scientist, ML Engineer, Data Engineer) with full trend charts and computed roadmaps.

---

## 3. Production Deployment (Render)

SkillGap is pre-configured for one-click deployment on [Render](https://render.com) using either Native Python or Docker.

### Option A: Deploy via GitHub & `render.yaml` (Recommended)
1. Push `SkillGap_v2` to your GitHub repository.
2. Sign in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Connect your repository. Render will automatically read `render.yaml` and provision the web service.
5. In your service settings, add the following environment variables:
   - `SECRET_KEY`: Enter a 32+ character random string.
   - `DATABASE_URL`: `sqlite:///./skillgap.db` (or a managed PostgreSQL connection string).

### Option B: Deploy via Docker
1. In Render, select **New +** -> **Web Service**.
2. Connect your repository and select **Docker** as the runtime.
3. Render will build using the included `Dockerfile` and expose `/health` for health checking.

> **Important Persistence Note for Render Free Tier:**  
> The free web tier on Render uses an ephemeral disk; any SQLite database file will reset when the container spins down. For permanent production persistence, attach a free cloud PostgreSQL database (such as [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com)) by simply pasting the PostgreSQL connection URI into the `DATABASE_URL` environment variable. The app automatically detects PostgreSQL and handles schema initialization on startup.

---

## 4. Data Science Architecture & Code Directory

All algorithms are fully explainable, computationally lightweight for free hosting, and implemented without heavy external transformer dependencies.

| Data Science Concept | Technical Implementation | Code Location |
| :--- | :--- | :--- |
| **Section Parsing & Confidence** | PyMuPDF text streaming + Regex section headers (`Skills`, `Experience`, `Projects`, `Education`) with tiered confidence weighting. | [`app/services/pdf.py`](file:///d:/SkillGap_v2/app/services/pdf.py) & [`app/services/nlp.py`](file:///d:/SkillGap_v2/app/services/nlp.py) |
| **Word-Boundary Alias Matching** | Look-around regexes (`(?<![A-Za-z0-9_])...(?![A-Za-z0-9_])`) preventing boundary false positives (e.g. Excel/excellent, Java/JavaScript, Git/digital, ML/HTML). Dedicated patterns for `C++`, `C#`, `Node.js`, `CI/CD`. | [`app/services/nlp.py`](file:///d:/SkillGap_v2/app/services/nlp.py) |
| **Cue Phrase Intent Extraction** | Regex cue detection classifying required skills vs. preferred ("nice to have", "plus", "bonus") in JD text. | [`app/services/nlp.py`](file:///d:/SkillGap_v2/app/services/nlp.py) |
| **TF-IDF Skill Importance** | Scikit-learn `TfidfVectorizer` (sub-linear TF scaling, n-grams 1-2) fitted across a 25-role corpus to penalize generic words and weight rare domain competencies. | [`app/services/matching.py`](file:///d:/SkillGap_v2/app/services/matching.py) |
| **Partial Match Cosine Similarity** | Character n-gram (2–4 chars) cosine similarity with TF-IDF vectorization + domain relation ontology (e.g., PyTorch -> Deep Learning). Threshold: $0.45$. | [`app/services/matching.py`](file:///d:/SkillGap_v2/app/services/matching.py) |
| **Explainable Scoring Model** | Linear weighted formulation: 60% Exact Match + 20% Partial Credit + 10% Category Breadth + 10% Resume Quality. | [`app/services/scoring.py`](file:///d:/SkillGap_v2/app/services/scoring.py) |
| **Role-Fit Vector Ranking** | Cosine similarity between resume skill confidence vector and role requirement profiles in `jobs.csv`. | [`app/services/roles.py`](file:///d:/SkillGap_v2/app/services/roles.py) |
| **Market Clustering & PCA** | Unsupervised K-Means ($k=5$) with 2D Principal Component Analysis (PCA) projection and candidate profile coordinate mapping. | [`app/services/roles.py`](file:///d:/SkillGap_v2/app/services/roles.py) |
| **Topological Prerequisite Sort** | Directed Acyclic Graph (DAG) using NetworkX to sequence missing skills in order of foundational dependencies. | [`app/services/roadmap.py`](file:///d:/SkillGap_v2/app/services/roadmap.py) |
| **Greedy Marginal-Gain What-If** | Score gain per estimated learning hour ($\Delta \text{Score} / \text{Hours}$) determining optimal next learning investments. | [`app/services/whatif.py`](file:///d:/SkillGap_v2/app/services/whatif.py) |

---

## 5. Live Benchmark Evaluation

The application includes an automated ground-truth evaluation suite on 10 hand-labelled test cases with boundary traps:
- **Precision:** $\approx 96.0\%$
- **Recall:** $\approx 92.3\%$
- **F1-Score:** $\approx 94.1\%$

These metrics are computed on the fly and visible on the **[About & Methodology](file:///d:/SkillGap_v2/app/templates/about.html)** page (`/about`).

---

## 6. Faculty Presentation & 5-Minute Demo Script

Follow this sequence for an engaging, smooth faculty walkthrough:

### Minute 0:00 – 1:00: The Problem & The Solution (Landing Page)
1. Open `http://localhost:8000/`.
2. Point out the original SVG ascending-bars logo: the middle bar is hollow to symbolize the "skill gap".
3. **What to say:**  
   *"Faculty members, job applicants frequently struggle to understand why applicant tracking systems reject their resumes. Black-box LLMs hallucinate recommendations. SkillGap solves this with explainable NLP, deterministic scoring, and graph-based roadmapping."*
4. Click **"Try the demo"** to show instant authentication into `demo@skillgap.app`.

### Minute 1:00 – 2:00: Dashboard & Historical Analytics
1. Highlight the **Score Trend** line chart over Alex Demo's three prior analyses (Data Scientist, ML Engineer, Data Engineer).
2. Point out the recent analyses table showing date, score percentage, and letter grades (A through F).
3. Click into the latest analysis to open the **Results Page**.

### Minute 2:00 – 3:30: Explainable Results & Tabs Walkthrough
1. **Overview Tab:** Show the animated circular score ring (63%, Grade C) and the component breakdown bar chart:
   - 60% exact skill match
   - 20% partial credit
   - 10% category coverage
   - 10% resume quality
   - Explain that every point is mathematically accounted for.
2. **Skills Tab:** 
   - Demonstrate category chips. Click the category filters ("Programming", "Database", "Machine Learning").
   - Hover over a chip to show the exact evidence sentence extracted from the PDF resume.
   - Point out partial matches (e.g. Machine Learning receiving 72% credit via Scikit-learn).
3. **Learning Roadmap Tab:** 
   - Show how NetworkX topological sorting places foundational prerequisites before advanced ones.
   - Point to suggested real projects and estimated learning hours.
4. **What-If Simulator Tab:**
   - Tick the checkboxes next to missing skills (e.g., Deep Learning, TensorFlow).
   - Watch the projected score update live from 63% to 81% without reloading the page, along with the "Best next skill" recommendation.
5. **Careers Tab:**
   - Show the ranking of adjacent job roles and the radar chart illustrating category coverage.

### Minute 3:30 – 4:15: Market Explorer & Career Assistant
1. Navigate to **Job Market**:
   - Show the **Skill Demand** bar chart, **Co-occurrence Heatmap**, and **PCA + K-Means Role Clustering**.
   - Point out the red diamond marker indicating the candidate's coordinates in the PCA space.
2. Navigate to **Career Assistant**:
   - Click a suggested question pill: *"What should I learn first?"*
   - Show the instant, rule-based response referencing the candidate's exact gaps without latency or external API costs.

### Minute 4:15 – 5:00: Report Generation, Methodology & Wrap-up
1. Click **"Download report"** to download the clean, branded PDF report generated via ReportLab. Open the PDF to show the clean layout.
2. Navigate to **About & Methodology** (`/about`):
   - Highlight the live Model Evaluation table demonstrating precision/recall metrics.
3. Toggle dark mode using the sun/moon button to prove theme consistency.
4. Conclude and invite questions.

---

## 7. Honest System Limitations

When presenting to faculty, candidly acknowledge these real-world engineering boundaries:
1. **Not a Hiring Prediction Engine:** The score measures linguistic and semantic skill alignment between two documents; it does not assess emotional intelligence, code quality, or soft skills.
2. **Scanned Image PDFs:** PDFs consisting entirely of flattened bitmap scans without OCR text layers cannot be parsed and will yield zero extracted skills.
3. **Vocabulary Bounding:** While the system recognizes 84+ technical skills and aliases, ultra-niche or proprietary in-house tools not present in `skills.csv` require manual alias expansion.
4. **Small Ground-Truth Test Suite:** Benchmark accuracy is computed over 10 curated test cases; real-world resumes with unconventional formatting or multi-column layouts may produce minor extraction variance.

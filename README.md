# Kodex — NBU OpenData Bank Dashboard (Python) v2

Fixes Streamlit Cloud import issues + adds:
- auto-search for `apikod` by keywords,
- auto-detect "bank dimension" (heuristic),
- formula KPIs: ROA, ROE, Equity ratio, YoY growth, CAGR,
- separate "Structure" module (assets/liabilities pie/treemap).

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Deploy to Streamlit Cloud
Push repo and set main file: `app/streamlit_app.py`.
No extra packaging steps needed (we add `src/` to sys.path in the app).

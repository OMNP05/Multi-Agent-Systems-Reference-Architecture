# GCP Enterprise BOM Agent

Python backend (FastAPI + LangGraph + LangChain) and one HTML/JS page. GCP only.

## Run
```
cd backend
pip install -r requirements.txt
$env:GCP_PRICING_API_KEY="your_key"      # PowerShell
python -m uvicorn app:app --port 8000
```
Open http://127.0.0.1:8000.

## Live GCP prices (free)
1. Google Cloud Console -> create or pick a project (a billing account is not needed for the Catalog API).
2. APIs & Services -> Library -> enable **Cloud Billing API**.
3. APIs & Services -> Credentials -> Create credentials -> **API key**. Restrict it to the Cloud Billing API.
4. Set it as `GCP_PRICING_API_KEY` before starting the server.

Prices are fetched on every request (the catalog is cached in memory for 1 hour). Without the key the table falls back to approximate prices and the Price column says "static".

## Files
- `backend/catalog.py` - the GCP services the LLM may choose from, and how each is priced
- `backend/prompts.py` - the strict prompt and knowledge-base loader
- `backend/graph.py` - the LangGraph agent (`python graph.py` prints the graph)
- `backend/pricing.py` - Cloud Billing Catalog lookups
- `KnowledgeBase/*.md` - reference architecture read by the agent

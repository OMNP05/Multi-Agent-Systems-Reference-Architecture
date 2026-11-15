"""FastAPI app: serves the single page and the BOM API. Run: uvicorn app:app --port 8000"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from graph import run_agent
from schemas import BomRequest

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
app = FastAPI(title="GCP Enterprise BOM Agent")


@app.get("/")
def index():
    return FileResponse(FRONTEND)


@app.post("/api/bom")
def bom(req: BomRequest):
    try:
        return run_agent(req)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        # Never echo request details (the API key) back; type + message only.
        raise HTTPException(502, f"{type(e).__name__}: {str(e)[:400]}")

"""FastAPI 웹 화면: 질문을 받아 에이전트를 돌리고, 답변과 도구 호출 과정을 보여준다."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import run_agent

load_dotenv()

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="stat-agent")
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


class AskRequest(BaseModel):
    question: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.post("/api/ask")
def ask(req: AskRequest) -> dict:
    return run_agent(req.question, verbose=False)

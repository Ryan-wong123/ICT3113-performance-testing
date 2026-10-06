"""Assignment 1 baseline API: synchronous classification, simple storage and request logs."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
import uuid

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .categories import CATEGORIES
from .config import Settings
from .ollama_client import OllamaClassifier, OllamaError
from .request_logging import RequestLogger
from .storage import StoredTicket, TicketStore


settings = Settings.from_environment()
store = TicketStore(settings.database_path)
classifier = OllamaClassifier(settings)
request_logger = RequestLogger(settings.request_log_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield


app = FastAPI(title="Ticket Triage Baseline", version="0.1.0", lifespan=lifespan)


class TicketSubmission(BaseModel):
    narrative: str = Field(min_length=1, max_length=50_000)
    ticket_row: int | None = Field(default=None, ge=8000, le=8999)


class TicketResponse(BaseModel):
    id: int
    ticket_row: int | None
    category: str
    model: str


class StoredTicketResponse(TicketResponse):
    narrative: str
    created_at: str


@app.middleware("http")
async def instrument_requests(request: Request, call_next):
    start_wall = datetime.now(timezone.utc)
    start_monotonic = time.perf_counter()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    request.state.ticket_row = None
    request.state.predicted_category = None
    request.state.error = None
    error = None
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            error = request.state.error or f"HTTP {response.status_code}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        end_wall = datetime.now(timezone.utc)
        request_logger.write(
            {
                "timestamp": end_wall.isoformat(),
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "model": classifier.model if request.url.path == "/tickets" else None,
                "ticket_row_if_available": request.state.ticket_row,
                "request_start": start_wall.isoformat(),
                "request_end": end_wall.isoformat(),
                "latency_ms": round((time.perf_counter() - start_monotonic) * 1000, 3),
                "http_status": getattr(locals().get("response", None), "status_code", 500),
                "predicted_category": request.state.predicted_category,
                "error": error,
            }
        )
    response.headers["X-Request-ID"] = request_id
    return response


def ticket_response(ticket: StoredTicket) -> TicketResponse:
    return TicketResponse(id=ticket.id, ticket_row=ticket.ticket_row, category=ticket.category, model=ticket.model)


@app.post("/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(submission: TicketSubmission, request: Request) -> TicketResponse:
    request.state.ticket_row = submission.ticket_row
    try:
        category = classifier.classify(submission.narrative)
    except OllamaError as exc:
        request.state.error = str(exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    request.state.predicted_category = category
    stored_ticket = store.insert(submission.ticket_row, submission.narrative, category, classifier.model)
    return ticket_response(stored_ticket)


@app.get("/search", response_model=list[StoredTicketResponse])
def search_tickets(q: str = Query(min_length=1), limit: int = Query(default=20, ge=1, le=100)) -> list[StoredTicketResponse]:
    return [StoredTicketResponse(**ticket.__dict__) for ticket in store.search(q, limit)]


@app.get("/stats")
def ticket_stats() -> dict[str, object]:
    return {"categories": store.category_counts()}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": classifier.model, "classification_mode": "synchronous_sequential"}

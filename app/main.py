from __future__ import annotations

import json
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.db import get_db, init_db
from app.models import ModelRecord
from app.services.export import export_records_csv, export_records_json
from app.services.update_pipeline import import_manual_seed, records_for_export, reclassify_all, run_update_pipeline

app = FastAPI(title="GraphRAG LLM Comparison Dashboard")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    q: str = "",
    role: str = "",
    hardware_fit: str = "",
    recommendation: str = "",
    sort: str = Query("score", pattern="^(score|last_seen)$"),
) -> HTMLResponse:
    query = db.query(ModelRecord)
    # Build the dashboard query from optional filters so blank form fields keep
    # showing the full model catalogue.
    if q:
        like = f"%{q}%"
        query = query.filter(or_(ModelRecord.model_name.ilike(like), ModelRecord.provider.ilike(like)))
    if role:
        query = query.filter(ModelRecord.graph_rag_roles.ilike(f"%{role}%"))
    if hardware_fit:
        query = query.filter(ModelRecord.hardware_fit == hardware_fit)
    if recommendation:
        query = query.filter(ModelRecord.recommendation == recommendation)
    if sort == "last_seen":
        query = query.order_by(desc(ModelRecord.last_seen_at))
    else:
        query = query.order_by(desc(ModelRecord.graph_rag_score), asc(ModelRecord.model_name))

    # Limit the first page to keep the dashboard responsive when provider
    # catalogs return hundreds or thousands of models.
    models = [view_model(model) for model in query.limit(500).all()]
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "models": models,
            "filters": {"q": q, "role": role, "hardware_fit": hardware_fit, "recommendation": recommendation, "sort": sort},
            "roles": [
                "entity_extraction",
                "relationship_extraction",
                "graph_cleaning",
                "graph_validation",
                "query_routing",
                "retrieval",
                "reranking",
                "final_answer_generation",
                "answer_verification",
                "coding_tooling",
                "multimodal_document_understanding",
            ],
            "hardware_fits": ["laptop", "desktop_gpu", "workstation_gpu", "server_gpu", "api_only", "unknown"],
            "recommendations": ["test_now", "monitor", "ignore_for_now"],
        },
    )


@app.get("/models/{model_id}", response_class=HTMLResponse)
def detail(request: Request, model_id: int, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    model = db.get(ModelRecord, model_id)
    if not model:
        return templates.TemplateResponse(request, "not_found.html", {"request": request}, status_code=404)
    return templates.TemplateResponse(request, "detail.html", {"request": request, "model": view_model(model)})


@app.post("/admin/update", response_class=HTMLResponse)
def update_now(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    result = run_update_pipeline(db)
    return templates.TemplateResponse(request, "admin_result.html", {"request": request, "title": "Update complete", "result": result})


@app.post("/admin/import-seed", response_class=HTMLResponse)
def import_seed(request: Request, db: Annotated[Session, Depends(get_db)], path: str = Form("data/manual_models.seed.json")) -> HTMLResponse:
    result = import_manual_seed(db, path)
    return templates.TemplateResponse(request, "admin_result.html", {"request": request, "title": "Manual seed import complete", "result": result})


@app.post("/admin/reclassify", response_class=HTMLResponse)
def reclassify(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    count = reclassify_all(db)
    return templates.TemplateResponse(request, "admin_result.html", {"request": request, "title": "Reclassified models", "result": {"upserted": count, "errors": []}})


@app.get("/export.csv")
def export_csv(db: Annotated[Session, Depends(get_db)]) -> Response:
    return Response(export_records_csv(records_for_export(db)), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=llm_models.csv"})


@app.get("/export.json")
def export_json(db: Annotated[Session, Depends(get_db)]) -> Response:
    return Response(export_records_json(records_for_export(db)), media_type="application/json")


def view_model(model: ModelRecord) -> dict:
    # Templates work with Python lists/dicts, while the database stores several
    # flexible fields as JSON strings for SQLite compatibility.
    return {
        "id": model.id,
        "model_name": model.model_name,
        "provider": model.provider,
        "source": model.source,
        "source_url": model.source_url,
        "release_date": model.release_date,
        "last_seen_at": model.last_seen_at,
        "model_family": model.model_family,
        "model_type": model.model_type,
        "parameter_size": model.parameter_size,
        "context_window": model.context_window,
        "modalities": _loads(model.modalities, []),
        "license": model.license,
        "api_available": model.api_available,
        "local_available": model.local_available,
        "hardware_fit": model.hardware_fit,
        "estimated_cost_input": model.estimated_cost_input,
        "estimated_cost_output": model.estimated_cost_output,
        "speed_notes": model.speed_notes,
        "strengths": _loads(model.strengths, []),
        "weaknesses": _loads(model.weaknesses, []),
        "graph_rag_roles": _loads(model.graph_rag_roles, []),
        "graph_rag_score": model.graph_rag_score,
        "hardware_score": model.hardware_score,
        "cost_score": model.cost_score,
        "recommendation": model.recommendation,
        "notes": model.notes,
        "classification_notes": _loads(model.classification_notes, []),
        "raw_metadata_json": json.dumps(_loads(model.raw_metadata_json, {}), indent=2, ensure_ascii=False),
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _loads(value, default):
    # Bad or older JSON should not break page rendering; fall back to the shape
    # expected by the template instead.
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default

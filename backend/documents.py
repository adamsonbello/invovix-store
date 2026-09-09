"""Module 24 — Gestion documentaire.
Stockage objet Emergent (persistant). Fichiers privés servis via endpoint protégé."""
import uuid
import logging
from io import BytesIO
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from database import db
from security import require_area
import storage as objstore

logger = logging.getLogger("invovix")
documents_router = APIRouter(prefix="/api")

CATEGORIES = {"contract", "invoice", "supplier", "legal", "shipping", "other"}
MAX_BYTES = 25 * 1024 * 1024  # 25 Mo


def _now():
    return datetime.now(timezone.utc).isoformat()


@documents_router.get("/admin/documents")
async def list_documents(
    admin: dict = Depends(require_area("operations")),
    category: str = "", q: str = "",
):
    query = {}
    if category:
        query["category"] = category
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"filename": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]
    items = await db.documents.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    by_cat = {}
    for d in items:
        by_cat[d.get("category", "other")] = by_cat.get(d.get("category", "other"), 0) + 1
    total_size = sum(d.get("size", 0) for d in items)
    return {"items": items, "count": len(items), "by_category": by_cat, "total_size": total_size}


@documents_router.post("/admin/documents")
async def upload_document(
    file: UploadFile = File(...),
    name: str = Form(""),
    category: str = Form("other"),
    tags: str = Form(""),
    notes: str = Form(""),
    linked_order: str = Form(""),
    linked_supplier: str = Form(""),
    admin: dict = Depends(require_area("operations")),
):
    if category not in CATEGORIES:
        category = "other"
    if not objstore.storage_configured():
        raise HTTPException(503, "Stockage objet non configuré (EMERGENT_LLM_KEY manquant)")
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Fichier trop volumineux (max 25 Mo)")
    did = str(uuid.uuid4())
    orig = file.filename or "document"
    ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else "bin"
    content_type = file.content_type or objstore.guess_content_type(orig)
    path = f"{objstore.APP_NAME}/documents/{did}.{ext}"
    try:
        result = objstore.put_object(path, content, content_type)
    except Exception as e:
        raise HTTPException(502, f"Échec du téléversement: {e}")
    doc = {
        "id": did,
        "name": name.strip() or orig,
        "filename": orig,
        "storage_path": result["path"],
        "content_type": content_type,
        "category": category,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "notes": notes.strip(),
        "linked_order": linked_order.strip(),
        "linked_supplier": linked_supplier.strip(),
        "size": result.get("size", len(content)),
        "uploaded_by": admin.get("name", ""),
        "created_at": _now(),
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return doc


@documents_router.get("/admin/documents/{doc_id}/download")
async def download_document(doc_id: str, admin: dict = Depends(require_area("operations"))):
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Document introuvable")
    try:
        data, content_type = objstore.get_object(doc["storage_path"])
    except Exception as e:
        raise HTTPException(404, f"Fichier introuvable dans le stockage: {e}")
    return StreamingResponse(
        BytesIO(data),
        media_type=doc.get("content_type", content_type),
        headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
    )


@documents_router.delete("/admin/documents/{doc_id}")
async def delete_document(doc_id: str, admin: dict = Depends(require_area("operations"))):
    await db.documents.delete_one({"id": doc_id})
    return {"ok": True}

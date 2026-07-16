"""FastAPI backend: exposes extraction and PO creation as a JSON API,
and serves the built React frontend from frontend/dist.

Run with:  uvicorn backend:app --port 8004
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from api_registry import OPERATIONS, PayloadError, build_po_payload
from extractor import extract_po_fields
from sap_client import SAPClient, SAPError

app = FastAPI(title="MatAI SAP PO Assistant")


class ExtractRequest(BaseModel):
    prompt: str


class CreatePORequest(BaseModel):
    payload: dict


@app.post("/api/extract")
def extract(req: ExtractRequest):
    missing_cfg = config.validate()
    if missing_cfg:
        raise HTTPException(500, f"Missing configuration in .env: {', '.join(missing_cfg)}")
    try:
        fields = extract_po_fields(req.prompt)
    except Exception as e:
        raise HTTPException(502, f"Extraction failed: {e}")

    mandatory = OPERATIONS["create_purchase_order"]["mandatory_fields"]
    missing = fields.missing_fields(mandatory)
    result = {"fields": fields.model_dump(), "missing": missing, "payload": None}
    if not missing:
        try:
            result["payload"] = build_po_payload(fields)
        except PayloadError as e:
            raise HTTPException(400, str(e))
    return result


@app.post("/api/create-po")
def create_po(req: CreatePORequest):
    try:
        result = SAPClient().create_purchase_order(req.payload)
    except SAPError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(502, f"SAP call failed: {e}")
    
    po_number = result.get("PoNumber", "")
    client = config.SAP_CLIENT or "900"
    preview_url = f"{config.SAP_BASE_URL}/sap/bc/gui/sap/its/webgui?sap-client={client}&~transaction=*OLR3_ME2XN%20OLR3_R3_TS_PDOC-EBELN={po_number};DYNP_OKCODE=DISP#"

    return {
        "po_number": po_number,
        "message": result.get("Message", ""),
        "preview_url": preview_url,
    }


# Serve the built React app (frontend/dist) at /
_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")

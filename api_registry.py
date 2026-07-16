"""Static API registry.

Instead of a vector database, each supported operation is described here as
plain configuration: which OData service to call, which fields are mandatory,
and how to build the payload. Deterministic and easy to extend — add a new
entry to OPERATIONS and a builder function when you cover a new API.
"""
from models import PurchaseOrderFields

# ---------------------------------------------------------------------------
# Operation registry
# ---------------------------------------------------------------------------
OPERATIONS = {
    "create_purchase_order": {
        "service": "/sap/opu/odata/sap/ZPO_CREATE_SRV",
        "entity_set": "POHeaderSet",
        "description": "Create a purchase order via the custom ZPO_CREATE_SRV service",
        "mandatory_fields": [
            "vendor_id",
            "material",
            "plant",
            "quantity",
        ],
    },
}

# Default document type when the user doesn't name one
DEFAULT_DOC_TYPE = "ZSE1"
# Default 'Our reference' when the user doesn't mention one
DEFAULT_OUR_REF = "MATAI-APP"

# ---------------------------------------------------------------------------
# Plant master data
# ---------------------------------------------------------------------------
# Company code / purchasing org / purchasing group are derivable from the
# plant, so we enrich the payload here instead of hoping the LLM knows them.
# Maintain one entry per plant you order for.
PLANT_CONFIG = {
    "1000": {
        "comp_code": "1000",
        "purch_org": "1000",
        "pur_group": "ADM",
    },
}


class PayloadError(Exception):
    """The extracted values can't form a valid SAP payload."""


class UnknownPlantError(PayloadError):
    pass


# Max lengths from the ZPO_CREATE_SRV $metadata (Edm.String MaxLength facets)
FIELD_LIMITS = {
    "DocType": 4,
    "Vendor": 10,
    "Material": 40,
    "Plant": 4,
}
OUR_REF_MAX = 12  # free text — safe to truncate


def _check_length(name: str, value: str):
    limit = FIELD_LIMITS[name]
    if len(value) > limit:
        raise PayloadError(
            f"{name} '{value}' is {len(value)} characters, but SAP allows at "
            f"most {limit}. Please check the value."
        )


def _num(value: float) -> str:
    """Format a number for OData Edm.Decimal: no trailing .0 on whole numbers."""
    return f"{value:g}"


def build_po_payload(po: PurchaseOrderFields) -> dict:
    """Build the flat POHeaderSet payload for ZPO_CREATE_SRV.

    Pure Python — no LLM involved. The payload structure for a known
    endpoint is static; only the values vary.
    """
    plant_cfg = PLANT_CONFIG.get(po.plant)
    if plant_cfg is None:
        raise UnknownPlantError(
            f"Plant '{po.plant}' is not maintained in PLANT_CONFIG "
            f"(known plants: {', '.join(PLANT_CONFIG)}). "
            "Add its company code and purchasing org to api_registry.py."
        )

    doc_type = po.doc_type or DEFAULT_DOC_TYPE
    for name, value in (
        ("DocType", doc_type),
        ("Vendor", po.vendor_id),
        ("Material", po.material),
        ("Plant", po.plant),
    ):
        _check_length(name, value)

    return {
        "PoNumber": "",
        "DocType": doc_type,
        "Vendor": po.vendor_id,
        "PurchOrg": plant_cfg["purch_org"],
        "PurGroup": plant_cfg["pur_group"],
        "CompCode": plant_cfg["comp_code"],
        "OurRef": (po.our_ref or DEFAULT_OUR_REF)[:OUR_REF_MAX],
        "Material": po.material,
        "Plant": po.plant,
        "Quantity": _num(po.quantity),
    }

"""Pydantic models shared by the extractor and the payload builder."""
from typing import Optional

from pydantic import BaseModel, Field


class PurchaseOrderFields(BaseModel):
    """Fields Groq extracts from the user's natural-language request.

    Every field is optional at extraction time — validation of what is
    actually mandatory happens afterwards, so we can tell the user exactly
    which values are missing instead of failing the SAP call.
    """

    vendor_id: Optional[str] = Field(
        None, description="Supplier/vendor number, e.g. L200000263"
    )
    material: Optional[str] = Field(
        None, description="Material number, e.g. MECHSP3871"
    )
    plant: Optional[str] = Field(None, description="Plant code, e.g. 1000")
    quantity: Optional[float] = Field(None, description="Order quantity, e.g. 100")
    doc_type: Optional[str] = Field(
        None,
        description="Purchase order document type, e.g. ZSE1. "
        "Only set if the user names one explicitly.",
    )
    our_ref: Optional[str] = Field(
        None,
        description="'Our reference' free text, if the user mentions a "
        "reference, e.g. TEST-REF",
    )

    def missing_fields(self, mandatory: list[str]) -> list[str]:
        return [name for name in mandatory if getattr(self, name) in (None, "")]

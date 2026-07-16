"""Natural language → structured PO fields, using the Groq LLM API.

The LLM's only job is extraction. Groq's JSON mode forces a JSON object
response, which we then validate against the Pydantic schema — payload
assembly is done in plain Python (api_registry.build_po_payload), so a
hallucinated field name can never reach SAP.
"""
import json
from functools import lru_cache

from groq import Groq

import config
from models import PurchaseOrderFields


@lru_cache(maxsize=1)
def _client() -> Groq:
    # Created lazily so the app can show a friendly config error when
    # GROQ_API_KEY is missing, instead of crashing at import time.
    return Groq(api_key=config.GROQ_API_KEY)


_SYSTEM = """\
You extract purchase order fields from a user's natural-language request
for an SAP procurement chatbot.

Respond ONLY with a JSON object matching this schema (all fields nullable):
{schema}

Rules:
- Extract only values the user actually stated. Never invent or guess a
  value; use null for any field the user did not provide.
- vendor_id and material are alphanumeric codes (e.g. L200000263,
  MECHSP3871) — copy them exactly as strings, character for character.
- quantity is a number.
- doc_type is an SAP document type code (e.g. ZSE1) — only set it if the
  user names one explicitly; "standard purchase order" alone does NOT set it.
- our_ref is free reference text, only if the user mentions a reference.
"""


def extract_po_fields(user_prompt: str) -> PurchaseOrderFields:
    schema = json.dumps(PurchaseOrderFields.model_json_schema(), indent=2)
    response = _client().chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0,
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM.format(schema=schema)},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content
    return PurchaseOrderFields.model_validate_json(raw)

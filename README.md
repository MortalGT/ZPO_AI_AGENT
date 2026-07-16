# SAP Purchase Order Assistant

A chat app that turns natural-language requests like

> *Create a standard purchase order for vendor 1400000032 for material 7100000082 with quantity 1 EA in plant JE06, tax code Y6 and net price 10000 INR*

into real purchase orders in SAP S/4HANA via the `API_PURCHASEORDER_PROCESS_SRV` OData service.

## Architecture

```
User prompt (Streamlit chat)
   │
   ▼
Groq LLM (JSON-mode extraction → Pydantic model)      extractor.py / models.py
   │
   ▼
Validation: which mandatory fields are missing?       models.py
   │
   ▼
Static API registry + plant master data               api_registry.py
   (endpoint, mandatory fields, payload template,
    plant → company code / purch org enrichment)
   │
   ▼
User confirms the payload in the UI                   app.py
   │
   ▼
SAP OData client (basic auth + CSRF token,            sap_client.py
   POST A_PurchaseOrder, innererror parsing)
```

Design choices (deliberately different from a pure-LLM pipeline):

- **The LLM only extracts fields.** The final JSON payload is assembled by plain Python from a template, so a hallucinated field name can never reach SAP.
- **Static registry instead of a vector DB.** For a handful of known APIs, a config dict is deterministic and has no retrieval failure mode. Add new operations in `api_registry.py`.
- **Plant enrichment.** Company code / purchasing org / purchasing group are derived from the plant via `PLANT_CONFIG` — the user doesn't have to say them and the LLM can't get them wrong.
- **Confirmation step.** The extracted payload is shown and must be confirmed before anything is posted to SAP.
- **Real error messages.** OData `innererror.errordetails` are parsed and shown, instead of the useless generic `Exception raised without specific error`.

## Setup

```powershell
cd C:\FioriApps\MatAiApp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# edit .env: GROQ_API_KEY, SAP_BASE_URL, SAP_USER, SAP_PASSWORD
```

Then maintain your plants in `api_registry.py` → `PLANT_CONFIG` (company code, purchasing organization, purchasing group per plant — check the values for JE06 against your system).

## Run

```powershell
streamlit run app.py
```

Opens at http://localhost:8501.

## SAP prerequisites

- The OData service `API_PURCHASEORDER_PROCESS_SRV` must be activated (transaction `/IWFND/MAINT_SERVICE`).
- The SAP user needs authorization to create purchase orders (`ME21N`-equivalent auth objects) and to call the service.
- If your test system uses a self-signed certificate, set `SAP_VERIFY_SSL=false` in `.env`.

## Extending

- **New API (e.g. purchase requisition, goods receipt):** add an entry to `OPERATIONS`, a Pydantic model in `models.py`, a builder function in `api_registry.py`, and a method on `SAPClient`.
- **Intent routing:** once there are multiple operations, add a small classification step (Claude with an enum output) before extraction to pick the operation.

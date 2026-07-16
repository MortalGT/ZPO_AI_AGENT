"""Streamlit chat UI: natural language → Claude extraction → confirm → SAP PO.

Run with:  streamlit run app.py
"""
import streamlit as st

import config
from api_registry import OPERATIONS, PayloadError, build_po_payload
from extractor import extract_po_fields
from sap_client import SAPClient, SAPError

st.set_page_config(page_title="SAP PO Assistant", page_icon="🛒")
st.title("🛒 SAP Purchase Order Assistant")

# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------
missing_cfg = config.validate()
if missing_cfg:
    st.error(
        "Missing configuration in your `.env` file: **"
        + ", ".join(missing_cfg)
        + "**. Copy `.env.example` to `.env` and fill in the values."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # list of {"role", "content", optional "payload"}
if "pending_payload" not in st.session_state:
    st.session_state.pending_payload = None


def add(role: str, content: str, payload: dict | None = None):
    st.session_state.history.append(
        {"role": role, "content": content, "payload": payload}
    )


# ---------------------------------------------------------------------------
# Render history
# ---------------------------------------------------------------------------
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("payload"):
            st.json(msg["payload"])

# ---------------------------------------------------------------------------
# Confirmation step for a pending payload
# ---------------------------------------------------------------------------
if st.session_state.pending_payload is not None:
    st.info("Review the payload above, then confirm to create the PO in SAP.")
    col1, col2 = st.columns(2)
    if col1.button("✅ Create PO in SAP", type="primary", use_container_width=True):
        payload = st.session_state.pending_payload
        st.session_state.pending_payload = None
        try:
            with st.spinner("Calling SAP..."):
                result = SAPClient().create_purchase_order(payload)
            po_number = result.get("PoNumber") or "(unknown)"
            sap_msg = result.get("Message", "")
            client = config.SAP_CLIENT or "900"
            preview_url = f"{config.SAP_BASE_URL}/sap/bc/gui/sap/its/webgui?sap-client={client}&~transaction=*OLR3_ME2XN%20OLR3_R3_TS_PDOC-EBELN={po_number};DYNP_OKCODE=DISP#"
            add(
                "assistant",
                f"✅ **SUCCESS:** Purchase Order **{po_number}** created in SAP "
                f"for plant {payload['Plant']} (CC: {payload['CompCode']})."
                f"\n\n🔗 **[Preview PO in SAP WebGUI]({preview_url})**"
                + (f"\n\n> SAP: _{sap_msg}_" if sap_msg else ""),
            )
        except SAPError as e:
            add("assistant", f"❌ **FAILED at PO creation.** SAP said:\n```\n{e}\n```")
        except Exception as e:  # network errors etc.
            add("assistant", f"❌ **FAILED:** {e}")
        st.rerun()
    if col2.button("❌ Cancel", use_container_width=True):
        st.session_state.pending_payload = None
        add("assistant", "Cancelled — no PO was created.")
        st.rerun()

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
prompt = st.chat_input(
    "e.g. Create a purchase order for vendor L200000263 for material "
    "MECHSP3871 with quantity 100 in plant 1000"
)

if prompt:
    add("user", prompt)
    try:
        with st.spinner("Extracting fields with Claude..."):
            fields = extract_po_fields(prompt)

        mandatory = OPERATIONS["create_purchase_order"]["mandatory_fields"]
        missing = fields.missing_fields(mandatory)
        if missing:
            add(
                "assistant",
                "I couldn't find these mandatory values in your request: **"
                + ", ".join(missing)
                + "**. Please repeat the request including them.",
            )
        else:
            payload = build_po_payload(fields)
            st.session_state.pending_payload = payload
            add(
                "assistant",
                "✅ **Payload extracted successfully.** Please review and confirm:",
                payload=payload,
            )
    except PayloadError as e:
        add("assistant", f"⚠️ {e}")
    except Exception as e:
        add("assistant", f"❌ Extraction failed: {e}")
    st.rerun()

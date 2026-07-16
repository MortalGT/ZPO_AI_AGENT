"""SAP OData client: authentication, CSRF token handling, PO creation,
and proper parsing of OData error responses (including innererror)."""
import json

import requests

import config
from api_registry import OPERATIONS


class SAPError(Exception):
    """Raised when SAP rejects a request. str(e) is a human-readable summary."""


class SAPClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.auth = (config.SAP_USER, config.SAP_PASSWORD)
        self.session.verify = config.SAP_VERIFY_SSL
        self.session.headers.update({"Accept": "application/json"})
        if config.SAP_CLIENT:
            self.session.params = {"sap-client": config.SAP_CLIENT}

    def _fetch_csrf_token(self, service_path: str) -> str:
        """GET the service root with x-csrf-token: Fetch to obtain a token.

        The session keeps the cookies SAP sets here — both the cookies and
        the token must go back on the POST.
        """
        url = f"{config.SAP_BASE_URL}{service_path}/"
        resp = self.session.get(url, headers={"x-csrf-token": "Fetch"}, timeout=60)
        if resp.status_code == 401:
            raise SAPError("Authentication failed (401) — check SAP_USER / SAP_PASSWORD.")
        resp.raise_for_status()
        token = resp.headers.get("x-csrf-token")
        if not token:
            raise SAPError("SAP did not return a CSRF token — check the service path and user authorizations.")
        return token

    def create_purchase_order(self, payload: dict) -> dict:
        """POST the payload to A_PurchaseOrder. Returns the created entity data."""
        op = OPERATIONS["create_purchase_order"]
        token = self._fetch_csrf_token(op["service"])
        url = f"{config.SAP_BASE_URL}{op['service']}/{op['entity_set']}"

        resp = self.session.post(
            url,
            json=payload,
            headers={"x-csrf-token": token, "Content-Type": "application/json"},
            timeout=120,
        )
        if resp.status_code not in (200, 201):
            raise SAPError(parse_odata_error(resp))
        return resp.json().get("d", {})


def parse_odata_error(resp: requests.Response) -> str:
    """Turn an OData error response into a readable message.

    The generic message ("Exception raised without specific error") is
    usually useless — the real cause lives in innererror.errordetails,
    so surface those lines too.
    """
    try:
        err = resp.json().get("error", {})
    except (ValueError, json.JSONDecodeError):
        return f"SAP returned HTTP {resp.status_code}: {resp.text[:500]}"

    lines = []
    main_msg = err.get("message", {})
    if isinstance(main_msg, dict):
        main_msg = main_msg.get("value", "")
    if main_msg:
        lines.append(f"{err.get('code', 'SAP error')}: {main_msg}")

    details = err.get("innererror", {}).get("errordetails", [])
    for d in details:
        msg = d.get("message", "")
        # Skip duplicates of the generic top-level message
        if msg and msg not in lines[0:1] and "Exception raised without" not in msg:
            severity = d.get("severity", "error")
            lines.append(f"  - [{severity}] {msg}")

    if len(lines) <= 1 and not details:
        lines.append(f"  (HTTP {resp.status_code}, no further details from SAP)")

    return "\n".join(lines) if lines else f"SAP returned HTTP {resp.status_code}"

import { useEffect, useRef, useState } from "react";

const FIELD_LABELS = {
  PoNumber: "PO Number",
  DocType: "Document Type",
  Vendor: "Vendor",
  PurchOrg: "Purchasing Org",
  PurGroup: "Purchasing Group",
  CompCode: "Company Code",
  OurRef: "Our Reference",
  Material: "Material",
  Plant: "Plant",
  Quantity: "Quantity",
};

const SUGGESTIONS = [
  "Create a purchase order for vendor L200000263 for material MECHSP3871 with quantity 50 in plant 1000",
  "Order 25 units of MECHSP3871 from vendor L200000263 for plant 1000, reference PROJECT-ALPHA",
];

let nextId = 1;

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: "assistant",
      type: "text",
      text: "Hello! Describe the purchase order you need — vendor, material, quantity and plant — and I'll prepare it for SAP.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState("");
  const [pending, setPending] = useState(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy, pending]);

  const add = (msg) => setMessages((prev) => [...prev, { id: nextId++, ...msg }]);

  async function send(textOverride) {
    const text = (textOverride ?? input).trim();
    if (!text || busy || pending) return;
    setInput("");
    add({ role: "user", type: "text", text });
    setBusy(true);
    setBusyLabel("Extracting fields with Groq…");
    try {
      const r = await fetch("/api/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Extraction failed");
      if (data.missing.length > 0) {
        add({
          role: "assistant",
          type: "text",
          tone: "warn",
          text: `I couldn't find these mandatory values in your request: ${data.missing.join(
            ", "
          )}. Please repeat the request including them.`,
        });
      } else {
        add({ role: "assistant", type: "payload", payload: data.payload });
        setPending(data.payload);
      }
    } catch (e) {
      add({ role: "assistant", type: "text", tone: "error", text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  async function confirm(yes) {
    const payload = pending;
    setPending(null);
    if (!yes) {
      add({ role: "assistant", type: "text", text: "Cancelled — no PO was created." });
      return;
    }
    setBusy(true);
    setBusyLabel("Creating purchase order in SAP…");
    try {
      const r = await fetch("/api/create-po", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "SAP call failed");
      add({
        role: "assistant",
        type: "success",
        po: data.po_number,
        sapMessage: data.message,
        previewUrl: data.preview_url,
        plant: payload.Plant,
        compCode: payload.CompCode,
      });
    } catch (e) {
      add({ role: "assistant", type: "text", tone: "error", text: String(e.message || e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <div className="brand-title">MatAI</div>
            <div className="brand-sub">SAP Purchase Order Assistant</div>
          </div>
        </div>
        <div className="status-chip">
          <span className="status-dot" />
          SAP · ZPO_CREATE_SRV
        </div>
      </header>

      <main className="chat">
        {messages.map((m) => (
          <Message key={m.id} msg={m} />
        ))}

        {pending && !busy && (
          <div className="confirm-row">
            <button className="btn btn-primary" onClick={() => confirm(true)}>
              Create PO in SAP
            </button>
            <button className="btn btn-ghost" onClick={() => confirm(false)}>
              Cancel
            </button>
          </div>
        )}

        {busy && (
          <div className="row assistant">
            <div className="avatar bot">AI</div>
            <div className="bubble thinking">
              <span className="dots">
                <i /><i /><i />
              </span>
              {busyLabel}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </main>

      {messages.length <= 1 && !busy && (
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <footer className="composer">
        <textarea
          ref={inputRef}
          rows={1}
          value={input}
          placeholder={
            pending
              ? "Confirm or cancel the payload above first…"
              : "Describe the purchase order… vendor, material, quantity, plant"
          }
          disabled={busy || !!pending}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button
          className="send"
          onClick={() => send()}
          disabled={busy || !!pending || !input.trim()}
          aria-label="Send"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 2 11 13" />
            <path d="M22 2 15 22l-4-9-9-4Z" />
          </svg>
        </button>
      </footer>
    </div>
  );
}

function Message({ msg }) {
  if (msg.role === "user") {
    return (
      <div className="row user">
        <div className="bubble user-bubble">{msg.text}</div>
        <div className="avatar you">You</div>
      </div>
    );
  }

  return (
    <div className="row assistant">
      <div className="avatar bot">AI</div>
      {msg.type === "text" && (
        <div className={`bubble ${msg.tone === "error" ? "error" : ""} ${msg.tone === "warn" ? "warn" : ""}`}>
          <FormattedText text={msg.text} />
        </div>
      )}
      {msg.type === "payload" && <PayloadCard payload={msg.payload} />}
      {msg.type === "success" && (
        <div className="success-card">
          <div className="success-head">
            <div className="success-icon">✓</div>
            <div>
              <div className="success-title">Purchase order created</div>
              <div className="success-sub">
                Plant {msg.plant} · Company code {msg.compCode}
              </div>
            </div>
          </div>
          <div className="po-number">{msg.po}</div>
          {msg.sapMessage && <div className="sap-msg">SAP: {msg.sapMessage}</div>}
          {msg.previewUrl && (
            <div className="success-actions" style={{ marginTop: "16px" }}>
              <a
                href={msg.previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  textDecoration: "none",
                  width: "100%",
                  padding: "10px 16px",
                  fontSize: "13.5px",
                }}
              >
                <svg
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                Preview PO in SAP WebGUI
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PayloadCard({ payload }) {
  return (
    <div className="payload-card">
      <div className="payload-head">
        <span>Purchase order payload</span>
        <span className="payload-tag">review &amp; confirm</span>
      </div>
      <div className="payload-grid">
        {Object.entries(payload)
          .filter(([k, v]) => !(k === "PoNumber" && v === ""))
          .map(([k, v]) => (
            <div className="payload-item" key={k}>
              <div className="payload-label">{FIELD_LABELS[k] || k}</div>
              <div className="payload-value">{String(v)}</div>
            </div>
          ))}
      </div>
    </div>
  );
}

function FormattedText({ text }) {
  // Multi-line SAP errors read better preformatted
  if (text.includes("\n")) return <pre className="pre">{text}</pre>;
  return <>{text}</>;
}

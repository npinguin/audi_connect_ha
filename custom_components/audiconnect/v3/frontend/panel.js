/* Audi Connect V3 — local administrator development panel (zero dependencies).
 * Uses authenticated Home Assistant WebSocket API. Never reads bearer tokens.
 * In a user-action test, HTTP success is not proof the physical car acted.
 */
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (x) => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]
));

class AudiConnectV3Panel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this.entries = [];
    this.selected = "";
    this.vin = "";
    this.aspect = "status";
    this.routes = [];
    this.pending = null;
    this.lastResult = null;
    this.error = "";
    this.loading = false;
    this._loaded = false;
    this.shadowRoot.addEventListener("click", (e) => this._click(e));
    this.shadowRoot.addEventListener("change", (e) => this._change(e));
  }

  set hass(value) {
    this._hass = value;
    if (!this._loaded) {
      this._loaded = true;
      void this._load();
    }
  }

  set panel(value) { this._panel = value; }
  set narrow(value) { this._narrow = value; }

  async api(type, data = {}) {
    return this._hass.callWS({type: "audiconnect/v3/" + type, ...data});
  }

  get selection() {
    return {entry_id: this.selected, vin: this.vin};
  }

  async _load() {
    this.loading = true; this.render();
    try {
      const response = await this.api("list");
      this.entries = response.integrations || [];
      if (!this.entries.some((e) => e.entry_id === this.selected)) {
        this.selected = this.entries[0]?.entry_id || "";
      }
      const group = this.entries.find((e) => e.entry_id === this.selected);
      if (!group?.vehicles.some((v) => v.vin === this.vin)) {
        this.vin = group?.vehicles[0]?.vin || "";
      }
      await this._routes();
      this.error = "";
    } catch (err) {
      this.error = String(err.message || err);
    } finally {
      this.loading = false; this.render();
    }
  }

  async _routes() {
    if (!this.selected || !this.vin) {
      this.routes = []; this.pending = null; return;
    }
    const data = await this.api("routes", {
      ...this.selection, aspect: this.aspect
    });
    this.routes = data.routes || [];
    this.disabled = data.disabled;
    const waiting = (data.history || []).filter((a) =>
      a.result === "uncertain_pending_review" ||
      a.result === "awaiting_user_feedback"
    );
    this.pending = waiting.at(-1) || null;
  }

  async _change(e) {
    if (e.target.id === "entry") {
      this.selected = e.target.value; this.vin = "";
      await this._load();
    } else if (e.target.id === "vehicle") {
      this.vin = e.target.value;
      this.error = ""; await this._reloadRoutes();
    } else if (e.target.id === "aspect") {
      this.aspect = e.target.value;
      this.error = ""; await this._reloadRoutes();
    }
  }

  async _reloadRoutes() {
    try {
      await this._routes();
      this.error = "";
    } catch (err) {
      this.error = String(err.message || err);
    }
    this.render();
  }

  async _click(e) {
    const button = e.target.closest("button[data-action]");
    if (!button || this.loading) return;
    const action = button.dataset.action;
    const route = this.shadowRoot.getElementById("route")?.value;
    // Capture edits BEFORE re-render: otherwise the textarea is reset and a
    // custom request silently loses its parameters or entire definition.
    const rawParameters = this.shadowRoot.getElementById("parameters")?.value || "{}";
    const rawDefinition = this.shadowRoot.getElementById("definition")?.value || "";
    this.loading = true; this.error = ""; this.render();
    try {
      if (action === "refresh") {
        await this._load(); return;
      }
      if (action === "test") {
        let parameters = {};
        parameters = JSON.parse(rawParameters);
        this.lastResult = await this.api("test", {
          ...this.selection, aspect: this.aspect,
          operation: route, parameters
        });
      } else if (action === "select") {
        this.lastResult = await this.api("select", {
          ...this.selection, aspect: this.aspect, operation: route
        });
      } else if (action === "disable") {
        this.lastResult = await this.api("disable", {
          ...this.selection, aspect: this.aspect
        });
      } else if (action === "add") {
        const candidate = JSON.parse(rawDefinition);
        this.lastResult = await this.api("add_route", {
          ...this.selection, route: candidate
        });
      } else if (action.startsWith("confirm-")) {
        if (!this.pending) throw new Error("No open action to review");
        const result = action.slice("confirm-".length);
        this.lastResult = await this.api("review", {
          ...this.selection, sequence: this.pending.sequence, result
        });
      }
      await this._routes();
      const list = await this.api("list");
      this.entries = list.integrations || [];
    } catch (err) {
      this.error = String(err.message || err);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  get initialRoute() {
    const id = "user.climate." + this.aspect + ".new_variant";
    return JSON.stringify({
      id, capability: "climate", aspect: this.aspect,
      family: "cariad",
      method: this.aspect === "status" ? "GET" : "POST",
      path: this.aspect === "status" ?
        "/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs=climatisation" :
        "/vehicle/v1/vehicles/{VIN}/climatisation/" + this.aspect,
      variables: {}, body: null,
      response_paths: this.aspect === "status" ?
        ["climatisation.climatisationStatus.value.climatisationState"] : [],
      description: "Experimental route"
    }, null, 2);
  }

  render() {
    const item = this.entries.find((entry) => entry.entry_id === this.selected);
    const car = item?.vehicles?.find((v) => v.vin === this.vin);
    const selectedRoute = this.routes.find((r) => r.selected)?.id || this.routes[0]?.id || "";
    const status = car?.climate_state ?? "unknown";
    const bg = "var(--primary-background-color, #f8fafc)";
    const body = "var(--primary-text-color, #111827)";
    this.shadowRoot.innerHTML = `
      <style>
        :host {display:block; min-height:100%; background:${bg}; color:${body};
          font-family:var(--paper-font-body1_-_font-family,Arial,sans-serif);}
        *{box-sizing:border-box}
        main{max-width:1240px;margin:auto;padding:28px 24px 48px}
        .eyebrow{letter-spacing:.12em;text-transform:uppercase;font-weight:700;
          font-size:11px;color:var(--secondary-text-color,#64748b)}
        h1{font-size:26px;margin:8px 0 4px;font-weight:750}
        h2{font-size:17px;margin:0 0 18px}
        p{line-height:1.5;color:var(--secondary-text-color,#64748b)}
        .top,.toolbar,.line{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
        .toolbar{justify-content:flex-start;padding:22px 0}
        .grid{display:grid;grid-template-columns:1fr 1.6fr;gap:18px}
        .card{border-radius:13px;background:var(--card-background-color,white);
          border:1px solid var(--divider-color,#e2e8f0);padding:22px;min-width:0}
        .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}
        .stat{font-size:20px;font-weight:700;margin-top:8px;overflow-wrap:anywhere}
        label{font-size:12px;color:var(--secondary-text-color,#64748b);display:block;font-weight:700;margin-bottom:6px}
        select,textarea,input{width:100%;font:inherit;padding:10px 12px;border:1px solid
          var(--divider-color,#d1d5db);border-radius:8px;background:var(--card-background-color,white);
          color:inherit}
        textarea{font-family:ui-monospace,monospace;font-size:12px;line-height:1.5;resize:vertical}
        .tool{min-width:180px;flex:1;max-width:360px}
        button{font:inherit;border:1px solid var(--divider-color,#cbd5e1);
          border-radius:8px;background:var(--card-background-color,white);
          color:inherit;padding:10px 15px;cursor:pointer;font-weight:650}
        button.primary{background:var(--primary-color,#2366a6);border-color:var(--primary-color,#2366a6);color:white}
        button:disabled{opacity:.42;cursor:not-allowed}
        .badge{display:inline-block;font-size:11px;border:1px solid var(--divider-color,#cbd5e1);
          border-radius:20px;padding:4px 9px;font-weight:700}
        .route{display:flex;justify-content:space-between;gap:12px;padding:11px 0;
          border-bottom:1px solid var(--divider-color,#e2e8f0);font-size:12px}
        code{overflow-wrap:anywhere;font-family:ui-monospace,monospace}
        .summary{font-size:12px;margin-top:12px}
        .error{padding:12px;border:1px solid #d97706;border-radius:9px;margin:14px 0}
        .warn{border-left:3px solid #d97706;padding:12px;background:var(--secondary-background-color,#f8fafc)}
        .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:15px}
        pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--secondary-background-color,#f8fafc);
          padding:14px;border-radius:9px;font-size:12px;max-height:340px;overflow:auto}
        .foot{font-size:12px;margin-top:25px}
        @media(max-width:780px){main{padding:18px 12px}.grid,.cards{grid-template-columns:1fr}h1{font-size:21px}}
      </style>
      <main>
        <div class="top">
          <div><div class="eyebrow">Audi Connect / V3 capability workbench</div>
            <h1>Vehicle API Development</h1>
            <p>One capability at a time. Discover, test, verify, activate.</p></div>
          <button data-action="refresh" ${this.loading?"disabled":""}>↻ Refresh</button>
        </div>
        <div class="toolbar">
          <div class="tool"><label>Integration</label>
            <select id="entry">${this.entries.map((v) => `<option value="${escapeHTML(v.entry_id)}" ${v.entry_id===this.selected?"selected":""}>Audi Connect / ${escapeHTML(v.entry_id.slice(0,8))}</option>`).join("")}</select></div>
          <div class="tool"><label>Vehicle</label><select id="vehicle">
            ${(item?.vehicles||[]).map((v)=>`<option value="${escapeHTML(v.vin)}" ${v.vin===this.vin?"selected":""}>${escapeHTML(v.name)} — ${escapeHTML(v.model)}</option>`).join("")}
          </select></div>
        </div>
        ${this.error?`<div class="error">${escapeHTML(this.error)}</div>`:""}
        ${!car?`<div class="card">No V3 vehicle loaded. Enable V3 and confirm Audi authentication before testing.</div>`: `
          <div class="cards">
            <div class="card"><div class="eyebrow">Cloud polling</div>
              <div class="stat">${item.poll_success?"Connected":"Not confirmed"}</div>
              <div class="summary">${escapeHTML(item.poll_success||"No successful cloud poll")}</div></div>
            <div class="card"><div class="eyebrow">Climate state</div>
              <div class="stat">${escapeHTML(status)}</div>
              <div class="summary">Vehicle age: ${escapeHTML(car.age_minutes??"unknown")} minutes</div></div>
            <div class="card"><div class="eyebrow">Climate control</div>
              <div class="stat">${car.start_enabled?"Start ready":"Start unverified"}</div>
              <div class="summary">${car.stop_enabled?"Stop ready":"Stop unverified"} · API quota: ${escapeHTML(item.quota??"unknown")}</div></div>
          </div>
          <div class="grid">
            <section class="card">
              <div class="eyebrow">01 / Capability</div>
              <h2>Climate</h2>
              <label>Optional aspect</label>
              <select id="aspect">
                ${["status","start","stop"].map((v)=>`<option value="${v}" ${this.aspect===v?"selected":""}>${v==="status"?"Status (GET)":v==="start"?"Control · Start":"Control · Stop"}</option>`).join("")}
              </select>
              <p>Select a known API path or add your own, scoped to this vehicle.</p>
              <div style="margin-top:20px"><label>API candidate</label>
                <select id="route">${this.routes.map((r)=>`<option value="${escapeHTML(r.id)}" ${r.id===selectedRoute?"selected":""}>${escapeHTML(r.id)} [${escapeHTML(r.outcome)}]</option>`).join("")}</select>
              </div>
              <div style="margin-top:16px">
                ${this.routes.map((r)=>`<div class="route">
                  <div><b>${escapeHTML(r.id)}</b><div><code>${escapeHTML(r.method)} ${escapeHTML(r.path)}</code></div></div>
                  <span class="badge">${r.selected?"ACTIVE":escapeHTML(r.outcome)}</span>
                </div>`).join("")||"<p>No applicable routes found.</p>"}
              </div>
              <label style="margin-top:22px">Request parameters (JSON)</label>
              <textarea id="parameters" rows="3">{}</textarea>
              <div class="actions">
                <button class="primary" data-action="test" ${!selectedRoute||this.loading||this.pending?"disabled":""}>
                  ${this.aspect==="status"?"Test GET":"Test selected action"}
                </button>
                <button data-action="select" ${!selectedRoute||this.loading?"disabled":""}>Activate verified path</button>
                ${this.aspect!=="status"?`<button data-action="disable" ${this.loading?"disabled":""}>Disable control</button>`:""}
              </div>
              ${this.pending ? `
                <div class="warn" style="margin-top:20px">
                  <b>Physical action not yet confirmed.</b>
                  <p>Inspect the car or myAudi. Do not test another API path until this result is known.</p>
                  <div class="actions">
                    <button data-action="confirm-worked">Worked</button>
                    <button data-action="confirm-failed">Failed</button>
                    <button data-action="confirm-uncertain">Not sure</button>
                  </div>
                </div>` : ""}
            </section>
            <section class="card">
              <div class="eyebrow">02 / Developer tools</div>
              <h2>Custom API path</h2>
              <p>Relative paths only. Auth and host remain owned by the Audi integration. {VIN} and typed parameters are supported.</p>
              <label>API definition (JSON)</label>
              <textarea id="definition" rows="13">${escapeHTML(this.initialRoute)}</textarea>
              <div class="actions"><button data-action="add" class="primary">Add experimental route</button></div>
              <div class="eyebrow" style="margin-top:28px">03 / Last experiment</div>
              <pre>${escapeHTML(JSON.stringify(this.lastResult??{"message":"No test yet"}, null, 2))}</pre>
            </section>
          </div>
          <p class="foot">Experimental mode. HTTP 200/202 confirms gateway acceptance, not vehicle action.
          Custom paths and results stay in private local HA storage. V2 remains available for rollback.</p>`}
      </main>`;
  }
}
customElements.define("audiconnect-v3-panel", AudiConnectV3Panel);

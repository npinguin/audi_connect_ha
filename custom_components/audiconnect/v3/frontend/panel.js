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
    this.step = 1;
    this.category = "charging";
    this.attribute = "";
    this.controlTarget = "climate";
    this.inventoryFilter = "available";
    this.readRoutes = [];
    this.readChoice = "";
    this.readDraft = "";
    this.readActive = "";
    this.routeChoice = "";
    this.routes = [];
    this.capabilityStatus = {counts: {}, rows: []};
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
      await this._loadCapabilityStatus();
      await this._readRoutes();
      this.error = "";
    } catch (err) {
      this.error = String(err.message || err);
    } finally {
      this.loading = false; this.render();
    }
  }

  async _loadCapabilityStatus() {
    if (!this.selected || !this.vin) {
      this.capabilityStatus = {counts: {}, rows: []};
      return;
    }
    this.capabilityStatus = await this.api("status", this.selection);
  }

  async _readRoutes() {
    if (!this.selected || !this.vin || !this.attribute) {
      this.readRoutes = []; this.readChoice = ""; this.readActive = ""; return;
    }
    const data = await this.api("attribute_routes", {...this.selection, attribute: this.attribute});
    this.readRoutes = data.routes || [];
    this.readDraft = data.draft || "";
    this.readActive = data.active || "";
    this.readChoice = this.readRoutes.some(r => r.id === this.readDraft) ? this.readDraft :
      this.readRoutes.some(r => r.id === this.readActive) ? this.readActive :
      this.readRoutes[0]?.id || "";
  }

  async _routes() {
    if (!this.selected || !this.vin) {
      this.routes = []; this.pending = null; return;
    }
    const data = await this.api("routes", {
      ...this.selection, aspect: this.aspect
    });
    this.routes = data.routes || [];
    this.routeChoice = (
      data.draft_candidate && this.routes.some((r) => r.id === data.draft_candidate)
        ? data.draft_candidate
        : this.routes.find((r) => r.selected)?.id || this.routes[0]?.id || ""
    );
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
      this.routeChoice = "";
      this.error = ""; await this._reloadRoutes();
    } else if (e.target.id === "aspect") {
      this.aspect = e.target.value;
      this.routeChoice = "";
      this.error = ""; await this._reloadRoutes();
    } else if (e.target.id === "route") {
      this.routeChoice = e.target.value;
      // Keep edited parameters and JSON definitions in place.
    } else if (e.target.id === "category") {
      this.category = e.target.value;
      this.attribute = "";
      this.readRoutes = [];
      this.render();
    } else if (e.target.id === "attribute") {
      this.attribute = e.target.value;
      this.step = 3;
      await this._readRoutes();
      this.render();
    } else if (e.target.id === "control-target") {
      this.controlTarget = e.target.value;
      this.attribute = "";
      this.step = 3;
      this.render();
    } else if (e.target.id === "read-route") {
      this.readChoice = e.target.value;
      this.render();
    } else if (e.target.id === "inventory-filter") {
      this.inventoryFilter = e.target.value;
      this.render();
    }
  }

  async _reloadRoutes() {
    try {
      await this._routes();
      await this._loadCapabilityStatus();
      await this._readRoutes();
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
    if (action.startsWith("step-")) {
      this.step = Number(action.slice(5)); this.render(); return;
    }
    if (action === "open-capability") {
      this.category = button.dataset.capability;
      this.attribute = "";
      this.step = 2; this.render(); return;
    }
    if (action === "select-attribute") {
      this.category = button.dataset.capability;
      this.attribute = button.dataset.attribute;
      this.step = 3;
      try { await this._readRoutes(); this.error = ""; }
      catch (err) { this.error = String(err.message || err); }
      this.render(); return;
    }
    const readRoute = this.shadowRoot.getElementById("read-route")?.value || this.readChoice;
    const rawReadDefinition = this.shadowRoot.getElementById("read-definition")?.value || "";
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
      } else if (action === "save") {
        this.lastResult = await this.api("save_candidate", {
          ...this.selection, aspect: this.aspect, operation: route
        });
      } else if (action === "select") {
        this.lastResult = await this.api("select", {
          ...this.selection, aspect: this.aspect, operation: route
        });
      } else if (action === "disable") {
        this.lastResult = await this.api("disable", {
          ...this.selection, aspect: this.aspect
        });
      } else if (action === "read-test") {
        this.lastResult = await this.api("attribute_test", {...this.selection,
          attribute: this.attribute, operation: readRoute});
      } else if (action === "read-save") {
        this.lastResult = await this.api("attribute_save", {...this.selection,
          attribute: this.attribute, operation: readRoute});
      } else if (action === "read-activate") {
        this.lastResult = await this.api("attribute_activate", {...this.selection,
          attribute: this.attribute, operation: readRoute});
      } else if (action === "read-disable") {
        this.lastResult = await this.api("attribute_disable", {...this.selection,
          attribute: this.attribute});
      } else if (action === "read-add") {
        this.lastResult = await this.api("attribute_add", {...this.selection,
          definition: JSON.parse(rawReadDefinition)});
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
      await this._loadCapabilityStatus();
      await this._readRoutes();
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

  get initialReadRoute() {
    const entry = (this.capabilityStatus.rows || []).find(
      row => row.attribute === this.attribute && row.entity_key);
    return JSON.stringify({id:"user.read.new_mapping", attribute:this.attribute,
      family:"cariad", method:"GET",
      path:"/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs=" + (entry?.job || "charging"),
      response_path:entry?.path && !entry.path.startsWith("/") && entry.path !== "-" ? entry.path :
        "charging.batteryStatus.value.currentSOC_pct"}, null, 2);
  }

  render() {
    const item = this.entries.find((entry) => entry.entry_id === this.selected);
    const car = item?.vehicles?.find((v) => v.vin === this.vin);
    const selectedRoute = this.routes.some((r) => r.id === this.routeChoice)
      ? this.routeChoice : this.routes.find((r) => r.selected)?.id || this.routes[0]?.id || "";
    const routeVerified = this.routes.some((r) =>
      r.id === selectedRoute && r.outcome === "worked"
    );
    const status = car?.climate_state ?? "unknown";
    const coverage = this.capabilityStatus || {counts: {}, rows: []};
    const counts = coverage.counts || {};
    const rows = coverage.rows || [];
    const attributes = rows.filter(r => r.entity_key &&
      ["v3_live_evidence","v2_attribute_reference"].includes(r.source));
    const controls = rows.filter(r => r.source === "v2_control_reference");
    const capabilityNames = [...new Set([...attributes,...controls].map(r => r.capability))].sort();
    const visibleAttributes = attributes.filter(r => r.capability === this.category &&
      (this.inventoryFilter !== "available" || ["verified","readable_but_stale"].includes(r.status)));
    const chosen = this.readRoutes.find(r => r.id === this.readChoice);
    const canActivateRead = chosen?.result === "verified" ||
      (chosen?.family === "mbb" && chosen?.result === "readable_but_stale");
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
        .steps{display:flex;gap:8px;margin:12px 0 22px;flex-wrap:wrap}
        .steps button{flex:1;min-width:145px;text-align:left}
        .steps button.current{border-color:var(--primary-color,#2366a6);box-shadow:inset 0 -3px var(--primary-color,#2366a6)}
        .cap-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}
        .cap-card{width:100%;padding:16px;text-align:left}
        .cap-card b{font-size:15px}
        .cap-card .subline{line-height:1.6;margin-top:8px}
        .eyeline{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
        .callout{background:var(--secondary-background-color,#f8fafc);padding:15px;border-radius:9px}
        .attribute-row{display:flex;justify-content:space-between;align-items:center;gap:16px;
          border-top:1px solid var(--divider-color,#e2e8f0);padding:11px 0}
        .attribute-row button{text-align:left;flex:1;overflow-wrap:anywhere}
        .helper{font-size:12px;margin:9px 0;color:var(--secondary-text-color,#64748b)}
        .coverage-table{max-height:400px;overflow:auto}
        table{width:100%;border-collapse:collapse;font-size:12px}
        th{text-align:left;font-weight:700;color:var(--secondary-text-color,#64748b);
          padding:11px 10px;position:sticky;top:0;background:var(--card-background-color,white);
          border-bottom:1px solid var(--divider-color,#d1d5db)}
        td{padding:11px 10px;vertical-align:top;border-bottom:1px solid var(--divider-color,#e2e8f0)}
        .subline{font-size:11px;opacity:.8;margin-top:4px}
        .coverage-note{font-size:12px;margin:10px 0 0}
        @media(max-width:780px){main{padding:18px 12px}.grid,.cards,.cap-grid{grid-template-columns:1fr}h1{font-size:21px}}
      </style>
      <main>
        <div class="top">
          <div><div class="eyebrow">Audi Connect / V3 capability workbench</div>
            <h1>Audi V3 — Experimental</h1>
            <p>Recover historical V2 capabilities across API families. Only verified data and manually confirmed controls become active.</p></div>
          <button data-action="refresh" ${this.loading?"disabled":""}>↻ Refresh</button>
        </div>
        <div class="toolbar">
          <div class="tool"><label>Integration</label>
            <select id="entry">${this.entries.map((v) => `<option value="${escapeHTML(v.entry_id)}" ${v.entry_id===this.selected?"selected":""}>Audi Connect / ${escapeHTML(v.entry_id.slice(0,8))}</option>`).join("")}</select></div>
          <div class="tool"><label>Vehicle</label><select id="vehicle">
            ${(item?.vehicles||[]).map((v)=>`<option value="${escapeHTML(v.vin)}" ${v.vin===this.vin?"selected":""}>${escapeHTML(v.name)} — ${escapeHTML(v.model)}</option>`).join("")}
          </select></div>
        </div>
        <div class="steps">
          <button data-action="step-1" class="${this.step===1?"current":""}">1 · Inventory & status</button>
          <button data-action="step-2" class="${this.step===2?"current":""}">2 · Select capability</button>
          <button data-action="step-3" class="${this.step===3?"current":""}">3 · Configure & test</button>
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
            <div class="card"><div class="eyebrow">Climate pilot / controls</div>
              <div class="stat">${car.start_enabled?"Start ready":"Start unverified"}</div>
              <div class="summary">${car.stop_enabled?"Stop ready":"Stop unverified"} · API quota: ${escapeHTML(item.quota??"unknown")}</div></div>
          </div>
          <section class="card" style="margin-bottom:18px;display:${this.step===1?"block":"none"}">
            <div class="eyebrow">Capability discovery / evidence</div>
            <h2>Historical coverage vs verified V3 data</h2>
            <p>Known from V2 does not mean discovered by V3.
              Read-only attributes and controls have independent evidence;
              stale vehicle readings are not current.</p>
            <div class="line" style="justify-content:flex-start;gap:16px;font-size:12px;margin-bottom:14px">
              <span><b>${escapeHTML(counts.v2_attribute_inventory??0)}</b> V2 attribute references</span>
              <span><b>${escapeHTML(counts.v2_unique_attributes??counts.v2_attribute_inventory??0)}</b> unique attributes</span>
              <span><b>${escapeHTML(counts.v2_alias_references??0)}</b> aliases (not duplicate functions)</span>
              <span><b>${escapeHTML(counts.v2_control_inventory??0)}</b> V2 controls</span>
              <span><b>${escapeHTML(counts.v3_verified_attributes??0)}</b> V3 verified attributes</span>
              <span><b>${escapeHTML(counts.verified_working??0)}</b> verified</span>
              <span><b>${escapeHTML(counts.not_tested??0)}</b> not tested</span>
              <span><b>${escapeHTML(counts.stale??0)}</b> stale</span>
              <span><b>${escapeHTML(counts.reported_failed??0)}</b> failed</span>
              <span><b>${escapeHTML(counts.v2_reference_only??0)}</b> known V2 / not migrated</span>
            </div>
            <div class="cap-grid">${capabilityNames.map(cap=>{
                const a=attributes.filter(r=>r.capability===cap);
                const ct=controls.filter(r=>r.capability===cap);
                const verified=a.filter(r=>r.status==="verified").length;
                const stale=a.filter(r=>r.status==="readable_but_stale").length;
                return `<button class="cap-card" data-action="open-capability" data-capability="${escapeHTML(cap)}">
                  <b>${escapeHTML(cap.replaceAll("_"," "))}</b>
                  <div class="subline">${verified} verified · ${stale} stale</div>
                  <div class="subline">${a.length} read-only attributes · ${ct.length} controls</div>
                </button>`;
              }).join("")}</div>
            <details>
              <summary style="cursor:pointer;font-weight:700;padding:8px 0">
                Technical evidence — ${escapeHTML(rows.length)} route and attribute records
              </summary>
              <div class="coverage-table"><table>
                <thead><tr><th>Capability</th><th>Attribute / Control</th>
                  <th>API family / Path</th><th>Discovery result</th></tr></thead>
                <tbody>${rows.map((r)=>`<tr>
                  <td><b>${escapeHTML(r.capability)}</b>
                    <div class="subline">${escapeHTML(r.aspect)}</div></td>
                  <td><code>${escapeHTML(r.attribute)}</code></td>
                  <td><b>${escapeHTML(r.api_family)}</b>
                    <div class="subline"><code>${escapeHTML(r.method)} ${escapeHTML(r.path)}</code></div></td>
                  <td><b>${escapeHTML(r.status)}</b>
                    <div class="subline">${escapeHTML(r.source)}
                    ${r.selected?" · ACTIVE":""}
                    ${r.saved_candidate?" · SAVED CANDIDATE":""}</div></td>
                </tr>`).join("")}</tbody>
              </table></div>
            </details>
            <p class="coverage-note">${escapeHTML(coverage.notes||"")}
              V2 reference candidates need separate V3 tests.</p>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===2?"block":"none"}">
            <div class="eyebrow">Step 2 / Select</div>
            <h2>Choose what to configure</h2>
            <p>Select a domain and one attribute or control. This catalog includes historical support for other Audi vehicles, not just the current Q8.</p>
            <label>Capability domain</label>
            <select id="category">${capabilityNames.map(c=>`<option value="${escapeHTML(c)}" ${this.category===c?"selected":""}>${escapeHTML(c.replaceAll("_"," "))}</option>`).join("")}</select>
            <div class="toolbar">
              <div class="tool"><label>Show attributes</label>
                <select id="inventory-filter">
                  <option value="available" ${this.inventoryFilter==="available"?"selected":""}>Observed on this vehicle</option>
                  <option value="all" ${this.inventoryFilter==="all"?"selected":""}>All historical V2 references</option>
                </select>
              </div>
            </div>
            <h2>Read-only attributes</h2>
            ${visibleAttributes.map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.entity_key.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.attribute)} · ${escapeHTML(r.status)}</div></div>
              <button data-action="select-attribute" data-capability="${escapeHTML(r.capability)}"
                data-attribute="${escapeHTML(r.attribute)}">Configure routes</button>
            </div>`).join("") || '<p>No observed attributes in this domain. Change the filter to show the complete historical catalog.</p>'}
            <h2 style="margin-top:20px">Controls</h2>
            <p>Historical control definitions stay in the catalog. Only Climate has the existing guided POST testing workflow; unverified actions remain disabled.</p>
            ${controls.filter(r=>r.capability===this.category).map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.attribute.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.status)} · ${escapeHTML(r.api_family)}</div></div>
              <button data-action="step-3">Review controls</button>
            </div>`).join("") || '<p>No historical control references in this domain.</p>'}
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3&&this.attribute?"block":"none"}">
            <div class="eyebrow">Step 3 / Read-only discovery</div>
            <h2>${escapeHTML(this.attribute || "Choose an attribute in Step 2")}</h2>
            <p>Compare API routes for this specific attribute. A saved candidate is not enabled. Only a tested route returning a valid, recent vehicle value can drive regular polling.</p>
            <label>API route</label>
            <select id="read-route">${this.readRoutes.map(r=>`<option value="${escapeHTML(r.id)}" ${r.id===this.readChoice?"selected":""}>
              ${escapeHTML(r.family)} · ${escapeHTML(r.kind)} [${escapeHTML(r.result)}]</option>`).join("")}</select>
            <div class="callout" style="margin-top:13px"><b>${escapeHTML(chosen?.method||"GET")} · ${escapeHTML(chosen?.family||"No route")}</b>
              <div class="subline"><code>${escapeHTML(chosen?.path||"No mapped path yet")}</code></div>
              <div class="helper">Active: ${escapeHTML(this.readActive||"none")} · Draft: ${escapeHTML(this.readDraft||"none")}</div>
            </div>
            <div class="actions">
              <button data-action="read-test" class="primary" ${!this.readChoice||this.loading?"disabled":""}>Test read-only GET</button>
              <button data-action="read-save" ${!this.readChoice||this.loading?"disabled":""}>Save candidate</button>
              <button data-action="read-activate" ${!canActivateRead||this.loading?"disabled":""}>Activate for polling</button>
              <button data-action="read-disable" ${!this.readActive||this.loading?"disabled":""}>Disable attribute</button>
            </div>
            <details style="margin-top:18px"><summary>Advanced · define another API path and response mapping</summary>
              <p>Only safe relative CARIAD GET paths. JSON definitions are for engineering cases; no credentials, tokens or external URLs.</p>
              <textarea id="read-definition" rows="9">${escapeHTML(this.initialReadRoute)}</textarea>
              <button data-action="read-add" ${this.loading?"disabled":""}>Add custom read route</button>
            </details>
            <h2 style="margin-top:20px">Last test result</h2>
            <pre>${escapeHTML(JSON.stringify(this.lastResult??{"message":"No test yet"},null,2))}</pre>
          </section>
          <div class="grid" style="display:${this.step===3&&!this.attribute&&this.category==="climate"?"grid":"none"}">
            <section class="card">
              <div class="eyebrow">Control discovery</div>
              <h2>Climate (guided controls)</h2>
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
              <p style="font-size:12px">Save candidate remembers your choice without enabling an untested API.
                Activation requires a confirmed working result.</p>
              <div class="actions">
                <button class="primary" data-action="test" ${!selectedRoute||this.loading||this.pending?"disabled":""}>
                  ${this.aspect==="status"?"Test GET":"Test selected action"}
                </button>
                <button data-action="save" ${!selectedRoute||this.loading?"disabled":""}>Save candidate</button>
                <button data-action="select" ${!routeVerified||this.loading?"disabled":""}>Activate verified path</button>
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
              <h2>Advanced · Custom API path</h2>
              <p>Relative paths only. Auth and host remain owned by the Audi integration. {VIN} and typed parameters are supported.</p>
              <label>API definition (JSON)</label>
              <textarea id="definition" rows="13">${escapeHTML(this.initialRoute)}</textarea>
              <div class="actions"><button data-action="add" class="primary">Add experimental route</button></div>
              <div class="eyebrow" style="margin-top:28px">03 / Last experiment</div>
              <pre>${escapeHTML(JSON.stringify(this.lastResult??{"message":"No test yet"}, null, 2))}</pre>
            </section>
          </div>
          ${this.step===3&&!this.attribute&&this.category!=="climate"?`<section class="card"><h2>Control migration pending</h2><p>Historical ${escapeHTML(this.category)} controls remain in the V2 catalog until their own safe route, payload and physical confirmation workflow is implemented. No unverified POST is enabled.</p></section>`:""}
          <p class="foot">Experimental mode. HTTP 200/202 confirms gateway acceptance, not vehicle action.
          Custom paths and results stay in private local HA storage. V2 remains available for rollback.</p>`}
      </main>`;
  }
}
customElements.define("audiconnect-v3-panel", AudiConnectV3Panel);

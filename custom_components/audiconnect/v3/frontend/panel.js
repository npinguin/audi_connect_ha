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
    this.controlCapability = "";
    this.controlAction = "";
    this.controlRoutes = [];
    this.controlChoice = "";
    this.controlRequirement = "";
    this.discoveryGroup = "read_only";
    this.spinConfigured = false;
    this.inventoryFilter = "all";
    this.apiHistory = [];
    this.apiFamily = "vehicle";
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
      await this._controlRoutes();
      await this._apiResults();
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
    this.pending = this.capabilityStatus.pending_control || null;
  }

  async _apiResults() {
    if (!this.selected || !this.vin) { this.apiHistory = []; return; }
    const response = await this.api("api_results", this.selection);
    this.apiHistory = response.records || [];
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

  async _controlRoutes() {
    if (!this.selected || !this.vin || !this.controlAction || !this.controlCapability) {
      this.controlRoutes = []; this.controlChoice = ""; return;
    }
    const value = await this.api("control_routes", {
      ...this.selection, capability: this.controlCapability, action: this.controlAction
    });
    this.controlRoutes = value.routes || [];
    this.controlRequirement = value.requires || "";
    this.spinConfigured = value.spin_configured === true;
    this.controlChoice = value.active && this.controlRoutes.some(r=>r.id===value.active)
      ? value.active : this.controlRoutes.some(r=>r.id===this.controlChoice)
        ? this.controlChoice : this.controlRoutes[0]?.id || "";
    this.pending = value.pending || null;
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
      this.controlAction = "";
      this.readRoutes = [];
      this.render();
    } else if (e.target.id === "attribute") {
      this.attribute = e.target.value;
      this.controlAction = "";
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
    } else if (e.target.id === "control-route") {
      this.controlChoice = e.target.value;
      this.render();
    } else if (e.target.id === "inventory-filter") {
      this.inventoryFilter = e.target.value;
      this.render();
    } else if (e.target.id === "api-family") {
      this.apiFamily = e.target.value;
      this.render();
    }
  }

  async _reloadRoutes() {
    try {
      await this._routes();
      await this._loadCapabilityStatus();
      await this._readRoutes();
      await this._controlRoutes();
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
    if (action === "discovery-group") {
      if (this.pending) {
        this.error = "Resolve the pending physical action before changing discovery groups.";
        this.render(); return;
      }
      this.discoveryGroup = button.dataset.group;
      this.controlAction = ""; this.attribute = "";
      this.step = this.discoveryGroup === "read_only" ? 1 : 2;
      this.render(); return;
    }
    if (action === "open-capability") {
      this.category = button.dataset.capability;
      this.attribute = "";
      this.controlAction = "";
      this.step = 2; this.render(); return;
    }
    if (action === "select-attribute") {
      this.category = button.dataset.capability;
      this.attribute = button.dataset.attribute;
      this.controlAction = "";
      this.step = 3;
      try { await this._readRoutes(); this.error = ""; }
      catch (err) { this.error = String(err.message || err); }
      this.render(); return;
    }
    if (action === "select-control") {
      this.category = button.dataset.capability;
      this.controlCapability = button.dataset.capability;
      this.controlAction = button.dataset.control;
      this.attribute = "";
      this.step = 3;
      try { await this._controlRoutes(); this.error = ""; }
      catch(err) { this.error = String(err.message || err); }
      this.render(); return;
    }
    const readRoute = this.shadowRoot.getElementById("read-route")?.value || this.readChoice;
    const controlRoute = this.shadowRoot.getElementById("control-route")?.value || this.controlChoice;
    const rawReadDefinition = this.shadowRoot.getElementById("read-definition")?.value || "";
    const controlParameters = this.shadowRoot.getElementById("control-parameters")?.value || "{}";
    const approved = this.shadowRoot.getElementById("control-approval")?.checked === true;
    const approvalGroup = this.controlRoutes.find(r=>r.id===controlRoute)?.approval_group;
    const rawControlDefinition = this.shadowRoot.getElementById("control-definition")?.value || "";
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
      if (action === "review-normal") {
        const command = this.capabilityStatus.normal_command;
        if (!command || !["pending", "uncertain"].includes(command.state)) throw new Error("No unresolved command");
        this.lastResult = await this.api("review_normal_command", {...this.selection, command_id: command.command_id});
      } else if (action === "test") {
        let parameters = {};
        parameters = JSON.parse(rawParameters);
        if (this.aspect !== "status") throw new Error("Use the explicit control discovery workflow");
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
      } else if (action === "family-test") {
        const car = this.entries.find(e=>e.entry_id===this.selected)
          ?.vehicles.find(v=>v.vin===this.vin);
        const family = this.apiFamily === "vehicle" || this.apiFamily === "all"
          ? car?.api_family || "cariad" : this.apiFamily;
        this.lastResult = await this.api("test_family_reads", {...this.selection, family});
      } else if (action === "control-add") {
        this.lastResult = await this.api("add_route", {
          ...this.selection, route: JSON.parse(rawControlDefinition)
        });
        this.controlChoice = this.lastResult.operation || this.controlChoice;
      } else if (action === "control-test") {
        if (!approved || !["non_spin","spin"].includes(approvalGroup))
          throw new Error("Approve this exact vehicle control before sending it");
        if (approvalGroup === "spin" && !this.spinConfigured)
          throw new Error("Configure your Audi S-PIN first");
        this.lastResult = await this.api("control_test", {
          ...this.selection, capability: this.controlCapability,
          action: this.controlAction, operation: controlRoute,
          approval: approvalGroup, parameters: JSON.parse(controlParameters)
        });
      } else if (action === "control-select") {
        this.lastResult = await this.api("select", {...this.selection,
          capability: this.controlCapability, aspect: this.controlAction, operation: controlRoute});
      } else if (action === "control-disable") {
        this.lastResult = await this.api("control_disable", {
          ...this.selection, capability: this.controlCapability,
          action: this.controlAction
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
      await this._controlRoutes();
      if (["test","read-test","control-test","family-test"].includes(action)) {
        await this._apiResults();
      }
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

  get initialControlRoute() {
    const capability = this.controlCapability || "access";
    const action = this.controlAction || "lock";
    const selected = this.controlRoutes.find(r=>r.id===this.controlChoice);
    const body = capability==="access" && ["lock","unlock"].includes(action)
      ? {spin:"{SPIN}"}
      : ["remote","charging"].includes(capability) ? {} : null;
    return JSON.stringify({
      id:"user."+capability+"."+action+".alternative",
      capability, aspect:action, family:"cariad", method:selected?.method || "POST",
      path:selected?.path || "/vehicle/v1/vehicles/{VIN}/"+capability+"/"+action,
      variables:{}, body:selected?.method==="PUT"?null:body,
      ...(selected?.method==="PUT"?{handler:selected.id}:{}),
      description:"Reviewed experimental command template"
    },null,2);
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
    const vehicleFamily = car?.api_family || "cariad";
    const family = this.apiFamily === "vehicle" ? vehicleFamily : this.apiFamily;
    const filteredRows = rows.filter(r => family === "all" || r.api_family === family);
    const attributes = filteredRows.filter(r => r.entity_key &&
      ["v3_live_evidence","v2_attribute_reference"].includes(r.source));
    const controls = filteredRows.filter(r => r.source === "v2_control_reference");
    const controlActions = (coverage.control_actions || []).filter(r =>
      family === "all" || r.api_family === family);
    const capabilityNames = [...new Set([...attributes,...controls,...controlActions].map(r => r.capability))].sort();
    const readable = attributes.filter(r => ["verified","readable_but_stale"].includes(r.status));
    const visibleAttributes = attributes.filter(r => r.capability === this.category &&
      (this.inventoryFilter !== "available" || ["verified","readable_but_stale"].includes(r.status)));
    const chosen = this.readRoutes.find(r => r.id === this.readChoice);
    const activeRoute = this.controlAction ? this.controlChoice :
      this.attribute ? this.readChoice : "";
    const records = (this.apiHistory || []).filter(r =>
      family === "all" || r.family === family);
    const lastSelectedResult = records.find(r=>r.operation===activeRoute);
    const applicableFamily = family === "all" || family === vehicleFamily;
    const selectedControl = this.controlRoutes.find(r=>r.id===this.controlChoice);
    const group = selectedControl?.approval_group;
    const groupActions = controlActions.filter(r => this.discoveryGroup === "read_only"
      ? r.capability === this.category
      : (r.approval_groups || []).includes(this.discoveryGroup));
    const canActivateRead = chosen?.result === "verified" ||
      (chosen?.family === "mbb" && chosen?.result === "readable_but_stale");
    const bg = "var(--primary-background-color, #f8fafc)";
    const body = "var(--primary-text-color, #111827)";
    this.shadowRoot.innerHTML = `
      <style>
        :host {display:block; min-height:100%; background:${bg}; color:${body};
          font-family:var(--ha-font-family-body,Roboto,Noto,sans-serif);font-size:var(--ha-font-size-m,16px);line-height:var(--ha-line-height-normal,1.6);}
        *{box-sizing:border-box}
        main{max-width:1240px;margin:auto;padding:28px 24px 48px}
        .eyebrow{letter-spacing:.12em;text-transform:uppercase;font-weight:700;
          font-size:var(--ha-font-size-s,12px);color:var(--secondary-text-color,#64748b)}
        h1{font-size:var(--ha-font-size-2xl,24px);margin:8px 0 4px;font-weight:750}
        h2{font-size:var(--ha-font-size-xl,20px);margin:0 0 18px}
        p{line-height:1.5;color:var(--secondary-text-color,#64748b)}
        .top,.toolbar,.line{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
        .toolbar{justify-content:flex-start;padding:22px 0}
        .grid{display:grid;grid-template-columns:1fr 1.6fr;gap:18px}
        .card{border-radius:13px;background:var(--card-background-color,white);
          border:1px solid var(--divider-color,#e2e8f0);padding:22px;min-width:0}
        .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}
        .stat{font-size:20px;font-weight:700;margin-top:8px;overflow-wrap:anywhere}
        label{font-size:var(--ha-font-size-m,14px);color:var(--secondary-text-color,#64748b);display:block;font-weight:700;margin-bottom:6px}
        select,textarea,input{width:100%;font:inherit;padding:10px 12px;border:1px solid
          var(--divider-color,#d1d5db);border-radius:8px;background:var(--card-background-color,white);
          color:inherit}
        textarea{font-family:var(--ha-font-family-code,monospace);font-size:var(--ha-font-size-m,14px);line-height:1.5;resize:vertical}
        .tool{min-width:180px;flex:1;max-width:360px}
        button{font:inherit;border:1px solid var(--divider-color,#cbd5e1);
          border-radius:8px;background:var(--card-background-color,white);
          color:inherit;padding:10px 15px;cursor:pointer;font-weight:650}
        button.primary{background:var(--primary-color,#2366a6);border-color:var(--primary-color,#2366a6);color:white}
        button:disabled{opacity:.42;cursor:not-allowed}
        .badge{display:inline-block;font-size:var(--ha-font-size-s,12px);border:1px solid var(--divider-color,#cbd5e1);
          border-radius:20px;padding:4px 9px;font-weight:700}
        .route{display:flex;justify-content:space-between;gap:12px;padding:11px 0;
          border-bottom:1px solid var(--divider-color,#e2e8f0);font-size:var(--ha-font-size-m,14px)}
        code{overflow-wrap:anywhere;font-family:var(--ha-font-family-code,monospace)}
        .summary{font-size:var(--ha-font-size-m,14px);margin-top:12px}
        .error{padding:12px;border:1px solid #d97706;border-radius:9px;margin:14px 0}
        .warn{border-left:3px solid #d97706;padding:12px;background:var(--secondary-background-color,#f8fafc)}
        .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:15px}
        pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--secondary-background-color,#f8fafc);
          padding:14px;border-radius:9px;font-size:var(--ha-font-size-m,14px);max-height:340px;overflow:auto}
        .foot{font-size:var(--ha-font-size-m,14px);margin-top:25px}
        .steps{display:flex;gap:8px;margin:12px 0 22px;flex-wrap:wrap}
        .steps button{flex:1;min-width:145px;text-align:left}
        .steps button.current{border-color:var(--primary-color,#2366a6);box-shadow:inset 0 -3px var(--primary-color,#2366a6)}
        .cap-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:16px 0}
        .cap-card{width:100%;padding:16px;text-align:left}
        .cap-card b{font-size:var(--ha-font-size-l,16px)}
        .cap-card .subline{line-height:1.6;margin-top:8px}
        .eyeline{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
        .callout{background:var(--secondary-background-color,#f8fafc);padding:15px;border-radius:9px}
        .attribute-row{display:flex;justify-content:space-between;align-items:center;gap:16px;
          border-top:1px solid var(--divider-color,#e2e8f0);padding:11px 0}
        .attribute-row button{text-align:center;flex:0 0 auto;overflow-wrap:anywhere}
        .helper{font-size:var(--ha-font-size-m,14px);margin:9px 0;color:var(--secondary-text-color,#64748b)}
        .coverage-table{max-height:400px;overflow:auto}
        table{width:100%;border-collapse:collapse;font-size:var(--ha-font-size-m,14px)}
        th{text-align:left;font-weight:700;color:var(--secondary-text-color,#64748b);
          padding:11px 10px;position:sticky;top:0;background:var(--card-background-color,white);
          border-bottom:1px solid var(--divider-color,#d1d5db)}
        td{padding:11px 10px;vertical-align:top;border-bottom:1px solid var(--divider-color,#e2e8f0)}
        .subline{font-size:var(--ha-font-size-m,14px);color:var(--secondary-text-color);margin-top:5px;line-height:1.5}
        .coverage-note{font-size:var(--ha-font-size-m,14px);margin:10px 0 0}
        .family-toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:14px 0}
        .family-toolbar select{width:auto;min-width:240px}
        .discovery-summary{padding:16px;border-radius:12px;background:var(--secondary-background-color,#f3f6f9);margin:14px 0 18px}
        .family-hint{color:var(--secondary-text-color);font-size:var(--ha-font-size-m,14px)}
        button:focus-visible,select:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
        .record{border-top:1px solid var(--divider-color);padding:12px 0}
        .record summary{cursor:pointer;font-weight:600}
        .family-select{width:280px;max-width:100%}
        @media(max-width:780px){.attribute-row{align-items:stretch;flex-direction:column}.attribute-row button{width:100%}}
        @media(max-width:780px){main{padding:18px 12px}.grid,.cards,.cap-grid{grid-template-columns:1fr}h1{font-size:21px}}
      </style>
      <main>
        <div class="top">
          <div><div class="eyebrow">Audi Connect / V3 capability workbench</div>
            <h1>Audi V3 — Experimental</h1>
            <p>Recover historical V2 capabilities across API families. Read-only discovery plus explicitly approved control discovery.</p></div>
          <button data-action="refresh" ${this.loading?"disabled":""}>↻ Refresh</button>
        </div>
        <div class="toolbar">
          <div class="tool"><label>Integration</label>
            <select id="entry">${this.entries.map((v) => `<option value="${escapeHTML(v.entry_id)}" ${v.entry_id===this.selected?"selected":""}>Audi Connect / ${escapeHTML(v.entry_id.slice(0,8))}</option>`).join("")}</select></div>
          <div class="tool"><label>Vehicle</label><select id="vehicle">
            ${(item?.vehicles||[]).map((v)=>`<option value="${escapeHTML(v.vin)}" ${v.vin===this.vin?"selected":""}>${escapeHTML(v.name)} — ${escapeHTML(v.model)}</option>`).join("")}
          </select></div>
          <div class="tool family-select"><label for="api-family">API family</label>
            <select id="api-family">
              <option value="vehicle" ${this.apiFamily==="vehicle"?"selected":""}>This vehicle · ${escapeHTML(vehicleFamily.toUpperCase())}</option>
              <option value="cariad" ${this.apiFamily==="cariad"?"selected":""}>CARIAD · modern</option>
              <option value="mbb" ${this.apiFamily==="mbb"?"selected":""}>MBB · legacy</option>
              <option value="all" ${this.apiFamily==="all"?"selected":""}>All historical API families</option>
            </select></div>
        </div>
        <div class="steps">
          <button data-action="step-1" class="${this.step===1?"current":""}">1 · Inventory & status</button>
          <button data-action="step-2" class="${this.step===2?"current":""}">2 · Select capability</button>
          <button data-action="step-3" class="${this.step===3?"current":""}">3 · Configure & test</button>
        </div>
        ${this.error?`<div class="error">${escapeHTML(this.error)}</div>`:""}
        ${car&&this.pending&&!this.controlAction?`<section class="card" style="margin-bottom:18px">
          <div class="warn"><b>Pending vehicle control: ${escapeHTML(this.pending.capability)} · ${escapeHTML(this.pending.action)}</b>
            <p>Review the physical result before starting another discovery action.</p>
            <div class="actions">
              <button data-action="confirm-worked">Verified working</button>
              <button data-action="confirm-failed">Did not work</button>
              <button data-action="confirm-uncertain">Not sure</button>
            </div>
          </div>
        </section>`:""}
        ${car?`<section class="card" style="margin-bottom:18px">
          <h2>Discovery mode</h2>
          <div class="actions">
            <button data-action="discovery-group" data-group="read_only" class="${this.discoveryGroup==="read_only"?"primary":""}">Read-only · automatic</button>
            <button data-action="discovery-group" data-group="non_spin" class="${this.discoveryGroup==="non_spin"?"primary":""}">Controls · without S-PIN</button>
            <button data-action="discovery-group" data-group="spin" class="${this.discoveryGroup==="spin"?"primary":""}">Controls · with S-PIN</button>
          </div>
          ${coverage.normal_command && ["pending", "uncertain"].includes(coverage.normal_command.state) ? `
            <p>A previous vehicle command has an uncertain result. Inspect the vehicle before acknowledging it. No command is replayed.</p>
            <button data-action="review-normal">I inspected the vehicle — acknowledge uncertainty</button>` : ""}
          <p>Choose a group to review candidates. Selecting a group sends no command. Every control needs separate approval for this vehicle and physical review before the next action.</p>
        </section>`:""}
        ${!car?`<div class="card">No V3 vehicle loaded. Enable V3 and confirm Audi authentication before testing.</div>`: `
          <div class="cards" style="display:${this.step===1?"grid":"none"}">
            <div class="card"><div class="eyebrow">Cloud polling</div>
              <div class="stat">${item.poll_success?"Connected":"Not confirmed"}</div>
              <div class="summary">${escapeHTML(item.poll_success||"No successful cloud poll")}</div></div>
            <div class="card"><div class="eyebrow">Automatic read discovery</div>
              <div class="stat">${readable.length} readable</div>
              <div class="summary">${escapeHTML(counts.observed_jobs??0)} CARIAD jobs observed · ${escapeHTML(counts.not_observed_jobs??0)} not observed</div></div>
            <div class="card"><div class="eyebrow">Climate & controls</div>
              <div class="stat">${escapeHTML(status)}</div>
              <div class="summary">Climate start: ${car.start_enabled?"verified":"not tested"} · Stop: ${car.stop_enabled?"verified":"not tested"}</div></div>
          </div>
          <section class="card" style="margin-bottom:18px;display:${this.step===1?"block":"none"}">
            <div class="eyebrow">Step 1 / Automatic discovery</div>
            <h2>Status & inventory · what works on this Audi?</h2>
            <p>Startup uses safe read-only GET requests. Other API routes stay available for fine tuning. No vehicle action is automatically tested.</p>
            <div class="discovery-summary"><b>${readable.length} readable attributes</b>
              · ${readable.filter(r=>r.status==="verified").length} fresh
              · ${readable.filter(r=>r.status==="readable_but_stale").length} stale
              <div>${escapeHTML(counts.observed_jobs??0)} of ${escapeHTML((counts.catalog_jobs??0)-(counts.not_scanned_jobs??0))} scanned jobs observed.
              ${escapeHTML(counts.not_scanned_jobs??0)} jobs pending.</div>
              <div class="family-hint">Not observed does not mean unsupported. V2 history does not equal V3 validation.</div>
            </div>
            <details><summary>Historical V2 inventory totals</summary>
            <div class="line" style="justify-content:flex-start;gap:16px;font-size:var(--ha-font-size-m,14px);margin-bottom:14px">
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
            </div></details>
            <h2>Capabilities · ${escapeHTML(family==="all"?"all API families":family.toUpperCase())}</h2>
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
                Technical evidence — ${escapeHTML(filteredRows.length)} selected-family records
              </summary>
              <div class="coverage-table"><table>
                <thead><tr><th>Capability</th><th>Attribute / Control</th>
                  <th>API family / Path</th><th>Discovery result</th></tr></thead>
                <tbody>${filteredRows.map((r)=>`<tr>
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
            <h2>Capabilities & API routes</h2>
            <p>Choose a capability, read-only field or control, then inspect and test its specific route in Step 3. Use the API-family filter above to compare historical alternatives.</p>
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
            <h2>Read-only attributes · select a route</h2>
            ${visibleAttributes.map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.entity_key.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.attribute)} · ${escapeHTML(r.status)}</div></div>
              <button data-action="select-attribute" data-capability="${escapeHTML(r.capability)}"
                data-attribute="${escapeHTML(r.attribute)}">Routes & test</button>
            </div>`).join("") || '<p>No observed attributes in this domain. Change the filter to show the complete historical catalog.</p>'}
            <h2 style="margin-top:20px">Vehicle controls · physical verification required</h2>
            <p>Wake-up, Climate ON/OFF, Lock/Unlock, charging and other vehicle actions are NEVER automatically tested. Select a control to test one API route while at the car.</p>
            ${groupActions.map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.action.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.api_family)} · ${escapeHTML(r.status)} · ${r.candidate_count} candidate routes</div></div>
              <button data-action="select-control" data-capability="${escapeHTML(r.capability)}"
                data-control="${escapeHTML(r.action)}" ${!r.candidate_count?"disabled":""}>Routes & test</button>
            </div>`).join("")||'<p>No supported control routes for this vehicle API family.</p>'}
            <details><summary>Historical controls not yet migrated</summary>
            ${controls.filter(r=>r.capability===this.category).map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.attribute.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.status)} · ${escapeHTML(r.api_family)}</div></div>
              <button data-action="step-3">Review controls</button>
            </div>`).join("") || '<p>No additional historical control references in this domain.</p>'}</details>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3&&this.attribute?"block":"none"}">
            <div class="eyebrow">Step 3 / Configure & test · GET route</div>
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
            <div class="callout" style="margin-top:18px">
              <b>Latest saved response for this route</b>
              <div>${escapeHTML(lastSelectedResult?.at||"Never executed")} · HTTP ${escapeHTML(lastSelectedResult?.http_status??"-")} · ${escapeHTML(lastSelectedResult?.result||"not tested")}</div>
              <details><summary>Redacted response preview</summary><pre>${escapeHTML(JSON.stringify(lastSelectedResult?.preview??"No recorded response",null,2))}</pre></details>
            </div>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3&&this.controlAction?"block":"none"}">
            <div class="eyebrow">Step 3 / Configure & test · POST / PUT control</div>
            <h2>${escapeHTML(this.controlCapability.replaceAll("_"," "))} · ${escapeHTML(this.controlAction.replaceAll("_"," "))}</h2>
            <p>Send only one explicitly selected CARIAD command. HTTP 200/202 is not confirmation that the car acted. Never auto-retry with another variant.</p>
            <div class="warn">Before testing: be physically present, understand the action, and verify the result on the vehicle or myAudi. ${escapeHTML(this.controlRequirement)}</div>
            <label for="control-route" style="margin-top:16px">API-family executor / route</label>
            <select id="control-route">${this.controlRoutes.map(r=>`<option value="${escapeHTML(r.id)}" ${this.controlChoice===r.id?"selected":""}>${escapeHTML(r.family.toUpperCase())} · ${escapeHTML(r.id)} [${escapeHTML(r.status)}]</option>`).join("")}</select>
            <div class="callout" style="margin-top:12px">
              <b>Physically verified route: ${this.controlRoutes.find(r=>r.active)?"Yes":"No"}</b>
              <div class="helper"><code>${escapeHTML(this.controlRoutes.find(r=>r.id===this.controlChoice)?.path||"No route available")}</code></div>
            </div>
            <p><b>Approval group:</b> ${escapeHTML(group==="spin"?"S-PIN protected":group==="non_spin"?"Without S-PIN":"Not available")}</p>
            ${group==="spin"&&!this.spinConfigured?'<p class="warn">Configure your S-PIN in the Audi account before protected discovery.</p>':""}
            ${selectedControl?.parameters_required?`<label for="control-parameters">Action parameters (JSON; never enter a PIN)</label>
              <textarea id="control-parameters" rows="3">{}</textarea>
              ${Object.keys(selectedControl.parameter_bindings||{}).length?`<p>Semantic inputs: ${escapeHTML(Object.values(selectedControl.parameter_bindings).join(", "))}</p>`:""}`:""}
            <label style="display:flex;gap:8px;align-items:center">
              <input id="control-approval" type="checkbox" style="width:auto">
              I approve this exact action on the selected car and will verify its effect.
            </label>
            <div class="actions">
              <button data-action="control-test" class="primary" ${!this.controlChoice||this.loading||this.pending||group==="unsupported"||(group==="spin"&&!this.spinConfigured)?"disabled":""}>Send one test command</button>
              <button data-action="control-select" ${this.loading||this.pending||selectedControl?.status!=="worked"||!selectedControl?.runtime_ready?"disabled":""}>Activate verified route</button>
              <button data-action="control-disable" ${this.loading||this.pending?"disabled":""}>Disable this control</button>
            </div>
            ${this.pending ? `<div class="warn" style="margin-top:18px">
              <b>Test sent · physical result pending</b>
              <p>Inspect the actual vehicle state. Do not try another command until this result is resolved.</p>
              <div class="actions">
                <button data-action="confirm-worked">Verified working</button>
                <button data-action="confirm-failed">Did not work</button>
                <button data-action="confirm-uncertain">Not sure</button>
              </div>
            </div>` : ""}
            <details style="margin-top:18px">
              <summary>Advanced · Add an alternative command template</summary>
              <p>System variables: <code>{VIN}</code> is filled from this car. <code>{SPIN}</code> is filled securely from the configured Audi account, only for Access Lock/Unlock using <code>{"spin":"{SPIN}"}</code>. Do not enter or save a real S-PIN.</p>
              <label for="control-definition">Control template (JSON)</label>
              <textarea id="control-definition" rows="12">${escapeHTML(this.initialControlRoute)}</textarea>
              <div class="actions"><button data-action="control-add" ${this.loading||this.pending?"disabled":""}>Save alternative route · no command sent</button></div>
            </details>
            <div class="callout" style="margin-top:18px">
              <b>Last control execution</b>
              <div>${escapeHTML(lastSelectedResult?.at||"Never executed")} · HTTP ${escapeHTML(lastSelectedResult?.http_status??"-")} · ${escapeHTML(lastSelectedResult?.result||"not tested")}</div>
              <p>Control response bodies are withheld. HTTP acceptance does not confirm the vehicle acted.</p>
            </div>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3?"block":"none"}">
            <div class="eyebrow">Step 3 / Read-only API family</div>
            <h2>Test all applicable GET functions · ${escapeHTML(family==="all"?vehicleFamily.toUpperCase():family.toUpperCase())}</h2>
            <p>Up to three safe CARIAD GET requests (one batch and two targeted probes), or five MBB legacy GETs. No POST commands, no wake-up, no automatic fallback, and no repeated route spraying.</p>
            ${!applicableFamily?'<div class="warn">This API family does not apply to the selected vehicle.</div>':""}
            <div class="actions"><button data-action="family-test" class="primary"
              ${this.loading||!applicableFamily?"disabled":""}>Test read-only API family</button></div>
            <div class="helper">${escapeHTML(this.lastResult?.family?JSON.stringify(this.lastResult):"No manual family test in this session")}</div>
          </section>
          ${this.step===3&&!this.attribute&&!this.controlAction?`<section class="card" style="margin-bottom:18px">
            <h2>Choose an individual API path</h2>
            <p>Open Step 2 to select a capability and one GET attribute or POST control. Alternatively, test the applicable GET family above.</p>
          </section>`:""}
          <section class="card" style="margin-bottom:18px;display:${this.step===3?"block":"none"}">
            <div class="eyebrow">Diagnostics / Persisted API evidence</div>
            <h2>Last result and response by API route</h2>
            <p>Timestamp · API family · HTTP status · bounded redacted GET response. Only the latest result per route is kept per vehicle, including after a Home Assistant restart.</p>
            ${records.map(r=>`<details class="record">
              <summary>${escapeHTML(r.operation)} · HTTP ${escapeHTML(r.http_status??"-")} · ${escapeHTML(r.at)}</summary>
              <div><b>${escapeHTML(r.family.toUpperCase())} · ${escapeHTML(r.method)}</b> · ${escapeHTML(r.result)}</div>
              <pre>${escapeHTML(JSON.stringify(r.preview,null,2))}</pre>
            </details>`).join("")||'<p>No saved API results yet.</p>'}
          </section>
          <p class="foot">Experimental mode. HTTP 200/202 confirms gateway acceptance, not vehicle action.
          Only bounded redacted response previews stay in private local HA storage. V2 remains available for rollback.</p>`}
      </main>`;
  }
}
customElements.define("audiconnect-v3-panel", AudiConnectV3Panel);

/* Audi Connect V3 — local administrator development panel (zero dependencies).
 * Uses authenticated Home Assistant WebSocket API. Never reads bearer tokens.
 * In a user-action test, HTTP success is not proof the physical car acted.
 */
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (x) => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]
));

const friendly = value => ({
  verified:"Fresh", readable_but_stale:"Last known", invalid_value:"Invalid value",
  not_tested:"Not tested", mapping_pending:"Mapping needed", not_applicable_to_vehicle:"Not applicable",
  catalog_matched:"Catalog matched", local_verified:"Locally verified", worked:"Verified",
  boolean_oil_level_use_binary:"Oil level is a warning, not a percentage",
  negative_duration:"Invalid remaining duration", unmapped_response_fields_review:"Review unmapped response fields",
  response_schema_mismatch:"Response does not match mapping",
  accepted_not_physically_verified:"Command accepted; physical result not verified",
  model_family_unknown:"Vehicle model family unknown", http_error:"API request failed"
}[value] || String(value || "Unknown").replaceAll("_"," "));
const domainName = value => ({access:"Access & security",charging:"Charging",climate:"Climate",
  mobility:"Trips & location",remote:"Remote actions",service:"Service & maintenance",
  vehicle_status:"Vehicle status"}[value] || friendly(value));
const actionName = (cap, action) => ({
  "climate.start":"Climate · Turn on (vehicle settings)",
  "climate.stop":"Climate · Turn off",
  "climate.start_with_settings":"Climate · Turn on with selected settings",
  "climate.set_settings":"Climate · Update settings",
  "climate.window_heating_start":"Window heating · Turn on",
  "climate.window_heating_stop":"Window heating · Turn off",
  "climate.preheater_start":"Preheater · Turn on",
  "climate.preheater_stop":"Preheater · Turn off",
  "access.lock":"Central locking · Lock",
  "access.unlock":"Central locking · Unlock",
  "charging.start":"Charging · Start",
  "charging.stop":"Charging · Stop",
}[cap+"."+action] || ({wake:"Wake vehicle",refresh:"Request fresh vehicle data",
  flash:"Flash lights",set_target_soc:"Set charge target",set_charge_mode:"Set charge mode"}[action] || friendly(action)));
const stateTone = value => ["verified","worked","local_verified"].includes(value)?"good":
  ["invalid_value","failed","physical_failed"].includes(value)?"bad":
  ["readable_but_stale","mapping_pending","pending_review"].includes(value)?"warn":"neutral";
const pill = (value,label) => `<span class="state ${stateTone(value)}">${escapeHTML(label||friendly(value))}</span>`;

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
    this.functionMode = "all";
    this.apiHistory = [];
    this.engineeringHistory = [];
    this.apiFamily = "vehicle";
    this.operationFilter = "all";
    this.searchText = "";
    this.entityFilter = "";
    this.focusOperation = "";
    this.identityOperation = ""; this.identityQuery = ""; this.identityVariables = "{}"; this.identityExecution = null;
    this.operationMethod = "all";
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
    this.definitionEdits = new Map();
    this.shadowRoot.addEventListener("input", (e) => {
      const {definition, field} = e.target.dataset || {};
      if (definition && field) this.definitionEdits.set(definition + ":" + field, e.target.value);
    });
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
    if (!this.selected || !this.vin) { this.apiHistory = []; this.engineeringHistory = []; return; }
    const response = await this.api("api_results", {...this.selection, include_engineering:true});
    this.apiHistory = response.records || [];
    this.engineeringHistory = response.engineering_history || [];
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
    if (this.loading) return;
    if (e.target.id === "entry") {
      this.selected = e.target.value; this.vin = ""; this._resetVehicleSelection();
      await this._load();
    } else if (e.target.id === "vehicle") {
      this.vin = e.target.value; this._resetVehicleSelection();
      await this._load();
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
    } else if (e.target.id === "global-search") {
      this.searchText = e.target.value.trim(); this.focusOperation = ""; if(this.searchText) this.apiFamily="all"; this.render();
    } else if (e.target.id === "operation-filter") {
      this.operationFilter = e.target.value; this.focusOperation = "";
      this.render();
    } else if (e.target.id === "operation-method") {
      this.operationMethod = e.target.value;
      this.render();
    } else if (e.target.id === "entity-filter") {
      this.selectEntityFilter(e.target.value);
    } else if (e.target.id === "identity-operation") {
      this.openIdentityEditor(e.target.value);
    } else if (e.target.id === "api-family") {
      this.apiFamily = e.target.value;
      this.focusOperation = ""; this.attribute = ""; this.controlAction = "";
      if (this.step === 3) this.step = 2;
      this.render();
    }
  }

  _resetVehicleSelection() {
    this.definitionEdits.clear();
    this.entityFilter = "";
    this.identityOperation = ""; this.identityQuery = ""; this.identityVariables = "{}"; this.identityExecution = null;
    this.attribute = ""; this.controlAction = ""; this.controlCapability = "";
    this.readRoutes = []; this.controlRoutes = []; this.readChoice = ""; this.controlChoice = "";
    this.readActive = ""; this.readDraft = ""; this.pending = null; this.lastResult = null;
    this.apiHistory = []; this.engineeringHistory = []; this.capabilityStatus = {counts:{},rows:[]}; this.routeChoice = "";
    this.step = 1; this.apiFamily = "vehicle"; this.functionMode = "all"; this.discoveryGroup = "read_only";
    this.focusOperation = ""; this.operationFilter = "all"; this.operationMethod = "all";
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

  identityTemplate(operation) {
    return this.capabilityStatus.identity_templates?.[operation] || "";
  }
  entityLinks(ids) {
    return [...new Set(ids||[])].map(id=>`<button class="entity-link" data-action="filter-entity" data-entity="${escapeHTML(id)}">${escapeHTML(id)}</button>`).join(" ");
  }
  selectEntityFilter(id) {
    this.entityFilter = id || ""; this.searchText = ""; this.focusOperation = ""; this.apiFamily = "all";
    this.attribute = ""; this.controlAction = ""; this.identityOperation = ""; this.identityExecution = null;
    const link = (this.capabilityStatus.entity_links||[]).find(row=>(row.entity_ids||[]).includes(id));
    if(link?.capabilities?.length) this.category = link.capabilities[0];
    if(this.step===3) this.step=2;
    this.render();
  }
  openIdentityEditor(operation, useDefault=false) {
    this.identityOperation = operation;
    const draft = useDefault ? null : this.capabilityStatus.identity_drafts?.[operation];
    this.identityQuery = draft?.query ?? this.identityTemplate(operation);
    this.identityVariables = JSON.stringify(draft?.variables ?? this.capabilityStatus.identity_fixed_parameters?.[operation]?.variables ?? {}, null, 2);
    this.identityExecution = null;
    this.attribute = ""; this.controlAction = "";
    this.category = "vehicle_identity"; this.step = 3; this.render();
  }
  unresolvedCommands() {
    const normal = this.capabilityStatus.normal_command;
    return this.capabilityStatus.unresolved_commands || (normal && ["pending","uncertain"].includes(normal.state) ? [normal] : []);
  }
  capabilityBlocked(capability) {
    return this.unresolvedCommands().some(row=>row.capability===capability && this.reviewRequired(row));
  }
  reviewRequired(row) {
    return row.review_required ?? (row.state==="pending" || row.capability==="access" ||
      (row.capability==="remote" && ["engine_start","engine_stop"].includes(row.action)));
  }
  localTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    try { return date.toLocaleString(undefined, {timeZone:this._hass?.config?.time_zone,
      year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"}); }
    catch { return date.toLocaleString(); }
  }

  async _click(e) {
    const button = e.target.closest("button[data-action]");
    if (!button || this.loading) return;
    const action = button.dataset.action;
    if (action.startsWith("step-")) {
      this.step = Number(action.slice(5)); this.focusOperation = ""; this.render(); return;
    }
    if (action === "filter-entity") { this.selectEntityFilter(button.dataset.entity); return; }
    if (action === "identity-test" || action === "identity-reset") {
      this.openIdentityEditor(button.dataset.operation || this.identityOperation, action==="identity-reset"); return;
    }
    if (action === "open-identity") {
      this.category = "vehicle_identity"; this.apiFamily = "all"; this.attribute = ""; this.controlAction = ""; this.step = 2; this.render(); return;
    }
    if (action === "identity-evidence") {
      this.apiFamily = button.dataset.operation?.startsWith("cariad.")?"cariad":"graphql"; this.step = 4; this.focusOperation = button.dataset.operation || ""; this.operationFilter = "all"; this.operationMethod = "all"; this.render(); return;
    }
    if (action === "discovery-group") {
      if (this.pending) {
        this.error = "Resolve the pending physical action before changing discovery groups.";
        this.render(); return;
      }
      this.discoveryGroup = button.dataset.group;
      this.controlAction = ""; this.attribute = "";
      this.step = 2; this.functionMode = "controls";
      this.render(); return;
    }
    if (action === "inspect-finding") {
      const finding = (this.capabilityStatus.findings||[])[Number(button.dataset.index)];
      if (!finding) return;
      const row = (this.capabilityStatus.rows||[]).find(r=>r.attribute===finding.attribute && r.entity_key);
      if (row) {
        this.category = row.capability; this.attribute = row.attribute; this.controlAction = "";
        this.readRoutes = []; this.readChoice = ""; this.readActive = ""; this.readDraft = "";
        this.step = 3; this.loading = true; this.error = ""; this.render();
        try { await this._readRoutes(); } catch (err) { this.error = String(err.message||err); }
        finally { this.loading = false; this.render(); }
      } else {
        this.focusOperation = finding.operation || ""; this.operationFilter = "all"; this.operationMethod = "all";
        this.step = 4; this.apiFamily = "all"; this.render();
      }
      return;
    }
    if (action === "function-mode") {
      this.functionMode = button.dataset.mode; this.render(); return;
    }
    if (action === "open-capability") {
      this.category = button.dataset.capability;
      this.functionMode = "all"; this.discoveryGroup = "read_only";
      this.attribute = "";
      this.controlAction = "";
      this.step = 2; this.render(); return;
    }
    if (action === "select-attribute") {
      this.identityOperation = ""; this.identityExecution = null;
      this.category = button.dataset.capability;
      this.attribute = button.dataset.attribute;
      this.controlAction = "";
      this.step = 3; this.readRoutes = []; this.readChoice = ""; this.readDraft = ""; this.readActive = "";
      this.loading = true; this.error = ""; this.render();
      try { await this._readRoutes(); }
      catch (err) { this.error = String(err.message || err); }
      finally { this.loading = false; this.render(); } return;
    }
    if (action === "select-control") {
      this.identityOperation = ""; this.identityExecution = null;
      this.category = button.dataset.capability;
      this.controlCapability = button.dataset.capability;
      this.controlAction = button.dataset.control;
      this.attribute = "";
      this.step = 3; this.controlRoutes = []; this.controlChoice = ""; this.controlRequirement = "";
      this.loading = true; this.error = ""; this.render();
      try { await this._controlRoutes(); }
      catch(err) { this.error = String(err.message || err); }
      finally { this.loading = false; this.render(); } return;
    }
    const readRoute = this.shadowRoot.getElementById("read-route")?.value || this.readChoice;
    const controlRoute = this.shadowRoot.getElementById("control-route")?.value || this.controlChoice;
    const readTemplate = this.initialReadRoute;
    const newAttributeTemplate = this.initialNewAttribute;
    const controlParameters = this.shadowRoot.getElementById("control-parameters")?.value || "{}";
    const approved = this.shadowRoot.getElementById("control-approval")?.checked === true;
    const approvalGroup = this.controlRoutes.find(r=>r.id===controlRoute)?.approval_group;
    const controlTemplate = this.initialControlRoute;
    const route = this.shadowRoot.getElementById("route")?.value;
    // Capture edits BEFORE re-render: otherwise the textarea is reset and a
    // custom request silently loses its parameters or entire definition.
    const rawParameters = this.shadowRoot.getElementById("parameters")?.value || "{}";
    if (action === "identity-submit" || action === "identity-save") {
      this.identityQuery = this.shadowRoot.getElementById("identity-query")?.value || "";
      this.identityVariables = this.shadowRoot.getElementById("identity-variables")?.value || "{}";
    }
    const rawDefinition = this.shadowRoot.getElementById("definition")?.value || "";
    this.loading = true; this.error = ""; this.render();
    try {
      if (action === "refresh") {
        await this._load(); return;
      }
      if (action === "review-normal") {
        const command = this.unresolvedCommands().find(row=>row.command_id===button.dataset.command);
        if (!command) throw new Error("No unresolved command");
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
      } else if (action === "identity-save") {
        this.lastResult = await this.api("save_identity_draft", {...this.selection, operation:this.identityOperation,
          query:this.identityQuery, variables:JSON.parse(this.identityVariables)});
      } else if (action === "identity-submit") {
        const args = {...this.selection, operation:this.identityOperation};
        if (this.identityOperation.startsWith("graphql.")) {
          args.query = this.identityQuery;
          args.variables = JSON.parse(this.identityVariables);
        }
        const result = await this.api("test_identity_operation", args);
        this.identityExecution = result.execution || result;
        this.lastResult = result; this.step = 3;
      } else if (action === "family-test" || action === "family-full-test") {
        const car = this.entries.find(e=>e.entry_id===this.selected)
          ?.vehicles.find(v=>v.vin===this.vin);
        const family = this.apiFamily === "vehicle" || this.apiFamily === "all"
          ? car?.api_family || "cariad" : this.apiFamily;
        this.lastResult = await this.api("test_family_reads", {...this.selection, family, full:action==="family-full-test"});
      } else if (action === "control-add") {
        this.lastResult = await this.api("add_route", {
          ...this.selection, route: this.definitionValue("control", controlTemplate, {parameter_bindings:null})
        });
        this.controlChoice = this.lastResult.operation || this.controlChoice;
      } else if (action === "control-test") {
        if (this.pending || this.capabilityBlocked(this.controlCapability)) throw new Error("Resolve the previous command for this capability first");
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
      } else if (action === "read-new") {
        const definition = this.definitionValue("new-attribute", newAttributeTemplate, {conversion:null});
        this.lastResult = await this.api("attribute_add", {...this.selection, definition});
        this.attribute = definition.attribute;
        this.category = definition.attribute_definition.capability;
        this.inventoryFilter = "all";
        this.controlAction = "";
        this.step = 3;
      } else if (action === "read-add") {
        this.lastResult = await this.api("attribute_add", {...this.selection,
          definition: this.definitionValue("read", readTemplate, {capture_path:null,conversion:null})});
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
      if (["test","read-test","control-test","family-test","family-full-test","identity-submit"].includes(action)) {
        await this._apiResults();
        if(action==="read-test" && this.readRoutes.some(r=>r.id===readRoute)) this.readChoice=readRoute;
        if(action==="control-test" && this.controlRoutes.some(r=>r.id===controlRoute)) this.controlChoice=controlRoute;
      }
      if (action==="read-add" && this.readRoutes.some(r=>r.id===this.lastResult.operation)) this.readChoice=this.lastResult.operation;
      if (action==="control-add" && this.controlRoutes.some(r=>r.id===this.lastResult.operation)) this.controlChoice=this.lastResult.operation;
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

  definitionKey(id, template) {
    return JSON.stringify([id, this.selected, this.vin, template]);
  }

  definitionFields(id, template, optional = {}) {
    const fields = {...optional, ...JSON.parse(template)};
    const key = this.definitionKey(id, template);
    return Object.entries(fields).map(([field,value]) => {
      const simple = typeof value === "string" || field === "capture_path";
      const optionalField = Object.hasOwn(optional, field);
      const initial = optionalField && value == null ? "" : simple ? value : JSON.stringify(value, null, 2);
      const current = this.definitionEdits.get(key + ":" + field) ?? initial;
      const attrs = `data-definition="${escapeHTML(key)}" data-field="${escapeHTML(field)}"`;
      const label = `<label>${escapeHTML(field.replaceAll("_"," "))}${optionalField?" (optional)":""}</label>`;
      return simple
        ? `<div class="definition-row">${label}<input ${attrs} type="text" value="${escapeHTML(current)}" spellcheck="false"></div>`
        : `<details><summary>${escapeHTML(field.replaceAll("_"," "))}${optionalField?" (optional)":""}</summary><textarea ${attrs} rows="4" spellcheck="false">${escapeHTML(current)}</textarea></details>`;
    }).join("");
  }

  definitionValue(id, template, optional = {}) {
    const fields = {...optional, ...JSON.parse(template)};
    const key = this.definitionKey(id, template);
    const result = {};
    for (const [field,value] of Object.entries(fields)) {
      const edited = this.definitionEdits.get(key + ":" + field);
      if (edited === undefined) {
        if (!Object.hasOwn(optional, field) || value != null) result[field] = value;
      } else if (Object.hasOwn(optional, field) && !edited.trim()) {
        continue;
      } else if (typeof value === "string" || field === "capture_path") {
        result[field] = edited;
      } else {
        try { result[field] = JSON.parse(edited); }
        catch { throw new Error("Invalid JSON in " + field); }
      }
    }
    return result;
  }

  get initialControlRoute() {
    const capability = this.controlCapability || "access";
    const action = this.controlAction || "lock";
    const selected = this.controlRoutes.find(r=>r.id===this.controlChoice);
    const body = selected && Object.hasOwn(selected,"request_body") ? selected.request_body :
      capability==="access" && ["lock","unlock"].includes(action) ? {spin:"{SPIN}"} : null;
    return JSON.stringify({
      id:"user."+capability+"."+action+".alternative",
      capability, aspect:action, family:selected?.family || "cariad", method:selected?.method || "POST",
      path:selected?.path || "/vehicle/v1/vehicles/{VIN}/"+capability+"/"+action,
      variables:selected?.method==="PUT"?{}:selected?.request_variables||{}, body:selected?.method==="PUT"?null:body,
      ...(selected?.method==="PUT"?{handler:selected.handler||selected.id}:{}),
      ...(selected?.method!=="PUT"&&Object.keys(selected?.parameter_bindings||{}).length?{parameter_bindings:selected.parameter_bindings}:{}),
      description:"Reviewed experimental command template"
    },null,2);
  }

  get initialNewAttribute() {
    return JSON.stringify({id:"user.read.example_pressure", attribute:"user.attribute.example_pressure",
      family:"cariad", method:"GET", path:"/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs=example",
      response_path:"/example/pressure", capture_path:"/example/carCapturedTimestamp",
      attribute_definition:{id:"user.attribute.example_pressure", capability:"example", name:"Example pressure",
        type:"number", unit:"bar", device_class:"pressure", state_class:"measurement", precision:1}}, null, 2);
  }

  get initialReadRoute() {
    const entry = (this.capabilityStatus.rows || []).find(
      row => row.attribute === this.attribute && row.entity_key);
    const selected = this.readRoutes.find(r=>r.id===this.readChoice);
    const source = selected?.kind === "shared_batch"
      ? this.readRoutes.find(r=>r.kind==="targeted_job" && r.family===selected.family) || selected : selected;
    return JSON.stringify({id:"user.read.new_mapping", attribute:this.attribute,
      family:source?.family || "cariad", method:"GET",
      path:source?.path || "",
      response_path:source?.response_paths?.[0] || (entry?.path !== "-" ? entry?.path || "" : ""),
      ...(source?.capture_path ? {capture_path:source.capture_path} : {}),
      ...(source?.conversion ? {conversion:source.conversion} : {})}, null, 2);
  }

  responseInspector(operation, execution=null) {
    if (!operation) return "";
    const saved = this.apiHistory.find(r=>r.operation===operation);
    const detail = execution || this.engineeringHistory.find(r=>r.operation===operation && (!saved || r.at===saved.at));
    const json = value=>escapeHTML(JSON.stringify(value,null,2));
    if(!detail) return saved?`<h3>Response · restricted historical evidence</h3><pre>${json(saved.preview)}</pre>
      <p>Full request/response was not retained. Never repeat a vehicle command just to obtain evidence.</p>`:
      "<p>No execution recorded for this route.</p>";
    return `<div class="callout"><b>HTTP ${escapeHTML(detail.http_status??"—")} · ${escapeHTML(this.localTime(detail.at))}</b>
      <h3>Request sent</h3>
      ${detail.request?`<pre style="max-height:none;user-select:text">${json(detail.request.payload)}</pre>`:"<p>Actual request was not recorded for this execution.</p>"}
      <h3>${detail.operation==="graphql.inventory.vehicleList"?"Response received · selected vehicle only":"Response received"}</h3>
      <pre style="max-height:none;user-select:text">${json(detail.payload)}</pre>
      <p class="helper">Masked JSON · ${detail.truncated||detail.request?.truncated?"Size limit reached; partial evidence.":"Within local inspection limits."} ${detail.operation==="graphql.inventory.vehicleList"?"Read-only inventory query; other vehicles excluded.":"HTTP acceptance is not physical confirmation."}</p>
    </div>`;
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
    const entityLinks = coverage.entity_links || [];
    const selectedEntity = entityLinks.find(r=>(r.entity_ids||[]).includes(this.entityFilter));
    const entityMatches = r => !selectedEntity || (r.entity_ids||[]).includes(this.entityFilter);
    const operationMatches = o => !selectedEntity || selectedEntity.operations.includes(o.operation) || (o.mappings||[]).some(entityMatches);
    const operations = (coverage.operations || []).filter(o => (family === "all" || o.family === family) && operationMatches(o));
    const matchesSearch = value => !this.searchText || JSON.stringify(value).toLowerCase().includes(this.searchText.toLowerCase());
    const visibleOperations = operations.filter(o => matchesSearch(o) &&
      (!this.focusOperation || o.operation===this.focusOperation) &&
      (this.operationMethod === "all" || o.method === this.operationMethod) &&
      (this.operationFilter === "all" ||
       this.operationFilter === "tested" && o.tested ||
       this.operationFilter === "untested" && !o.tested && !o.reference_only ||
       this.operationFilter === "active" && o.active ||
       this.operationFilter === "attention" && (o.attention || []).length ||
       this.operationFilter === "historical" && o.reference_only));
    const findings = coverage.findings || [];
    const projection = coverage.account_entity_projection || {};
    const filteredRows = rows.filter(r => (family === "all" || r.api_family === family) && (!selectedEntity || entityMatches(r) || (!r.entity_key && selectedEntity.operations.includes(r.operation))));
    const attributes = filteredRows.filter(r => r.entity_key &&
      ["v3_live_evidence","v2_attribute_reference","local_attribute_definition"].includes(r.source));
    const controls = filteredRows.filter(r => r.source === "v2_control_reference");
    const controlActions = (coverage.control_actions || []).filter(r =>
      (family === "all" || r.api_family === family) && entityMatches(r));
    const identityOps = (coverage.operations || []).filter(o=>o.read_only && (o.capabilities||[]).includes("vehicle_identity") && operationMatches(o));
    const capabilityNames = [...new Set([...attributes,...controls,...controlActions].map(r => r.capability).concat(identityOps.length?["vehicle_identity"]:[], selectedEntity?.capabilities||[]))].filter(cap=>!selectedEntity||selectedEntity.capabilities.includes(cap)).sort();
    if (capabilityNames.length && !capabilityNames.includes(this.category) && this.step!==3) this.category=capabilityNames[0];
    const readable = attributes.filter(r => ["verified","readable_but_stale"].includes(r.status));
    const visibleAttributes = attributes.filter(r => matchesSearch(r) && (this.searchText || r.capability === this.category) &&
      (this.inventoryFilter !== "available" || ["verified","readable_but_stale"].includes(r.status)));
    const chosen = this.readRoutes.find(r => r.id === this.readChoice);
    const activeRoute = this.controlAction ? this.controlChoice :
      this.attribute ? this.readChoice : "";
    const records = (this.apiHistory || []).filter(r =>
      (family === "all" || r.family === family) && (!selectedEntity || selectedEntity.operations.includes(r.operation)));
    const lastSelectedResult = records.find(r=>r.operation===activeRoute);
    const applicableFamily = family === "graphql" || (["cariad","mbb"].includes(vehicleFamily) && (family === "all" || family === vehicleFamily));
    const selectedControl = this.controlRoutes.find(r=>r.id===this.controlChoice);
    const group = selectedControl?.approval_group;
    const groupActions = controlActions.filter(r => r.capability === this.category &&
      (this.discoveryGroup === "read_only" || (r.approval_groups || []).includes(this.discoveryGroup)));
    const freshCount = readable.filter(r=>r.status==="verified").length;
    const staleCount = readable.length-freshCount;
    const enabledCount = controlActions.filter(r=>r.enabled).length;
    const verifiedCount = controlActions.filter(r=>r.physical_evidence==="local_verified").length;
    const selectedCapabilityEntities = entityLinks.filter(link=>link.capabilities.includes(this.category) && entityMatches(link));
    const selectedAttribute = attributes.find(r=>r.attribute===this.attribute);
    const selectedDomain = domainName(this.controlAction?this.controlCapability:this.category);
    const canActivateRead = chosen?.result === "verified" ||
      ((chosen?.family === "mbb" || chosen?.allow_last_known) && chosen?.result === "readable_but_stale");
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
        .cap-card .subline{line-height:1.45;margin-top:5px}
        .state{display:inline-flex;align-items:center;border-radius:6px;padding:3px 8px;font-size:12px;font-weight:650;background:var(--secondary-background-color,#eee);white-space:nowrap}
        .state.good{color:var(--success-color,#237647)} .state.warn{color:var(--warning-color,#a36100)} .state.bad{color:var(--error-color,#c62828)}
        .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}.metrics .card{padding:16px}.metrics .stat{font-size:26px}.metrics .summary{margin-top:4px}
        .section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.section-head h2{margin:0}.cap-card:hover{border-color:var(--primary-color)}
        .cap-card .eyeline{justify-content:space-between}.cap-card .stat{font-size:22px}.cap-card .subline{font-size:13px}.cap-card b{font-size:16px}
        .function-tabs{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}.function-tabs button.current{border-color:var(--primary-color);color:var(--primary-color)}
        .compact{padding:14px 18px}.muted{color:var(--secondary-text-color)}.finding{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 0;border-top:1px solid var(--divider-color)}
        .steps{position:sticky;top:0;z-index:2;background:var(--primary-background-color);padding:8px 0}.steps button{text-align:center;min-width:100px}.steps button.current{background:var(--card-background-color);color:var(--primary-color)}
        @media(max-width:780px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.finding{align-items:flex-start}.steps{position:static}.steps button{min-width:40%}}
        .eyeline{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
        .callout{background:var(--secondary-background-color,#f8fafc);padding:15px;border-radius:9px}
        .attribute-row{display:flex;justify-content:space-between;align-items:center;gap:16px;
          border-top:1px solid var(--divider-color,#e2e8f0);padding:11px 0}
        .attribute-row button{text-align:center;flex:0 0 auto;overflow-wrap:anywhere}
        .helper{font-size:var(--ha-font-size-m,14px);margin:9px 0;color:var(--secondary-text-color,#64748b)}
        .coverage-table{overflow-x:auto}.entity-link{font-size:12px;max-width:100%;overflow-wrap:anywhere;text-align:left;white-space:normal;padding:4px 7px;margin:2px;color:var(--primary-color)}
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
        .definition-row{display:grid;grid-template-columns:minmax(100px,1fr) minmax(0,3fr);align-items:center;gap:8px;margin:6px 0}
        .definition-row label{margin:0}
        @media(max-width:600px){.definition-row{grid-template-columns:1fr}}
        .family-select{width:280px;max-width:100%}
        @media(max-width:780px){.attribute-row{align-items:stretch;flex-direction:column}.attribute-row button{width:100%}}
        @media(max-width:780px){main{padding:18px 12px}.grid,.cards,.cap-grid{grid-template-columns:1fr}h1{font-size:21px}}
      </style>
      <main>
        <div class="top">
          <div><div class="eyebrow">Audi Connect · V3</div>
            <h1>Audi Engineering Dashboard</h1>
            <p>Explore your Audi, validate functions and manage API mappings.</p></div>
          <button data-action="refresh" ${this.loading?"disabled":""}>↻ Refresh</button>
        </div>
        <div class="toolbar">
          <div class="tool"><label>Integration</label>
            <select id="entry" ${this.loading?"disabled":""}>${this.entries.map((v) => `<option value="${escapeHTML(v.entry_id)}" ${v.entry_id===this.selected?"selected":""}>Audi Connect / ${escapeHTML(v.entry_id.slice(0,8))}</option>`).join("")}</select></div>
          <div class="tool"><label>Vehicle</label><select id="vehicle" ${this.loading?"disabled":""}>
            ${(item?.vehicles||[]).map((v)=>`<option value="${escapeHTML(v.vin)}" ${v.vin===this.vin?"selected":""}>${escapeHTML([v.name,v.model].filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).join(" — ")||"Audi vehicle")}${!v.model&&item.vehicles.length>1?` · …${escapeHTML(v.vin.slice(-4))}`:""}</option>`).join("")}
          </select></div>
          <div class="tool family-select"><label for="api-family">API family <span class="muted">· advanced</span></label>
            <select id="api-family" ${this.loading?"disabled":""}>
              <option value="vehicle" ${this.apiFamily==="vehicle"?"selected":""}>This vehicle · ${escapeHTML(vehicleFamily.toUpperCase())}</option>
              <option value="cariad" ${this.apiFamily==="cariad"?"selected":""}>CARIAD · modern</option>
              <option value="mbb" ${this.apiFamily==="mbb"?"selected":""}>MBB · legacy</option>
              <option value="graphql" ${this.apiFamily==="graphql"?"selected":""}>GraphQL</option>
              <option value="all" ${this.apiFamily==="all"?"selected":""}>All API families</option>
            </select></div>
        </div>
        <div class="toolbar" style="padding-top:0"><label for="global-search">Search capabilities, entities and API fields</label><input id="global-search" type="search" value="${escapeHTML(this.searchText)}" placeholder="e.g. model, charging, media.longName"></div>
        <div class="toolbar"><label for="entity-filter">Home Assistant entity</label><select id="entity-filter"><option value="">All entities</option>${entityLinks.flatMap(link=>link.entity_ids.map(id=>`<option value="${escapeHTML(id)}" ${this.entityFilter===id?"selected":""}>${escapeHTML(id)}</option>`)).join("")}</select>${selectedEntity?`<p class="helper">${escapeHTML(selectedEntity.capabilities.map(domainName).join(" · ")||"No capability mapping declared")} · ${selectedEntity.operations.length} linked API operations</p>`:""}</div>
        <div class="steps">
          <button data-action="step-1" class="${this.step===1?"current":""}">Overview</button>
          <button data-action="step-2" class="${this.step===2?"current":""}">Capabilities</button>
          <button data-action="step-3" class="${this.step===3?"current":""}">Configure & test</button>
          <button data-action="step-4" class="${this.step===4?"current":""}">API Log</button>
        </div>
        ${this.error?`<div class="error">${escapeHTML(this.error)}</div>`:""}
        ${car&&this.pending?`<section class="card" style="margin-bottom:18px">
          <div class="warn"><b>Pending vehicle control: ${escapeHTML(this.pending.capability)} · ${escapeHTML(this.pending.action)}</b>
            <p>Review the physical result before starting another discovery action.</p>
            <div class="actions">
              <button data-action="confirm-worked">Verified working</button>
              <button data-action="confirm-failed">Did not work</button>
              <button data-action="confirm-uncertain">Not sure</button>
            </div>
          </div>
        </section>`:""}
        ${car?this.unresolvedCommands().map(command=>`<section class="card warn" style="margin-bottom:18px"><b>${escapeHTML(friendly(command.capability))} · ${this.reviewRequired(command)?"review required":"last command outcome uncertain"}</b><p>Previous command: <b>${escapeHTML(command.operation)}</b> · ${escapeHTML(command.state)} ${command.http_status?"· HTTP "+escapeHTML(command.http_status):""} · ${escapeHTML(this.localTime(command.started_at*1000))}</p><p>Other capabilities remain available. Read-only polling and query experiments remain available. ${this.reviewRequired(command)?"Inspect the actual vehicle before acknowledging uncertainty.":"Check the vehicle; you can retry explicitly after the short cooldown. No review required."} No command is replayed or marked successful.</p><button data-action="review-normal" data-command="${escapeHTML(command.command_id)}" ${this.loading?"disabled":""}>${this.reviewRequired(command)?"I inspected the vehicle — acknowledge uncertainty":"Dismiss warning after checking vehicle"}</button></section>`).join(""):""}
        ${!car?`<div class="card">No V3 vehicle loaded. Enable V3 and confirm Audi authentication before testing.</div>`: `
          <section style="display:${this.step===1?"block":"none"}" data-view="overview">
            <div class="metrics">
              <div class="card"><div class="eyebrow">Cloud connection</div><div class="stat">${item.poll_success?"Connected":"Unknown"}</div><div class="summary">${escapeHTML(item.poll_success?new Date(item.poll_success).toLocaleString():"No successful poll")}</div></div>
              <div class="card"><div class="eyebrow">Readable data</div><div class="stat">${readable.length}</div><div class="summary">${freshCount} fresh · ${staleCount} last known</div></div>
              <div class="card"><div class="eyebrow">Enabled controls</div><div class="stat">${enabledCount}</div><div class="summary">${verifiedCount} locally verified</div></div>
              <div class="card"><div class="eyebrow">Needs review</div><div class="stat">${findings.length}</div><div class="summary"><button data-action="step-4">View evidence</button></div></div>
            </div>
            <div class="section-head"><h2>Capabilities</h2><button data-action="step-2">Browse functions</button></div>
            <div class="cap-grid">${capabilityNames.map(cap=>{
              const ar=attributes.filter(r=>r.capability===cap);
              const rr=ar.filter(r=>["verified","readable_but_stale"].includes(r.status));
              const ca=controlActions.filter(r=>r.capability===cap);
              const issues=findings.filter(r=>r.capability===cap).length;
              return `<button class="cap-card card" data-action="open-capability" data-capability="${escapeHTML(cap)}">
                <div class="eyeline"><b>${escapeHTML(domainName(cap))}</b><span>›</span></div>
                <div class="stat">${rr.length} <span class="muted" style="font-size:13px">/ ${ar.length} readable</span></div>
                <div class="subline">${ca.filter(r=>r.enabled).length} / ${ca.length} controls enabled</div>
                <div class="subline">${issues?pill("mapping_pending",issues+" to review"):pill("neutral","No reported findings")}</div>
              </button>`;
            }).join("")}</div>
            <section class="card" style="margin:18px 0">
              <div class="section-head"><h2>Next actions</h2><button data-action="step-4">All findings</button></div>
              ${findings.slice(0,3).map((f,i)=>`<div class="finding"><div><b>${escapeHTML(friendly(f.reason))}</b><div class="subline">${escapeHTML(f.capability?domainName(f.capability):"Vehicle")}</div></div><button data-action="inspect-finding" data-index="${i}">Review</button></div>`).join("")||"<p>No findings reported in this snapshot.</p>"}
            </section>
            <section class="card compact"><div class="section-head"><h2>Home Assistant</h2><button data-action="step-4">Details</button></div><div>${escapeHTML(projection.registered??"—")} registered · ${escapeHTML(projection.projected??"—")} projected <span class="muted">· account scope</span></div></section>
          </section>
          <section class="card" data-view="evidence" style="margin-bottom:18px;display:${this.step===4?"block":"none"}">
            <div class="section-head"><h2>API Log</h2><span class="muted">${escapeHTML(family.toUpperCase())}</span></div>
            <details><summary>All findings · ${findings.length}</summary>${findings.map((f,i)=>`<div class="finding"><div><b>${escapeHTML(friendly(f.reason))}</b><div class="subline">${escapeHTML(f.operation||f.attribute||"Vehicle")}</div></div><button data-action="inspect-finding" data-index="${i}">Review</button></div>`).join("")}</details>
            <details><summary>Home Assistant projection & historical inventory</summary><p>${Object.entries(projection.counts||{}).map(([k,v])=>escapeHTML(friendly(k))+": "+escapeHTML(v)).join(" · ")}</p><p>${escapeHTML(counts.v2_attribute_inventory??0)} historical attributes · ${escapeHTML(counts.v2_control_inventory??0)} historical controls · ${escapeHTML(counts.observed_jobs??0)} observed jobs</p></details>
            <div style="margin-top:20px"></div>
            <h2>API operations · validation matrix</h2>
            ${this.focusOperation?`<div class="callout">Focused on ${escapeHTML(this.focusOperation)} <button data-action="step-4">Show all operations</button></div>`:""}
            <p>Tested, active, schema validity and physical confirmation are independent. HTTP 2xx/207 alone is not proof of a working command or complete mapping.</p>
            <div class="line">
              <label>Evidence <select id="operation-filter">${["all","tested","untested","active","attention","historical"].map(v=>`<option value="${v}" ${this.operationFilter===v?"selected":""}>${v}</option>`).join("")}</select></label>
              <label>Method <select id="operation-method">${["all","GET","POST","PUT","DELETE"].map(v=>`<option value="${v}" ${this.operationMethod===v?"selected":""}>${v}</option>`).join("")}</select></label>
            </div>
            <p>${visibleOperations.length} matching / ${operations.length} operations · ${operations.filter(o=>o.tested).length} tested · ${operations.filter(o=>o.active).length} active · ${operations.filter(o=>o.reference_only).length} historical only</p>
            <div class="coverage-table"><table>
              <thead><tr><th>Operation / capability</th><th>Test & HTTP</th><th>Mapping / binding</th><th>Physical / attention</th></tr></thead>
              <tbody>${visibleOperations.map(o=>`<tr>
                <td><b>${escapeHTML(o.operation)}</b><div class="subline">${escapeHTML(o.family)} · ${escapeHTML(o.method)} · ${escapeHTML((o.capabilities||[]).join(", "))}</div><code>${escapeHTML(o.path||"")}</code></td>
                <td><b>${o.reference_only?"Historical only":o.tested?"Tested directly":o.job_evidence==="observed"?"Observed via batch":o.job_evidence==="not_observed"?"Requested; not observed":"Not tested"}</b><div class="subline">HTTP ${escapeHTML(o.http_status??"—")} · ${escapeHTML(o.transport||"unknown")} · ${escapeHTML(this.localTime(o.last_test))}</div></td>
                <td>Schema: ${escapeHTML(o.schema||"unknown")}
                  ${(o.mappings||[]).map(m=>`<div class="subline"><button data-action="${m.capability==="vehicle_identity"?"open-identity":"open-capability"}" data-capability="${escapeHTML(m.capability)}">${escapeHTML(m.capability)}</button> · ${this.entityLinks(m.entity_ids)||escapeHTML(m.entity_key||"No published entity")}<br><code>${escapeHTML(m.field||"")}</code></div>`).join("")}
                  ${(o.graphql_errors||[]).map(err=>`<div class="warn">${escapeHTML(err.code)} · ${escapeHTML(err.field)} ${escapeHTML(err.reason||"")}</div>`).join("")}
                  ${o.auth_context?`<div class="subline">${escapeHTML(o.auth_context.provider)} · ${escapeHTML(o.auth_context.role)} · ${escapeHTML(o.auth_context.audience)} · ${escapeHTML(o.auth_context.age_minutes??"?")} min</div>`:""}
                  ${o.read_only&&(o.capabilities||[]).includes("vehicle_identity")?`<button data-action="identity-test" data-operation="${escapeHTML(o.operation)}">Test read-only</button>`:""}<div class="subline">${o.active?"ACTIVE":"Inactive"} · ${escapeHTML(o.applicability||"unknown")}</div>
                  ${(o.fields||[]).length?`<details><summary>${o.fields.length} response fields · ${o.fields_truncated===true?"truncated":o.fields_truncated===false?"within sample limits":"coverage unknown"}</summary>${o.fields.map(f=>`<div class="subline"><code>${escapeHTML(f.path)}</code> · ${escapeHTML(f.type)} · ${escapeHTML(f.quality)} · ${escapeHTML(f.mapping)} ${escapeHTML((f.attributes||[]).join(", "))}</div>`).join("")}</details>`:""}</td>
                <td>Physical: ${escapeHTML(o.physical||"not verified")}<div class="subline">${escapeHTML(o.last_command_state||"")} ${escapeHTML(o.backend_result||"")}</div>
                  <div class="subline">${escapeHTML((o.attention||[]).join(" · "))}</div></td>
              </tr>`).join("") || '<tr><td colspan="4">No matching operations.</td></tr>'}</tbody>
            </table></div>
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
                  <td><code>${escapeHTML(r.attribute)}</code><div class="subline">${escapeHTML(r.platform||"")} · ${escapeHTML(r.value_type||"")} ${escapeHTML(r.semantic_issue||"")}</div></td>
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
          <section class="card" data-view="capabilities" style="margin-bottom:18px;display:${this.step===2?"block":"none"}">
            <div class="section-head"><h2>${escapeHTML(this.category==="vehicle_identity"?"Vehicle Identity":domainName(this.category))}</h2><button data-action="step-1">‹ Overview</button></div>
            <p>Select a function to inspect or test its route.</p>
            <label>Capability domain</label>
            <select id="category" ${this.loading?"disabled":""}>${capabilityNames.map(c=>`<option value="${escapeHTML(c)}" ${this.category===c?"selected":""}>${escapeHTML(c==="vehicle_identity"?"Vehicle Identity":domainName(c))}</option>`).join("")}</select>
            ${selectedCapabilityEntities.length?`<div class="callout"><b>Home Assistant entities</b><div>${this.entityLinks(selectedCapabilityEntities.flatMap(l=>l.entity_ids))}</div></div>`:""}
            ${this.category==="vehicle_identity"?`<div class="card"><h2>Vehicle Identity</h2>${[["Manufacturer model",["manufacturer_model","garage_model","garage_car_model"]],["Model family",["model_family"]],["Model year",["model_year","garage_model_year","garage_model_year_alt"]],["OEM drivetrain",["drive_train"]],["Vehicle image",["vehicle_image"]]].map(([name,keys])=>{const linked=identityOps.filter(o=>(o.mappings||[]).some(m=>keys.includes(m.attribute)));const mappings=linked.flatMap(o=>o.mappings.filter(m=>keys.includes(m.attribute)));return `<div class="attribute-row"><div><b>${escapeHTML(name)}</b><div class="subline">${mappings.some(m=>m.status==="observed")?"Observed":"Not observed"} · ${linked.length} sources</div></div><div>${linked.length?`<button data-action="identity-test" data-operation="${escapeHTML(linked[0].operation)}">Configure &amp; test</button> <button data-action="identity-evidence" data-operation="${escapeHTML(linked[0].operation)}">API Log</button>`:""}</div></div>`}).join("")}</div>`:""}
            <div class="function-tabs">${[["all","All functions"],["data","Data"],["controls","Controls"]].map(([mode,label])=>`<button data-action="function-mode" data-mode="${mode}" class="${this.functionMode===mode?"current":""}">${label}</button>`).join("")}</div>
            <div style="display:${this.functionMode==="controls"?"none":"block"}">
            <div class="toolbar">
              <div class="tool"><label>Show attributes</label>
                <select id="inventory-filter">
                  <option value="available" ${this.inventoryFilter==="available"?"selected":""}>Observed on this vehicle</option>
                  <option value="all" ${this.inventoryFilter==="all"?"selected":""}>All historical and local attributes</option>
                </select>
              </div>
            </div>
            <h2>Vehicle data <span class="muted" style="font-size:14px">· ${visibleAttributes.length} functions</span></h2>
            <details><summary>Add a vehicle-local sensor / capability group</summary>
              <p>Illustrative JSON only: replace the example job and paths with an observed Audi response. Save creates a draft, not an active sensor. Test and activate explicitly.</p>
              ${this.definitionFields("new-attribute", this.initialNewAttribute, {conversion:null})}
              <button data-action="read-new" ${this.loading?"disabled":""}>Save local attribute</button>
            </details>
            ${visibleAttributes.map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.metadata?.name||friendly(r.entity_key))}</b>
                <div class="subline">${pill(r.status)} ${r.selected?pill("neutral","Active"):""}</div><div class="subline">${this.entityLinks(r.entity_ids)||"No registered entity"}</div></div>
              <button data-action="select-attribute" data-capability="${escapeHTML(r.capability)}"
                data-attribute="${escapeHTML(r.attribute)}">Inspect & test ›</button>
            </div>`).join("") || '<p>No observed attributes in this domain. Change the filter to show the complete historical catalog.</p>'}
            </div>
            <div style="display:${this.functionMode==="data"?"none":"block"}">
            <h2 style="margin-top:20px">Vehicle controls <span class="muted" style="font-size:14px">· ${groupActions.length} functions</span></h2>
            <div class="function-tabs">${[["read_only","All controls"],["non_spin","Without S-PIN"],["spin","With S-PIN"]].map(([mode,label])=>`<button data-action="discovery-group" data-group="${mode}" class="${this.discoveryGroup===mode?"current":""}">${label}</button>`).join("")}</div>
            <p>Wake-up, Climate ON/OFF, Lock/Unlock, charging and other vehicle actions are NEVER automatically tested. Select a control to test one API route while at the car.</p>
            ${groupActions.map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(actionName(r.capability,r.action))}</b>
                <div class="subline">${pill(r.status,r.physical_evidence==="local_verified"?"Verified on vehicle":r.status==="verified"?"Previously verified":friendly(r.status))} ${r.enabled?pill("neutral","Enabled"):""} · ${r.candidate_count} routes</div><div class="subline">${this.entityLinks(r.entity_ids)||"No registered entity"}</div></div>
              <button data-action="select-control" data-capability="${escapeHTML(r.capability)}"
                data-control="${escapeHTML(r.action)}" ${!r.candidate_count?"disabled":""}>Inspect & test ›</button>
            </div>`).join("")||'<p>No supported control routes for this vehicle API family.</p>'}
            <details><summary>Historical controls not yet migrated</summary>
            ${controls.filter(r=>r.capability===this.category).map(r=>`<div class="attribute-row">
              <div><b>${escapeHTML(r.attribute.replaceAll("_"," "))}</b>
                <div class="subline">${escapeHTML(r.status)} · ${escapeHTML(r.api_family)}</div></div>
              <span class="muted">Historical reference only</span>
            </div>`).join("") || '<p>No additional historical control references in this domain.</p>'}</details>
            </div>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3&&this.attribute?"block":"none"}">
            <div class="section-head"><div><div class="eyebrow">${escapeHTML(selectedDomain)} · Read-only data</div><h2>${escapeHTML(selectedAttribute?.metadata?.name||friendly(selectedAttribute?.entity_key||this.attribute))}</h2></div><button data-action="step-2">‹ Capabilities</button></div>
            <p>Test the selected read-only route, then activate it for polling if eligible.</p><div class="subline">HA entities: ${this.entityLinks(selectedAttribute?.entity_ids)||"No registered entity"}</div>
            <label>API route</label>
            <select id="read-route">${this.readRoutes.map(r=>`<option value="${escapeHTML(r.id)}" ${r.id===this.readChoice?"selected":""}>
              ${escapeHTML(r.family)} · ${escapeHTML(r.kind)} [${escapeHTML(r.result)}]</option>`).join("")}</select>
            <div class="callout" style="margin-top:13px">
              ${pill(chosen?.result)} ${this.readChoice&&this.readChoice===this.readActive?pill("neutral","Active for polling"):""} ${this.readChoice&&this.readChoice===this.readDraft?pill("neutral","Saved candidate"):""}
              <details><summary>Route details</summary><code>${escapeHTML(chosen?.path||"No mapped path yet")}</code><div class="helper">Active: ${escapeHTML(this.readActive||"none")} · Draft: ${escapeHTML(this.readDraft||"none")}</div></details>
            </div>
            <div class="actions">
              <button data-action="read-test" class="primary" ${!this.readChoice||this.loading?"disabled":""}>Test read-only GET</button>
              <button data-action="read-save" ${!this.readChoice||this.loading?"disabled":""}>Save candidate</button>
              <button data-action="read-activate" ${!canActivateRead||this.loading?"disabled":""}>Activate for polling</button>
              <button data-action="read-disable" ${!this.readActive||this.loading?"disabled":""}>Disable attribute</button>
            </div>
            <details style="margin-top:18px"><summary>Advanced · define another API path and response mapping</summary>
              <p>Only safe relative CARIAD GET paths. JSON definitions are for engineering cases; no credentials, tokens or external URLs.</p>
              ${this.definitionFields("read", this.initialReadRoute, {capture_path:null,conversion:null})}
              <button data-action="read-add" ${this.loading?"disabled":""}>Add custom read route</button>
            </details>
            <div class="callout" style="margin-top:18px">
              <b>Latest saved response for this route</b>
              <div>${escapeHTML(lastSelectedResult?.at||"Never executed")} · HTTP ${escapeHTML(lastSelectedResult?.http_status??"-")} · ${escapeHTML(lastSelectedResult?.result||"not tested")}</div>
              ${this.step===3&&this.attribute&&!this.controlAction?this.responseInspector(activeRoute):""}
            </div>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===3&&this.controlAction?"block":"none"}">
            <div class="section-head"><div><div class="eyebrow">${escapeHTML(selectedDomain)} · Vehicle control</div><h2>${escapeHTML(actionName(this.controlCapability,this.controlAction))}</h2></div><button data-action="step-2">‹ Capabilities</button></div>
            <p>Test one command, confirm what happened on the car, then activate the verified route.</p>
            <div class="warn">Before testing: be physically present, understand the action, and verify the result on the vehicle or myAudi. ${escapeHTML(this.controlRequirement)}</div>
            <label for="control-route" style="margin-top:16px">API-family executor / route</label>
            <select id="control-route">${this.controlRoutes.map(r=>`<option value="${escapeHTML(r.id)}" ${this.controlChoice===r.id?"selected":""}>${escapeHTML(r.family.toUpperCase())} · ${escapeHTML(r.id)} [${escapeHTML(r.status)}]</option>`).join("")}</select>
            <div class="callout" style="margin-top:12px">
              ${pill(selectedControl?.status,selectedControl?.status==="worked"?"Physically verified":friendly(selectedControl?.status))} ${pill("neutral",selectedControl?.active?"Active":"Inactive")}
              <details><summary>Route details</summary><code>${escapeHTML(selectedControl?.path||"No route available")}</code></details>
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
              <button data-action="control-test" class="primary" ${!this.controlChoice||this.loading||this.pending||this.capabilityBlocked(this.controlCapability)||group==="unsupported"||(group==="spin"&&!this.spinConfigured)?"disabled":""}>Send one test command</button>
              <button data-action="control-select" ${this.loading||this.pending||selectedControl?.status!=="worked"||!selectedControl?.runtime_ready?"disabled":""}>Activate verified route</button>
              <button data-action="control-disable" ${this.loading||this.pending?"disabled":""}>Disable this control</button>
            </div>
            <details style="margin-top:18px">
              <summary>Advanced · Add an alternative command template</summary>
              <p>System variables: <code>{VIN}</code> is filled from this car. <code>{SPIN}</code> is filled securely from the configured Audi account, only for Access Lock/Unlock using <code>{"spin":"{SPIN}"}</code>. Do not enter or save a real S-PIN.</p>
              ${this.definitionFields("control", this.initialControlRoute, {parameter_bindings:null})}
              <div class="actions"><button data-action="control-add" ${this.loading||this.pending?"disabled":""}>Save alternative route · no command sent</button></div>
            </details>
            <div class="callout" style="margin-top:18px">
              <b>Last control execution</b>
              <div>${escapeHTML(lastSelectedResult?.at||"Never executed")} · HTTP ${escapeHTML(lastSelectedResult?.http_status??"-")} · ${escapeHTML(lastSelectedResult?.result||"not tested")}</div>
              ${this.step===3&&this.controlAction?`<h3>Home Assistant entities</h3>${this.entityLinks(controlActions.find(r=>r.capability===this.controlCapability&&r.action===this.controlAction)?.entity_ids)||"No registered entity"}${this.responseInspector(activeRoute)}`:""}
              <p>HTTP acceptance does not confirm the vehicle acted. Detailed response stays in local session memory; control bodies are not exported.</p>
            </div>
          </section>
          <section class="card" style="margin-bottom:18px;display:${this.step===4?"block":"none"}">
            <div class="eyebrow">Read-only discovery</div>
            <h2>Scan read-only functions · ${escapeHTML(family==="all"?vehicleFamily.toUpperCase():family.toUpperCase())}</h2>
            <p>${family==="graphql"?"Quick scan tests the original inventory. Full scan tests the reviewed inventory variants and image query. No vehicle commands or automatic activation.":"Quick scan uses the shared batch and a few targeted GETs. Full scan tries each distinct applicable reviewed GET route, including unmapped jobs, in batches of up to 12 calls. No vehicle commands, no automatic activation."}</p>
            ${!applicableFamily?'<div class="warn">This API family does not apply to the selected vehicle.</div>':""}
            <div class="actions"><button data-action="family-test" class="primary"
              ${this.loading||!applicableFamily?"disabled":""}>Quick scan</button>
              <button data-action="family-full-test" ${this.loading||!applicableFamily?"disabled":""}>Full read-only scan / continue</button></div>
            ${this.lastResult?.mode==="full"?`<p><b>${this.lastResult.request_count} requests · ${this.lastResult.eligible_routes} eligible routes · ${this.lastResult.remaining_routes.length} remaining</b> ${escapeHTML(this.lastResult.stopped||"Completed")}</p><details open><summary>Remaining and excluded routes</summary><pre>${escapeHTML(JSON.stringify({remaining:this.lastResult.remaining_routes,excluded:this.lastResult.excluded_routes},null,2))}</pre></details>`:""}
            <div class="helper">${escapeHTML(this.lastResult?.family?JSON.stringify(this.lastResult):"No manual family test in this session")}</div>
          </section>
          ${this.step===3&&!this.attribute&&!this.controlAction?`<section class="card" style="margin-bottom:18px">
            <div class="section-head"><h2>Configure &amp; test</h2><button data-action="step-2">‹ Capabilities</button></div>
            <label>Vehicle Identity · API operation<select id="identity-operation"><option value="">Choose a source</option>${identityOps.map(o=>`<option value="${escapeHTML(o.operation)}" ${this.identityOperation===o.operation?"selected":""}>${escapeHTML(o.operation)}</option>`).join("")}</select></label>
            ${this.identityOperation?`<p><b>${escapeHTML(identityOps.find(o=>o.operation===this.identityOperation)?.method)} ${escapeHTML(identityOps.find(o=>o.operation===this.identityOperation)?.path)}</b> · Read-only</p>
              ${this.identityOperation.startsWith("graphql.")?`<label>Query template<textarea id="identity-query" rows="10" spellcheck="false">${escapeHTML(this.identityQuery)}</textarea></label><label>Variables (JSON)<textarea id="identity-variables" rows="3" spellcheck="false">${escapeHTML(this.identityVariables)}</textarea></label>${this.capabilityStatus.identity_fixed_parameters?.[this.identityOperation]? `<p>myAudi web document tested using native Audi bearer authentication; not a web session replay.</p>`:""}`:"<p>Fixed read-only garage inventory GET.</p>"}
              <div class="actions"><button class="primary" data-action="identity-submit" ${this.loading?"disabled":""}>Submit</button>${this.identityOperation.startsWith("graphql.")?`<button data-action="identity-save" ${this.loading?"disabled":""}>Save local draft</button>`:""}<button data-action="identity-reset">Reset template</button><button data-action="identity-evidence" data-operation="${escapeHTML(this.identityOperation)}">API Log</button></div>
              <p class="helper">Experiments do not change active mappings. Edited GraphQL supports one userVehicles selection with vin, orderBy and renderPictures mediaTypes. No mutations, arbitrary hosts or directives.</p>
              ${this.identityExecution?this.responseInspector(this.identityOperation,this.identityExecution):this.responseInspector(this.identityOperation)}
              ${this.identityExecution?.fields?.length?`<details open><summary>Discovered fields · ${this.identityExecution.fields.length}</summary>${this.identityExecution.fields.map(f=>`<div class="subline"><code>${escapeHTML(f.path)}</code> · ${escapeHTML(f.type)}</div>`).join("")}</details>`:""}
              <h3>Linked capability · Vehicle Identity</h3>${(identityOps.find(o=>o.operation===this.identityOperation)?.mappings||[]).map(m=>`<div class="subline">${escapeHTML(m.name)} → ${this.entityLinks(m.entity_ids)||escapeHTML(m.entity_key)} · ${escapeHTML(m.status)}</div>`).join("")}`:"<p>Select an identity API operation above, or browse other capabilities.</p>"}
          </section>`:""}
          <section class="card" style="margin-bottom:18px;display:${this.step===4?"block":"none"}">
            <div class="eyebrow">Engineering / API evidence</div>
            <h2>Last result and response by API route</h2>
            <p>Inspect the latest masked JSON from existing requests, including command responses. Detailed responses are session-only; restricted diagnostics previews survive a restart.</p>
            ${this.step===4?[
              ...this.engineeringHistory.filter(r=>(family==="all"||r.family===family)&&(!selectedEntity||selectedEntity.operations.includes(r.template||r.operation))&&(!this.focusOperation||(r.template||r.operation)===this.focusOperation)).map(r=>({record:r,detail:r})),
              ...records.filter(r=>(!this.focusOperation||r.operation===this.focusOperation)&&!this.engineeringHistory.some(e=>e.operation===r.operation&&e.at===r.at)).map(r=>({record:r,detail:null}))
            ].map(({record:r,detail})=>`<details class="record" open>
              <summary>${escapeHTML(r.operation)} · HTTP ${escapeHTML(r.http_status??"-")} · <time datetime="${escapeHTML(r.at||"")}">${escapeHTML(this.localTime(r.at))}</time></summary>
              <div><b>${escapeHTML(r.family.toUpperCase())} · ${escapeHTML(r.method)}</b></div>
              ${(operations.find(o=>o.operation===(r.template||r.operation))?.mappings||[]).map(m=>`<div class="subline"><button data-action="${m.capability==="vehicle_identity"?"open-identity":"open-capability"}" data-capability="${escapeHTML(m.capability)}">${escapeHTML(m.capability)}</button> · ${this.entityLinks(m.entity_ids)||escapeHTML(m.entity_key||"No published entity")} · <code>${escapeHTML(m.field||"")}</code></div>`).join("")}
              ${detail?this.responseInspector(r.operation,detail):`<h3>Restricted historical response</h3><pre>${escapeHTML(JSON.stringify(r.preview,null,2))}</pre><p>Actual request and full response were not retained.</p>`}
            </details>`).join("")||'<p>No saved API results yet.</p>':""}
          </section>
          <p class="foot">Experimental mode. HTTP 200/202 confirms gateway acceptance, not vehicle action.
          Detailed engineering responses are local, temporary and masked. Only restricted previews are persisted. V2 remains available for rollback.</p>`}
      </main>`;
  }
}
customElements.define("audiconnect-v3-panel", AudiConnectV3Panel);

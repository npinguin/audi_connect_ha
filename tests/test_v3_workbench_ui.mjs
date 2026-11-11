import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
let Panel;
class FakeElement {
  attachShadow() {
    this.shadowRoot = {
      addEventListener() {}, innerHTML: "", getElementById() {return null;},
    };
    return this.shadowRoot;
  }
}
vm.runInNewContext(
  fs.readFileSync("custom_components/audiconnect/v3/frontend/panel.js", "utf8"),
  {HTMLElement: FakeElement, customElements: {define(name, klass) {
    assert.equal(name, "audiconnect-v3-panel"); Panel = klass;
  }}}
);
test("Save candidate survives route selection and rerender", async () => {
  const panel = new Panel();
  panel.selected = "entry"; panel.vin = "TESTVIN";
  panel.entries = [{entry_id: "entry", vehicles: [{
    vin: "TESTVIN", name: "Test Audi", model: "Q8",
    climate_state: "off", age_minutes: 5,
  }]}];
  const routes = [
    {id: "cariad.climate.status.batch", selected: true, outcome: "worked",
      family: "cariad", method: "GET", path: "/a"},
    {id: "cariad.climate.status.probe", selected: false, outcome: "untested",
      family: "cariad", method: "GET", path: "/b"},
  ];
  let saved = null, activated = false;
  panel.api = async (name, data) => {
    if (name === "routes") return {routes, draft_candidate: saved, history: []};
    if (name === "save_candidate") {
      saved = data.operation; return {saved, activated: false};
    }
    if (name === "select") {activated = true; return {selected: data.operation};}
    if (name === "status") return {counts: {}, rows: []};
    if (name === "list") return {integrations: panel.entries};
    throw Error("Unexpected WS operation " + name);
  };
  await panel._routes();
  await panel._change({target: {id: "route", value: routes[1].id}});
  panel.render();
  assert.match(panel.shadowRoot.innerHTML,
    /value="cariad\.climate\.status\.probe" selected/);
  panel.shadowRoot.getElementById = id => ({
    value: id === "route" ? panel.routeChoice : "{}",
  });
  await panel._click({target: {closest: () => ({dataset: {action: "save"}})}});
  assert.equal(saved, routes[1].id);
  assert.equal(activated, false);
  await panel._routes();
  assert.equal(panel.routeChoice, routes[1].id);
});

test("Workbench has three steps and keeps V2 backlog separate from verified attributes", async () => {
  const panel = new Panel();
  panel.step = 1;
  panel.entries = [{entry_id:"entry", vehicles:[{vin:"TESTVIN",name:"Audi",model:"Q8"}]}];
  panel.selected="entry"; panel.vin="TESTVIN";
  panel.capabilityStatus = {counts:{
    v2_attribute_inventory:109,v2_control_inventory:21,v3_verified_attributes:1,
  },rows:[
    {capability:"charging",aspect:"status",attribute:"stateOfCharge",
      entity_key:"state_of_charge",status:"verified",source:"v3_live_evidence",
      api_family:"cariad",path:"charging.batteryStatus.value.currentSOC_pct"},
    {capability:"remote",aspect:"control",attribute:"lock",
      status:"migration_pending",source:"v2_control_reference"},
  ]};
  panel.render();
  assert.match(panel.shadowRoot.innerHTML,/Inventory & status/);
  assert.match(panel.shadowRoot.innerHTML,/Select capability/);
  assert.match(panel.shadowRoot.innerHTML,/Configure & test/);
  assert.match(panel.shadowRoot.innerHTML,/109/);
  assert.match(panel.shadowRoot.innerHTML,/21/);
  assert.match(panel.shadowRoot.innerHTML,/1 verified/);
  await panel._click({target:{closest:() => ({dataset:{action:"step-2"}})}});
  assert.equal(panel.step,2);
  assert.match(panel.shadowRoot.innerHTML,/state of charge/);
  panel.api=async (name,data) => {
    assert.equal(name,"attribute_routes");
    assert.equal(data.attribute,"stateOfCharge");
    return {routes:[{id:"cariad.selectivestatus.batch",family:"cariad",
      method:"GET",kind:"shared_batch",result:"verified",
      path:"/vehicle/v1/vehicles/{VIN}/selectivestatus?jobs={JOBS}"}],
      active:"cariad.selectivestatus.batch"};
  };
  await panel._click({target:{closest:() => ({dataset:{
    action:"select-attribute",capability:"charging",attribute:"stateOfCharge"
  }})}});
  assert.equal(panel.step,3);
  assert.equal(panel.attribute,"stateOfCharge");
  assert.match(panel.shadowRoot.innerHTML,/Activate for polling/);
  assert.match(panel.shadowRoot.innerHTML,/Advanced · define another API path/);
});

test("HA-native Workbench groups by the vehicle's API family", () => {
  const panel=new Panel();panel.selected="sample";panel.vin="VIN1";
  panel.entries=[{entry_id:"sample",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  panel.capabilityStatus={counts:{catalog_jobs:23,not_scanned_jobs:0,observed_jobs:2,not_observed_jobs:21},rows:[
    {api_family:"cariad",capability:"charging",attribute:"stateOfCharge",entity_key:"state_of_charge",status:"verified",source:"v3_live_evidence"},
    {api_family:"mbb",capability:"charging",attribute:"stateOfCharge",entity_key:"state_of_charge",status:"not_tested",source:"v2_attribute_reference"},
  ]};
  panel.render();
  assert.match(panel.shadowRoot.innerHTML,/ha-font-family-body/);
  assert.match(panel.shadowRoot.innerHTML,/Step 1 \/ Automatic discovery/);
  assert.match(panel.shadowRoot.innerHTML,/1 readable attributes/);
  assert.match(panel.shadowRoot.innerHTML,/1 read-only attributes/);
  panel.apiFamily="all";panel.render();
  assert.match(panel.shadowRoot.innerHTML,/2 read-only attributes/);
});

test("Wake, lock and climate are independently selectable for guarded physical testing", async () => {
  const p = new Panel();
  p.selected="test";p.vin="VIN1";
  p.entries=[{entry_id:"test",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.step=2;p.category="remote";
  p.capabilityStatus={counts:{},rows:[],control_actions:[
    {capability:"remote",action:"wake",api_family:"cariad",candidate_count:1,status:"not_tested"},
    {capability:"access",action:"lock",api_family:"cariad",candidate_count:1,status:"not_tested"},
    {capability:"climate",action:"start",api_family:"cariad",candidate_count:1,status:"not_tested"},
  ]};
  p.render();
  assert.match(p.shadowRoot.innerHTML,/wake/);
  assert.match(p.shadowRoot.innerHTML,/Configure control/);
  p.api=async (name,args) => {
    assert.equal(name,"control_routes");
    assert.equal(args.capability,"remote");
    assert.equal(args.action,"wake");
    return {routes:[{id:"cariad.remote.wake",family:"cariad",status:"not_tested",
      path:"/vehicle/v1/vehicles/{VIN}/vehiclewakeuptrigger"}],requires:"Physical verification"};
  };
  await p._click({target:{closest:()=>({dataset:{
    action:"select-control",capability:"remote",control:"wake"
  }})}});
  assert.equal(p.controlAction,"wake");
  assert.equal(p.step,3);
  assert.match(p.shadowRoot.innerHTML,/Send one test command/);
  assert.match(p.shadowRoot.innerHTML,/Physical verification/);
});

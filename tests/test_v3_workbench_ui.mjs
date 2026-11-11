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
  assert.equal(panel.routeChoice, routes[1].id);
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
  assert.match(p.shadowRoot.innerHTML,/Routes & test/);
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

test("Step 3 shows one unified test workflow and saved responses, no Climate-only editor", () => {
  const p=new Panel();p.step=3;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.apiHistory=[{operation:"cariad.discovery.full",family:"cariad",method:"GET",
    at:"2026-11-11T20:00:00+00:00",http_status:200,result:"http_ok",preview:{soc:97}}];
  p.render();
  assert.match(p.shadowRoot.innerHTML,/Test read-only API family/);
  assert.match(p.shadowRoot.innerHTML,/Last result and response by API route/);
  assert.match(p.shadowRoot.innerHTML,/2026-11-11T20:00:00/);
  assert.doesNotMatch(p.shadowRoot.innerHTML,/Climate \(guided controls\)/);
  assert.doesNotMatch(p.shadowRoot.innerHTML,/Control migration pending/);
});

test("Manual scan sends GET-family command only", async () => {
  const p=new Panel();p.step=3;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  const commands=[];
  p.api=async (name,data)=>{
    commands.push(name);
    if(name==="test_family_reads"){assert.equal(data.family,"cariad");return {family:"cariad",request_count:1};}
    if(name==="routes")return {routes:[],history:[]};
    if(name==="status")return {counts:{},rows:[]};
    if(name==="list")return {integrations:p.entries};
    if(name==="api_results")return {records:[]};
    throw Error("Unexpected command "+name);
  };
  await p._click({target:{closest:()=>({dataset:{action:"family-test"}})}});
  assert.deepEqual(commands.filter(x=>x.includes("test")),["test_family_reads"]);
});

test("Alternative access command template exposes only reserved runtime placeholders", () => {
  const p=new Panel();p.step=3;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",api_family:"cariad",name:"Audi",model:"Q8"}]}];
  p.controlCapability="access";p.controlAction="unlock";
  p.controlRoutes=[{id:"cariad.access.unlock",family:"cariad",path:"/vehicle/v1/vehicles/{VIN}/access/unlock",status:"not_tested"}];
  p.controlChoice="cariad.access.unlock";
  const template=JSON.parse(p.initialControlRoute);
  assert.equal(template.path,"/vehicle/v1/vehicles/{VIN}/access/unlock");
  assert.deepEqual(JSON.parse(JSON.stringify(template.body)),{spin:"{SPIN}"});
  assert.deepEqual(JSON.parse(JSON.stringify(template.variables)),{});
  p.render();
  assert.match(p.shadowRoot.innerHTML,/Advanced · Add an alternative command template/);
  assert.match(p.shadowRoot.innerHTML,/Do not enter or save a real S-PIN/);
  assert.doesNotMatch(p.shadowRoot.innerHTML,/9876/);
});

test("Saving an access command template does not send a POST or require PIN input", async () => {
  const p=new Panel();p.step=3;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",api_family:"cariad",name:"Audi",model:"Q8"}]}];
  p.controlCapability="access";p.controlAction="lock";
  const data=p.initialControlRoute;
  const calls=[];
  p.shadowRoot.getElementById = id=>({value:id==="control-definition"?data:"{}"});
  p.api=async (name, args)=>{
    calls.push(name);
    if(name==="add_route"){
      assert.equal(args.route.body.spin,"{SPIN}");
      assert.equal(args.route.path,"/vehicle/v1/vehicles/{VIN}/access/lock");
      return {operation:"user.access.lock.alternative"};
    }
    if(name==="routes")return {routes:[],history:[]};
    if(name==="status")return {counts:{},rows:[]};
    if(name==="attribute_routes")return {routes:[]};
    if(name==="control_routes")return {routes:[{id:"user.access.lock.alternative",family:"cariad",method:"POST",path:"/vehicle/v1/vehicles/{VIN}/access/lock",status:"not_tested"}]};
    if(name==="list")return {integrations:p.entries};
    throw Error("Unexpected command "+name);
  };
  await p._click({target:{closest:()=>({dataset:{action:"control-add"}})}});
  assert.deepEqual(calls.filter(x=>/test|control_test/.test(x)),[]);
  assert.equal(p.controlChoice,"user.access.lock.alternative");
});

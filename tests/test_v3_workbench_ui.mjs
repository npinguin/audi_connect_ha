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
  assert.match(panel.shadowRoot.innerHTML,/Overview/);
  assert.match(panel.shadowRoot.innerHTML,/Capabilities/);
  assert.match(panel.shadowRoot.innerHTML,/Configure & test/);
  assert.match(panel.shadowRoot.innerHTML,/109/);
  assert.match(panel.shadowRoot.innerHTML,/21/);
  assert.match(panel.shadowRoot.innerHTML,/1 fresh/);
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
  assert.match(panel.shadowRoot.innerHTML,/Audi Engineering Dashboard/);
  assert.match(panel.shadowRoot.innerHTML,/1 readable/);
  assert.match(panel.shadowRoot.innerHTML,/1 readable/);
  panel.apiFamily="all";panel.render();
  assert.match(panel.shadowRoot.innerHTML,/\/ 2 readable/);
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
  assert.match(p.shadowRoot.innerHTML,/Wake vehicle/);
  assert.match(p.shadowRoot.innerHTML,/Inspect & test/);
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

test("API evidence shows scan options and restricted historical executions", () => {
  const p=new Panel();p.step=4;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.apiHistory=[{operation:"cariad.discovery.full",family:"cariad",method:"GET",
    at:"2026-11-11T20:00:00+00:00",http_status:200,result:"http_ok",preview:{soc:97}}];
  p.render();
  assert.match(p.shadowRoot.innerHTML,/Quick scan/);
  assert.match(p.shadowRoot.innerHTML,/Full read-only scan/);
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


test("Discovery modes do not send commands; exact approval is required", async () => {
  const p = new Panel();
  p.selected="entry"; p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",api_family:"cariad"}]}];
  p.capabilityStatus={counts:{},rows:[],control_actions:[
    {capability:"remote",action:"wake",api_family:"cariad",candidate_count:1,approval_groups:["non_spin"]},
    {capability:"access",action:"unlock",api_family:"cariad",candidate_count:1,approval_groups:["spin"]}
  ]};
  const calls=[];
  p.api=async (name,args)=>{
    calls.push({name,args});
    if(name==="control_test") return {sequence:1};
    if(name==="routes")return {routes:[],history:[]};
    if(name==="status")return p.capabilityStatus;
    if(name==="control_routes")return {routes:p.controlRoutes,spin_configured:true};
    if(name==="api_results")return {records:[]};
    if(name==="list")return {integrations:p.entries};
    throw Error(name);
  };
  const click=(action,group)=>p._click({target:{closest:()=>({dataset:{action,group}})}});
  await click("discovery-group","spin");
  assert.equal(p.discoveryGroup,"spin");
  assert.equal(calls.length,0);
  p.controlCapability="access";p.controlAction="unlock";p.step=3;
  p.controlChoice="cariad.access.unlock";
  p.controlRoutes=[{id:p.controlChoice,family:"cariad",approval_group:"spin"}];
  p.spinConfigured=true;
  await click("control-test");
  assert.equal(calls.filter(x=>x.name==="control_test").length,0);
  p.shadowRoot.getElementById=id=>id==="control-approval"?{checked:true}:null;
  await click("control-test");
  const sent=calls.filter(x=>x.name==="control_test");
  assert.equal(sent.length,1);
  assert.equal(sent[0].args.approval,"spin");
  assert.equal(sent[0].args.operation,"cariad.access.unlock");
});

test("cockpit separates tested operations, active bindings and physical evidence", async () => {
  const p=new Panel();p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad",start_enabled:true}]}];
  p.capabilityStatus={counts:{},rows:[],operations:[
    {operation:"test.read",family:"cariad",method:"GET",tested:true,active:true,schema:"valid",fields:[{path:"oil.level",type:"boolean",quality:"valid",mapping:"unmapped"}]},
    {operation:"test.command",family:"cariad",method:"POST",tested:true,active:false,physical:"unknown",attention:["needs physical proof"]},
    {operation:"test.pending",family:"cariad",method:"GET",tested:false}
  ],findings:[{severity:"warning",reason:"needs physical proof",capability:"climate"}]};
  p.render();
  assert.match(p.shadowRoot.innerHTML,/Enabled controls/);
  assert.match(p.shadowRoot.innerHTML,/oil.level/);
  assert.match(p.shadowRoot.innerHTML,/test.pending/);
  await p._change({target:{id:"operation-filter",value:"attention"}});
  assert.match(p.shadowRoot.innerHTML,/test.command/);
  assert.doesNotMatch(p.shadowRoot.innerHTML,/test.pending/);
});

test("controls filter never leaks another capability and vehicle changes clear selection", async () => {
  const p=new Panel();p.selected="entry";p.vin="VIN1";p.step=2;p.category="climate";p.discoveryGroup="non_spin";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.capabilityStatus={rows:[],control_actions:[
    {capability:"climate",action:"start",api_family:"cariad",candidate_count:1,approval_groups:["non_spin"]},
    {capability:"charging",action:"set_target_soc",api_family:"cariad",candidate_count:1,approval_groups:["non_spin"]}
  ]};p.render();
  assert.match(p.shadowRoot.innerHTML,/data-control="start"/);
  assert.doesNotMatch(p.shadowRoot.innerHTML,/data-control="set_target_soc"/);
  p.controlAction="start";p.pending={sequence:1};p.apiHistory=[{}];p._resetVehicleSelection();
  assert.equal(p.controlAction,"");assert.equal(p.pending,null);assert.equal(p.apiHistory.length,0);assert.equal(p.step,1);
});

test("failed route lookup clears old action and prevents stale dispatch", async () => {
  const p=new Panel();p.selected="entry";p.vin="VIN1";p.controlChoice="old.route";
  p.controlRoutes=[{id:"old.route",approval_group:"non_spin"}];
  p.api=async()=>{throw Error("lookup failed")};
  await p._click({target:{closest:()=>({dataset:{action:"select-control",capability:"climate",control:"stop"}})}});
  assert.equal(p.controlChoice,"");assert.equal(p.controlRoutes.length,0);assert.match(p.error,/lookup failed/);
});
test("review finding opens only the affected evidence without sending vehicle commands", async()=>{
  const p=new Panel();p.selected="entry";p.vin="VIN1";
  p.capabilityStatus={rows:[],findings:[{operation:"cariad.test",reason:"http_error"}]};
  p.api=async()=>{throw Error("No request expected")};
  await p._click({target:{closest:()=>({dataset:{action:"inspect-finding",index:"0"}})}});
  assert.equal(p.step,4);assert.equal(p.focusOperation,"cariad.test");
});

test("loading historical evidence is local, escapes payload HTML and resets on vehicle change", async()=>{
  const p=new Panel();p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.step=4;
  const calls=[];
  p.api=async(name,data)=>{calls.push([name,data]);return {records:[],engineering_history:[
    {operation:"test.read",family:"cariad",method:"GET",at:"now",http_status:207,
      payload:{vin:"{VIN}",target:15.5,detail:"<script>"}}]};};
  await p._apiResults();p.render();
  assert.equal(calls.length,1);assert.equal(calls[0][0],"api_results");
  assert.match(p.shadowRoot.innerHTML,/15\.5/);assert.match(p.shadowRoot.innerHTML,/\{VIN\}/);
  assert.match(p.shadowRoot.innerHTML,/&lt;script&gt;/);
  p._resetVehicleSelection();assert.equal(p.engineeringHistory.length,0);
});

test("selected test and historical execution show request and response without another click", async()=>{
  const p=new Panel();p.selected="entry";p.vin="VIN1";p.step=4;
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",model:"Q8",api_family:"cariad"}]}];
  p.api=async(name,data)=>{assert.equal(name,"api_results");assert.equal(data.include_engineering,true);
    return {records:[],engineering_history:[{operation:"test.read",family:"cariad",method:"GET",at:"now",http_status:207,
      request:{payload:{method:"GET",url:"/vehicles/{VIN}"}},payload:{value:15.5}}]};};
  await p._apiResults();p.render();
  assert.match(p.shadowRoot.innerHTML,/Request sent/);
  assert.match(p.shadowRoot.innerHTML,/Response received/);
  assert.match(p.shadowRoot.innerHTML,/15\.5/);
  assert.match(p.shadowRoot.innerHTML,/<details class="record" open>/);
});


test("HAR identity template exposes fixed variables without browser credentials", () => {
  const p=new Panel();p.step=3;p.selected="entry";p.vin="VIN1";
  p.entries=[{entry_id:"entry",vehicles:[{vin:"VIN1",name:"Audi",api_family:"cariad"}]}];
  const op="graphql.inventory.webOrdered";
  p.apiFamily="all";
  p.capabilityStatus={counts:{},rows:[],operations:[{operation:op,method:"POST",path:"/vgql/v1/graphql",
    family:"graphql",read_only:true,capabilities:["vehicle_identity"],mappings:[]}],
    identity_templates:{[op]:"query GET_USER_VEHICLES_ORDERED_BY"},
    identity_fixed_parameters:{[op]:{operationName:"GET_USER_VEHICLES_ORDERED_BY",variables:{orderBy:"FAVORITE_AND_REGISTRATION"}}}};
  p.openIdentityEditor(op);
  assert.match(p.shadowRoot.innerHTML,/FAVORITE_AND_REGISTRATION/);
  assert.match(p.shadowRoot.innerHTML,/readonly/);
  assert.match(p.shadowRoot.innerHTML,/not a web session replay/);
});

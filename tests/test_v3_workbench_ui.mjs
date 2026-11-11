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

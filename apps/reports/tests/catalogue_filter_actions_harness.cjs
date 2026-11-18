/** Reuse the existing DOM fixture, but exercise real new catalogue opt-ins. */
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const assert = require("node:assert/strict");
const fixturePath = path.join(__dirname, "tfux_s3_harness.cjs");
const fixture = fs.readFileSync(fixturePath, "utf8").split("const scenario =")[0];
const fixtureModule = new Module(fixturePath, module);
fixtureModule.filename = fixturePath;
fixtureModule.paths = module.paths;
fixtureModule._compile(fixture + "\nmodule.exports={buildWorld,El};", fixturePath);
const { buildWorld, El } = fixtureModule.exports;
const passed = [], failed = [];
const settle = () => new Promise(resolve => setTimeout(resolve, 25));

function world(options = {}) {
  const w = buildWorld({
    q: "Ana", marker: "manual", mode: "all",
    applied: "q=Ana&tag_filter=manual&tag_mode=all&tags=7",
    tagIds: ["7"], ...options,
  });
  w.form.setAttribute("data-catalogue-filter-actions", "");
  w.clearLink.setAttribute("data-catalogue-navigation", "");
  w.clearLink.setAttribute("data-catalogue-clear-all", "");
  w.reapplyLink.setAttribute("data-catalogue-navigation", "");
  w.reapplyLink.setAttribute("data-catalogue-restore", "");
  const apply = new El("button", {"data-discovery-apply":""});
  apply.focus = () => { w.sandbox.document.activeElement = apply; };
  w.form.appendChild(apply);
  w.apply = apply;
  const Parser = w.sandbox.DOMParser;
  w.sandbox.DOMParser = function() {
    const parser = new Parser();
    return { parseFromString(...args) {
      const root = parser.parseFromString(...args).querySelector("[data-discovery-results]");
      root.setAttribute("data-catalogue-can-restore", String(w.canRestore ?? true));
      return { querySelector: () => root };
    }};
  };
  w.aborts = 0;
  w.sandbox.AbortController = class {
    constructor() { this.signal = {}; }
    abort() { w.aborts += 1; }
  };
  return w;
}
async function check(name, fn) {
  try { await fn(); passed.push(name); }
  catch(error) { failed.push({name,error:error.message}); }
}

(async function() {
  await check("canonical clear is a native fresh manual/ANY action", async () => {
    const w = world(); w.search.value = "Bruno";
    const event = w.root.dispatch("click", {target:w.clearLink});
    await settle();
    assert.equal(event.defaultPrevented, false);
    assert.equal(w.calls.fetch.length, 0);
    assert.equal(w.clearLink.getAttribute("href"), "?tag_filter=manual&tag_mode=any");
    assert.equal(w.calls.pushState.length, 0);
  });
  await check("canonical restore uses applied name and historical, not drafts", async () => {
    const w = world({applied:"q=Ana&tag_filter=manual&tags=7&tag_mode=all&include_historical=1"});
    w.search.value = "Bruno"; w.mode.value = "any";
    const event = w.root.dispatch("click", {target:w.reapplyLink});
    await settle();
    assert.equal(event.defaultPrevented, false);
    assert.equal(w.calls.fetch.length, 0);
    assert.equal(w.reapplyLink.getAttribute("href"), "?q=Ana&include_historical=1");
  });
  await check("restore href drops unknown parameters and normalizes applied name", async () => {
    const w = world({applied:"q=+Ana+&tag=7&tag_filter=manual&tag_mode=all&stale=x&page=2"});
    w.root.dispatch("click", {target:w.reapplyLink}); await settle();
    assert.equal(w.reapplyLink.getAttribute("href"), "?q=Ana");
  });
  await check("persisted pageshow restores controls and visibility without extra history", async () => {
    const w = world(); w.search.value = "Bruno"; w.canRestore = false;
    w.calls.__nextApplied = "q=Ana"; w.calls.__nextSelected = ["7"];
    w.calls.__nextSource = "saved";
    w.sandbox.window.location.search = "?q=Ana";
    w.sandbox.__winListeners.pageshow[0]({persisted:true}); await settle();
    assert.equal(w.search.value, "Ana");
    assert.equal(w.reapplyLink.hidden, true);
    assert.equal(w.calls.pushState.length, 0);
    assert.equal(w.dirty.hidden, true);
  });
  await check("historical reconciliation cannot convert clear-all into tag-only clear", async () => {
    const w = world(); w.historical.checked = true;
    w.historical.dispatch("change", {});
    await settle();
    assert.equal(w.clearLink.getAttribute("href"), "?tag_filter=manual&tag_mode=any");
    assert.equal(w.reapplyLink.getAttribute("href"), "?q=Ana&include_historical=1");
    assert.equal(w.calls.fetch.length, 0);
  });
  await check("AJAX metadata exposes restore after manual Apply", async () => {
    const w = world({q:"",applied:"",marker:"",source:"saved"});
    w.reapplyLink.hidden = true; w.search.value = "Nova";
    w.calls.__nextApplied = "q=Nova&tag_filter=manual&tag_mode=all&tags=7";
    w.calls.__nextSelected = ["7"];
    w.form.dispatch("submit", {}); await settle();
    assert.equal(w.calls.fetch.length, 1);
    assert.equal(w.reapplyLink.hidden, false);
    assert.equal(w.reapplyLink.getAttribute("href"), "?q=Nova");
  });
  await check("server metadata hides restore and moves focus safely", async () => {
    const w = world(); w.canRestore = false;
    w.sandbox.document.activeElement = w.reapplyLink;
    let hidden = false;
    Object.defineProperty(w.reapplyLink, "hidden", {
      get: () => hidden,
      set(value) { hidden = value; if (value) w.sandbox.document.activeElement = null; },
    });
    w.search.value = "Nova"; w.form.dispatch("submit", {}); await settle();
    assert.equal(w.reapplyLink.hidden, true);
    assert.equal(w.sandbox.document.activeElement === w.apply, true);
  });
  for (const key of ["clearLink","reapplyLink"]) {
    await check(key + " invalidates in-flight response even without fetch abort support", async () => {
      const w = world({controlled:true});
      w.search.value = "Bruno"; w.form.dispatch("submit", {}); await settle();
      const before = w.calls.fetch.length;
      w.root.dispatch("click", {target:w[key]}); await settle();
      assert.equal(w.aborts, 1);
      assert.equal(w.calls.fetch.length, before);
      w.calls.__nextApplied = "q=Bruno&tag_filter=manual&tags=7";
      w.resolvePending("fragment"); await settle();
      assert.equal(w.calls.pushState.length, 0);
      assert.equal(w.root.querySelector("[data-discovery-results]"), w.results);
    });
  }
  for (const properties of [{ctrlKey:true}, {metaKey:true}, {shiftKey:true}, {altKey:true}, {button:1}, {button:2}, {defaultPrevented:true}]) {
    await check("non-navigating canonical click preserves pending Apply " + JSON.stringify(properties), async () => {
      const w = world({controlled:true});
      w.search.value = "Bruno"; w.form.dispatch("submit", {}); await settle();
      w.root.dispatch("click", {target:w.reapplyLink, ...properties});
      assert.equal(w.reapplyLink.getAttribute("href"), "?q=Ana");
      assert.equal(w.aborts, 0);
      assert.equal(w.calls.fetch.length, 1);
      w.calls.__nextApplied = "q=Bruno&tag_filter=manual&tags=7";
      w.resolvePending("fragment"); await settle();
      assert.equal(w.calls.pushState.length, 1);
      assert.match(w.calls.pushState[0], /q=Bruno/);
    });
  }
  await check("legacy tag-only hooks retain AJAX ownership", async () => {
    const w = world(); w.clearLink.removeAttribute("data-catalogue-navigation");
    w.clearLink.removeAttribute("data-catalogue-clear-all");
    const event = w.root.dispatch("click", {target:w.clearLink}); await settle();
    assert.equal(event.defaultPrevented, true);
    assert.equal(w.calls.fetch.length, 1);
    assert.match(w.calls.fetch[0], /q=Ana/);
  });
  console.log(JSON.stringify({passed,failed}, null, 2));
  process.exitCode = failed.length ? 1 : 0;
})();

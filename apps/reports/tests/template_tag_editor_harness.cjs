/** Actual editor source with the existing minimal DOM fixture, no transport. */
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Module = require("node:module"), assert = require("node:assert/strict");
const fixturePath = path.join(__dirname, "tfux_s3_harness.cjs");
const fixture = new Module(fixturePath, module);
fixture.filename = fixturePath; fixture.paths = module.paths;
fixture._compile(fs.readFileSync(fixturePath, "utf8").split("function buildWorld")[0] +
  "\nmodule.exports={El};", fixturePath);
const { El } = fixture.exports;
const source = fs.readFileSync(path.resolve(__dirname, "../../../assets/js/report-template-tag-editor.js"), "utf8");
const passed = [], failed = [], settle = () => new Promise(r => setTimeout(r, 5));
const originalDispatch = El.prototype.dispatch;
El.prototype.dispatch = function(type, event = {}) {
  if (type !== "keydown") return originalDispatch.call(this, type, event);
  event.target ||= this; event.defaultPrevented ||= false;
  event.preventDefault = function() { this.defaultPrevented = true; };
  for (let node = this; node; node = node.parentNode) {
    for (const fn of node.listeners[type] || []) fn(event);
  }
  return event;
};

function world(options = {}) {
  const document = { readyState: options.loading ? "loading" : "complete", activeElement: null };
  function element(tag, attrs = {}) {
    const el = new El(tag, attrs);
    el.focus = () => { document.activeElement = el; el.dispatch("focus", {}); };
    Object.defineProperty(el, "innerHTML", { set() { throw Error("Unsafe HTML"); } });
    return el;
  }
  const form = element("form"), root = element("div", {"data-template-tag-editor":""});
  form.appendChild(root);
  const native = element("select", {name:"tag_ids"}); native.multiple = true; native.form = form;
  Object.defineProperty(native, "options", { get: () => native.children });
  const w = { document, form, root, native, sentinels: {name:"DRAFT",markdown:"TEXT",active:false,public:true} };
  for (const name of ["native","enhanced","search","panel","results","empty","chips","status"]) {
    w[name === "native" ? "fallback" : name] = element(name === "search" ? "input" : "div", {["data-editor-"+name]:""});
  }
  w.fallback.appendChild(native); root.appendChild(w.fallback); root.appendChild(w.enhanced);
  for (const name of ["search","panel","chips","status"]) w.enhanced.appendChild(w[name]);
  w.panel.appendChild(w.results); w.panel.appendChild(w.empty);
  w.enhanced.hidden = true; w.panel.hidden = true;
  for (const [id,label,selected] of options.rows || [["7","Reabilitação Clínica",false],["8","Outra Equipe",false]]) {
    const option = element("option",{value:id}); option.textContent = label;
    option.selected = !!selected; option.defaultSelected = !!selected; native.appendChild(option);
  }
  const events = {};
  document.querySelectorAll = () => [root];
  document.createElement = tag => { if (options.renderFailure) throw Error("DOM failure"); return element(tag); };
  document.addEventListener = (type,fn) => { (events[type] ||= []).push(fn); };
  const forbidden = () => { throw Error("Forbidden transport/storage/history"); };
  w.sandbox = {document,console,setTimeout,clearTimeout,fetch:forbidden,localStorage:new Proxy({}, {get:forbidden}),history:new Proxy({}, {get:forbidden})};
  w.start = () => vm.runInNewContext(source,w.sandbox);
  w.ready = () => (events.DOMContentLoaded || []).forEach(fn=>fn());
  if (options.missingHook) w.empty.remove();
  w.start(); return w;
}
const values = w => w.native.options.filter(o=>o.selected).map(o=>o.value);
const result = (w,id) => w.results.querySelector('[data-editor-result="'+id+'"]');
const remove = (w,id) => w.chips.querySelector('[data-editor-remove="'+id+'"]');
function check(name,fn) {
  try { const value=fn(); if(value?.then)return value.then(()=>passed.push(name)).catch(e=>failed.push({name,error:e.message})); passed.push(name); }
  catch(e) { failed.push({name,error:e.message}); }
}

function selectionCases() {
  check("initial state comes from rendered selected options",()=>{
    const w=world({rows:[["7","Inicial",true],["8","Outra",false]]});
    assert.equal(w.chips.children.length,1); assert.equal(w.fallback.hidden,true);
    assert.equal(w.enhanced.hidden,false); assert.equal(w.native.disabled,false);
  });
  check("ordinary clicks accumulate and selected results are inert",()=>{
    const w=world(); result(w,"7").dispatch("click");result(w,"8").dispatch("click");result(w,"7").dispatch("click");
    assert.deepEqual(values(w),["7","8"]);assert.equal(w.chips.children.length,2);
    assert.equal(result(w,"7").getAttribute("aria-disabled"),"true");
  });
  check("remove final chip leaves empty native field and search focus",()=>{
    const w=world({rows:[["7","Inicial",true]]});remove(w,"7").dispatch("click");
    assert.deepEqual(values(w),[]);assert.equal(w.chips.children.length,0);
    assert.equal(w.document.activeElement===w.search,true);assert.equal(w.status.textContent,"Nenhuma tag selecionada.");
  });
  check("removal focuses another remaining chip",()=>{
    const w=world({rows:[["7","Primeira",true],["8","Segunda",true]]});
    remove(w,"7").dispatch("click");assert.equal(w.document.activeElement===remove(w,"8"),true);
  });
}

function searchCases() {
  check("local search is case/accent insensitive without clearing selected chips",()=>{
    const w=world({rows:[["7","Reabilitação Clínica",true],["8","Outra",false]]});
    w.search.value="REABILITACAO";w.search.dispatch("input");
    assert.equal(w.results.children.length,1);assert.deepEqual(values(w),["7"]);assert.equal(w.chips.children.length,1);
    w.search.value="";w.search.dispatch("input");assert.equal(w.results.children.length,2);
  });
  check("no-match cannot add an unknown identity",()=>{
    const w=world();w.search.value="forjada";w.search.dispatch("input");
    assert.equal(w.results.children.length,0);assert.equal(w.empty.hidden,false);assert.deepEqual(values(w),[]);
  });
  check("HTML-like labels remain literal text",()=>{
    const w=world({rows:[["7","<img src=x onerror=bad()>",false]]});
    result(w,"7").dispatch("click");
    assert.equal(w.chips.querySelector("img"),null);
    assert.equal(w.chips.children[0].children[0].textContent,"<img src=x onerror=bad()>");
  });
  check("Enter search is cancelled and Escape closes results",()=>{
    const w=world();assert.equal(w.search.dispatch("keydown",{key:"Enter"}).defaultPrevented,true);
    assert.equal(w.panel.hidden,false);
    result(w,"7").dispatch("keydown",{key:"Escape"});
    assert.equal(w.panel.hidden,true);assert.equal(w.document.activeElement===w.search,true);
  });
  check("all dynamic buttons are type button and native name stays unique",()=>{
    const w=world();result(w,"7").dispatch("click");
    assert(w.root.querySelectorAll("button").every(b=>b.type==="button"));
    assert.equal(w.root.querySelectorAll('[name="tag_ids"]').length,1);
    assert.equal(w.native.name,"tag_ids");assert.equal(w.native.disabled,false);
  });
}

async function synchronizationCases() {
  check("native change synchronizes the enhanced presentation",()=>{
    const w=world();w.native.options[1].selected=true;w.native.dispatch("change");
    assert.equal(w.chips.children[0].getAttribute("data-editor-chip"),"8");
  });
  await check("form reset restores only tag display from native state",async()=>{
    const w=world({rows:[["7","Inicial",true],["8","Outra",false]]});
    remove(w,"7").dispatch("click");result(w,"8").dispatch("click");
    w.form.dispatch("reset");w.native.options.forEach(o=>o.selected=o.defaultSelected);
    await settle();assert.deepEqual(values(w),["7"]);assert.equal(w.chips.children.length,1);
    assert.deepEqual(w.sentinels,{name:"DRAFT",markdown:"TEXT",active:false,public:true});
  });
  await check("cancelled form reset keeps the actual current selection",async()=>{
    const w=world();result(w,"8").dispatch("click");
    w.form.dispatch("reset",{defaultPrevented:true});await settle();assert.deepEqual(values(w),["8"]);
  });
}

function fallbackCases() {
  check("initialization is idempotent",()=>{
    const w=world();w.start();assert.equal(w.search.listeners.input.length,1);
  });
  check("no options has generic field status",()=>{
    const w=world({rows:[]});assert.equal(w.status.textContent,"Nenhuma tag disponível para seleção.");
  });
  check("incomplete markup retains native fallback",()=>{
    const w=world({missingHook:true});assert.equal(w.fallback.hidden,false);assert.equal(w.enhanced.hidden,true);
  });
  check("render failure retains native fallback and field values",()=>{
    const w=world({renderFailure:true,rows:[["7","Inicial",true]]});
    assert.equal(w.fallback.hidden,false);assert.equal(w.enhanced.hidden,true);assert.deepEqual(values(w),["7"]);
  });
  check("DOMContentLoaded defers enhancement safely",()=>{
    const w=world({loading:true});assert.equal(w.fallback.hidden,false);
    w.ready();assert.equal(w.fallback.hidden,true);
  });
}

(async()=>{
  selectionCases();
  searchCases();
  await synchronizationCases();
  fallbackCases();
  console.log(JSON.stringify({passed,failed},null,2));process.exitCode=failed.length?1:0;
})();

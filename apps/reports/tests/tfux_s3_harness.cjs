const fs = require("fs");
const vm = require("vm");
const nodePath = require("node:path");
const ROOT = nodePath.resolve(__dirname, "..", "..", "..");
const hostSource = fs.readFileSync(
  ROOT + "/assets/js/report-catalogue-filter-form.js", "utf8"
);
const selectorSource = fs.readFileSync(
  ROOT + "/assets/js/tag-selector.js", "utf8"
);
const transportSource = fs.readFileSync(
  ROOT + "/assets/js/report-template-discovery.js", "utf8"
);
const markerFn = "  // Report-creation selector (S3, D6)";
const discoverySource =
  transportSource.slice(0, transportSource.indexOf(markerFn)) +
  "  function start() {\n    Array.prototype.forEach.call(\n      document.querySelectorAll(\"[data-report-template-discovery]\"),\n      function (root) {\n        if (root.hasAttribute(\"data-template-selection\")) { return; }\n        initializeDiscovery(root);\n      }\n    );\n  }\n\n  if (document.readyState === \"loading\") {\n    document.addEventListener(\"DOMContentLoaded\", start);\n  } else {\n    start();\n  }\n})();\n";

// TFUX S3 fix3: the harness runs the REAL shared selector
// (assets/js/tag-selector.js) together with the REAL catalogue host and
// transport, under one DOM stub, exactly like the S2 escape-term harness
// ran real selector bytes. `document.querySelectorAll` ordering (host
// selectors first, then the discovery root, then the selector root) and
// the immediate-start hook registry reproduce script `defer` order:
// tag-selector.js, report-catalogue-filter-form.js,
// report-template-discovery.js. The selector's start() scans for
// [data-tag-selector]; only the catalogue selector box exists here.

class El {
  constructor(tag, attrs) {
    this.tagName = String(tag || "div").toUpperCase();
    this.attrs = Object.assign({}, attrs);
    this.children = [];
    // Like a real DOM element, reflected attributes are also readable as
    // JS properties (the catalogue host reads .name/.value/.checked).
    // Deferred: the harness sets .value/.checked AFTER construction, so
    // define accessors that always mirror the live property instead of a
    // construction-time snapshot.
    for (const key of ["name", "type"]) {
      if (key in this.attrs && !(key in this)) {
        this[key] = this.attrs[key];
      }
    }
    this.listeners = {};
    this.hidden = false;
    this._value = "";
    this._checked = false;
    this._disabled = false;
    this.type = "";
    this.parentNode = null;
    this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
    this.style = {};
    this.textContent = "";
    this.selected = false;
  }
  get childElementCount() { return this.children.length; }
  get value() { return this._value !== undefined ? this._value : (this.attrs.value !== undefined ? String(this.attrs.value) : ""); }
  set value(v) { this._value = String(v); }
  get checked() { return this._checked !== undefined ? this._checked : this.attrs.checked === "" || this.attrs.checked === true; }
  set checked(v) { this._checked = !!v; }
  get disabled() { return this._disabled !== undefined ? this._disabled : ("disabled" in this.attrs); }
  set disabled(v) { this._disabled = !!v; }
  // Class-level accessors live on the prototype, but constructor
  // assignments (this._value etc.) create own data properties first; keep
  // them in sync so reflection always reads the live state.
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "value") this._value = String(v); if (k === "checked") this._checked = true; if (k === "disabled") this._disabled = true; }
  removeAttribute(k) { delete this.attrs[k]; if (k === "value") this._value = ""; if (k === "checked") this._checked = false; if (k === "disabled") this._disabled = false; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  dispatch(t, ev) {
    const event = ev || {};
    if (!("target" in event)) event.target = this;
    if (!event.target) event.target = this;
    if (!("defaultPrevented" in event)) {
      event.defaultPrevented = false;
      event.preventDefault = function () { this.defaultPrevented = true; };
    }
    // Registration order mirrors script load order (selector, host,
    // transport): a clean enhanced Apply is already defaultPrevented
    // when the transport listener runs, and the transport honors
    // event.defaultPrevented by issuing no request. All listeners run
    // on the same event object, exactly like a browser dispatch.
    for (const fn of (this.__docListeners || {})[t] || []) fn(event);
    for (const fn of this.listeners[t] || []) fn(event);
    // DOM change/click/input/submit/tag-selector events bubble to ancestors.
    if (t === "change" || t === "click" || t === "input" || t === "submit" || t === "tag-selector:change" || t === "tag-selector:set-selection" || t === "catalogue:applied") {
      let node = this.parentNode;
      while (node) {
        for (const fn of node.listeners[t] || []) fn(event);
        node = node.parentNode;
      }
    }
    return event;
  }
  appendChild(c) { c.parentNode = this; c.__docListeners = this.__docListeners; this.children.push(c); return c; }
  remove() {
    if (this.parentNode) {
      const i = this.parentNode.children.indexOf(this);
      if (i >= 0) this.parentNode.children.splice(i, 1);
      this.parentNode = null;
    }
  }
  replaceChildren(...cs) { this.children = []; for (const c of cs) this.appendChild(c); }
  replaceWith(n) {
    if (!this.parentNode) return;
    const i = this.parentNode.children.indexOf(this);
    if (i >= 0) { this.parentNode.children[i] = n; n.parentNode = this.parentNode; this.parentNode = null; }
  }
  focus() {}
  dispatchEvent(event) { return this.dispatch(event.type, event); }
  contains(t) { if (t === this) return true; return this.children.some((c) => c.contains(t)); }
  closest(sel) {
    let node = this;
    while (node) { if (node._match(sel)) return node; node = node.parentNode; }
    return null;
  }
  _match(sel) {
    if (sel.indexOf(",") !== -1) return sel.split(",").some((p) => this._match(p.trim()));
    // Class selectors: `.foo` or `.foo.bar`, matched against the
    // space-separated class attribute (the stub classList is a no-op
    // recorder, so classes live in attrs only).
    if (/^\.[\w-]+(\.[\w-]+)*$/.test(sel)) {
      const want = sel.slice(1).split(".");
      const have = String(this.attrs.class || "").split(/\s+/).filter(Boolean);
      return want.every((c) => have.indexOf(c) !== -1);
    }
    if (/\s/.test(sel)) {
      const parts = sel.trim().split(/\s+/);
      if (!this._match(parts[parts.length - 1])) return false;
      let node = this.parentNode;
      for (let i = parts.length - 2; i >= 0; i -= 1) {
        while (node && !node._match(parts[i])) node = node.parentNode;
        if (!node) return false;
        node = node.parentNode;
      }
      return true;
    }
    if (/^\w+\[/.test(sel)) {
      const tag = sel.slice(0, sel.indexOf("[")).toUpperCase();
      const rest = sel.slice(sel.indexOf("["));
      const groups = rest.match(/\[[^\]]+\]/g) || [];
      return groups.every((g) => this._match(g));
    }
    let m = sel.match(/^\[([^\]=]+)(?:=("([^"]*)"|'([^']*)'|([^\]]+)))?\]$/);
    if (m) {
      const name = m[1];
      if (m[2] === undefined) return (name in this.attrs) || (name in this);
      const want = m[3] !== undefined ? m[3] : (m[4] !== undefined ? m[4] : m[5]);
      const actual = (name in this.attrs) ? this.attrs[name] : this[name];
      return String(actual) === want;
    }
    m = sel.match(/^(\w+)\[([^\]]+)\]$/);
    if (m) {
      if (this.tagName !== m[1].toUpperCase()) return false;
      return this._match("[" + m[2] + "]");
    }
    if (/^\w+$/.test(sel)) return this.tagName === sel.toUpperCase();
    if (sel === "option:checked") return this.tagName === "OPTION" && !!this.selected;
    return false;
  }
  // Depth-first document order, excluding the node itself: mirrors
  // querySelectorAll on a real Element (unlike the earlier stub, which
  // also returned the context node first and broke form-order reads).
  _all(out) {
    out = out || [];
    for (const c of this.children) { out.push(c); c._all(out); }
    return out;
  }
  querySelector(sel) {
    return this._all().find((e) => e._match(sel)) || null;
  }
  querySelectorAll(sel) {
    return this._all().filter((e) => e._match(sel));
  }
}

function buildWorld(opts) {
  opts = opts || {};
  // Selected identity shown while its lookup is still pending: the seed
  // carries the fragment-parsed name immediately; the lookup resolves
  // the authoritative requester-safe payload when it answers.
  const pendingSeeds = {};
  const calls = { fetch: [], fetchUrls: [], nonFragmentFetch: [], lookupCalls: [], pushState: [], replaceState: [], tagSelectorChange: 0 };
  const docListeners = {};
  const controlled = opts.controlled === true;
  const pendingLookups = [];
  const documentStub = {
    __listeners: docListeners,
    readyState: "complete",
    addEventListener(t, fn) { (docListeners[t] = docListeners[t] || []).push(fn); },
    querySelectorAll(sel) {
      if (sel === "[data-catalogue-filter-form]") return [form];
      if (sel === "[data-report-template-discovery]") return [root];
      if (sel === "[data-tag-selector]") return [selectorRoot];
      return [];
    },
    querySelector(sel) {
      if (sel === "[data-tag-preference-form]") return null;
      return null;
    },
    createElement(tag) { const el = new El(tag); el.__docListeners = docListeners; return el; },
    createTextNode(text) {
      const el = new El("#text");
      el.textContent = String(text);
      el.__docListeners = docListeners;
      return el;
    },
    // importNode returns a same-tree adoptable copy: clone the stub node
    // so replaceWith detaches the OLD results node (a real replace keeps
    // the stale node out of future querySelector results).
    importNode(n) {
      if (!n || !n.attrs) return n;
      const clone = new El(n.tagName.toLowerCase(), Object.assign({}, n.attrs));
      clone.__docListeners = docListeners;
      clone.textContent = n.textContent || "";
      clone.selected = !!n.selected;
      clone.hidden = !!n.hidden;
      n.children.forEach((c) => clone.appendChild(cloneNode(c, clone)));
      return clone;
    },
  };
  function cloneNode(n, parent) {
    const el = new El(n.tagName.toLowerCase(), Object.assign({}, n.attrs));
    el.__docListeners = docListeners;
    el.textContent = n.textContent || "";
    el.selected = !!n.selected;
    el.hidden = !!n.hidden;
    n.children.forEach((c) => el.appendChild(cloneNode(c, el)));
    return el;
  }
  const root = new El("div", { "data-report-template-discovery": "" });
  root.__docListeners = docListeners;
  const form = new El("form", { "data-discovery-form": "", "data-catalogue-filter-form": "" });
  form.__docListeners = docListeners;
  const search = new El("input", { "data-discovery-q": "", name: "q" });
  search.value = opts.q || "";
  search.name = "q";
  const mode = new El("select", { "data-discovery-mode": "", name: "tag_mode" });
  mode.value = opts.mode || "any";
  mode.name = "tag_mode";
  const marker = new El("input", { "data-discovery-marker": "" });
  marker.value = opts.marker || "";
  const status = new El("p", { "data-discovery-status": "" });
  const errorSlot = new El("p", { "data-catalogue-filter-error": "" });
  errorSlot.hidden = true;
  const dirty = new El("p", { "data-catalogue-filter-dirty": "" });
  dirty.hidden = true;
  const results = new El("div", { "data-discovery-results": "" });
  results.setAttribute("data-discovery-applied", opts.applied || "");
  results.setAttribute("data-discovery-mode", opts.mode || "any");
  results.setAttribute("data-discovery-source", opts.source || "");
  results.setAttribute("data-discovery-count", "1");
  const historical = new El("input", { "data-tag-historical": "" });
  historical.type = "checkbox";
  historical.name = "include_historical";
  historical.checked = !!(opts.applied || "").match(/include_historical=1/);
  const native = new El("select", { "data-tag-native": "" });
  native.disabled = true;
  const hiddenBox = new El("div", { "data-tag-hidden-inputs": "" });
  // Sibling hook holder: the live catalogue nests [data-tag-historical]
  // inside the selector's own subtree (a sibling of the hidden inputs
  // from the transport's viewpoint), so resolve the checkbox through
  // the catalogue root here, exactly as production markup does.
  const tagMarker = new El("input", { "data-tag-marker": "" });
  tagMarker.value = opts.marker || "";
  const selectorClear = new El("a", { "data-tag-clear": "", href: "?tag_filter=manual&tag_mode=any" });
  const clearLink = new El("a", { "data-discovery-clear": "", href: "?" + (opts.applied || "") });
  const reapplyLink = new El("a", { "data-discovery-reapply": "", href: "?" });
  const removeLink = new El("a", { "data-discovery-remove": "", href: "?" + (opts.applied || "") });
  form.appendChild(search); form.appendChild(mode); form.appendChild(marker);
  form.appendChild(dirty); form.appendChild(errorSlot); form.appendChild(native);
  form.appendChild(hiddenBox); form.appendChild(tagMarker);
  form.appendChild(selectorClear); form.appendChild(clearLink); form.appendChild(reapplyLink); form.appendChild(removeLink);
  (opts.tagIds || []).forEach((id) => {
    // Server-rendered: the native fallback carries the selected option
    // AND the selector enhancement seeds hidden inputs + chips at init,
    // exactly like production (server renders both; the selector hides
    // the native and owns the enhanced controls from there).
    const option = new El("option", { value: String(id), selected: "" });
    option.selected = true;
    option.textContent = "Tag " + id;
    native.appendChild(option);
  });
  // Full selector subtree, mirroring
  // components/_report_template_tag_selector.html: the REAL selector
  // script enhances this box (disables native, seeds hidden inputs from
  // server-rendered chips). Chips rendered for the visible applied state
  // carry working remove buttons, attached by the selector itself.
  const selectorRoot = new El("div", { "data-tag-selector": "", "data-lookup-url": "/reports/templates/tag-lookup/" });
  selectorRoot.__docListeners = docListeners;
  const enhanced = new El("div", { "data-tag-enhanced": "" });
  enhanced.setAttribute("class", "d-none");
  const tagSearch = new El("input", { "data-tag-search": "" });
  tagSearch.type = "search";
  const tagPanel = new El("div", { "data-tag-panel": "" });
  tagPanel.hidden = true;
  const tagResults = new El("ul", { "data-tag-results": "" });
  tagResults.hidden = true;
  const tagMore = new El("button", { "data-tag-more": "" });
  tagMore.hidden = true;
  const tagStatus = new El("p", { "data-tag-status": "" });
  const chips = new El("div", { "data-tag-chips": "" });
  enhanced.appendChild(tagSearch);
  enhanced.appendChild(historical);
  enhanced.appendChild(chips);
  enhanced.appendChild(tagPanel);
  tagPanel.appendChild(tagResults);
  tagPanel.appendChild(tagMore);
  enhanced.appendChild(tagStatus);
  selectorRoot.appendChild(native);
  selectorRoot.appendChild(enhanced);
  selectorRoot.appendChild(hiddenBox);
  selectorRoot.appendChild(tagMarker);
  form.appendChild(selectorRoot);
  (opts.tagIds || []).forEach((id) => {
    const label = "Tag " + id + ((opts.stateLabels || {})[String(id)] ? " (" + opts.stateLabels[String(id)] + ")" : "");
    const chip = new El("span", { "data-tag-chip": "", "data-tag-id": String(id) });
    const chipLabel = new El("span", { "data-tag-chip-label": "" });
    chipLabel.textContent = label;
    const remove = new El("button", { "data-tag-remove": "", "aria-label": "Remover Tag " + id + " da seleção" });
    remove.type = "button";
    const cross = new El("span", { "aria-hidden": "true" });
    cross.textContent = "×";
    remove.appendChild(cross);
    chip.appendChild(chipLabel);
    chip.appendChild(remove);
    // Mount BEFORE the scripts run: the real selector attaches its own
    // remove handlers to these server-rendered chips at init.
    chips.appendChild(chip);
  });
  root.appendChild(form); root.appendChild(status); root.appendChild(results);
  const fragmentDoc = {
    querySelector(sel) {
      if (sel === "[data-discovery-results]") {
        const fresh = new El("div", { "data-discovery-results": "" });
        const nextApplied = calls.__nextApplied !== undefined ? calls.__nextApplied : (opts.applied || "");
        fresh.setAttribute("data-discovery-applied", nextApplied);
        fresh.setAttribute("data-discovery-mode", calls.__nextMode !== undefined ? calls.__nextMode : (opts.mode || "any"));
        fresh.setAttribute("data-discovery-source", calls.__nextSource !== undefined ? calls.__nextSource : "manual");
        fresh.setAttribute("data-discovery-count", calls.__nextCount !== undefined ? calls.__nextCount : "1");
        // Inert selected options = the fragment's EFFECTIVE applied
        // selection (incl. automatic defaults that carry no tag params).
        const template = new El("template", { "data-template-tag-options": "" });
        template.content = new El("div", {});
        template.content.children = [];
        const optionDefs = calls.__nextOptions !== undefined ? calls.__nextOptions : [];
        for (const def of optionDefs) {
          const option = new El("option", { value: String(def.id) });
          if (installNextOptions.__selectedSet && installNextOptions.__selectedSet.has(String(def.id))) {
            option.setAttribute("selected", "");
          }
          option.textContent = def.label || ("Tag " + def.id);
          template.content.appendChild(option);
        }
        fresh.appendChild(template);
        return fresh;
      }
      return null;
    },
  };
  // Convenience: `__nextSelected=[ids]` renders inert options whose
  // `selected` flags carry exactly those ids (the fragment's EFFECTIVE
  // applied selection, incl. automatic defaults).
  function installNextOptions() {
    if (calls.__nextSelected === undefined) return;
    const selected = new Set((calls.__nextSelected || []).map(String));
    installNextOptions.__selectedSet = selected;
    calls.__nextOptions = (calls.__nextBadges || (calls.__nextSelected || []).map((id) => ({ id: String(id), label: "Tag " + id })));
  }
  const badgeDefs = opts.badgeDefs || {};
  const sandbox = {
    process: { env: process.env },
    document: documentStub,
    window: {
      location: { pathname: "/reports/templates/", search: "?" + (opts.applied || ""), href: "http://t/reports/templates/" },
      history: {
        pushState(s, t, u) { calls.pushState.push(String(u)); sandbox.window.location.search = String(u).split("?")[1] ? "?" + String(u).split("?")[1] : ""; },
        replaceState(s, t, u) { calls.replaceState.push(String(u)); sandbox.window.location.search = String(u).split("?")[1] ? "?" + String(u).split("?")[1] : ""; },
      },
      addEventListener(t, fn) { (sandbox.__winListeners[t] = sandbox.__winListeners[t] || []).push(fn); },
      clearTimeout: clearTimeout,
      setTimeout: setTimeout,
    },
    __winListeners: {},
    URLSearchParams,
    URL,
    DOMParser: function () { this.parseFromString = function () { installNextOptions(); return fragmentDoc; }; },
    AbortController: undefined,
    fetch(url, options) {
      calls.fetchUrls.push(String(url));
      const urlString = String(url);
      if (urlString.indexOf("fragment=results") !== -1) {
        calls.fetch.push(String(url));
        if (controlled) {
          let resolveFetch;
          const promise = new Promise((resolve) => { resolveFetch = resolve; });
          pendingLookups.push({ url: urlString, kind: "fragment", resolve: resolveFetch });
          return promise;
        }
        return Promise.resolve({ ok: true, text() { installNextOptions(); return Promise.resolve('<div data-discovery-results></div>'); } });
      }
      if (urlString.indexOf("selected=") !== -1) {
        const selectedIds = urlString.split("selected=").slice(1).map((part) => decodeURIComponent(part.split("&")[0]));
        calls.lookupCalls.push(urlString);
        const lookupDef = opts.lookupDef;
        if (lookupDef && lookupDef.fail) {
          if (controlled) {
            let resolveFetch;
            const promise = new Promise((resolve) => { resolveFetch = resolve; });
            pendingLookups.push({ url: urlString, kind: "lookup", resolve: resolveFetch, fail: true });
            return promise;
          }
          return Promise.resolve({ ok: false, status: 500, json() { return Promise.resolve({}); }, text() { return Promise.resolve("{}"); } });
        }
        if (controlled || (lookupDef && (lookupDef.delay || lookupDef.badges))) {
          let resolveFetch;
          const promise = new Promise((resolve) => { resolveFetch = resolve; });
          pendingLookups.push({ url: urlString, kind: "lookup", resolve: resolveFetch, ids: selectedIds, respondBadges: lookupDef && lookupDef.badges });
          return promise;
        }
        return Promise.resolve({
          ok: true,
          json() {
            return Promise.resolve({
              results: [],
              selected: selectedIds.map((id) => {
                const def = badgeDefs[String(id)] || {};
                return {
                  id: Number(id),
                  name: def.name || ("Tag " + id),
                  display_name: def.display_name || ("Tag " + id),
                  color: "#007bff",
                  team_abbreviation: "",
                  state: "active",
                  state_label: def.state_label || "",
                  is_historical: false,
                  is_restricted: false,
                };
              }),
              count: 0, page: 1, num_pages: 1, page_size: 20,
              has_next: false, has_previous: false, include_historical: false,
            });
          },
          text() { return Promise.resolve("{}"); },
        });
      }
      return Promise.resolve({ ok: true, text() { return Promise.resolve('<div data-discovery-results></div>'); } });
    },
    CustomEvent: class { constructor(t, o) { this.type = t; this.bubbles = o && o.bubbles; this.detail = (o && o.detail) || {}; } },
    console,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
  };
  function lookupPayload(ids) {
    return {
      ok: true,
      json() {
        return Promise.resolve({
          results: [],
          selected: (ids || []).map((id) => {
            const def = badgeDefs[String(id)] || {};
            return {
              id: Number(id),
              name: def.name || ("Tag " + id),
              display_name: def.display_name || ("Tag " + id),
              color: "#007bff",
              team_abbreviation: "",
              state: "active",
              state_label: def.state_label || "",
              is_historical: false,
              is_restricted: false,
            };
          }),
          count: 0, page: 1, num_pages: 1, page_size: 20,
          has_next: false, has_previous: false, include_historical: false,
        });
      },
      text() { return Promise.resolve("{}"); },
    };
  }
  function resolvePending(kind, payload) {
    const index = pendingLookups.findIndex((p) => p.kind === kind);
    if (index === -1) return null;
    const [pending] = pendingLookups.splice(index, 1);
    if (pending.fail) {
      pending.resolve({ ok: false, status: 500, json() { return Promise.resolve({}); }, text() { return Promise.resolve("{}"); } });
    } else if (kind === "lookup") {
      const badges = pending.respondBadges || pending.ids;
      pending.resolve(lookupPayload(badges));
    } else {
      installNextOptions();
      pending.resolve({ ok: true, text() { return Promise.resolve('<div data-discovery-results></div>'); } });
    }
    return pending;
  }
  // Script load order mirrors the catalogue page (`defer` in document
  // order): real selector first, then host, then transport. Each runs
  // its own start() hook immediately (readyState is complete), in load
  // order, exactly like deferred scripts execute in document order.
  vm.runInNewContext(selectorSource, sandbox);
  vm.runInNewContext(hostSource, sandbox);
  vm.runInNewContext(discoverySource, sandbox);
  form.addEventListener("tag-selector:change", function () { calls.tagSelectorChange += 1; });
  return { calls, sandbox, root, form, search, mode, marker, status, errorSlot, dirty, results, historical, hiddenBox, selectorClear, clearLink, reapplyLink, removeLink, chips, selectorRoot, selectorBox: selectorRoot, tagSearch, native, tagStatus, pendingLookups, resolvePending };
}

const scenario = process.argv[process.argv.length - 1];
const out = {};
function settle() { return new Promise((r) => setTimeout(r, 20)); }
function hiddenIds(w) {
  return w.hiddenBox.querySelectorAll("[data-tag-input]").map((i) => String(i.value));
}
function chipIds(w) {
  return w.chips.querySelectorAll("[data-tag-chip]").map((c) => String(c.getAttribute("data-tag-id")));
}
function clickRemove(w, tagId) {
  const chip = w.chips.querySelectorAll("[data-tag-chip]").find((c) => String(c.getAttribute("data-tag-id")) === String(tagId));
  if (!chip) return false;
  const button = chip.querySelector("[data-tag-remove]");
  if (!button) return false;
  button.dispatch("click", {});
  return true;
}
function chipLabels(w) {
  return w.chips.querySelectorAll("[data-tag-chip]").map((c) => {
    const label = c.querySelector("[data-tag-chip-label]");
    return label ? label.textContent : c.textContent;
  });
}
// Mimics the shared selector's own user-add path (addChip + hidden
// input) for draft additions the harness performs directly.
function addDraftTag(w, id, label) {
  const input = w.sandbox.document.createElement("input");
  input.name = "tags";
  input.value = String(id);
  input.setAttribute("data-tag-input", "");
  w.hiddenBox.appendChild(input);
  const chip = new El("span", { "data-tag-chip": "", "data-tag-id": String(id) });
  const chipLabel = new El("span", { "data-tag-chip-label": "" });
  chipLabel.textContent = label || ("Tag " + id);
  const remove = new El("button", { "data-tag-remove": "", "aria-label": "Remover Tag " + id + " da seleção" });
  remove.type = "button";
  chip.appendChild(chipLabel);
  chip.appendChild(remove);
  w.chips.appendChild(chip);
  return input;
}

(async () => {
  if (scenario === "clean-apply") {
    const w = buildWorld({ q: "", mode: "any", marker: "", applied: "tag_filter=manual&tag_mode=any", tagIds: [] });
    w.form.dispatch("submit", {});
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.pushCount = w.calls.pushState.length;

  } else if (scenario === "dirty-apply") {
    // Draft q=novo against an EMPTY applied state (no q, no tags): the
    // host baseline is the server-rendered EMPTY state while the pending
    // q control holds "novo", so the host reads dirty, does NOT
    // preventDefault, and the transport issues one fragment request.
    const w = buildWorld({ q: "", mode: "any", marker: "", applied: "", tagIds: [] });
    w.search.value = "novo";
    w.form.dispatch("submit", {});
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.fetchUrl = w.calls.fetch[0] || "";
  } else if (scenario === "reconcile") {
    // A applied, B pending: the server-rendered controls hold A while the
    // B draft is typed post-render; submit B (dirty, 1 fetch); success
    // rebaselines the host to B, so the untouched-apart pending state
    // reads clean; a further unrelated pending edit (mode) flips dirty
    // again while the baseline stays B.
    const w = buildWorld({ q: "A", mode: "any", marker: "manual", applied: "q=A&tag_filter=manual&tag_mode=any", tagIds: [] });
    w.search.value = "B";
    w.calls.__nextApplied = "q=B&tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    w.form.dispatch("submit", {});
    await settle();
    out.dirtyHiddenAfterRebaseline = w.dirty.hidden;
    out.fetchCount = w.calls.fetch.length;
    w.mode.value = "all";
    w.form.dispatch("change", { target: w.mode });
    out.dirtyHiddenAfterUnrelatedEdit = w.dirty.hidden;
  } else if (scenario === "popstate") {
    // A-in-all applied, then B applied, then Back: the visible controls
    // wrongly hold B/any while the popped canonical URL/state is A/all.
    // Reconciliation must restore the q AND mode controls plus the host
    // baseline from the popped canonical state without pushing a entry.
    const w = buildWorld({ q: "B", mode: "any", marker: "manual", applied: "q=B&tag_filter=manual&tag_mode=any", tagIds: ["9"] });
    w.search.value = "B";
    w.calls.__nextApplied = "q=A&tag_filter=manual&tag_mode=all";
    w.calls.__nextMode = "all";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = ["3", "5"];
    w.calls.__nextBadges = [
      { id: "3", label: "Tag Três" },
      { id: "5", label: "Tag Cinco" },
    ];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=all";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.searchValue = w.search.value;
    out.pushCount = w.calls.pushState.length;
    out.qAfter = w.search.value;
    out.fetchUrl = w.calls.fetch[0] || "";
    out.modeAfter = w.mode.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.removeWorks = clickRemove(w, "3");
    out.hiddenIdsAfterRemove = hiddenIds(w);
    out.chipIdsAfterRemove = chipIds(w);
    out.tagSelectorChangeCount = w.calls.tagSelectorChange;
    out.lookupCalls = w.calls.lookupCalls.length;
  } else if (scenario === "selector-clear") {
    // Applied tags=7 with pending drafts: q=pendente typed post-render,
    // a pending tag REMOVAL (chip 7 removed via the real selector) and
    // a pending tag ADDITION (11) plus a pending mode. Clear derives
    // manual-empty from the applied state (drops tags=7, keeps applied
    // q which is empty) while ALL pending controls stay untouched and
    // visibly pending against the new manual-empty baseline.
    const w = buildWorld({ q: "", mode: "any", marker: "manual", applied: "tag_filter=manual&tag_mode=any&tags=7", tagIds: ["7"] });
    w.search.value = "pendente";
    clickRemove(w, "7");
    addDraftTag(w, "11", "Tag Onze");
    w.mode.value = "all";
    w.mode.dispatch("change", {});
    w.root.dispatch("click", { target: w.selectorClear });
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.fetchUrl = w.calls.fetch.filter((u) => u.indexOf("fragment=results") !== -1)[0] || "";
    out.qStaysPending = w.search.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.additionSurvives = hiddenIds(w).indexOf("11") !== -1 && chipIds(w).indexOf("11") !== -1;
    out.removalSurvives = hiddenIds(w).indexOf("7") === -1 && chipIds(w).indexOf("7") === -1;
    out.modeStaysPending = w.mode.value;
    out.dirtyHiddenAfterClear = w.dirty.hidden;
  } else if (scenario === "historical") {
    // Toggle ON against applied-without-flag: no model-result request,
    // one replaceState carrying the flag, no push, visible toggle stays
    // ON. Then reconcile to a genuinely new applied state that LACKS the
    // flag (new page load semantics): the checkbox must follow the new
    // canonical state (OFF). A stale reconciliation carrying the same
    // flag the user just affirmed must NOT reverse their toggle.
    const w = buildWorld({ q: "", mode: "any", marker: "", applied: "tag_filter=manual&tag_mode=any", tagIds: [] });
    w.historical.checked = true;
    // Bubbled DOM change: the checkbox notifies ancestors; the host
    // ignores it (option-only) and the transport handles it.
    w.historical.dispatch("change", {});
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.replaceCount = w.calls.replaceState.length;
    out.pushCount = w.calls.pushState.length;
    out.checkedAfter = w.historical.checked;
    out.replaceUrl = w.calls.replaceState[0] || "";
    // Simulate success carrying a genuinely new applied state WITHOUT
    // the flag while the user toggle is ON (e.g. new navigation): force
    // re-reconciliation through the popped canonical path.
    w.calls.__nextApplied = "tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?tag_filter=manual&tag_mode=any";
    w.search.value = "";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    out.checkedAfterNewApplied = w.historical.checked;
  } else if (scenario === "same-canonical") {
    // Direct unit coverage for the canonical-comparison seam: extract
    // the real `sameCanonical` from the transport source and pin its
    // contract (page/fragment-insensitive, order-insensitive).
    const start = transportSource.indexOf("    function sameCanonical(left, right) {");
    const end = transportSource.indexOf("\n    }\n", start) + 6;
    const scope = { URLSearchParams };
    scope.window = scope;
    vm.createContext(scope);
    vm.runInContext(transportSource.slice(start, end) + "\nthis.__sc = sameCanonical;", scope);
    const sameCanonical = scope.__sc;
    out.pageInsensitive = sameCanonical("q=a&tag_mode=any&page=2", "q=a&tag_mode=any");
    out.fragmentInsensitive = sameCanonical("q=a&fragment=results", "q=a");
    out.orderInsensitive = sameCanonical("tags=2&q=a&tags=1", "tags=2&q=a&tags=1");
    out.detectsChange = !sameCanonical("q=a", "q=b");
    out.detectsTagChange = !sameCanonical("tags=1", "tags=2");
  } else if (scenario === "delayed-apply") {
    // Apply B while A is applied, then edit q to C BEFORE the response
    // lands: the Apply success must preserve the post-submission edit
    // (controls keep CURRENT values) while the host baseline moves to
    // the applied B state (dirty stays visible against B).
    const w = buildWorld({ q: "A", mode: "any", marker: "manual", applied: "q=A&tag_filter=manual&tag_mode=any", tagIds: [], controlled: true });
    w.search.value = "B";
    w.calls.__nextApplied = "q=B&tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    w.form.dispatch("submit", {});
    await settle();
    w.search.value = "C";
    w.form.dispatch("input", { target: w.search });
    w.resolvePending("fragment");
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.qAfter = w.search.value;
    out.dirtyHiddenAfter = w.dirty.hidden;
    out.pushCount = w.calls.pushState.length;
  } else if (scenario === "delayed-apply-tags-mode") {
    // Apply B while A is applied, then edit TAGS and MODE after
    // submission but before the response lands: the Apply success
    // must keep both post-submission edits (controls are user-owned)
    // while the host baseline moves to the applied B state.
    const w = buildWorld({ q: "A", mode: "any", marker: "manual", applied: "q=A&tag_filter=manual&tag_mode=any", tagIds: [], controlled: true });
    w.search.value = "B";
    w.calls.__nextApplied = "q=B&tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    w.form.dispatch("submit", {});
    await settle();
    addDraftTag(w, "11", "Tag Onze");
    w.mode.value = "all";
    w.mode.dispatch("change", {});
    w.resolvePending("fragment");
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.qAfter = w.search.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.modeAfter = w.mode.value;
    out.dirtyVisible = !w.dirty.hidden;
    out.pushCount = w.calls.pushState.length;
    out.lookupCalls = w.calls.lookupCalls.length;
  } else if (scenario === "pending-survives-pagination") {
    // Pending drafts survive a scoped pagination success untouched:
    // a tag ADDITION (11), a tag REMOVAL (applied 7 removed via the
    // real selector) and a pending mode all stay visibly pending.
    const w = buildWorld({ q: "", mode: "any", marker: "manual", applied: "tag_filter=manual&tag_mode=any&tags=7", tagIds: ["7"] });
    clickRemove(w, "7");
    addDraftTag(w, "11", "Tag Onze");
    w.mode.value = "all";
    w.mode.dispatch("change", {});
    w.calls.__nextApplied = "tag_filter=manual&tag_mode=any&tags=7";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = ["7"];
    w.calls.__nextBadges = [{ id: "7", label: "Tag Sete" }];
    const pageItem = new El("li", { class: "page-item" });
    const pageNav = new El("ul", { class: "pagination justify-content-center" });
    const pageLink = new El("a", { href: "?tag_filter=manual&tag_mode=any&page=2", class: "page-link" });
    pageItem.appendChild(pageLink);
    pageNav.appendChild(pageItem);
    w.results.appendChild(pageNav);
    w.root.dispatch("click", { target: pageLink });
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.draftTagSurvives = hiddenIds(w).indexOf("11") !== -1;
    out.additionSurvives = hiddenIds(w).indexOf("11") !== -1 && chipIds(w).indexOf("11") !== -1;
    out.removalSurvives = hiddenIds(w).indexOf("7") === -1 && chipIds(w).indexOf("7") === -1;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.modeStaysPending = w.mode.value;
    out.dirtyVisible = !w.dirty.hidden;
  } else if (scenario === "pending-survives-badge") {
    // Pending drafts survive an applied badge-removal success
    // untouched: a tag ADDITION (11), a tag REMOVAL (applied 8
    // removed via the real selector) and a pending mode all stay
    // visibly pending. The badge action moves only the applied
    // baseline (the server fragment's effective selection [8]);
    // the controls keep the user's drafts (7 stays as a draft
    // against the new baseline).
    const w = buildWorld({ q: "", mode: "any", marker: "manual", applied: "tag_filter=manual&tag_mode=any&tags=7&tags=8", tagIds: ["7", "8"] });
    clickRemove(w, "8");
    addDraftTag(w, "11", "Tag Onze");
    w.mode.value = "all";
    w.mode.dispatch("change", {});
    w.calls.__nextApplied = "tag_filter=manual&tag_mode=any&tags=8";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = ["8"];
    w.calls.__nextBadges = [{ id: "8", label: "Tag Oito" }];
    w.root.dispatch("click", { target: w.removeLink });
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.modeStaysPending = w.mode.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.additionSurvives = hiddenIds(w).indexOf("11") !== -1 && chipIds(w).indexOf("11") !== -1;
    out.removalSurvives = hiddenIds(w).indexOf("8") === -1 && chipIds(w).indexOf("8") === -1;
    out.dirtyVisible = !w.dirty.hidden;
  } else if (scenario === "reapply-defaults") {
    // Automatic defaults (no tag params, server-rendered selected
    // options) as the reapply success's effective selection: the
    // applied baseline moves to [21,22] while the canonical URL
    // stays automatic (no automatic→manual conversion).
    const w = buildWorld({ q: "", mode: "any", marker: "", applied: "", tagIds: [], source: "" });
    w.calls.__nextApplied = "";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "saved";
    w.calls.__nextSelected = ["21", "22"];
    w.calls.__nextBadges = [
      { id: "21", label: "Tag Auto Um" },
      { id: "22", label: "Tag Auto Dois" },
    ];
    w.root.dispatch("click", { target: w.reapplyLink });
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    // Controls are user-owned: reapply moves only the applied
    // baseline to the automatic effective selection [21,22]; the
    // (empty) controls are untouched and read dirty against it.
    out.chipIds = chipIds(w);
    out.hiddenIds = hiddenIds(w);
    out.markerAfter = w.marker.value;
    out.modeAfter = w.mode.value;
    out.dirtyVisible = !w.dirty.hidden;
    out.pushCount = w.calls.pushState.length;
    out.removeWorks = clickRemove(w, "21");
    out.hiddenIdsAfterRemove = hiddenIds(w);
  } else if (scenario === "popstate-restore-names") {
    // Popstate to an AUTOMATIC-default state (no tag params): chips
    // rebuild SYNCHRONOUSLY from the fragment's inert option data
    // (ids AND display names/state labels), with NO selected= lookup
    // fetch issued. Reconciled chips keep working remove buttons.
    const w = buildWorld({ q: "B", mode: "any", marker: "manual", applied: "q=B&tag_filter=manual&tag_mode=any", tagIds: ["9"] });
    w.search.value = "B";
    w.calls.__nextApplied = "";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "saved";
    w.calls.__nextSelected = ["21", "22"];
    w.calls.__nextBadges = [
      { id: "21", label: "Tag Auto Um \u2014 Ativa" },
      { id: "22", label: "Tag Auto Dois \u2014 Arquivada" },
    ];
    w.sandbox.window.location.search = "";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.lookupCalls = w.calls.lookupCalls.length;
    out.qAfter = w.search.value;
    out.modeAfter = w.mode.value;
    out.markerAfter = w.marker.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.chipLabels = chipLabels(w);
    out.pushCount = w.calls.pushState.length;
    out.removeWorks = clickRemove(w, "21");
    out.hiddenIdsAfterRemove = hiddenIds(w);
    out.chipIdsAfterRemove = chipIds(w);
    out.tagSelectorChangeCount = w.calls.tagSelectorChange;
  } else if (scenario === "pagination-history") {
    // Pagination to page 2 pushes a history URL that KEEPS page=2;
    // Back (page 1) and Forward (page 2) fetch and restore the
    // popped page without pushing new entries.
    const w = buildWorld({ q: "A", mode: "any", marker: "manual", applied: "q=A&tag_filter=manual&tag_mode=any", tagIds: [] });
    w.calls.__nextApplied = "q=A&tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    const pgItem = new El("li", { class: "page-item" });
    const pgNav = new El("ul", { class: "pagination justify-content-center" });
    const pageLink = new El("a", { href: "?q=A&tag_filter=manual&tag_mode=any&page=2", class: "page-link" });
    pgItem.appendChild(pageLink);
    pgNav.appendChild(pgItem);
    w.results.appendChild(pgNav);
    w.root.dispatch("click", { target: pageLink });
    await settle();
    await settle();
    out.fetchCountAfterPage = w.calls.fetch.length;
    out.pushCountAfterPage = w.calls.pushState.length;
    out.pushedUrl = w.calls.pushState[w.calls.pushState.length - 1] || "";
    out.pageInPushedUrl = out.pushedUrl.indexOf("page=2") !== -1;
    // Back to page 1.
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    await settle();
    out.fetchCountAfterBack = w.calls.fetch.length;
    out.pushCountAfterBack = w.calls.pushState.length;
    out.qAfterBack = w.search.value;
    out.fetchUrlAfterBack = w.calls.fetch[w.calls.fetch.length - 1] || "";
    // Forward to the pushed page-2 URL.
    const pushedQuery = out.pushedUrl.split("?")[1] || "";
    w.sandbox.window.location.search = pushedQuery ? "?" + pushedQuery : "";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    await settle();
    out.fetchCountAfterForward = w.calls.fetch.length;
    out.pushCountAfterForward = w.calls.pushState.length;
    out.qAfterForward = w.search.value;
    out.fetchUrlAfterForward = w.calls.fetch[w.calls.fetch.length - 1] || "";
    out.forwardFetchHasPage = out.fetchUrlAfterForward.indexOf("page=2") !== -1;
  } else if (scenario === "historical-inflight") {
    // Toggle ON while pagination is in flight: when the older response
    // lands, the checkbox stays ON and the newer flag wins in the
    // pushed URL without a model query. The pagination itself still
    // pushes (it changes the canonical URL by adding page=2).
    const w = buildWorld({ q: "", mode: "any", marker: "", applied: "tag_filter=manual&tag_mode=any", tagIds: [], controlled: true });
    w.calls.__nextApplied = "tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    const histItem = new El("li", { class: "page-item" });
    const histNav = new El("ul", { class: "pagination justify-content-center" });
    const pageLink = new El("a", { href: "?tag_filter=manual&tag_mode=any&page=2", class: "page-link" });
    histItem.appendChild(pageLink);
    histNav.appendChild(histItem);
    w.results.appendChild(histNav);
    w.root.dispatch("click", { target: pageLink });
    await settle();
    // Toggle ON while the pagination request is still in flight.
    w.historical.checked = true;
    w.historical.dispatch("change", {});
    await settle();
    const replaceBefore = w.calls.replaceState.length;
    // The older pagination response lands now.
    w.resolvePending("fragment");
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.replaceBeforeLanding = replaceBefore;
    out.checkedAfter = w.historical.checked;
    out.pushCount = w.calls.pushState.length;
    out.pushedUrls = w.calls.pushState.slice();
    out.staleFlagPushed = w.calls.pushState.some((u) => u.indexOf("page=") !== -1 && u.indexOf("include_historical") === -1);
    out.pushedUrlHasPageAndFlag = w.calls.pushState.some((u) => u.indexOf("page=2") !== -1 && u.indexOf("include_historical=1") !== -1);
    out.currentSearch = w.sandbox.window.location.search;
  } else if (scenario === "historical-after-pagination") {
    // Toggle historical AFTER page 2 has landed (its URL pushed with
    // page=2): the option-only replaceState must keep page=2 plus the
    // flag, so a reload/Forward-equivalent popstate fetches page 2.
    const w = buildWorld({ q: "A", mode: "any", marker: "manual", applied: "q=A&tag_filter=manual&tag_mode=any", tagIds: [] });
    w.calls.__nextApplied = "q=A&tag_filter=manual&tag_mode=any";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=any";
    const pgItem = new El("li", { class: "page-item" });
    const pgNav = new El("ul", { class: "pagination justify-content-center" });
    const pageLink = new El("a", { href: "?q=A&tag_filter=manual&tag_mode=any&page=2", class: "page-link" });
    pgItem.appendChild(pageLink);
    pgNav.appendChild(pgItem);
    w.results.appendChild(pgNav);
    w.root.dispatch("click", { target: pageLink });
    await settle();
    await settle();
    out.pushCountAfterPage = w.calls.pushState.length;
    out.pushedUrl = w.calls.pushState[w.calls.pushState.length - 1] || "";
    // Toggle ON now that page 2 is displayed.
    w.historical.checked = true;
    w.historical.dispatch("change", {});
    await settle();
    out.fetchCountAfterToggle = w.calls.fetch.length;
    out.replaceCount = w.calls.replaceState.length;
    out.replaceUrl = w.calls.replaceState[w.calls.replaceState.length - 1] || "";
    out.replaceUrlHasPage2 = out.replaceUrl.indexOf("page=2") !== -1;
    out.replaceUrlHasFlag = out.replaceUrl.indexOf("include_historical=1") !== -1;
    out.currentSearchAfterToggle = w.sandbox.window.location.search;
    out.checkedAfter = w.historical.checked;
    // Reload/Forward-equivalent restoration: popstate on the current
    // (replaced) URL must fetch page 2, not page 1.
    w.calls.__nextApplied = "q=A&tag_filter=manual&tag_mode=any&include_historical=1";
    w.calls.__nextMode = "any";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = [];
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    await settle();
    out.fetchCountAfterRestore = w.calls.fetch.length;
    out.fetchUrlAfterRestore = w.calls.fetch[w.calls.fetch.length - 1] || "";
    out.restoreFetchHasPage2 = out.fetchUrlAfterRestore.indexOf("page=2") !== -1;
    out.restoreFetchHasFlag = out.fetchUrlAfterRestore.indexOf("include_historical=1") !== -1;
    out.pushCountAfterRestore = w.calls.pushState.length;
    out.qAfterRestore = w.search.value;
  } else if (scenario === "historical-during-popstate") {
    // Back B->A with A's response deferred; toggle BEFORE it lands.
    // The final URL must be A+flag (not B), with controls/results = A.
    const w = buildWorld({ q: "B", mode: "any", marker: "manual", applied: "q=B&tag_filter=manual&tag_mode=any", tagIds: ["9"], controlled: true });
    w.search.value = "B";
    w.calls.__nextApplied = "q=A&tag_filter=manual&tag_mode=all";
    w.calls.__nextMode = "all";
    w.calls.__nextSource = "manual";
    w.calls.__nextSelected = ["3", "5"];
    w.calls.__nextBadges = [
      { id: "3", label: "Tag Três" },
      { id: "5", label: "Tag Cinco" },
    ];
    // Back: the browser URL already shows A before the response lands.
    w.sandbox.window.location.search = "?q=A&tag_filter=manual&tag_mode=all";
    for (const fn of w.sandbox.__winListeners["popstate"] || []) fn({});
    await settle();
    out.fetchCountBeforeToggle = w.calls.fetch.length;
    // Toggle ON while A's response is still in flight.
    w.historical.checked = true;
    w.historical.dispatch("change", {});
    await settle();
    out.replaceUrl = w.calls.replaceState[w.calls.replaceState.length - 1] || "";
    out.currentSearchAfterToggle = w.sandbox.window.location.search;
    // A's response lands now.
    w.resolvePending("fragment");
    await settle();
    await settle();
    out.fetchCount = w.calls.fetch.length;
    out.currentSearch = w.sandbox.window.location.search;
    out.urlIsAWithFlag = out.currentSearch.indexOf("q=A") !== -1 && out.currentSearch.indexOf("include_historical=1") !== -1 && out.currentSearch.indexOf("q=B") === -1;
    out.qAfter = w.search.value;
    out.modeAfter = w.mode.value;
    out.hiddenIds = hiddenIds(w);
    out.chipIds = chipIds(w);
    out.checkedAfter = w.historical.checked;
    out.pushCount = w.calls.pushState.length;
  }
  console.log(JSON.stringify(out));
})();

/** Real loader, cancellable event propagation and deterministic navigation timers. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../..", "assets/js/page-loading.js"), "utf8"
);
const passed = [], failed = [];

function dispatch(listeners, scope, type, target, { early = false, late = false, ...properties } = {}) {
  const event = {
    target, button: 0, defaultPrevented: early, ...properties,
    preventDefault() { this.defaultPrevented = true; },
  };
  for (const callback of listeners.get(scope + ":" + type) || []) callback(event);
  // A later document/window listener cancels during the SAME event dispatch.
  if (late) event.preventDefault();
  return event;
}

function environment({ overlay = true, readyState = "complete" } = {}) {
  const classes = new Set(["d-none"]), listeners = new Map(), timers = new Map();
  let now = 0, next = 0;
  const box = { classList: {
    add: name => classes.add(name), remove: name => classes.delete(name),
  } };
  function on(scope, type, callback) {
    const key = scope + ":" + type;
    listeners.set(key, [...(listeners.get(key) || []), callback]);
  }
  const document = {
    readyState, getElementById: () => overlay ? box : null,
    addEventListener: (type, callback) => on("document", type, callback),
  };
  const window = {
    location: { hostname: "eqmd.test", href: "http://eqmd.test/current/", pathname: "/current/" },
    addEventListener: (type, callback) => on("window", type, callback),
  };
  vm.runInNewContext(source, {
    document, window, console: { warn() {} },
    setTimeout(callback, delay = 0) {
      const id = ++next; timers.set(id, { at: now + delay, callback }); return id;
    },
    clearTimeout: id => timers.delete(id),
  });
  function advance(milliseconds) {
    const until = now + milliseconds;
    while (true) {
      const first = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
      if (!first || first[1].at > until) break;
      timers.delete(first[0]); now = first[1].at; first[1].callback();
    }
    now = until;
  }
  return {
    advance, fire: (...args) => dispatch(listeners, ...args),
    visible: () => !classes.has("d-none"), pending: () => timers.size,
  };
}

function element(tag, attrs = {}, classes = []) {
  const url = new URL(attrs.href || "/next/", "http://eqmd.test");
  return {
    hostname: url.hostname, protocol: url.protocol, target: attrs.target || "",
    method: attrs.method || "post", action: attrs.action || "/next/",
    classList: { contains: name => classes.includes(name) },
    getAttribute: name => attrs[name] ?? null,
    hasAttribute: name => Object.hasOwn(attrs, name),
    tagName: tag.toUpperCase(), closest: () => null,
  };
}
function link(attrs = {}, classes = []) {
  const item = element("a", attrs, classes);
  item.closest = selector => selector === "a" ? item : null;
  return item;
}
function check(name, test) {
  try { test(); passed.push(name); }
  catch (error) { failed.push({ name, error: error.message }); }
}

for (const type of ["click", "submit"]) {
  for (const cancellation of ["early", "late"]) {
    check(type + " " + cancellation + " cancellation never displays or arms timeout", () => {
      const env = environment(), target = type === "click" ? link() : element("form");
      env.fire("document", type, target, { [cancellation]: true });
      env.advance(101);
      assert.equal(env.visible(), false);
      assert.equal(env.pending(), 0);
      env.advance(15000);
      assert.equal(env.visible(), false);
    });
  }
  for (const cleanup of ["load", "pageshow"]) {
    check(type + " " + cleanup + " clears already visible feedback", () => {
      const env = environment();
      env.fire("document", type, type === "click" ? link() : element("form"));
      env.advance(101); assert.equal(env.visible(), true);
      env.fire("window", cleanup); env.advance(16000);
      assert.equal(env.visible(), false); assert.equal(env.pending(), 0);
    });
    check(type + " " + cleanup + " cancels pending display", () => {
      const env = environment();
      env.fire("document", type, type === "click" ? link() : element("form"));
      env.fire("window", cleanup); env.advance(101);
      assert.equal(env.visible(), false); assert.equal(env.pending(), 0);
    });
  }
}

check("ordinary links retain 100ms feedback delay and 15s safety timeout", () => {
  const env = environment();
  env.fire("document", "click", link()); env.advance(99);
  assert.equal(env.visible(), false); env.advance(1); assert.equal(env.visible(), true);
  env.advance(15000); assert.equal(env.visible(), false);
});
check("native forms retain feedback after event dispatch completes", () => {
  const env = environment();
  env.fire("document", "submit", element("form")); env.advance(0);
  assert.equal(env.visible(), true); env.advance(15000); assert.equal(env.visible(), false);
});
for (const attrs of [
  { href: "https://foreign.test/" }, { href: "#details" }, { href: "javascript:void(0)" },
  { href: "mailto:someone@example.invalid" }, { href: "tel:123" },
  { target: "_blank" }, { target: "_new" }, { download: "" }, { "data-bs-toggle": "modal" },
]) {
  check("link opt-out " + JSON.stringify(attrs), () => {
    const env = environment(); env.fire("document", "click", link(attrs));
    env.advance(16000); assert.equal(env.visible(), false); assert.equal(env.pending(), 0);
  });
}
for (const className of ["no-loading", "copy-content-btn", "dropdown-toggle"]) {
  check("link class opt-out " + className, () => {
    const env = environment(); env.fire("document", "click", link({}, [className]));
    env.advance(101); assert.equal(env.visible(), false);
  });
}
for (const properties of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }]) {
  check("non-same-window click " + JSON.stringify(properties), () => {
    const env = environment(); env.fire("document", "click", link(), properties);
    env.advance(101); assert.equal(env.visible(), false);
  });
}
for (const attrs of [
  { "data-no-loading": "" }, { "data-ajax": "" },
  { method: "get", action: "http://eqmd.test/current/" },
]) {
  check("form opt-out " + JSON.stringify(attrs), () => {
    const env = environment(); env.fire("document", "submit", element("form", attrs));
    env.advance(101); assert.equal(env.visible(), false);
  });
}
for (const className of ["no-loading", "ajax-form"]) {
  check("form class opt-out " + className, () => {
    const env = environment();
    env.fire("document", "submit", element("form", {}, [className]));
    env.advance(101); assert.equal(env.visible(), false);
  });
}
check("no-overlay documents are safe", () => {
  const env = environment({ overlay: false });
  env.fire("document", "click", link()); env.fire("document", "submit", element("form"));
  env.advance(16000); assert.equal(env.pending(), 0);
});
check("DOMContentLoaded initializes once ready", () => {
  const env = environment({ readyState: "loading" });
  env.fire("document", "DOMContentLoaded"); env.fire("document", "click", link());
  env.advance(100); assert.equal(env.visible(), true);
});
console.log(JSON.stringify({ passed, failed }, null, 2));
process.exitCode = failed.length ? 1 : 0;

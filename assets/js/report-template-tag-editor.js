/**
 * Local progressive classification editor. The enabled native tag_ids select
 * is the only submitted identity source; choices are server-authorized.
 */
(function () {
  "use strict";

  function normalized(text) {
    return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
  }

  function controls(root) {
    if (root.hasAttribute("data-editor-ready")) { return null; }
    var ctx = { root: root, native: root.querySelector('select[name="tag_ids"]') };
    ["native", "enhanced", "search", "panel", "results", "empty", "chips", "status"].forEach(function (name) {
      ctx[name === "native" ? "fallback" : name] = root.querySelector("[data-editor-" + name + "]");
    });
    if (!ctx.native || !ctx.native.multiple || ctx.native.disabled ||
        !ctx.fallback || !ctx.enhanced || !ctx.search || !ctx.panel ||
        !ctx.results || !ctx.empty || !ctx.chips || !ctx.status) { return null; }
    ctx.options = Array.from(ctx.native.options);
    return ctx;
  }

  function showPanel(ctx, visible) {
    ctx.panel.hidden = !visible;
  }

  function selected(ctx) {
    return ctx.options.filter(function (option) { return option.selected; });
  }

  function choose(ctx, option) {
    if (option.selected || option.disabled) { return; }
    option.selected = true;
    render(ctx);
    ctx.search.focus();
  }

  function removeChoice(ctx, option) {
    var index = selected(ctx).indexOf(option);
    option.selected = false;
    render(ctx);
    var buttons = ctx.chips.querySelectorAll("button");
    var destination = buttons[Math.min(index, buttons.length - 1)] || ctx.search;
    destination.focus();
  }

  function resultButton(ctx, option) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "list-group-item list-group-item-action text-start text-break";
    button.style.whiteSpace = "normal";
    button.setAttribute("data-editor-result", option.value);
    button.setAttribute("aria-disabled", String(option.selected || option.disabled));
    button.setAttribute("aria-label", "Adicionar " + option.textContent.trim() +
      (option.selected ? " — Já selecionada" : ""));
    var label = document.createElement("span");
    label.textContent = option.textContent.trim();
    button.appendChild(label);
    if (option.selected) {
      var state = document.createElement("span");
      state.className = "badge bg-secondary ms-2";
      state.textContent = "Selecionada";
      button.appendChild(state);
    }
    button.addEventListener("click", function () { choose(ctx, option); });
    return button;
  }

  function renderResults(ctx) {
    var term = normalized(ctx.search.value.trim());
    var matches = ctx.options.filter(function (option) {
      return normalized(option.textContent).includes(term);
    });
    ctx.results.replaceChildren();
    matches.forEach(function (option) {
      ctx.results.appendChild(resultButton(ctx, option));
    });
    ctx.empty.textContent = ctx.options.length
      ? "Nenhuma tag corresponde à busca." : "Nenhuma tag disponível para seleção.";
    ctx.empty.hidden = matches.length > 0;
  }

  function chip(ctx, option) {
    var wrapper = document.createElement("span");
    wrapper.className = "badge tag-filter-chip d-inline-flex align-items-center gap-1";
    wrapper.setAttribute("data-editor-chip", option.value);
    var label = document.createElement("span");
    label.className = "tag-filter-chip-label";
    label.textContent = option.textContent.trim();
    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "tag-filter-chip-remove";
    remove.setAttribute("data-editor-remove", option.value);
    remove.setAttribute("aria-label", "Remover " + label.textContent + " da seleção");
    var cross = document.createElement("span");
    cross.textContent = "×";
    cross.setAttribute("aria-hidden", "true");
    remove.appendChild(cross);
    remove.addEventListener("click", function () { removeChoice(ctx, option); });
    wrapper.appendChild(label);
    wrapper.appendChild(remove);
    return wrapper;
  }

  function render(ctx) {
    renderResults(ctx);
    ctx.chips.replaceChildren();
    var choices = selected(ctx);
    choices.forEach(function (option) { ctx.chips.appendChild(chip(ctx, option)); });
    ctx.status.textContent = !ctx.options.length ? "Nenhuma tag disponível para seleção."
      : choices.length ? choices.length + " tag(s) selecionada(s)." : "Nenhuma tag selecionada.";
  }

  function handleKey(ctx, event) {
    if (event.key === "Escape") {
      event.preventDefault();
      ctx.search.focus();
      showPanel(ctx, false);
    } else if (event.target === ctx.search && event.key === "Enter") {
      event.preventDefault();
      showPanel(ctx, true);
    }
  }

  function bind(ctx) {
    ctx.search.addEventListener("input", function () {
      renderResults(ctx);
      showPanel(ctx, true);
    });
    ctx.search.addEventListener("focus", function () { showPanel(ctx, true); });
    ctx.search.addEventListener("click", function () { showPanel(ctx, true); });
    ctx.enhanced.addEventListener("keydown", function (event) { handleKey(ctx, event); });
    ctx.native.addEventListener("change", function () { render(ctx); });
    if (ctx.native.form) {
      ctx.native.form.addEventListener("reset", function (event) {
        setTimeout(function () {
          if (!event.defaultPrevented) {
            ctx.search.value = "";
            showPanel(ctx, false);
            render(ctx);
          }
        }, 0);
      });
    }
  }

  function initialize(root) {
    var ctx = controls(root);
    if (!ctx) { return; }
    try {
      render(ctx);
      bind(ctx);
      ctx.fallback.hidden = true;
      ctx.enhanced.hidden = false;
      root.setAttribute("data-editor-ready", "");
    } catch (error) {
      ctx.fallback.hidden = false;
      ctx.enhanced.hidden = true;
    }
  }

  function start() {
    document.querySelectorAll("[data-template-tag-editor]").forEach(initialize);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

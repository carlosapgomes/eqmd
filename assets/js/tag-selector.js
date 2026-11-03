/**
 * Progressive enhancement for the reusable multi-tag selector (S7).
 *
 * The Django template already renders an explicit, requester-filtered state.
 * This script only turns the native multi-select into a searchable lookup:
 * selections still submit as repeated `tags` inputs plus `tag_mode` and the
 * explicit `tag_filter=manual` marker. It also mirrors the current selection
 * into the separate explicit-save form so the saved preference matches what
 * the user sees. It never creates catalogue rows and renders only rows
 * returned by the visibility-checked lookup endpoint.
 *
 * Results are one compact activation row per tag (name, team pill, lifecycle
 * state) instead of a repeated `display_name`. The list stays an action list:
 * a result already in the selection is inert (`aria-disabled` plus a guard in
 * the click handler) and is re-enabled when its chip is removed. Keyboard
 * navigation lives in the search field (ArrowUp/ArrowDown open and enter the
 * list) and in the rows (arrows, Home, End, Escape). Every load announces its
 * progress in the polite status region, and responses that arrive after a
 * newer request are discarded.
 */
(function () {
  "use strict";

  var GENERIC_ERROR = "Filtro de tag inválido.";
  var EMPTY_MESSAGE = "Nenhuma tag visível encontrada.";
  var SEARCHING_MESSAGE = "Buscando tags...";
  var SEARCH_DELAY_MS = 250;
  var SELECTED_TEXT = "Selecionada";
  var INERT_SUFFIX = " — Já selecionada";

  function selectedInput(container, tagId) {
    var inputs = container.querySelectorAll("[data-tag-input]");
    for (var index = 0; index < inputs.length; index += 1) {
      if (inputs[index].value === String(tagId)) {
        return inputs[index];
      }
    }
    return null;
  }

  function chipFor(container, tagId) {
    var chips = container.querySelectorAll("[data-tag-chip]");
    for (var index = 0; index < chips.length; index += 1) {
      if (chips[index].getAttribute("data-tag-id") === String(tagId)) {
        return chips[index];
      }
    }
    return null;
  }

  function initializeSelector(root) {
    var lookupUrl = root.getAttribute("data-lookup-url");
    var native = root.querySelector("[data-tag-native]");
    var enhanced = root.querySelector("[data-tag-enhanced]");
    var search = root.querySelector("[data-tag-search]");
    var historical = root.querySelector("[data-tag-historical]");
    var results = root.querySelector("[data-tag-results]");
    var chips = root.querySelector("[data-tag-chips]");
    var hidden = root.querySelector("[data-tag-hidden-inputs]");
    var marker = root.querySelector("[data-tag-marker]");
    var status = root.querySelector("[data-tag-status]");
    var more = root.querySelector("[data-tag-more]");

    if (!lookupUrl || !native || !enhanced || !results || !chips || !hidden) {
      return;
    }

    native.classList.add("d-none");
    native.disabled = true;
    enhanced.classList.remove("d-none");

    var page = 1;
    var numPages = 1;
    var queryTerm = "";
    var timer = null;
    var requestGeneration = 0;
    var pendingFocus = null;
    var tagsById = {};

    function setStatus(message) {
      if (status) {
        status.textContent = message || "";
      }
    }

    function markManual() {
      if (marker && marker.value !== "manual") {
        marker.value = "manual";
      }
    }

    function isSelected(tagId) {
      return selectedInput(hidden, tagId) !== null;
    }

    function addInput(tagId) {
      if (selectedInput(hidden, tagId)) {
        return;
      }
      var input = document.createElement("input");
      input.type = "hidden";
      input.name = "tags";
      input.value = String(tagId);
      input.setAttribute("data-tag-input", "");
      hidden.appendChild(input);
      markManual();
    }

    function removeInput(tagId) {
      var input = selectedInput(hidden, tagId);
      if (input) {
        input.remove();
      }
      markManual();
    }

    function resultButtons() {
      return results.querySelectorAll("[data-tag-result]");
    }

    function resultButtonFor(tagId) {
      var buttons = resultButtons();
      for (var index = 0; index < buttons.length; index += 1) {
        if (buttons[index].getAttribute("data-tag-id") === String(tagId)) {
          return buttons[index];
        }
      }
      return null;
    }

    function rememberTag(tag) {
      tagsById[String(tag.id)] = {
        display_name: tag.display_name,
        state_label: tag.state_label || "",
      };
    }

    function resultLabel(tagId, selected) {
      var tag = tagsById[String(tagId)];
      var label = "Adicionar " + (tag ? tag.display_name : "");
      if (tag && tag.state_label) {
        label += " — " + tag.state_label;
      }
      return selected ? label + INERT_SUFFIX : label;
    }

    function syncResult(tagId) {
      var button = resultButtonFor(tagId);
      if (!button) {
        return;
      }
      var selected = isSelected(tagId);
      var selection = button.querySelector("[data-tag-result-selected]");
      if (selection) {
        selection.hidden = !selected;
      }
      button.setAttribute("aria-disabled", selected ? "true" : "false");
      button.setAttribute("aria-label", resultLabel(tagId, selected));
    }

    function addedMessage(tag) {
      var state = tag.state_label ? ", " + tag.state_label + "," : "";
      return tag.display_name + state + " adicionada à seleção.";
    }

    function chipLabel(chip) {
      if (!chip || !chip.firstChild) {
        return "";
      }
      return (chip.firstChild.nodeValue || "").replace(/\s+/g, " ").trim();
    }

    function nextRemoveButton(chip) {
      var sibling = chip ? chip.nextElementSibling : null;
      while (sibling) {
        var button = sibling.querySelector("[data-tag-remove]");
        if (button) {
          return button;
        }
        sibling = sibling.nextElementSibling;
      }
      return null;
    }

    function attachRemove(button, tagId) {
      button.addEventListener("click", function () {
        var chip = chipFor(chips, tagId);
        var next = nextRemoveButton(chip);
        var message = chip ? chipLabel(chip) + " removida da seleção." : "";
        removeInput(tagId);
        if (chip) {
          chip.remove();
        }
        setStatus(message);
        syncResult(tagId);
        if (next) {
          next.focus();
        } else if (search) {
          search.focus();
        }
      });
    }

    Array.prototype.forEach.call(
      chips.querySelectorAll("[data-tag-chip]"),
      function (chip) {
        addInput(chip.getAttribute("data-tag-id"));
        var button = chip.querySelector("[data-tag-remove]");
        if (button) {
          attachRemove(button, chip.getAttribute("data-tag-id"));
        }
      }
    );

    function addChip(tag) {
      if (chipFor(chips, tag.id)) {
        return;
      }
      var chip = document.createElement("span");
      chip.className =
        "badge bg-medical-teal d-inline-flex align-items-center gap-1";
      chip.setAttribute("data-tag-chip", "");
      chip.setAttribute("data-tag-id", String(tag.id));

      var label = document.createTextNode(
        tag.state_label
          ? tag.display_name + " (" + tag.state_label + ")"
          : tag.display_name
      );
      chip.appendChild(label);

      var button = document.createElement("button");
      button.type = "button";
      button.className = "btn-close btn-close-white";
      button.style.fontSize = "0.55rem";
      button.setAttribute("aria-label", "Remover " + tag.display_name);
      button.setAttribute("data-tag-remove", "");
      chip.appendChild(button);

      chips.appendChild(chip);
      attachRemove(button, tag.id);
    }

    function addTag(tag) {
      if (!tag || tag.id === undefined) {
        return;
      }
      addInput(tag.id);
      addChip(tag);
    }

    function resultButton(tag) {
      var item = document.createElement("li");
      item.className = "list-group-item list-group-item-action p-0";

      var button = document.createElement("button");
      button.type = "button";
      button.className =
        "btn btn-link btn-sm d-flex align-items-center gap-2 w-100 p-2 lh-lg text-start";
      button.setAttribute("data-tag-result", "");
      button.setAttribute("data-tag-id", String(tag.id));
      button.setAttribute("aria-label", resultLabel(tag.id, false));

      var name = document.createElement("span");
      name.className = "flex-grow-1 text-break";
      name.textContent = tag.name;
      button.appendChild(name);

      if (tag.team_abbreviation) {
        var team = document.createElement("span");
        team.className = "badge rounded-pill bg-light text-dark";
        team.textContent = tag.team_abbreviation;
        button.appendChild(team);
      }

      if (tag.state_label) {
        var state = document.createElement("span");
        state.className = "small text-secondary text-nowrap";
        state.textContent = tag.state_label;
        button.appendChild(state);
      }

      var selection = document.createElement("span");
      selection.className = "small fw-semibold text-nowrap";
      selection.setAttribute("data-tag-result-selected", "");
      selection.textContent = SELECTED_TEXT;
      selection.hidden = true;
      button.appendChild(selection);

      button.addEventListener("click", function () {
        if (isSelected(tag.id)) {
          button.focus();
          return;
        }
        addTag(tag);
        syncResult(tag.id);
        setStatus(addedMessage(tag));
        button.focus();
      });

      item.appendChild(button);
      return item;
    }

    function requestUrl() {
      var params = new URLSearchParams();
      if (queryTerm) {
        params.set("q", queryTerm);
      }
      if (historical && historical.checked) {
        params.set("include_historical", "1");
      }
      params.set("page", String(page));
      params.set("page_size", "20");
      return lookupUrl + "?" + params.toString();
    }

    function focusResult(position) {
      var buttons = resultButtons();
      if (!buttons.length) {
        return false;
      }
      var index =
        position < 0 ? buttons.length - 1 : Math.min(position, buttons.length - 1);
      buttons[index].focus();
      return true;
    }

    function openResults(position) {
      results.hidden = false;
      if (focusResult(position)) {
        return;
      }
      pendingFocus = position;
      load(true);
    }

    function load(reset) {
      requestGeneration += 1;
      var generation = requestGeneration;
      if (reset) {
        page = 1;
        results.replaceChildren();
      }
      setStatus(SEARCHING_MESSAGE);
      fetch(requestUrl(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            return { ok: response.ok, payload: payload };
          });
        })
        .then(function (result) {
          if (generation !== requestGeneration) {
            return;
          }
          if (!result.ok) {
            pendingFocus = null;
            setStatus(result.payload.error || GENERIC_ERROR);
            more.hidden = true;
            return;
          }
          var payload = result.payload;
          numPages = payload.num_pages || 1;
          (payload.results || []).forEach(function (tag) {
            rememberTag(tag);
            results.appendChild(resultButton(tag));
            syncResult(tag.id);
          });
          more.hidden = !payload.has_next;
          results.hidden = false;
          if (!payload.count) {
            setStatus(EMPTY_MESSAGE);
          } else if (reset) {
            setStatus(payload.count + " resultados encontrados.");
          } else {
            setStatus(
              results.childElementCount +
                " de " +
                payload.count +
                " resultados carregados."
            );
          }
          if (pendingFocus !== null) {
            var position = pendingFocus;
            pendingFocus = null;
            focusResult(position);
          }
        })
        .catch(function () {
          if (generation !== requestGeneration) {
            return;
          }
          pendingFocus = null;
          setStatus(GENERIC_ERROR);
          more.hidden = true;
        });
    }

    if (search) {
      search.addEventListener("input", function () {
        window.clearTimeout(timer);
        timer = window.setTimeout(function () {
          queryTerm = search.value.trim();
          load(true);
        }, SEARCH_DELAY_MS);
      });
      search.addEventListener("focus", function () {
        if (!results.childElementCount && page === 1) {
          load(true);
        }
      });
      search.addEventListener("keydown", function (event) {
        if (event.altKey || event.ctrlKey || event.metaKey) {
          return;
        }
        if (event.key === "Escape" || event.key === "Esc") {
          results.hidden = true;
          return;
        }
        if (event.key === "ArrowDown") {
          event.preventDefault();
          openResults(0);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          openResults(-1);
        }
      });
    }

    results.addEventListener("keydown", function (event) {
      var target = event.target;
      if (!target || !target.hasAttribute("data-tag-result")) {
        return;
      }
      if (event.key === "Escape" || event.key === "Esc") {
        event.preventDefault();
        results.hidden = true;
        if (search) {
          search.focus();
        }
        return;
      }
      var buttons = resultButtons();
      var index = Array.prototype.indexOf.call(buttons, target);
      if (index < 0) {
        return;
      }
      var next;
      if (event.key === "ArrowDown") {
        next = index + 1;
      } else if (event.key === "ArrowUp") {
        next = index - 1;
      } else if (event.key === "Home") {
        next = 0;
      } else if (event.key === "End") {
        next = buttons.length - 1;
      } else {
        return;
      }
      event.preventDefault();
      if (next < 0) {
        if (search) {
          search.focus();
        }
        return;
      }
      if (next < buttons.length) {
        buttons[next].focus();
      }
    });

    if (historical) {
      historical.addEventListener("change", function () {
        load(true);
      });
    }

    if (more) {
      more.addEventListener("click", function () {
        if (page < numPages) {
          page += 1;
          load(false);
        }
      });
    }

    var preferenceForm = document.querySelector("[data-tag-preference-form]");
    if (preferenceForm) {
      preferenceForm.addEventListener("submit", function () {
        var container = preferenceForm.querySelector(
          "[data-tag-preference-tags]"
        );
        if (container) {
          container.replaceChildren();
          Array.prototype.forEach.call(
            hidden.querySelectorAll("[data-tag-input]"),
            function (input) {
              var copy = document.createElement("input");
              copy.type = "hidden";
              copy.name = "tags";
              copy.value = input.value;
              container.appendChild(copy);
            }
          );
        }
        var modeField = preferenceForm.querySelector(
          "[data-tag-preference-mode]"
        );
        var modeSelect = root.querySelector('select[name="tag_mode"]');
        if (modeField && modeSelect) {
          modeField.value = modeSelect.value;
        }
      });
    }
  }

  function start() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-tag-selector]"),
      initializeSelector
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

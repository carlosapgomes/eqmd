/**
 * Progressive enhancement for the reusable multi-tag selector (S7).
 *
 * The Django template already renders an explicit, requester-filtered state.
 * This script only turns the native multi-select into a searchable lookup:
 * selections still submit as repeated `tags` inputs plus `tag_mode` and the
 * explicit `tag_filter=manual` marker. It never creates catalogue rows and
 * renders only rows returned by the visibility-checked lookup endpoint.
 */
(function () {
  "use strict";

  var GENERIC_ERROR = "Filtro de tag inválido.";
  var EMPTY_MESSAGE = "Nenhuma tag visível encontrada.";
  var SEARCH_DELAY_MS = 250;

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

    function attachRemove(button, tagId) {
      button.addEventListener("click", function () {
        removeInput(tagId);
        var chip = chipFor(chips, tagId);
        if (chip) {
          chip.remove();
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
      item.className = "list-group-item list-group-item-action p-2";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-link btn-sm p-0 text-start w-100";
      button.textContent = tag.display_name;
      button.addEventListener("click", function () {
        addTag(tag);
        setStatus("");
      });
      item.appendChild(button);
      if (tag.state_label || tag.team_abbreviation) {
        var meta = document.createElement("small");
        meta.className = "d-block text-muted";
        meta.textContent = [tag.team_abbreviation, tag.state_label]
          .filter(Boolean)
          .join(" · ");
        item.appendChild(meta);
      }
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

    function load(reset) {
      if (reset) {
        page = 1;
        results.replaceChildren();
        setStatus("");
      }
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
          if (!result.ok) {
            setStatus(result.payload.error || GENERIC_ERROR);
            more.hidden = true;
            return;
          }
          var payload = result.payload;
          numPages = payload.num_pages || 1;
          (payload.results || []).forEach(function (tag) {
            results.appendChild(resultButton(tag));
          });
          more.hidden = !payload.has_next;
          results.hidden = false;
          if (!payload.count) {
            setStatus(EMPTY_MESSAGE);
          }
        })
        .catch(function () {
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
    }

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

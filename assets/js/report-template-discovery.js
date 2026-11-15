/**
 * Progressive enhancement for report-template catalogue discovery (S2, D5).
 *
 * The server-rendered GET form and results partial are the no-JavaScript
 * contract. This script only refreshes the results fragment in place:
 * debounced name search (250 ms), Apply, clear/reapply, badge removal and
 * pagination fetch ``fragment=results``; the historical toggle fetches the
 * same fragment but replaces only the native select options, preserving
 * focus, selections, query, mode and automatic/manual origin. Each request
 * carries a generation number so stale responses never replace newer ones;
 * typing a new query bumps that generation and aborts the in-flight
 * request immediately, so an obsolete response cannot render during the
 * debounce window. A failed request keeps the current results and
 * selections while announcing a generic error. Labels are moved as DOM
 * nodes (cloneNode / textContent), never assembled as raw HTML.
 *
 * Last-applied state (``data-discovery-applied`` on the results root,
 * updated after each successful refresh) is the single source of truth.
 * Only Apply moves pending choices into the applied state; search, the
 * historical toggle and delegated clear/reapply/badge-remove/pagination
 * clicks all build their requests from it plus only their own parameter
 * (``q`` / ``include_historical`` / cleared predicate / page / removed
 * tag), preserving pending selections in the controls. Every
 * non-search request cancels a pending search debounce first, so a
 * timer scheduled by typing cannot abort a later Apply. Cancelling
 * that timer (or aborting an in-flight search) records the outstanding
 * search intent instead of losing it: after the intervening request
 * succeeds and ``rememberApplied`` has run, the recorded intent is
 * replayed at once through the normal search path against the newly
 * applied state plus the current input ``q``. The replay is dropped
 * when it would be redundant -- notably after a successful Apply,
 * whose request already carries the input ``q``, so applied and input
 * ``q`` agree and no second search is needed; if they differ, the
 * intent is kept and replayed. A failed intervening request keeps the recorded
 * intent for the next successful refresh. After each
 * successful refresh the historical checkbox and every canonical link
 * href are reconciled to the new applied state, so links outside the
 * replaced results root (clear/reapply) and links inside a fragment
 * kept by an options-only toggle (pagination/badge) never go stale.
 * Server-rendered hrefs stay canonical for the no-JS flow; delegated
 * clicks re-derive from applied state instead of trusting them.
 */
(function () {
  "use strict";

  var GENERIC_ERROR = "Não foi possível atualizar os resultados.";
  var SEARCHING_MESSAGE = "Atualizando resultados...";
  var SEARCH_DELAY_MS = 250;
  var EMPTY_MESSAGE = "Nenhum template encontrado.";

  function initializeDiscovery(root) {
    var form = root.querySelector("[data-discovery-form]");
    var search = root.querySelector("[data-discovery-q]");
    var select = root.querySelector("[data-discovery-tags]");
    var mode = root.querySelector("[data-discovery-mode]");
    var marker = root.querySelector("[data-discovery-marker]");
    var historical = root.querySelector("[data-discovery-historical]");
    var status = root.querySelector("[data-discovery-status]");
    var results = root.querySelector("[data-discovery-results]");

    if (!form || !search || !select || !mode || !marker || !results) {
      return;
    }

    var timer = null;
    var generation = 0;
    var controller = null;
    var inFlightIsSearch = false;
    // Outstanding typed-search intent dropped by cancelling its
    // debounce timer or by aborting an in-flight search. Replayed
    // once after the intervening request succeeds; kept across a
    // failed intervening request so a later success can still honour
    // it. See the success handler in applyFragment.
    var pendingSearchWanted = false;
    // Last-applied canonical state, seeded from the server-rendered
    // results root. Pending tag/mode edits in the controls never enter
    // it until Apply (or a canonical link) succeeds.
    var appliedParams = new URLSearchParams(
      results.getAttribute("data-discovery-applied") || ""
    );
    appliedParams.delete("fragment");
    appliedParams.delete("page");

    function abortInFlight() {
      // Aborting an in-flight search drops the same typed intent as
      // cancelling its timer would; record it so the action that
      // superseded the search can replay it against the newly
      // applied state once that action succeeds. Record and clear
      // the search flag independently of AbortController: without
      // a controller the generation guard already ignores the
      // superseded search response, but the intent must still be
      // recorded so the replay can honour the typed query.
      if (inFlightIsSearch) {
        pendingSearchWanted = true;
      }
      inFlightIsSearch = false;
      if (controller) {
        controller.abort();
        controller = null;
      }
    }

    function setStatus(message) {
      if (status) {
        status.textContent = message || "";
      }
    }

    // Pending form controls: only the explicit Apply flow may build a
    // request from these, so unapplied tag/mode edits stay unapplied.
    function pendingParams() {
      var params = new URLSearchParams();
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      }
      // Only an explicit Apply (or a manual-origin link) makes tag state
      // manual; typing q or paginating never converts automatic defaults.
      if (marker.value === "manual") {
        params.set("tag_filter", "manual");
        params.set("tag_mode", mode.value);
        Array.prototype.forEach.call(select.selectedOptions, function (option) {
          params.append("tags", option.value);
        });
      }
      if (historical && historical.checked) {
        params.set("include_historical", "1");
      }
      return params;
    }

    // Search builds from the last-applied predicate, changing only q.
    function searchParams() {
      var params = new URLSearchParams(appliedParams);
      params.delete("page");
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      } else {
        params.delete("q");
      }
      return params;
    }

    // The historical toggle builds from the last-applied predicate,
    // changing only include_historical, so the canonical URL it writes
    // cannot commit pending tag/mode choices.
    function historicalParams() {
      var params = new URLSearchParams(appliedParams);
      params.delete("page");
      if (historical && historical.checked) {
        params.set("include_historical", "1");
      } else {
        params.delete("include_historical");
      }
      return params;
    }

    function rememberApplied(params) {
      appliedParams = new URLSearchParams(params);
      appliedParams.delete("fragment");
      appliedParams.delete("page");
    }

    // A non-search action must cancel a pending search debounce: the
    // timer was scheduled from the pre-Apply applied state and would
    // otherwise abort the Apply request when it fires. Dropping the
    // timer must not drop the search itself, so record the intent for
    // replay after this action succeeds (see applyFragment).
    function cancelPendingSearch() {
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
        pendingSearchWanted = true;
      }
    }

    // Delegated link clicks derive their request from the last-applied
    // state plus the link's own single parameter, instead of trusting a
    // href that predates the latest search/toggle/Apply. Server-rendered
    // hrefs stay canonical for the no-JS flow; this only re-derives the
    // enhanced request at click time.
    function linkParams(link) {
      var hrefParams = new URLSearchParams(
        new URL(link.getAttribute("href"), window.location.href).search
      );
      if (link.hasAttribute("data-discovery-clear")) {
        // Clear preserves the applied q/historical and the applied mode
        // (falling back to the server-rendered mode for an automatic
        // applied state, which carries no tag_mode of its own).
        var clear = new URLSearchParams(appliedParams);
        clear.delete("tags");
        clear.delete("tag");
        clear.delete("page");
        clear.set("tag_filter", "manual");
        clear.set(
          "tag_mode",
          appliedParams.get("tag_mode") || hrefParams.get("tag_mode") || "any"
        );
        return clear;
      }
      if (link.hasAttribute("data-discovery-reapply")) {
        var reapply = new URLSearchParams(appliedParams);
        reapply.delete("tags");
        reapply.delete("tag");
        reapply.delete("tag_mode");
        reapply.delete("tag_filter");
        reapply.delete("page");
        return reapply;
      }
      if (link.hasAttribute("data-discovery-remove")) {
        // The href already encodes applied-minus-one-tag, including
        // automatic defaults the applied state does not carry; re-sync
        // only q/include_historical, which can go stale after a toggle.
        var remove = new URLSearchParams(hrefParams);
        remove.delete("q");
        if (appliedParams.has("q")) {
          remove.set("q", appliedParams.get("q"));
        }
        remove.delete("include_historical");
        if (appliedParams.has("include_historical")) {
          remove.set("include_historical", "1");
        }
        remove.delete("page");
        return remove;
      }
      var pageParams = new URLSearchParams(appliedParams);
      pageParams.delete("page");
      var page = hrefParams.get("page");
      if (page) {
        pageParams.set("page", page);
      }
      return pageParams;
    }

    function syncHistoricalCheckbox() {
      if (historical) {
        historical.checked = appliedParams.has("include_historical");
      }
    }

    // Keep canonical hrefs in the live DOM reconciled to the applied
    // state, including clear/reapply outside the results root and
    // pagination/badge links inside a fragment kept by a toggle.
    function reconcileLinks() {
      Array.prototype.forEach.call(
        root.querySelectorAll(
          "[data-discovery-clear], [data-discovery-reapply], " +
            "[data-discovery-remove], .pagination .page-link[href]"
        ),
        function (link) {
          var params = linkParams(link);
          params.delete("fragment");
          link.setAttribute("href", "?" + params.toString());
        }
      );
    }

    function fragmentUrl(params) {
      params.set("fragment", "results");
      return window.location.pathname + "?" + params.toString();
    }

    function canonicalUrl(params) {
      params.delete("fragment");
      var queryString = params.toString();
      return window.location.pathname + (queryString ? "?" + queryString : "");
    }

    function syncControls(fragmentRoot, preservePending) {
      var source = fragmentRoot.getAttribute("data-discovery-source");
      var fragmentMode = fragmentRoot.getAttribute("data-discovery-mode");
      // A search refresh is not Apply: keep the pending mode/selections
      // visible in the controls while the results use the applied state.
      if (fragmentMode && !preservePending) {
        mode.value = fragmentMode;
      }
      marker.value = source === "manual" ? "manual" : "";
      replaceOptions(fragmentRoot, preservePending);
      var count = fragmentRoot.getAttribute("data-discovery-count");
      if (count === "0") {
        setStatus(EMPTY_MESSAGE);
      } else if (count !== null) {
        setStatus(count + " resultados encontrados.");
      }
    }

    function replaceOptions(fragmentRoot, preserveSelection) {
      var template = fragmentRoot.querySelector(
        "template[data-template-tag-options]"
      );
      if (!template || !template.content) {
        return;
      }
      // A historical-toggle refresh is not Apply: keep the selections the
      // user currently sees, whatever the server's effective selections
      // are. A preserved identity the fragment does not offer (for
      // example a selected readable historical option while historical
      // choices are toggled off on an automatic-default page) is retained
      // as its own option so the choice itself is never discarded.
      var preservedOptions = [];
      var preservedIds = [];
      if (preserveSelection) {
        preservedOptions = Array.prototype.slice.call(select.selectedOptions);
        preservedIds = preservedOptions.map(function (option) {
          return option.value;
        });
      }
      var options = template.content.querySelectorAll("option");
      var seen = {};
      select.replaceChildren();
      Array.prototype.forEach.call(options, function (option) {
        var clone = option.cloneNode(true);
        seen[clone.value] = true;
        if (preserveSelection) {
          clone.selected = preservedIds.indexOf(clone.value) !== -1;
        }
        select.appendChild(clone);
      });
      if (preserveSelection) {
        preservedOptions.forEach(function (option) {
          if (!seen[option.value]) {
            var retained = option.cloneNode(true);
            retained.selected = true;
            select.appendChild(retained);
          }
        });
      }
    }

    function applyFragment(params, options) {
      // Every request (Apply, clear/reapply, toggle, pagination, badge
      // removal, and the search timer itself) starts here, so cancelling
      // any pending debounce here covers all non-search actions.
      cancelPendingSearch();
      abortInFlight();
      generation += 1;
      var requestGeneration = generation;
      inFlightIsSearch = !!(options && options.isSearch);
      controller =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      setStatus(SEARCHING_MESSAGE);
      fetch(fragmentUrl(params), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
        signal: controller ? controller.signal : undefined,
      })
        .then(function (response) {
          return response.text().then(function (body) {
            return { ok: response.ok, body: body };
          });
        })
        .then(function (result) {
          if (requestGeneration !== generation) {
            return;
          }
          if (!result.ok) {
            setStatus(GENERIC_ERROR);
            return;
          }
          var parser = new DOMParser();
          var documentFragment = parser.parseFromString(
            result.body,
            "text/html"
          );
          var fresh = documentFragment.querySelector("[data-discovery-results]");
          if (!fresh) {
            setStatus(GENERIC_ERROR);
            return;
          }
          rememberApplied(params);
          if (options && options.optionsOnly) {
            replaceOptions(fresh, true);
            setStatus("Opções de tags atualizadas.");
          } else {
            results.replaceWith(document.importNode(fresh, true));
            results = root.querySelector("[data-discovery-results]");
            syncControls(results, options && options.preservePending);
          }
          syncHistoricalCheckbox();
          reconcileLinks();
          window.history.pushState(null, "", canonicalUrl(params));
          // Replay a typed search dropped by this intervening action.
          // rememberApplied has run, so searchParams() builds from the
          // newly applied state plus the current input q, through the
          // normal generation/abort-guarded search path. The intent
          // is honoured only when the input q still differs from the
          // applied q: after a successful Apply the applied q already
          // is the input q, so the intent is dropped as redundant;
          // after toggle/clear/reapply/pagination/badge-removal the
          // applied q is still the old q, so the mismatch keeps the
          // intent and the replay restarts paging at page 1 with the
          // intervening action's state preserved. searchParams()
          // never commits pending tag/mode choices, and the replay
          // starts only now, after this request succeeded, so it
          // cannot race or abort Apply. A failed request never
          // reaches here, so its recorded intent survives for the
          // next successful refresh.
          var wantsSearch = pendingSearchWanted;
          pendingSearchWanted = false;
          var appliedQuery = (appliedParams.get("q") || "").trim();
          var currentQuery = search.value.trim();
          if (wantsSearch && currentQuery !== appliedQuery) {
            applyFragment(searchParams(), {
              preservePending: true,
              isSearch: true,
            });
          }
        })
        .catch(function () {
          if (requestGeneration !== generation) {
            return;
          }
          setStatus(GENERIC_ERROR);
        });
    }

    function fetchLink(link) {
      applyFragment(linkParams(link));
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (marker.value !== "manual") {
        marker.value = "manual";
      }
      applyFragment(pendingParams());
    });

    search.addEventListener("input", function () {
      // Invalidate any in-flight response immediately: a request started
      // for the previous query must not render while this query debounces.
      generation += 1;
      abortInFlight();
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        // The timer has fired; clear its id first so applyFragment's
        // cancelPendingSearch does not record its own search as a
        // dropped intent.
        timer = null;
        applyFragment(searchParams(), {
          preservePending: true,
          isSearch: true,
        });
      }, SEARCH_DELAY_MS);
    });

    if (historical) {
      historical.addEventListener("change", function () {
        applyFragment(historicalParams(), { optionsOnly: true });
      });
    }

    root.addEventListener("click", function (event) {
      var link = event.target.closest(
        "[data-discovery-clear], [data-discovery-reapply], " +
          "[data-discovery-remove], .pagination .page-link"
      );
      if (!link || !link.getAttribute("href")) {
        return;
      }
      event.preventDefault();
      fetchLink(link);
    });
  }

  // Report-creation selector (S3, D6): same discovery semantics as the
  // catalogue, but results come from the JSON lookup endpoint and the
  // bounded clinical select is refreshed without touching title, date,
  // EasyMDE content or the current selection, and without dispatching
  // the select's change handler (which would navigate to the GET
  // prefill flow). Only discovery interactions have this guarantee;
  // explicitly choosing another model still uses that prefill flow.
  function initializeSelection(root) {
    var lookupUrl = root.getAttribute("data-template-selection-url");
    var form = root.querySelector("[data-discovery-form]");
    var search = root.querySelector("[data-discovery-q]");
    var select = root.querySelector("[data-discovery-tags]");
    var mode = root.querySelector("[data-discovery-mode]");
    var marker = root.querySelector("[data-discovery-marker]");
    var historical = root.querySelector("[data-discovery-historical]");
    var status = root.querySelector("[data-discovery-status]");
    var results = root.querySelector("[data-template-selection-results]");
    var clinicalSelect = document.getElementById("id_template");
    var warning = root.querySelector("[data-template-selection-warning]");
    if (!lookupUrl || !form || !search || !select || !mode || !marker || !results || !clinicalSelect) {
      return;
    }
    if (warning) {
      warning.style.display = "none";
    }
    var timer = null;
    var generation = 0;
    var controller = null;
    var inFlightIsSearch = false;
    var pendingSearchWanted = false;
    var appliedParams = new URLSearchParams(
      results.getAttribute("data-discovery-applied") || ""
    );
    appliedParams.delete("fragment");
    appliedParams.delete("page");
    // The page actually displayed in the results list/nav. The
    // options-only historical lookup must preserve it so the
    // returned options, clinical choices and notices describe the
    // same page the user sees (rt2-1). Updated from every payload.
    var displayedPage =
      results.getAttribute("data-template-selection-page") || "1";

    function abortInFlight() {
      if (inFlightIsSearch) {
        pendingSearchWanted = true;
      }
      inFlightIsSearch = false;
      if (controller) {
        controller.abort();
        controller = null;
      }
    }
    function setStatus(message) {
      if (status) {
        status.textContent = message || "";
      }
    }
    function pendingParams() {
      var params = new URLSearchParams();
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      }
      if (marker.value === "manual") {
        params.set("tag_filter", "manual");
        params.set("tag_mode", mode.value);
        Array.prototype.forEach.call(select.selectedOptions, function (option) {
          params.append("tags", option.value);
        });
      }
      if (historical && historical.checked) {
        params.set("include_historical", "1");
      }
      return params;
    }
    function searchParams() {
      var params = new URLSearchParams(appliedParams);
      params.delete("page");
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      } else {
        params.delete("q");
      }
      return params;
    }
    function historicalParams() {
      var params = new URLSearchParams(appliedParams);
      params.delete("page");
      // Preserve the displayed page: without it the server returns
      // page-1 choices while page 2 stays visible.
      if (displayedPage && displayedPage !== "1") {
        params.set("page", displayedPage);
      }
      if (historical && historical.checked) {
        params.set("include_historical", "1");
      } else {
        params.delete("include_historical");
      }
      return params;
    }
    function rememberApplied(params) {
      appliedParams = new URLSearchParams(params);
      appliedParams.delete("fragment");
      appliedParams.delete("page");
    }
    function cancelPendingSearch() {
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
        pendingSearchWanted = true;
      }
    }
    function linkParams(link) {
      var hrefParams = new URLSearchParams(
        new URL(link.getAttribute("href"), window.location.href).search
      );
      if (link.hasAttribute("data-discovery-clear")) {
        var clear = new URLSearchParams(appliedParams);
        clear.delete("tags");
        clear.delete("tag");
        clear.delete("page");
        clear.set("tag_filter", "manual");
        clear.set(
          "tag_mode",
          appliedParams.get("tag_mode") || hrefParams.get("tag_mode") || "any"
        );
        return clear;
      }
      if (link.hasAttribute("data-discovery-reapply")) {
        var reapply = new URLSearchParams(appliedParams);
        reapply.delete("tags");
        reapply.delete("tag");
        reapply.delete("tag_mode");
        reapply.delete("tag_filter");
        reapply.delete("page");
        return reapply;
      }
      if (link.hasAttribute("data-discovery-remove")) {
        var remove = new URLSearchParams(hrefParams);
        remove.delete("q");
        if (appliedParams.has("q")) {
          remove.set("q", appliedParams.get("q"));
        }
        remove.delete("include_historical");
        if (appliedParams.has("include_historical")) {
          remove.set("include_historical", "1");
        }
        remove.delete("page");
        return remove;
      }
      var pageParams = new URLSearchParams(appliedParams);
      pageParams.delete("page");
      var page = hrefParams.get("page");
      if (page) {
        pageParams.set("page", page);
      }
      return pageParams;
    }
    function syncHistoricalCheckbox() {
      if (historical) {
        historical.checked = appliedParams.has("include_historical");
      }
    }
    function reconcileLinks() {
      Array.prototype.forEach.call(
        root.querySelectorAll(
          "[data-discovery-clear], [data-discovery-reapply], " +
            "[data-discovery-remove]"
        ),
        function (link) {
          var params = linkParams(link);
          link.setAttribute("href", "?" + params.toString());
        }
      );
    }
    function makeOption(value, label, selected) {
      var option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = !!selected;
      return option;
    }
    function replaceTagOptions(options, preserveSelection, retainedOptions) {
      // Preserve pending choices the rebuilt set omits (e.g. an
      // archived tag selected with the historical toggle on, then
      // toggled off before Apply) only when the server authorizes
      // them: ``retained_tag_options`` in the payload is the
      // resolved readable projection for the pending ids sent with
      // the lookup (see lookupUrlFor). A pending id the server does
      // not authorize (revoked readability) is dropped, never cloned
      // from the stale DOM option, and retained labels are rebuilt
      // from the authorized projection. Retention never applies a
      // filter: the ids travel as ``retained_tags``, not ``tags``.
      var preservedIds = [];
      if (preserveSelection) {
        preservedIds = Array.prototype.map.call(
          select.selectedOptions,
          function (option) {
            return option.value;
          }
        );
      }
      var seen = {};
      select.replaceChildren();
      (options || []).forEach(function (item) {
        var label = item.display_name;
        if (item.state_label) {
          label += " — " + item.state_label;
        }
        var isSelected = preserveSelection
          ? preservedIds.indexOf(String(item.tag_id)) !== -1
          : !!item.is_selected;
        select.appendChild(
          makeOption(String(item.tag_id), label, isSelected)
        );
        seen[String(item.tag_id)] = true;
      });
      if (preserveSelection) {
        var authorized = {};
        (retainedOptions || []).forEach(function (item) {
          authorized[String(item.tag_id)] = item;
        });
        preservedIds.forEach(function (id) {
          var item = authorized[id];
          if (!seen[id] && item) {
            var label = item.display_name;
            if (item.state_label) {
              label += " — " + item.state_label;
            }
            select.appendChild(makeOption(id, label, true));
          }
        });
      }
    }
    function updateClinicalSelect(payload) {
      var currentValue = clinicalSelect.value;
      var seen = {};
      clinicalSelect.replaceChildren();
      clinicalSelect.appendChild(makeOption("", "---------", !currentValue));
      (payload.results || []).forEach(function (item) {
        clinicalSelect.appendChild(
          makeOption(item.id, item.name, item.id === currentValue)
        );
        seen[item.id] = true;
      });
      if (currentValue && !seen[currentValue]) {
        if (payload.selection_unavailable) {
          clinicalSelect.appendChild(
            makeOption(currentValue, "Modelo selecionado indisponível", true)
          );
        } else if (payload.selected) {
          clinicalSelect.appendChild(
            makeOption(
              payload.selected.id,
              payload.selected.name + " (fora dos resultados atuais)",
              true
            )
          );
        } else {
          clinicalSelect.appendChild(
            makeOption(currentValue, "Modelo selecionado indisponível", true)
          );
        }
      }
      // Restore the value without dispatching change: replacing options
      // already reset it, and setting .value fires no event.
      clinicalSelect.value = currentValue;
    }
    function reconcileSelectionNotices(payload) {
      // Outside notice only when the selected id is absent from the
      // current results; unavailable notice only when the lookup
      // reports the selection unavailable. Create the elements when
      // the initial render omitted them (empty/filtered states).
      var inResults = !!(
        payload.selected &&
        (payload.results || []).some(function (item) {
          return item.id === payload.selected.id;
        })
      );
      var outside = results.querySelector("[data-selected-template-outside]");
      if (!outside) {
        outside = document.createElement("div");
        outside.className = "alert alert-info";
        outside.setAttribute("role", "status");
        outside.setAttribute("data-selected-template-outside", "");
        var listForOutside = results.querySelector(
          "[data-template-selection-list]"
        );
        if (listForOutside) {
          results.insertBefore(outside, listForOutside);
        } else {
          results.appendChild(outside);
        }
      }
      var unavailable = results.querySelector(
        "[data-selected-template-unavailable]"
      );
      if (!unavailable) {
        unavailable = document.createElement("div");
        unavailable.className = "alert alert-warning";
        unavailable.setAttribute("role", "alert");
        unavailable.setAttribute("data-selected-template-unavailable", "");
        results.insertBefore(unavailable, outside);
      }
      if (payload.selection_unavailable) {
        unavailable.textContent =
          "Modelo selecionado indisponível. Para criar manualmente, " +
          "limpar a seleção atual.";
        unavailable.hidden = false;
        unavailable.style.display = "";
      } else {
        unavailable.hidden = true;
        unavailable.style.display = "none";
      }
      if (payload.selected && !payload.selection_unavailable && !inResults) {
        outside.replaceChildren();
        outside.appendChild(
          document.createTextNode(
            "Modelo selecionado fora dos resultados atuais: "
          )
        );
        var strong = document.createElement("strong");
        strong.textContent = payload.selected.name;
        outside.appendChild(strong);
        outside.appendChild(
          document.createTextNode(" (fora dos resultados atuais)")
        );
        (payload.selected.tags || []).forEach(function (tag) {
          var badge = document.createElement("span");
          badge.className = "badge ms-2";
          badge.textContent =
            tag.display_name +
            (tag.state_label ? " (" + tag.state_label + ")" : "");
          outside.appendChild(badge);
        });
        outside.hidden = false;
        outside.style.display = "";
      } else {
        // Clear stale name/tags so a hidden notice never keeps
        // metadata for a selection that is no longer outside the
        // results (or no longer available) (rt2-2).
        outside.replaceChildren();
        outside.hidden = true;
        outside.style.display = "none";
      }
    }
    // Canonical pt-BR labels for the dynamic summary, mirroring
    // TagFilterSelection.state_label/mode_label on the server.
    // The JSON contract is unchanged: only source, mode and
    // selected_tags from payload.filter are read.
    function discoveryModeLabel(modeValue) {
      return modeValue === "all"
        ? "Todas as selecionadas (E)"
        : "Pelo menos uma selecionada (OU)";
    }
    function discoveryStateLabel(filter) {
      var hasSelected = (filter.selected_tags || []).length > 0;
      if (filter.source === "manual") {
        return hasSelected
          ? "Filtro personalizado"
          : "Sem filtro de tags (personalizado)";
      }
      if (filter.source === "saved") {
        return hasSelected
          ? "Padrão salvo da especialidade"
          : "Sem filtro de tags (preferência salva)";
      }
      if (filter.source === "principal") {
        return "Padrão inicial da especialidade";
      }
      return "Sem filtro de tag";
    }
    function updateResults(payload) {
      // Rebuild list, empty state and navigation from every response
      // so empty->match, single->multi-page and page transitions
      // never keep stale markup from the initial render.
      var list = results.querySelector("[data-template-selection-list]");
      if (!list) {
        list = document.createElement("ul");
        list.className = "list-group";
        list.setAttribute("data-template-selection-list", "");
        results.appendChild(list);
      }
      list.replaceChildren();
      (payload.results || []).forEach(function (item) {
        var li = document.createElement("li");
        li.className = "list-group-item";
        li.textContent = item.name;
        (item.tags || []).forEach(function (tag) {
          var badge = document.createElement("span");
          badge.className = "badge ms-2";
          badge.textContent =
            tag.display_name +
            (tag.state_label ? " (" + tag.state_label + ")" : "");
          li.appendChild(badge);
        });
        list.appendChild(li);
      });
      var empty = results.querySelector("[data-template-selection-empty]");
      if (!empty) {
        empty = document.createElement("div");
        empty.className = "alert alert-info";
        empty.setAttribute("role", "alert");
        empty.setAttribute("data-template-selection-empty", "");
        empty.textContent = EMPTY_MESSAGE;
        if (list.nextSibling) {
          results.insertBefore(empty, list.nextSibling);
        } else {
          results.appendChild(empty);
        }
      }
      var isEmpty = (payload.results || []).length === 0;
      empty.hidden = !isEmpty;
      empty.style.display = isEmpty ? "" : "none";
      var summary = results.querySelector("[data-discovery-summary]");
      if (summary) {
        summary.replaceChildren();
        var state = document.createElement("span");
        state.className = "badge bg-secondary";
        state.setAttribute("data-discovery-state", "");
        state.textContent =
          discoveryStateLabel(payload.filter) +
          " · " +
          discoveryModeLabel(payload.filter.mode);
        summary.appendChild(state);
        (payload.filter.selected_tags || []).forEach(function (tag) {
          var badge = document.createElement("span");
          badge.className = "badge bg-medical-teal";
          badge.setAttribute("data-active-tag-badge", "");
          badge.textContent =
            tag.display_name +
            (tag.state_label ? " (" + tag.state_label + ")" : "");
          // Recreate the per-badge remove link present in the
          // initial markup, with the server's effective filter
          // parameters for removing exactly this tag (rt2-5).
          if (tag.remove_querystring !== undefined) {
            var removeLink = document.createElement("a");
            removeLink.setAttribute("href", "?" + tag.remove_querystring);
            removeLink.className = "text-white text-decoration-none ms-1";
            removeLink.setAttribute("data-discovery-remove", "");
            removeLink.setAttribute(
              "aria-label",
              "Remover " + tag.display_name + " dos filtros aplicados"
            );
            removeLink.textContent = "×";
            badge.appendChild(removeLink);
          }
          summary.appendChild(badge);
        });
      }
      var warningBox = results.querySelector("[data-discovery-warning]");
      if (!warningBox) {
        warningBox = document.createElement("div");
        warningBox.className = "alert alert-warning";
        warningBox.setAttribute("role", "alert");
        warningBox.setAttribute("data-discovery-warning", "");
        results.appendChild(warningBox);
      }
      if (payload.filter.warning) {
        warningBox.textContent = payload.filter.warning;
        warningBox.hidden = false;
        warningBox.style.display = "";
      } else {
        warningBox.hidden = true;
        warningBox.style.display = "none";
      }
      displayedPage = String(payload.page);
      results.setAttribute("data-template-selection-page", String(payload.page));
      reconcileSelectionNotices(payload);
      results.setAttribute("data-discovery-count", String(payload.count));
      results.setAttribute("data-discovery-mode", payload.filter.mode);
      results.setAttribute("data-discovery-source", payload.filter.source);
      var nav = results.querySelector("[data-template-selection-nav]");
      if (!nav) {
        nav = document.createElement("nav");
        nav.setAttribute("aria-label", "Page navigation");
        nav.className = "mt-3";
        nav.setAttribute("data-template-selection-nav", "");
        results.appendChild(nav);
      }
      var navList = nav.querySelector("ul.pagination");
      if (!navList) {
        navList = document.createElement("ul");
        navList.className = "pagination justify-content-center";
        nav.appendChild(navList);
      }
      navList.replaceChildren();
      if (payload.num_pages > 1) {
        nav.hidden = false;
        nav.style.display = "";
        var page = payload.page;
        var numPages = payload.num_pages;
        function pageHref(pageNumber) {
          var pageParams = new URLSearchParams(appliedParams);
          pageParams.set("page", String(pageNumber));
          return "?" + pageParams.toString();
        }
        function pageItem(label, pageNumber, disabled, active) {
          var li = document.createElement("li");
          li.className =
            "page-item" + (disabled ? " disabled" : "") + (active ? " active" : "");
          var link;
          if (disabled || active) {
            link = document.createElement("span");
          } else {
            link = document.createElement("a");
            link.setAttribute("href", pageHref(pageNumber));
          }
          link.className = "page-link";
          link.textContent = label;
          li.appendChild(link);
          return li;
        }
        navList.appendChild(pageItem("Primeira", 1, page <= 1, false));
        navList.appendChild(pageItem("Anterior", page - 1, page <= 1, false));
        navList.appendChild(pageItem(String(page), page, false, true));
        navList.appendChild(
          pageItem("Próxima", page + 1, page >= numPages, false)
        );
        navList.appendChild(
          pageItem("Última", numPages, page >= numPages, false)
        );
      } else {
        nav.hidden = true;
        nav.style.display = "none";
      }
    }
    function lookupUrlFor(params) {
      var lookup = new URLSearchParams(params);
      // Ask the server to authorize the pending selections in the
      // tag control for retention (rt2-3). These travel as
      // ``retained_tags``, never as the ``tags`` filter, so they
      // cannot apply or widen a filter.
      Array.prototype.forEach.call(select.selectedOptions, function (option) {
        lookup.append("retained_tags", option.value);
      });
      if (clinicalSelect.value) {
        lookup.set("selected_template", clinicalSelect.value);
      }
      return lookupUrl + "?" + lookup.toString();
    }
    function applyPayload(params, options, payload) {
      rememberApplied(params);
      if (options && options.optionsOnly) {
        replaceTagOptions(payload.tag_options, true, payload.retained_tag_options);
        // Options-only lookups still carry the full page projection
        // for the displayed page: reproject the results (so a
        // revocation never leaves stale list/nav metadata, rt2-2)
        // and reconcile the clinical selection (without dispatching
        // change) and its notices from the same payload page.
        updateResults(payload);
        updateClinicalSelect(payload);
        reconcileSelectionNotices(payload);
        setStatus("Opções de tags atualizadas.");
      } else {
        replaceTagOptions(
          payload.tag_options,
          !!(options && options.preservePending),
          payload.retained_tag_options
        );
        mode.value = payload.filter.mode;
        marker.value = payload.filter.source === "manual" ? "manual" : "";
        updateResults(payload);
        updateClinicalSelect(payload);
        if (payload.count === 0) {
          setStatus(EMPTY_MESSAGE);
        } else {
          setStatus(payload.count + " resultados encontrados.");
        }
      }
      syncHistoricalCheckbox();
      reconcileLinks();
      var queryString = params.toString();
      window.history.pushState(
        null,
        "",
        window.location.pathname + (queryString ? "?" + queryString : "")
      );
      var wantsSearch = pendingSearchWanted;
      pendingSearchWanted = false;
      var appliedQuery = (appliedParams.get("q") || "").trim();
      var currentQuery = search.value.trim();
      if (wantsSearch && currentQuery !== appliedQuery) {
        applyFragment(searchParams(), {
          preservePending: true,
          isSearch: true,
        });
      }
    }
    function applyFragment(params, options) {
      cancelPendingSearch();
      abortInFlight();
      generation += 1;
      var requestGeneration = generation;
      inFlightIsSearch = !!(options && options.isSearch);
      controller =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      setStatus(SEARCHING_MESSAGE);
      fetch(lookupUrlFor(params), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
        signal: controller ? controller.signal : undefined,
      })
        .then(function (response) {
          return response.text().then(function (body) {
            return { ok: response.ok, body: body };
          });
        })
        .then(function (result) {
          if (requestGeneration !== generation) {
            return;
          }
          if (!result.ok) {
            setStatus(GENERIC_ERROR);
            return;
          }
          var payload;
          try {
            payload = JSON.parse(result.body);
          } catch (error) {
            setStatus(GENERIC_ERROR);
            return;
          }
          applyPayload(params, options, payload);
        })
        .catch(function () {
          if (requestGeneration !== generation) {
            return;
          }
          setStatus(GENERIC_ERROR);
        });
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (marker.value !== "manual") {
        marker.value = "manual";
      }
      applyFragment(pendingParams());
    });
    search.addEventListener("input", function () {
      generation += 1;
      abortInFlight();
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        timer = null;
        applyFragment(searchParams(), {
          preservePending: true,
          isSearch: true,
        });
      }, SEARCH_DELAY_MS);
    });
    if (historical) {
      historical.addEventListener("change", function () {
        applyFragment(historicalParams(), { optionsOnly: true });
      });
    }
    root.addEventListener("click", function (event) {
      var link = event.target.closest(
        "[data-discovery-clear], [data-discovery-reapply], " +
          "[data-discovery-remove], .pagination .page-link"
      );
      if (!link || !link.getAttribute("href")) {
        return;
      }
      event.preventDefault();
      applyFragment(linkParams(link));
    });
  }

  function start() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-report-template-discovery]"),
      function (root) {
        if (root.hasAttribute("data-template-selection")) {
          initializeSelection(root);
        } else {
          initializeDiscovery(root);
        }
      }
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

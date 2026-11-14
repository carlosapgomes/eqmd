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

  function start() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-report-template-discovery]"),
      initializeDiscovery
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

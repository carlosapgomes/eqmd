/**
 * Progressive enhancement for report-template catalogue discovery (S3, D5).
 *
 * The server-rendered GET form and results partial are the no-JavaScript
 * contract. The catalogue controller only refreshes the results fragment
 * in place on explicit Apply, scoped clear/reapply/badge-removal and
 * pagination; the selector owns tag-option lookup (250 ms) and row/chip
 * rendering through the reports-owned lookup view. Typing the model-name
 * query never issues a model-result request. Each request carries a
 * generation number so stale responses never replace newer ones. A failed
 * request keeps the current results and selections while announcing a
 * generic error. Labels are moved as DOM nodes (cloneNode / textContent),
 * never assembled as raw HTML.
 *
 * Canonical catalogue clear-all/restore are native GET opt-ins: invalidate
 * older fragment work, reconcile applied hrefs, then let navigation rebuild
 * the controls. Legacy scoped hooks and creation remain in-place. History
 * restoration includes persisted pageshow so Back cannot revive old drafts.
 *
 * Controls are user-owned (TFUX S3 fix3 invariant): the transport NEVER
 * writes the visible controls (q input, chips, hidden tag inputs, mode
 * select, historical checkbox) — with exactly ONE exception, popstate,
 * which performs a full synchronous restore of the navigated applied
 * state from the fragment's inert option data (ids AND display
 * names/state labels, no network). Reconciliation therefore moves only
 * the applied baseline, the results fragment (summary/links included),
 * and URL/history. Draft-vs-applied dirty semantics fall out of the
 * catalogue host comparing current controls against that baseline, so
 * pending edits (additions AND removals, made before OR after
 * submission) survive every successful applied change visibly pending.
 * Server-rendered hrefs stay canonical for the no-JS flow; delegated
 * clicks re-derive from applied state instead of trusting them.
 */
(function () {
  "use strict";

  var GENERIC_ERROR = "Não foi possível atualizar os resultados.";
  var SEARCHING_MESSAGE = "Atualizando resultados...";
  var SEARCH_DELAY_MS = 250;
  var EMPTY_MESSAGE = "Nenhum template encontrado.";

  // Catalogue explicit Apply/draft transport (TFUX S3, design D1/D2/D6).
  //
  // Typing the model-name query never issues a model-result request: the
  // name input is a pending draft control owned by the catalogue host
  // controller (`report-catalogue-filter-form.js`), which shows
  // `Alterações não aplicadas` and short-circuits clean Apply. Tag-option
  // search text inside the selector is likewise never a predicate. Only
  // explicit Apply (and the scoped canonical links below) fetch the
  // results fragment; the historical toggle refreshes selector options
  // only. Each request carries a generation number so stale responses
  // never replace newer ones. A failed request keeps the current results
  // and URL while announcing a generic error. `pushState` runs only when
  // a successful applied change actually changes the canonical URL
  // (pagination keeps `page` in the pushed URL); option-only historical
  // updates use `replaceState`; draft edits and failed/no-op requests
  // add no entry. `popstate` fetches the canonical URL's results without
  // pushing another entry.
  //
  // Last-applied state (`data-discovery-applied` on the results root,
  // updated after each successful applied refresh) is the single source
  // of truth for the predicate baseline. Only Apply moves pending
  // choices into the applied state; clear/reapply/badge-remove/
  // pagination build their requests from the last-applied state plus
  // only their own named parameter. Controls are user-owned: every
  // successful refresh moves only the baseline (via `catalogue:applied`
  // to the host), replaces the results fragment, reconciles links and
  // manages history — except popstate, which additionally restores the
  // controls synchronously from the fragment. The selector owns
  // rows/chips: this controller only consumes hidden `[data-tag-input]`
  // IDs and the `tag-selector:change` notice via the host controller,
  // and never renders tag-result rows itself. The reports lookup's
  // Badge hydration via the lookup is gone: the fragment's inert
  // option data already carries every selected id with its display
  // name/state label, so no reconciliation needs the network (S4 may
  // still use selected-ids on the selector's own lookup path).
  function initializeDiscovery(root) {
    var form = root.querySelector(
      "form[data-discovery-form][data-catalogue-filter-form]"
    );
    var search = root.querySelector("[data-discovery-q]");
    var mode = root.querySelector("[data-discovery-mode]");
    var marker = root.querySelector("[data-discovery-marker]");
    var status = root.querySelector("[data-discovery-status]");
    var errorSlot = root.querySelector("[data-catalogue-filter-error]");
    var results = root.querySelector("[data-discovery-results]");

    if (!form || !search || !mode || !marker || !results) {
      return;
    }

    var generation = 0;
    var controller = null;
    // Last-applied canonical state, seeded from the server-rendered
    // results root. Pending q/tag/mode edits in the controls never enter
    // it until Apply (or a canonical link) succeeds.
    var appliedParams = new URLSearchParams(
      results.getAttribute("data-discovery-applied") || ""
    );
    appliedParams.delete("fragment");
    appliedParams.delete("page");

    function setStatus(message) {
      if (status) {
        status.textContent = message || "";
      }
    }

    function setError(message) {
      if (errorSlot) {
        errorSlot.textContent = message || "";
        errorSlot.hidden = !message;
      }
      setStatus(message || "");
    }

    function selectedTagIds() {
      var ids = [];
      Array.prototype.forEach.call(
        form.querySelectorAll("[data-tag-input]"),
        function (input) {
          var value = String(input.value).trim();
          if (value && ids.indexOf(value) === -1) {
            ids.push(value);
          }
        }
      );
      // Unenhanced (no-JS) fallback: without the selector's hidden
      // inputs, the native multi-select carries the submission. The
      // selector disables the native select when it enhances the form.
      if (!ids.length) {
        var native = form.querySelector("[data-tag-native]");
        if (native && !native.disabled) {
          Array.prototype.forEach.call(
            native.querySelectorAll("option:checked"),
            function (option) {
              if (ids.indexOf(option.value) === -1) {
                ids.push(option.value);
              }
            }
          );
        }
      }
      return ids;
    }

    // Pending form controls: only the explicit Apply flow may build a
    // request from these, so unapplied q/tag/mode edits stay unapplied.
    // Tag-option search text is never read here: it lives inside the
    // selector and is not a model-name predicate.
    function pendingParams() {
      var params = new URLSearchParams();
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      }
      var tagIds = selectedTagIds();
      if (marker.value === "manual" || tagIds.length) {
        params.set("tag_filter", "manual");
        params.set("tag_mode", mode.value);
        tagIds.forEach(function (tagId) {
          params.append("tags", tagId);
        });
      }
      if (selectorHistoricalChecked()) {
        params.set("include_historical", "1");
      }
      return params;
    }

    function selectorHistorical() {
      return form.querySelector("[data-tag-historical]");
    }

    function selectorHistoricalChecked() {
      var historical = selectorHistorical();
      return !!(historical && historical.checked);
    }

    // The historical toggle builds from the CURRENT DISPLAYED URL
    // (window.location.search), changing only include_historical, so
    // its canonical URL cannot commit pending q/tag/mode choices, it
    // preserves the displayed page (a page-2 entry keeps page=2), and
    // during an in-flight popstate it builds from the popped entry
    // the browser already displays rather than the stale predicate
    // baseline. Predicate-changing links still derive from the
    // page-less appliedParams baseline (linkParams, unchanged);
    // rememberApplied still strips page from the baseline this
    // toggle records.
    function historicalParams() {
      var params = new URLSearchParams(window.location.search);
      params.delete("fragment");
      if (selectorHistoricalChecked()) {
        params.set("include_historical", "1");
      } else {
        params.delete("include_historical");
      }
      return params;
    }

    // The last user-visible historical choice wins across any pending
    // fragment request: an in-flight Apply/clear/badge/page sent with
    // the older flag must never push the stale flag when its (older)
    // response reconciles (the checkbox itself is user-owned and is
    // never written back, except on popstate). The toggle handler
    // below stamps every toggle; reconciliation then keeps the flag
    // newer than the request that is landing instead of replaying a
    // model query.
    var historicalStamp = 0;

    function rememberApplied(params) {
      appliedParams = new URLSearchParams(params);
      appliedParams.delete("fragment");
      appliedParams.delete("page");
    }

    // Parse the fresh fragment's EFFECTIVE applied selection, the
    // single source of truth for the applied baseline (TFUX S3 fix3).
    // The request params cannot carry it: automatic defaults
    // intentionally carry no tag params in the canonical URL, while
    // the fragment is server-rendered from the resolved selection
    // (effective tag ids incl. automatic defaults via the
    // `data-template-tag-options` selected states, mode/source via
    // `data-discovery-mode/source`, q via the canonical
    // `data-discovery-applied` querystring). The returned object
    // mirrors a canonical params shape: `{ q, tags, tag_mode, source,
    // includeHistorical, badges }` where `badges` maps each selected
    // id to its `{ id, display_name, state_label }`. The automatic
    // canonical URL and origin are retained: tags from an automatic
    // (non-manual) state NEVER become request params; the baseline
    // keeps q/tags/mode with the automatic source preserved by
    // leaving the marker empty. `badges` is consumed ONLY by the
    // popstate control restore; every other success leaves the
    // controls untouched, so no lookup fetch is ever needed here.
    function effectiveAppliedFromFragment(fresh) {
      var appliedQuery = new URLSearchParams(
        fresh.getAttribute("data-discovery-applied") || ""
      );
      appliedQuery.delete("fragment");
      appliedQuery.delete("page");
      var query = appliedQuery.get("q") || "";
      var template = fresh.querySelector("[data-template-tag-options]");
      var tags = [];
      if (template && template.content) {
        var content = template.content;
        var selected = content.querySelectorAll
          ? content.querySelectorAll("option[selected]")
          : [];
        Array.prototype.forEach.call(selected, function (option) {
          var value = String(
            option.getAttribute("value") || option.value || ""
          ).trim();
          if (value && tags.indexOf(value) === -1) {
            tags.push(value);
          }
        });
      }
      var fragmentMode = fresh.getAttribute("data-discovery-mode") || "any";
      var badges = {};
      var templateOptions = template && template.content
        ? template.content.querySelectorAll
          ? template.content.querySelectorAll("option")
          : []
        : [];
      Array.prototype.forEach.call(templateOptions, function (option) {
        var value = String(
          option.getAttribute("value") || option.value || ""
        ).trim();
        if (!value) {
          return;
        }
        var text = (option.textContent || "").trim();
        var separator = text.lastIndexOf(" — ");
        badges[value] = {
          id: value,
          display_name: separator === -1 ? text : text.slice(0, separator),
          state_label: separator === -1 ? "" : text.slice(separator + 3),
        };
      });
      return {
        q: query,
        tags: tags,
        tag_mode: fragmentMode,
        source: fresh.getAttribute("data-discovery-source") || "",
        includeHistorical: appliedQuery.has("include_historical"),
        badges: badges,
      };
    }

    // Delegated link clicks derive their request from the last-applied
    // state plus the link's own single parameter, instead of trusting a
    // href that predates the latest Apply/toggle. Server-rendered hrefs
    // stay canonical for the no-JS flow; this only re-derives the
    // enhanced request at click time.
    function catalogueActionParams(link) {
      if (link.hasAttribute("data-catalogue-clear-all")) {
        return new URLSearchParams("tag_filter=manual&tag_mode=any");
      }
      var params = new URLSearchParams();
      var name = (appliedParams.get("q") || "").trim();
      if (name) { params.set("q", name); }
      if (appliedParams.get("include_historical") === "1") {
        params.set("include_historical", "1");
      }
      return params;
    }

    function linkParams(link) {
      if (link.hasAttribute("data-catalogue-navigation")) {
        return catalogueActionParams(link);
      }
      var hrefParams = new URLSearchParams(
        new URL(link.getAttribute("href"), window.location.href).search
      );
      if (link.hasAttribute("data-discovery-clear") || link.hasAttribute("data-tag-clear")) {
        // Clear preserves the applied q/historical and the applied mode
        // (falling back to the server-rendered mode for an automatic
        // applied state, which carries no tag_mode of its own). The
        // selector's own [data-tag-clear] link routes here too, so the
        // manual-empty request never replays pending draft tags.
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

    // Keep canonical hrefs in the live DOM reconciled to the applied
    // state, including clear/reapply outside the results root and
    // pagination/badge links inside the replaced results root.
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
      var fragment = new URLSearchParams(params);
      fragment.set("fragment", "results");
      return window.location.pathname + "?" + fragment.toString();
    }

    function canonicalQueryString(params) {
      var canonical = new URLSearchParams(params);
      canonical.delete("fragment");
      return canonical.toString();
    }

    function canonicalUrl(params) {
      var queryString = canonicalQueryString(params);
      return window.location.pathname + (queryString ? "?" + queryString : "");
    }

    function currentUrlQuery() {
      return new URLSearchParams(window.location.search);
    }

    function sameCanonical(left, right) {
      var leftParams = new URLSearchParams(left);
      var rightParams = new URLSearchParams(right);
      leftParams.delete("fragment");
      leftParams.delete("page");
      rightParams.delete("fragment");
      rightParams.delete("page");
      leftParams.sort();
      rightParams.sort();
      return leftParams.toString() === rightParams.toString();
    }

    // Deliberate history (D6): successful applied changes push only when
    // the canonical applied URL actually changed; option-only updates
    // replace the current entry; failures never touch history. The
    // pushed canonical URL keeps `page` whenever the request carried
    // it (pagination); predicate-changing requests already omit `page`
    // via linkParams/pendingParams, so they restart at page 1. Only
    // the predicate baseline (rememberApplied) strips `page`.
    // sameCanonical compares canonical querystrings ignoring page and
    // fragment params and parameter order; the harness `same-canonical`
    // scenario pins that contract directly.
    function pushAppliedHistory(params) {
      var nextQuery = canonicalQueryString(params);
      var currentQuery = currentUrlQuery();
      currentQuery.delete("fragment");
      if (nextQuery === currentQuery.toString()) {
        return;
      }
      window.history.pushState(null, "", canonicalUrl(params));
    }

    function replaceAppliedHistory(params) {
      window.history.replaceState(null, "", canonicalUrl(params));
    }

    // Reconcile one successful EFFECTIVE applied state parsed from the
    // fresh fragment, without pushing history. Controls are
    // user-owned: except on popstate (below), NO control is written —
    // the q input, chips, hidden tag inputs, mode select and
    // historical checkbox keep whatever the user last set, so pending
    // drafts (additions AND removals, before or after submission)
    // survive every success. Only the applied baseline moves (via
    // rememberApplied + `catalogue:applied` to the host, which reads
    // dirty as current-controls-vs-baseline), plus the replaced
    // results fragment, its summary/status and the canonical links.
    // The effective selection comes from the fragment's canonical
    // applied querystring plus its inert `data-template-tag-options`
    // selected states (automatic defaults carry no tag params but ARE
    // selected there); it never comes from the pending controls or
    // from the request params, which may hold preserved draft values
    // or a stale pre-toggle flag.
    function reconcileAppliedState(effective, isPopstate) {
      rememberApplied(effective.canonical);
      if (isPopstate) {
        restoreControlsFromFragment(effective);
      }
      reconcileLinks();
      // The baseline notification goes LAST: on popstate the host
      // refresh must already see the restored controls (clean).
      notifyAppliedBaseline(effective);
      reconcileSummary(results);
    }

    // Popstate is the ONLY path that writes controls: restore the
    // navigated applied state fully and synchronously from the
    // fragment — q, mode, both origin markers, the historical
    // checkbox, and chips/hidden inputs through the shared selector's
    // opt-in `tag-selector:set-selection` event using the inert
    // option data (ids AND display names/state labels). No network:
    // the fragment already carries everything. The selector rebuild
    // never marks manual and never dispatches `tag-selector:change`,
    // so restored chips keep working remove buttons and the host
    // rebaselines via `catalogue:applied` to a clean state.
    function restoreControlsFromFragment(effective) {
      search.value = effective.q || "";
      mode.value = effective.tag_mode || "any";
      var manual = effective.source === "manual" ? "manual" : "";
      marker.value = manual;
      var tagMarker = form.querySelector("[data-tag-marker]");
      if (tagMarker) {
        tagMarker.value = manual;
      }
      var historical = selectorHistorical();
      if (historical) {
        historical.checked = !!effective.includeHistorical;
      }
      var selectorRoot = form.querySelector("[data-tag-selector]");
      if (selectorRoot) {
        var tags = effective.tags.map(function (tagId) {
          var badge = effective.badges[tagId] || {};
          return {
            id: tagId,
            display_name: badge.display_name || "Tag " + tagId,
            state_label: badge.state_label || "",
          };
        });
        selectorRoot.dispatchEvent(
          new CustomEvent("tag-selector:set-selection", {
            bubbles: false,
            detail: { tags: tags },
          })
        );
      }
    }

    // Host baseline: the catalogue host controller owns draft vs applied
    // and re-baselines from this event after every successful applied
    // change (Apply, clear/reapply/badge, pagination, popstate). The
    // baseline is the EFFECTIVE applied selection parsed from the fresh
    // fragment — including automatic defaults — never the request
    // params, and the automatic origin is preserved by leaving the
    // marker empty for non-manual states. Final contract:
    // `catalogue:applied` on the catalogue form, detail
    // `{ q: string, tags: string[], mode: string }` where `mode` is
    // the server canonical `tag_mode` normalized to the submitted
    // control name (`any` default). The host (`report-catalogue-
    // filter-form.js`) compares it against the current controls; the
    // transport never writes the controls it compares.
    function notifyAppliedBaseline(effective) {
      form.dispatchEvent(
        new CustomEvent("catalogue:applied", {
          bubbles: false,
          detail: { q: effective.q || "", tags: effective.tags, mode: effective.tag_mode || "any" },
        })
      );
    }

    // Summary/status from the fresh fragment root (which replaces the
    // old results node, summary included). This is not a control:
    // the count line is reconciled, the error is cleared on success.
    function reconcileSummary(fragmentRoot) {
      var restore = root.querySelector("[data-catalogue-restore]");
      if (restore) {
        var focused = document.activeElement === restore;
        restore.hidden = fragmentRoot.getAttribute("data-catalogue-can-restore") !== "true";
        if (restore.hidden && focused) {
          form.querySelector("[data-discovery-apply]").focus();
        }
      }
      var count = fragmentRoot.getAttribute("data-discovery-count");
      setError("");
      if (count === "0") {
        setStatus(EMPTY_MESSAGE);
      } else if (count !== null) {
        setStatus(count + " resultados encontrados.");
      }
    }

    function applyFragment(params, options) {
      if (controller) {
        controller.abort();
        controller = null;
      }
      generation += 1;
      var requestGeneration = generation;
      var isOptionsOnly = !!(options && options.optionsOnly);
      var isPopstate = !!(options && options.popstate);
      // Stamp the request against the latest user-visible historical
      // choice: a toggle stamped AFTER this request wins over the
      // landing response's older flag (fix2 historical race).
      var requestStamp = historicalStamp;
      controller =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      setStatus(SEARCHING_MESSAGE);
      if (!isOptionsOnly && !isPopstate) {
        setError("");
      }
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
            // Failure retains the last results and URL; only the
            // draft and the retryable error stay visible.
            setError(GENERIC_ERROR);
            return;
          }
          var parser = new DOMParser();
          var documentFragment = parser.parseFromString(
            result.body,
            "text/html"
          );
          var fresh = documentFragment.querySelector("[data-discovery-results]");
          if (!fresh) {
            setError(GENERIC_ERROR);
            return;
          }
          if (isOptionsOnly) {
            // Legacy options-only fragment path (kept for compatibility):
            // prefer the direct change listener above, which performs no
            // model-result request at all. The checkbox already holds
            // the user's toggle; only the baseline/URL reconcile.
            rememberApplied(params);
            reconcileLinks();
            replaceAppliedHistory(params);
            setStatus("Opções de tags atualizadas.");
            return;
          }
          var effective = effectiveAppliedFromFragment(fresh);
          // Canonical versus baseline differ on `page` only: the
          // baseline (rememberApplied) strips it (predicate identity),
          // while the pushed history URL keeps it when the request
          // carried it (pagination), so page-2 results are navigable.
          effective.canonical = new URLSearchParams(params);
          effective.canonical.delete("fragment");
          effective.historicalStamp = requestStamp;
          // The historical winner across an in-flight toggle: the flag
          // newer than this request was computed from the CURRENT
          // checkbox, never replayed stale from the landing response.
          // The checkbox itself stays user-owned (never written here).
          if (historicalStamp > requestStamp) {
            effective.includeHistorical = selectorHistoricalChecked();
            if (effective.includeHistorical) {
              effective.canonical.set("include_historical", "1");
            } else {
              effective.canonical.delete("include_historical");
            }
          }
          results.replaceWith(document.importNode(fresh, true));
          results = root.querySelector("[data-discovery-results]");
          // After EVERY successful applied-state change (Apply, clear,
          // reapply, badge removal, pagination), the baseline moves to
          // the NEW effective applied state and the controls stay
          // untouched (popstate additionally restores them). Popstate
          // pushes no new history entry and never loops back through
          // the push path.
          reconcileAppliedState(effective, isPopstate);
          if (isPopstate) {
            return;
          }
          pushAppliedHistory(effective.canonical);
        })
        .catch(function (error) {
          if (requestGeneration !== generation) {
            return;
          }
          if (error && error.name === "AbortError") {
            return;
          }
          setError(GENERIC_ERROR);
        });
    }

    form.addEventListener("submit", function (event) {
      // The host draft controller runs first: a clean enhanced submit is
      // already defaultPrevented there, so the transport must honor it
      // and issue no request, no manual conversion and no history entry.
      // The explicit Apply conversion of the origin marker to manual is
      // the user's own Apply action, not a reconciliation write.
      if (event.defaultPrevented) {
        return;
      }
      event.preventDefault();
      if (marker.value !== "manual") {
        marker.value = "manual";
      }
      applyFragment(pendingParams());
    });

    // No name-search debounce: typing q is a pending draft action only.
    // Tag-option search (250 ms) lives inside the selector, which owns
    // its lookup endpoint and option rendering.

    root.addEventListener("click", function (event) {
      // The selector's own [data-tag-clear] link is matched by linkParams
      // through the scoped manual-empty clear branch (see above), so it
      // shares the canonical clear derivation with [data-discovery-clear]
      // and never falls through to the applied-state pagination branch.
      var link = event.target.closest(
        "[data-discovery-clear], [data-tag-clear], [data-discovery-reapply], " +
          "[data-discovery-remove], .pagination .page-link"
      );
      if (!link || !link.getAttribute("href")) {
        return;
      }
      if (link.hasAttribute("data-catalogue-navigation")) {
        reconcileLinks();
        if (event.defaultPrevented || event.button > 0 || event.ctrlKey ||
            event.metaKey || event.shiftKey || event.altKey) { return; }
        generation += 1;
        if (controller) { controller.abort(); }
        return;
      }
      event.preventDefault();
      applyFragment(linkParams(link));
    });

    window.addEventListener("pageshow", function (event) {
      if (event.persisted) { applyFragment(currentUrlQuery(), { popstate: true }); }
    });

    // Historical toggle: options-only catalogue update. The selector owns
    // the lookup-driven option refresh; the transport only reconciles the
    // canonical include_historical flag via replaceState (no model-result
    // request, so pending q/tags/mode can never be committed by a toggle).
    // The toggle stamps the user-visible choice FIRST so any in-flight
    // fragment response landing afterwards keeps this newer flag in the
    // baseline/URL instead of pushing the stale one. The checkbox is
    // never written back by the transport (popstate excepted), so a
    // newer toggle can never be flipped back by an older result. A
    // genuinely new applied state (new request sent AFTER the toggle)
    // still reconciles its own flag normally.
    form.addEventListener("change", function (event) {
      var target = event.target;
      if (
        !target ||
        !target.hasAttribute ||
        !target.hasAttribute("data-tag-historical")
      ) {
        return;
      }
      historicalStamp += 1;
      var params = historicalParams();
      rememberApplied(params);
      reconcileLinks();
      replaceAppliedHistory(params);
      setStatus("Opções de tags atualizadas.");
    });

    window.addEventListener("popstate", function () {
      // Restore the popped canonical state without pushing a new entry:
      // the fetch replaces the results and restores the controls to the
      // popped URL (the only control-writing path), and
      // pushAppliedHistory is never reached on this path.
      var params = currentUrlQuery();
      params.delete("fragment");
      applyFragment(params, { popstate: true });
    });
  }

  // Report-creation discovery (S4, D1/D2/D6/D7): the same explicit
  // draft/Apply semantics as the catalogue, over the JSON lookup
  // endpoint. The shared selector owns tag search/rows/chips (reported
  // lookup, 250 ms); typing the model-name query is a pending draft only
  // and NEVER issues a model-result request (no debounce). Draft vs
  // applied is normalized (trimmed q, deduplicated hidden-input ids,
  // mode) with the persistent `Alterações não aplicadas` indicator near
  // Apply; a clean enhanced Apply short-circuits (no request, no
  // automatic→manual conversion, no history). Apply submits the whole
  // draft as one JSON request; failure retains the last results, the
  // draft and the dirty state and announces an honest error. Scoped
  // clear/reapply/badge-removal/pagination derive from the last-applied
  // state and preserve pending controls visibly. The historical toggle
  // is options-only (replaceState, no model request): the selector owns
  // its lookup refresh. History is deliberate: pushState only when the
  // canonical applied URL changes, replaceState for the toggle, and
  // popstate restores controls/results WITHOUT pushing.
  //
  // CLINICAL INVARIANT (R3, the heart of S4): controls are user-owned —
  // the transport writes them ONLY on popstate. Every other success
  // moves only the applied baseline, the results list/nav/summary, the
  // clinical SELECT's options (value preserved, NO change event
  // dispatched — dispatching would navigate to the GET prefill flow)
  // and the URL. Title, document_date, EasyMDE content and the selected
  // model are never read or written here, and the discovery form is a
  // sibling of (never nested in) the clinical POST form, so no
  // discovery interaction can POST clinical data. A still-authorized
  // selected model outside the current results stays pinned in the
  // clinical select with its count excluded (existing payload
  // semantics, unchanged).
  function initializeSelection(root) {
    var lookupUrl = root.getAttribute("data-template-selection-url");
    var form = root.querySelector("[data-discovery-form]");
    var search = root.querySelector("[data-discovery-q]");
    var mode = root.querySelector("[data-discovery-mode]");
    var marker = root.querySelector("[data-discovery-marker]");
    var dirty = root.querySelector("[data-creation-filter-dirty]");
    var errorSlot = root.querySelector("[data-creation-filter-error]");
    var status = root.querySelector("[data-discovery-status]");
    var results = root.querySelector("[data-template-selection-results]");
    var clinicalSelect = document.getElementById("id_template");
    var warning = root.querySelector("[data-template-selection-warning]");
    if (!lookupUrl || !form || !search || !mode || !marker || !results || !clinicalSelect) {
      return;
    }
    if (warning) {
      warning.style.display = "none";
    }
    // The native no-JS historical control (filters partial, outside the
    // selector's enhanced block) is only a fallback: once the selector
    // enhances the form, hide its wrapper div (so the label is not
    // orphaned next to the selector toggle) and disable the input, so
    // enhanced users keep the single panel toggle (its submitted name
    // would otherwise be ignored by the transport).
    var nativeHistorical = form.querySelector("[data-discovery-historical]");
    var nativeHistoricalWrap = form.querySelector(
      "[data-discovery-historical-wrap]"
    );
    if (nativeHistoricalWrap && isEnhanced()) {
      nativeHistoricalWrap.hidden = true;
    }
    if (nativeHistorical && isEnhanced()) {
      nativeHistorical.hidden = true;
      nativeHistorical.disabled = true;
    }
    var generation = 0;
    var controller = null;
    var appliedParams = new URLSearchParams(
      results.getAttribute("data-discovery-applied") || ""
    );
    appliedParams.delete("fragment");
    appliedParams.delete("page");
    // Draft/applied baseline, seeded from the server-rendered applied
    // state (the selector has already seeded hidden inputs from the
    // server-rendered chips in defer order). Rebased from every
    // successful applied response; never read from pending controls.
    var applied = null;

    function abortInFlight() {
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
    function setError(message) {
      if (errorSlot) {
        errorSlot.textContent = message || "";
        errorSlot.hidden = !message;
      }
      setStatus(message || "");
    }
    function isEnhanced() {
      var native = form.querySelector("[data-tag-native]");
      return !!native && native.disabled;
    }
    // Pending draft tag ids: hidden inputs when enhanced (authoritative,
    // including empty-after-clear), the native multi-select otherwise.
    function selectedTagIds() {
      if (isEnhanced()) {
        var ids = [];
        Array.prototype.forEach.call(
          form.querySelectorAll("[data-tag-input]"),
          function (input) {
            var value = String(input.value).trim();
            if (value && ids.indexOf(value) === -1) {
              ids.push(value);
            }
          }
        );
        return ids;
      }
      var native = form.querySelector("[data-tag-native]");
      var fallback = [];
      if (native && !native.disabled) {
        Array.prototype.forEach.call(
          native.querySelectorAll("option:checked"),
          function (option) {
            if (fallback.indexOf(option.value) === -1) {
              fallback.push(option.value);
            }
          }
        );
      }
      return fallback;
    }
    function readState() {
      return {
        q: search.value.trim(),
        tags: selectedTagIds().sort(),
        mode: mode.value,
      };
    }
    function statesEqual(left, right) {
      if (left.q !== right.q || left.mode !== right.mode) {
        return false;
      }
      if (left.tags.length !== right.tags.length) {
        return false;
      }
      for (var index = 0; index < left.tags.length; index += 1) {
        if (left.tags[index] !== right.tags[index]) {
          return false;
        }
      }
      return true;
    }
    function refreshDirty() {
      if (!dirty || !applied) {
        return false;
      }
      var isDirty = !statesEqual(applied, readState());
      dirty.hidden = !isDirty;
      return isDirty;
    }
    function rebaseline(next) {
      applied = {
        q: next.q || "",
        tags: (next.tags || []).slice().sort(),
        mode: next.mode || "any",
      };
      refreshDirty();
    }
    applied = readState();
    // Pending form controls: only explicit Apply may build a request
    // from these. Tag-option search text is never a predicate.
    function pendingParams() {
      var params = new URLSearchParams();
      var query = search.value.trim();
      if (query) {
        params.set("q", query);
      }
      var tagIds = selectedTagIds();
      if (marker.value === "manual" || tagIds.length) {
        params.set("tag_filter", "manual");
        params.set("tag_mode", mode.value);
        tagIds.forEach(function (tagId) {
          params.append("tags", tagId);
        });
      }
      if (selectorHistoricalChecked()) {
        params.set("include_historical", "1");
      }
      return params;
    }
    function selectorHistorical() {
      return form.querySelector("[data-tag-historical]");
    }
    function selectorHistoricalChecked() {
      var historical = selectorHistorical();
      return !!(historical && historical.checked);
    }
    // The historical toggle builds from the CURRENT DISPLAYED URL
    // (window.location.search), changing only include_historical, so
    // it preserves the displayed page and never commits pending
    // q/tags/mode (mirrors the catalogue fix4 mechanism).
    function historicalParams() {
      var params = new URLSearchParams(window.location.search);
      params.delete("fragment");
      if (selectorHistoricalChecked()) {
        params.set("include_historical", "1");
      } else {
        params.delete("include_historical");
      }
      return params;
    }
    // The last user-visible historical choice wins across any pending
    // request: a toggle stamped after a request was sent wins over the
    // landing response's older flag (catalogue historicalStamp seam).
    var historicalStamp = 0;
    function rememberApplied(params) {
      appliedParams = new URLSearchParams(params);
      appliedParams.delete("fragment");
      appliedParams.delete("page");
    }
    // Delegated link clicks derive their request from the last-applied
    // state plus the link's own single parameter. The selector's own
    // [data-tag-clear] shares the scoped manual-empty clear branch.
    function linkParams(link) {
      var hrefParams = new URLSearchParams(
        new URL(link.getAttribute("href"), window.location.href).search
      );
      if (link.hasAttribute("data-discovery-clear") || link.hasAttribute("data-tag-clear")) {
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
    function reconcileLinks() {
      Array.prototype.forEach.call(
        root.querySelectorAll(
          "[data-discovery-clear], [data-discovery-reapply], " +
            "[data-discovery-remove], [data-tag-clear]"
        ),
        function (link) {
          var params = linkParams(link);
          params.delete("fragment");
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
    // Clinical select: refresh options from the payload page while
    // preserving the current value exactly, WITHOUT dispatching change
    // (that would navigate to the GET prefill flow). A still-authorized
    // selection outside the results stays pinned with the generic
    // outside label; an unavailable one keeps its identity under the
    // generic unavailable label (full server validation still rejects
    // it; manual creation after explicit clear is unchanged).
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
        } else if (payload.selected && payload.selected.id === currentValue) {
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
      // Outside notice only when the CURRENT selection is absent from
      // the current results; unavailable notice only when the lookup
      // reports the selection unavailable. Create the elements when
      // the initial render omitted them (empty/filtered states).
      // Fix1: stale-selection reconciliation — reconcile against the
      // clinical select's CURRENT value when the response lands, not
      // the request-time selection in the payload. If the user cleared
      // the selection while the response was in flight, both notices
      // stay hidden (no phantom stale-model notice).
      var currentSelectedId = clinicalSelect.value || "";
      var inResults = (payload.results || []).some(function (item) {
        return item.id === currentSelectedId;
      });
      var selectedMatchesCurrent = !!(
        payload.selected && payload.selected.id === currentSelectedId
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
      if (currentSelectedId && payload.selection_unavailable) {
        unavailable.textContent =
          "Modelo selecionado indisponível. Para criar manualmente, " +
          "limpar a seleção atual.";
        unavailable.hidden = false;
        unavailable.style.display = "";
      } else {
        unavailable.hidden = true;
        unavailable.style.display = "none";
      }
      if (selectedMatchesCurrent && !payload.selection_unavailable && !inResults) {
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
        // results (or no longer available).
        outside.replaceChildren();
        outside.hidden = true;
        outside.style.display = "none";
      }
    }
    // Canonical pt-BR labels for the dynamic summary, mirroring
    // TagFilterSelection.state_label/mode_label on the server.
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
    // Results list/nav/summary only: never a clinical field, never a
    // filter control. The count is the payload's result count (a pinned
    // outside selection is excluded by the server payload itself).
    function updateResults(payload) {
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
          // parameters for removing exactly this tag.
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
      // tag control for retention. These travel as
      // ``retained_tags``, never as the ``tags`` filter, so they
      // cannot apply or widen a filter. (With the selector enhanced
      // the chips already represent the pending selection; the
      // retained projection keeps a readable historical selection
      // represented even when its options are hidden.)
      selectedTagIds().forEach(function (tagId) {
        lookup.append("retained_tags", tagId);
      });
      if (clinicalSelect.value) {
        lookup.set("selected_template", clinicalSelect.value);
      }
      return lookupUrl + "?" + lookup.toString();
    }
    function canonicalQueryString(params) {
      var canonical = new URLSearchParams(params);
      canonical.delete("fragment");
      return canonical.toString();
    }
    function canonicalUrl(params) {
      var queryString = canonicalQueryString(params);
      return window.location.pathname + (queryString ? "?" + queryString : "");
    }
    function currentUrlQuery() {
      return new URLSearchParams(window.location.search);
    }
    // Deliberate history (D6, catalogue pushAppliedHistory seam):
    // push only when the canonical applied URL actually changed;
    // pagination keeps `page` in the pushed URL (predicate requests
    // already omit it, restarting at page 1).
    function pushAppliedHistory(params) {
      var nextQuery = canonicalQueryString(params);
      var currentQuery = currentUrlQuery();
      currentQuery.delete("fragment");
      if (nextQuery === currentQuery.toString()) {
        return;
      }
      window.history.pushState(null, "", canonicalUrl(params));
    }
    function replaceAppliedHistory(params) {
      window.history.replaceState(null, "", canonicalUrl(params));
    }
    // Effective applied selection from a successful payload: the
    // canonical request params carry q/mode/origin/historical, while
    // the effective tag set (incl. automatic defaults that carry no
    // tag params) comes from the payload's selected tag_options.
    // Pending controls are never consulted here.
    function effectiveApplied(payload, canonical) {
      var tags = [];
      (payload.tag_options || []).forEach(function (option) {
        if (option.is_selected) {
          var value = String(option.tag_id);
          if (tags.indexOf(value) === -1) {
            tags.push(value);
          }
        }
      });
      return {
        q: canonical.get("q") || "",
        tags: tags,
        mode: payload.filter.mode || "any",
        canonical: canonical,
      };
    }
    // Popstate is the ONLY path that writes controls: restore the
    // navigated applied state from the payload (q, mode, both origin
    // markers, the historical checkbox, chips/hidden inputs through
    // the selector's `tag-selector:set-selection` with ids AND display
    // names — no network beyond the popped results fetch). Clinical
    // fields and the selected model are never written.
    function restoreControlsFromFragment(effective, canonical, payload) {
      search.value = effective.q || "";
      mode.value = effective.mode || "any";
      var manual = payload.filter.source === "manual" ? "manual" : "";
      marker.value = manual;
      var tagMarker = form.querySelector("[data-tag-marker]");
      if (tagMarker) {
        tagMarker.value = manual;
      }
      var historical = selectorHistorical();
      if (historical) {
        historical.checked = canonical.has("include_historical");
      }
      var selectorRoot = form.querySelector("[data-tag-selector]");
      if (selectorRoot) {
        var tags = effective.tags.map(function (tagId) {
          var found = null;
          (payload.tag_options || []).forEach(function (option) {
            if (String(option.tag_id) === tagId) {
              found = option;
            }
          });
          return {
            id: tagId,
            display_name: found ? found.display_name : "Tag " + tagId,
            state_label: found ? found.state_label || "" : "",
          };
        });
        selectorRoot.dispatchEvent(
          new CustomEvent("tag-selector:set-selection", {
            bubbles: false,
            detail: { tags: tags },
          })
        );
      }
    }
    function applyPayload(params, options, payload) {
      var canonical = new URLSearchParams(params);
      canonical.delete("fragment");
      var isPopstate = !!(options && options.popstate);
      var requestStamp = options && options.requestStamp !== undefined ? options.requestStamp : 0;
      // The historical winner across an in-flight toggle: the flag
      // newer than this request was computed from the CURRENT
      // checkbox, never replayed stale from the landing response.
      if (historicalStamp > requestStamp) {
        if (selectorHistoricalChecked()) {
          canonical.set("include_historical", "1");
        } else {
          canonical.delete("include_historical");
        }
      }
      var effective = effectiveApplied(payload, canonical);
      rememberApplied(canonical);
      updateResults(payload);
      updateClinicalSelect(payload);
      reconcileLinks();
      if (isPopstate) {
        restoreControlsFromFragment(effective, canonical, payload);
      }
      // Rebaseline LAST so the dirty refresh already sees the restored
      // controls on popstate (clean) and the untouched pending draft
      // on every other success (visibly pending).
      rebaseline(effective);
      setError("");
      if (payload.count === 0) {
        setStatus(EMPTY_MESSAGE);
      } else {
        setStatus(payload.count + " resultados encontrados.");
      }
      if (!isPopstate) {
        pushAppliedHistory(canonical);
      }
    }
    function applyFragment(params, options) {
      abortInFlight();
      generation += 1;
      var requestGeneration = generation;
      var requestStamp = historicalStamp;
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
            // Failure retains the last results, the draft/dirty state
            // and the URL; only the honest error is announced.
            setError(GENERIC_ERROR);
            return;
          }
          var payload;
          try {
            payload = JSON.parse(result.body);
          } catch (error) {
            setError(GENERIC_ERROR);
            return;
          }
          applyPayload(params, Object.assign({}, options, { requestStamp: requestStamp }), payload);
        })
        .catch(function (error) {
          if (requestGeneration !== generation) {
            return;
          }
          if (error && error.name === "AbortError") {
            return;
          }
          setError(GENERIC_ERROR);
        });
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      // Clean enhanced Apply: no request, no automatic→manual
      // conversion, no history entry (catalogue host seam).
      if (isEnhanced() && !refreshDirty()) {
        return;
      }
      if (marker.value !== "manual") {
        marker.value = "manual";
      }
      var tagMarker = form.querySelector("[data-tag-marker]");
      if (tagMarker && tagMarker.value !== "manual") {
        tagMarker.value = "manual";
      }
      applyFragment(pendingParams());
    });
    // No name-search debounce: typing q is a pending draft action only.
    // Tag-option search (250 ms) lives inside the selector.
    form.addEventListener("input", refreshDirty);
    form.addEventListener("change", function (event) {
      var target = event.target;
      if (!target) {
        return;
      }
      // The selector's historical toggle is option-only: it refreshes
      // lookup choices without changing the applied predicate or the
      // draft. The transport only reconciles the canonical flag via
      // replaceState (no model-result request), stamped FIRST so an
      // in-flight response keeps this newer flag.
      if (target.hasAttribute && target.hasAttribute("data-tag-historical")) {
        historicalStamp += 1;
        var params = historicalParams();
        rememberApplied(params);
        reconcileLinks();
        replaceAppliedHistory(params);
        setStatus("Opções de tags atualizadas.");
        return;
      }
      // Changing the matching mode is a manual tag-predicate edit.
      if (target.name === "tag_mode" && isEnhanced()) {
        var tagMarker = form.querySelector("[data-tag-marker]");
        if (tagMarker) {
          tagMarker.value = "manual";
        }
        marker.value = "manual";
      }
      refreshDirty();
    });
    form.addEventListener("tag-selector:change", refreshDirty);
    root.addEventListener("click", function (event) {
      var link = event.target.closest(
        "[data-discovery-clear], [data-tag-clear], [data-discovery-reapply], " +
          "[data-discovery-remove], .pagination .page-link"
      );
      if (!link || !link.getAttribute("href")) {
        return;
      }
      event.preventDefault();
      applyFragment(linkParams(link));
    });
    window.addEventListener("popstate", function () {
      // Restore the popped canonical state without pushing a new entry.
      var params = currentUrlQuery();
      params.delete("fragment");
      applyFragment(params, { popstate: true });
    });
    refreshDirty();
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

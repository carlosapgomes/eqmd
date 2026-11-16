/**
 * Host draft/applied orchestration for the report-template catalogue
 * GET filter form (TFUX S3, design D1/D2).
 *
 * The server-rendered controls are the applied state: the fragment
 * transport in `report-template-discovery.js` remains the only enhanced
 * transport, so no client filtering model is kept. This module only
 * normalizes the visible draft (trimmed q, deduplicated hidden-input tag
 * ids, mode), shows the persistent `Alterações não aplicadas` text near
 * Apply while draft and applied differ, and short-circuits a clean
 * enhanced Apply so it issues no result request, converts no automatic
 * origin and adds no history entry.
 *
 * Tag-option search text is never a predicate, and the selector's
 * historical toggle is option-only, so neither makes the host form dirty.
 * Selected-tag changes arrive as the `tag-selector:change` event from
 * `tag-selector.js`; those hidden `data-tag-input` values are the
 * submitted repeated `tags` parameters.
 *
 * Catalogue only: binds `[data-catalogue-filter-form]`, which the shared
 * filter form renders only for the catalogue. Report creation keeps its
 * accepted JSON controller untouched.
 */
(function () {
  "use strict";

  function fieldValue(form, name) {
    var field = form.querySelector('[name="' + name + '"]');
    return field ? field.value : "";
  }

  function selectedTagIds(form) {
    if (isEnhanced(form)) {
      // Enhanced: the hidden repeated inputs are authoritative,
      // including the empty selection after the last chip is
      // removed. The disabled native multi-select still holds
      // the server-rendered applied options and must not be
      // read here, or clearing to empty would be misread as the
      // applied selection.
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
    // Unenhanced (no-JS) fallback: the native multi-select is the
    // submitted selection.
    var native = form.querySelector("[data-tag-native]");
    if (!native) {
      return [];
    }
    var selected = [];
    Array.prototype.forEach.call(
      native.querySelectorAll("option:checked"),
      function (option) {
        if (selected.indexOf(option.value) === -1) {
          selected.push(option.value);
        }
      }
    );
    return selected;
  }

  function readState(form) {
    return {
      q: fieldValue(form, "q").trim(),
      tags: selectedTagIds(form).sort(),
      mode: fieldValue(form, "tag_mode"),
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

  function isEnhanced(form) {
    // The tag selector disables the native multi-select when it
    // enhances the form; without enhancement the native GET must
    // submit normally (including a clean Apply).
    var native = form.querySelector("[data-tag-native]");
    return !!native && native.disabled;
  }

  function initializeForm(form) {
    var dirty = form.querySelector("[data-catalogue-filter-dirty]");
    if (!form || !dirty) {
      return;
    }
    // Applied baseline: refreshed from the canonical applied state after
    // every successful applied change (Apply, scoped clear/reapply/badge,
    // pagination, popstate) via `rebaseline`, below. Never read the
    // pending form controls here: they may intentionally hold preserved
    // draft values that must stay visibly pending.
    var applied = readState(form);

    function rebaseline(next) {
      applied = {
        q: next.q || "",
        tags: (next.tags || []).slice().sort(),
        mode: next.mode || "any",
      };
      refresh();
    }

    function refresh() {
      var isDirty = !statesEqual(applied, readState(form));
      dirty.hidden = !isDirty;
      return isDirty;
    }

    form.addEventListener("input", refresh);
    form.addEventListener("change", function (event) {
      // Changing the matching mode is a manual tag-predicate edit:
      // the marker keeps a mode-only change on an empty selection
      // from decaying back into initial entry on Apply.
      if (
        event.target &&
        event.target.name === "tag_mode" &&
        isEnhanced(form)
      ) {
        var marker = form.querySelector("[data-tag-marker]");
        if (marker) {
          marker.value = "manual";
        }
      }
      // The selector's historical toggle is option-only: it refreshes
      // lookup choices without changing the applied predicate or the
      // draft, so its change must not refresh dirty state from here
      // (the selector owns that control). Any other change refreshes.
      if (
        event.target &&
        event.target.hasAttribute &&
        event.target.hasAttribute("data-tag-historical")
      ) {
        return;
      }
      refresh();
    });
    form.addEventListener("tag-selector:change", refresh);
    form.addEventListener("submit", function (event) {
      // NOTE: this listener must run BEFORE the transport's own submit
      // listener in registration order (host script loads first): a clean
      // enhanced Apply is already defaultPrevented when the transport
      // runs, and the transport honors event.defaultPrevented by issuing
      // no request, no manual conversion and no history entry. Capture
      // registration (`true`) is deliberately NOT used: it would change
      // dispatch order for every other listener on this form.
      if (isEnhanced(form) && !refresh()) {
        event.preventDefault();
      }
    });
    // Initialization must not mark the form dirty; the applied
    // baseline is the server-rendered state captured above.
    refresh();
    // The transport reconciles to the canonical applied state after
    // every successful applied change; unrelated pending edits stay
    // untouched so they remain visibly pending.
    form.addEventListener("catalogue:applied", function (event) {
      var detail = (event && event.detail) || {};
      rebaseline({
        q: detail.q || "",
        tags: detail.tags || [],
        mode: detail.mode || "any",
      });
    });
  }

  function start() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-catalogue-filter-form]"),
      initializeForm
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

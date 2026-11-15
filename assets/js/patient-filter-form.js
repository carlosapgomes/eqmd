/**
 * Host draft/applied orchestration for the patient list and ward map
 * GET filter forms (TFUX S2).
 *
 * The server-rendered controls are the applied state: the full-page GET
 * remains the only transport, so no client filtering model is kept. This
 * module only normalizes the visible draft (trimmed q, deduplicated tag
 * ids, mode and the host's other predicates), shows the persistent
 * `Alterações não aplicadas` text near Apply while draft and applied
 * differ, and short-circuits a clean enhanced Apply so it issues no
 * result request, converts no automatic origin and adds no history.
 *
 * Tag-option search text is never a predicate, and the historical
 * lookup toggle is option-only, so neither makes the host form dirty.
 * Selected-tag changes arrive as the `tag-selector:change` event from
 * `tag-selector.js`; those hidden `data-tag-input` values are the
 * submitted repeated `tags` parameters.
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
    var showEmpty = form.querySelector('[name="show_empty_wards"]');
    return {
      q: fieldValue(form, "q").trim(),
      status: fieldValue(form, "status"),
      ward: fieldValue(form, "ward"),
      tags: selectedTagIds(form).sort(),
      mode: fieldValue(form, "tag_mode"),
      showEmpty: showEmpty ? showEmpty.checked : false,
    };
  }

  function statesEqual(left, right) {
    if (left.q !== right.q || left.status !== right.status) {
      return false;
    }
    if (left.ward !== right.ward || left.mode !== right.mode) {
      return false;
    }
    if (left.showEmpty !== right.showEmpty) {
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
    var dirty = document.querySelector(
      "[data-patient-filter-dirty]"
    );
    if (!form || !dirty) {
      return;
    }
    var applied = readState(form);

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
      // `show_empty_wards` is a pending predicate: its change only
      // refreshes the dirty indication and never submits the form.
      refresh();
    });
    form.addEventListener("tag-selector:change", refresh);
    form.addEventListener("submit", function (event) {
      if (isEnhanced(form) && !refresh()) {
        // Clean enhanced Apply: no result request, no automatic to
        // manual conversion and no history entry.
        event.preventDefault();
      }
    });
    // Initialization must not mark the form dirty; the applied
    // baseline is the server-rendered state captured above.
    refresh();
  }

  function start() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-patient-filter-form]"),
      initializeForm
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();

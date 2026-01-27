(function () {
  "use strict";

  function getSearchConfig() {
    return window.pdfFormsProcedureSearch || {};
  }

  function ProcedureSearch() {
    this.config = getSearchConfig();
    this.inputs = Array.from(document.querySelectorAll(".procedure-search-input"));
    this.timeouts = new Map();

    if (!this.config.searchUrl || this.inputs.length === 0) {
      return;
    }

    this.init();
  }

  ProcedureSearch.prototype.init = function () {
    var self = this;

    this.inputs.forEach(function (input) {
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
        }
      });

      input.addEventListener("input", function () {
        self.handleInput(input);
      });
    });

    document.addEventListener("click", function (event) {
      if (!event.target.closest(".procedure-search-input") && !event.target.closest(".procedure-results")) {
        self.hideAllResults();
      }
    });

    var forms = new Set(
      this.inputs.map(function (input) {
        return input.form;
      })
    );

    forms.forEach(function (form) {
      if (!form) {
        return;
      }
      form.addEventListener("submit", function (event) {
        self.handleSubmit(event, form);
      });
    });
  };

  ProcedureSearch.prototype.getResultsContainer = function (input) {
    var wrapper = input.closest(".procedure-search-group");
    return wrapper ? wrapper.querySelector(".procedure-results") : null;
  };

  ProcedureSearch.prototype.getSpinner = function (input) {
    var wrapper = input.closest(".input-group");
    return wrapper ? wrapper.querySelector(".search-spinner") : null;
  };

  ProcedureSearch.prototype.getHiddenField = function (input, fieldName) {
    if (!fieldName || !input.form) {
      return null;
    }
    return input.form.querySelector('[name="' + fieldName + '"]');
  };

  ProcedureSearch.prototype.clearSelection = function (input) {
    var codeField = input.dataset.procedureCodeField;
    var descriptionField = input.dataset.procedureDescriptionField;
    var codeInput = this.getHiddenField(input, codeField);
    var descriptionInput = this.getHiddenField(input, descriptionField);

    if (codeInput) {
      codeInput.value = "";
    }
    if (descriptionInput) {
      descriptionInput.value = "";
    }
  };

  ProcedureSearch.prototype.showSpinner = function (input) {
    var spinner = this.getSpinner(input);
    if (spinner) {
      spinner.style.display = "block";
    }
  };

  ProcedureSearch.prototype.hideSpinner = function (input) {
    var spinner = this.getSpinner(input);
    if (spinner) {
      spinner.style.display = "none";
    }
  };

  ProcedureSearch.prototype.hideAllResults = function () {
    var containers = document.querySelectorAll(".procedure-results");
    containers.forEach(function (container) {
      container.classList.remove("show");
      container.style.display = "none";
    });
  };

  ProcedureSearch.prototype.renderResults = function (input, results) {
    var container = this.getResultsContainer(input);
    if (!container) {
      return;
    }

    container.innerHTML = "";

    if (!results.length) {
      container.classList.remove("show");
      container.style.display = "none";
      return;
    }

    var self = this;
    results.forEach(function (procedure) {
      var item = document.createElement("div");
      item.className = "dropdown-item";
      item.style.cursor = "pointer";
      item.innerHTML =
        "<strong>" + procedure.code + "</strong><br><small class=\"text-muted\">" +
        (procedure.short_description || procedure.description) +
        "</small>";
      item.addEventListener("click", function () {
        self.selectProcedure(input, procedure);
      });
      container.appendChild(item);
    });

    container.classList.add("show");
    container.style.display = "block";
  };

  ProcedureSearch.prototype.selectProcedure = function (input, procedure) {
    var codeField = input.dataset.procedureCodeField;
    var descriptionField = input.dataset.procedureDescriptionField;
    var codeInput = this.getHiddenField(input, codeField);
    var descriptionInput = this.getHiddenField(input, descriptionField);

    input.value = procedure.code + " - " + procedure.description;

    if (codeInput) {
      codeInput.value = procedure.code || "";
    }
    if (descriptionInput) {
      descriptionInput.value = procedure.description || "";
    }

    var container = this.getResultsContainer(input);
    if (container) {
      container.classList.remove("show");
      container.style.display = "none";
    }

    this.hideSpinner(input);
  };

  ProcedureSearch.prototype.handleInput = function (input) {
    var query = input.value.trim();
    var container = this.getResultsContainer(input);

    this.clearSelection(input);

    if (this.timeouts.has(input)) {
      clearTimeout(this.timeouts.get(input));
    }

    if (query.length < 2) {
      if (container) {
        container.classList.remove("show");
        container.style.display = "none";
      }
      this.hideSpinner(input);
      return;
    }

    var self = this;
    var timeoutId = setTimeout(function () {
      self.showSpinner(input);
      var url = self.config.searchUrl + "?q=" + encodeURIComponent(query) + "&limit=10";
      fetch(url, { credentials: "same-origin" })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          self.hideSpinner(input);
          self.renderResults(input, data && data.results ? data.results : []);
        })
        .catch(function () {
          self.hideSpinner(input);
          console.error("Error searching procedures");
        });
    }, 300);

    this.timeouts.set(input, timeoutId);
  };

  ProcedureSearch.prototype.handleSubmit = function (event, form) {
    var inputs = this.inputs.filter(function (input) {
      return input.form === form;
    });

    for (var i = 0; i < inputs.length; i += 1) {
      var input = inputs[i];
      var required = input.dataset.procedureRequired === "true";
      var displayValue = input.value.trim();
      var codeField = input.dataset.procedureCodeField;
      var descriptionField = input.dataset.procedureDescriptionField;
      var codeInput = this.getHiddenField(input, codeField);
      var descriptionInput = this.getHiddenField(input, descriptionField);
      var codeValue = codeInput ? codeInput.value.trim() : "";
      var descriptionValue = descriptionInput ? descriptionInput.value.trim() : "";

      if (required && !codeValue && !descriptionValue) {
        event.preventDefault();
        alert("Selecione o procedimento a partir da lista.");
        input.focus();
        return;
      }

      if (displayValue && (!codeValue || !descriptionValue)) {
        event.preventDefault();
        alert("Selecione um procedimento válido da lista de sugestões.");
        input.focus();
        return;
      }
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    new ProcedureSearch();
  });
})();

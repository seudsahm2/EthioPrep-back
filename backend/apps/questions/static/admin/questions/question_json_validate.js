(function () {
  function getCsrfToken() {
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  function levelFromFieldId(fieldId) {
    if (fieldId.indexOf("simple_") !== -1) return "simple";
    if (fieldId.indexOf("detailed_") !== -1) return "detailed";
    if (fieldId.indexOf("deep_") !== -1) return "deep";
    return null;
  }

  function renderResult(container, data, isError) {
    var status = document.createElement("div");
    status.style.marginTop = "8px";
    status.style.padding = "8px";
    status.style.borderRadius = "6px";
    status.style.border = "1px solid";
    status.style.fontSize = "12px";

    if (isError) {
      status.style.background = "#fff1f1";
      status.style.borderColor = "#ffb3b3";
      status.textContent = "Validation failed: " + data;
      container.innerHTML = "";
      container.appendChild(status);
      return;
    }

    status.style.background = "#f3fff4";
    status.style.borderColor = "#b8edc0";
    status.textContent = data.autofix_count
      ? "Valid JSON. Auto-fix preview generated for " + data.autofix_count + " path(s)."
      : "Valid JSON. No auto-fixes needed.";

    container.innerHTML = "";
    container.appendChild(status);

    if (Array.isArray(data.autofix_paths) && data.autofix_paths.length) {
      var listTitle = document.createElement("div");
      listTitle.style.marginTop = "8px";
      listTitle.style.fontSize = "12px";
      listTitle.style.fontWeight = "600";
      listTitle.textContent = "Auto-fixed paths:";
      container.appendChild(listTitle);

      var list = document.createElement("ul");
      list.style.margin = "6px 0 0 18px";
      list.style.padding = "0";
      list.style.fontSize = "12px";
      list.style.maxHeight = "150px";
      list.style.overflowY = "auto";

      data.autofix_paths.forEach(function (path) {
        var li = document.createElement("li");
        li.textContent = String(path);
        list.appendChild(li);
      });
      container.appendChild(list);
    }
  }

  function attachValidator(fieldId) {
    var textarea = document.getElementById(fieldId);
    if (!textarea) return;

    var level = levelFromFieldId(fieldId);
    if (!level) return;

    var wrap = document.createElement("div");
    wrap.style.marginTop = "8px";

    var button = document.createElement("button");
    button.type = "button";
    button.className = "button";
    button.textContent = "Validate JSON";

    var result = document.createElement("div");
    result.style.marginTop = "6px";

    button.addEventListener("click", function () {
      var raw = textarea.value || "";
      var csrfToken = getCsrfToken();

      fetch("/admin/questions/question/validate-rich-json/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ level: level, raw: raw }),
      })
        .then(function (response) {
          return response.json().then(function (data) {
            if (!response.ok) {
              throw new Error(data && data.error ? data.error : "Validation request failed");
            }
            return data;
          });
        })
        .then(function (data) {
          textarea.value = JSON.stringify(data.normalized, null, 2);
          textarea.style.outline = data.autofix_count ? "2px solid #f0b429" : "2px solid #4caf50";
          renderResult(result, data, false);
        })
        .catch(function (error) {
          renderResult(result, error.message || "Unknown error", true);
        });
    });

    wrap.appendChild(button);
    wrap.appendChild(result);
    textarea.parentElement.appendChild(wrap);
  }

  document.addEventListener("DOMContentLoaded", function () {
    [
      "id_simple_explanation_rich",
      "id_detailed_explanation_rich",
      "id_deep_explanation_rich",
    ].forEach(attachValidator);
  });
})();

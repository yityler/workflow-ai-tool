(function () {
  function parsePrice(value) {
    var cleaned = String(value || "0").replace(/[$,]/g, "").trim();
    var parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function money(value) {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "USD"
    }).format(parsePrice(value));
  }

  function updateConfigurator(root) {
    var lines = [];
    var configuredSubtotal = 0;
    var baseCost = parsePrice(root.getAttribute("data-base-cost"));
    var multiplier = parsePrice(root.getAttribute("data-price-multiplier") || "1") || 1;
    root.querySelectorAll("[data-ctcm-item-qty]").forEach(function (input) {
      var qty = parseInt(input.value || "0", 10);
      if (Number.isNaN(qty) || qty < 0) qty = 0;
      if (qty > 99) qty = 99;
      input.value = qty;
      if (!qty) return;
      var price = parsePrice(input.getAttribute("data-price") || "0");
      var name = input.getAttribute("data-name") || "Item";
      var lineTotal = price * qty;
      configuredSubtotal += lineTotal;
      lines.push('<div class="ctcm-summary-line"><span>' + name + ' x ' + qty + '</span><strong>' + money(lineTotal) + '</strong></div>');
    });
    var total = baseCost + (configuredSubtotal * multiplier);
    var lineHolder = root.querySelector("[data-ctcm-summary-lines]");
    var totalHolder = root.querySelector("[data-ctcm-summary-total]");
    var addButton = root.querySelector("[data-ctcm-add-selected]");
    var emptyText = root.getAttribute("data-empty-summary") || "No items selected yet.";
    lineHolder.innerHTML = lines.length ? lines.join("") : "<p>" + emptyText + "</p>";
    totalHolder.textContent = money(total);
    addButton.disabled = !lines.length && baseCost <= 0;
  }

  document.addEventListener("click", function (event) {
    var tabButton = event.target.closest("[data-ctcm-tab]");
    if (tabButton) {
      var group = tabButton.closest("[data-ctcm-tabs]");
      var target = tabButton.getAttribute("data-ctcm-tab");
      group.querySelectorAll("[data-ctcm-tab]").forEach(function (button) {
        button.classList.toggle("is-active", button === tabButton);
      });
      group.querySelectorAll("[data-ctcm-tab-panel]").forEach(function (panel) {
        panel.classList.toggle("is-active", panel.id === target);
      });
    }

    var categoryToggle = event.target.closest("[data-ctcm-category-toggle]");
    if (categoryToggle) {
      var category = categoryToggle.closest(".ctcm-category");
      category.classList.toggle("is-open");
    }

    var qtyButton = event.target.closest("[data-ctcm-qty]");
    if (qtyButton) {
      var wrapper = qtyButton.closest(".ctcm-qty");
      var input = wrapper.querySelector("input");
      var value = parseInt(input.value || "0", 10);
      var action = qtyButton.getAttribute("data-ctcm-qty");
      input.value = Math.max(0, Math.min(99, value + (action === "inc" ? 1 : -1)));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    var addButton = event.target.closest("[data-ctcm-add-selected]");
    if (addButton) {
      var root = addButton.closest("[data-ctcm-configurator]");
      var toast = root.querySelector("[data-ctcm-toast]");
      var lines = root.querySelectorAll(".ctcm-summary-line");
      toast.textContent = lines.length ? "Selected items are ready for cart integration." : "Choose at least one item first.";
    }
  });

  document.addEventListener("input", function (event) {
    if (!event.target.matches("[data-ctcm-item-qty]")) return;
    var root = event.target.closest("[data-ctcm-configurator]");
    updateConfigurator(root);
  });

  document.addEventListener("change", function (event) {
    if (!event.target.matches("[data-ctcm-variant-select]")) return;
    var selected = event.target.options[event.target.selectedIndex];
    var targetId = event.target.getAttribute("data-ctcm-variant-select");
    var target = document.getElementById(targetId);
    if (!target) return;
    target.querySelectorAll("[data-ctcm-variant-fields]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-ctcm-variant-fields") !== selected.value;
    });
  });

  document.querySelectorAll("[data-ctcm-configurator]").forEach(updateConfigurator);
})();
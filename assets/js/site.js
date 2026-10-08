// Portal arama/filtre iyileştirmesi — içerik statik HTML'de vardır, JS yalnız filtreler.
(function () {
  "use strict";
  var input = document.getElementById("q");
  var filters = document.getElementById("filters");
  if (!filters) return;
  var state = { year: null, quarter: null };

  function apply() {
    var term = (input && input.value ? input.value : "").trim().toUpperCase();
    var shown = 0;
    document.querySelectorAll("[data-card]").forEach(function (card) {
      var hay = (card.getAttribute("data-search") || "").toUpperCase();
      var year = card.getAttribute("data-year");
      var quarter = card.getAttribute("data-quarter");
      var ok = (!term || hay.indexOf(term) !== -1) &&
               (!state.year || year === state.year) &&
               (!state.quarter || quarter === state.quarter);
      card.hidden = !ok;
      if (ok) shown++;
    });
    // Şirket arşivi matrisi: satır = şirket, hücre = dönem çipi
    document.querySelectorAll("tr.arow").forEach(function (row) {
      var hay = (row.getAttribute("data-search") || "").toUpperCase();
      var okTerm = !term || hay.indexOf(term) !== -1;
      var any = false;
      row.querySelectorAll("a.chip").forEach(function (ch) {
        var okP = (!state.year || ch.getAttribute("data-year") === state.year) &&
                  (!state.quarter || ch.getAttribute("data-quarter") === state.quarter);
        ch.classList.toggle("dim", !okP);
        if (okP) any = true;
      });
      var vis = okTerm && any;
      row.hidden = !vis;
      if (vis) shown++;
    });
    document.querySelectorAll(".company-block").forEach(function (block) {
      var any = Array.prototype.some.call(
        block.querySelectorAll("[data-card]"),
        function (c) { return !c.hidden; }
      );
      block.hidden = !any;
    });
    var empty = document.getElementById("empty");
    if (empty) empty.hidden = shown !== 0;
  }

  filters.addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-filter]");
    if (!btn) return;
    var spec = btn.getAttribute("data-filter").split(":");
    var kind = spec[0], value = spec[1] || null;
    if (kind === "year") state.year = state.year === value ? null : value;
    if (kind === "quarter") state.quarter = state.quarter === value ? null : value;
    if (kind === "all") { state.year = null; state.quarter = null; }
    filters.querySelectorAll("button").forEach(function (b) {
      var s = b.getAttribute("data-filter");
      b.classList.toggle("active",
        s === "all" ? (!state.year && !state.quarter) :
        (s.indexOf("year:" + state.year) !== -1 || s.indexOf("quarter:" + state.quarter) !== -1));
    });
    apply();
  });

  if (input) input.addEventListener("input", apply);
  var activeAll = filters.querySelector('button[data-filter="all"]');
  if (activeAll) activeAll.classList.add("active");
})();

// Pagina Ferramentas / Tools: abas das ferramentas, etapas de cada fluxo e
// filtro por tipo de leitura. Usado por ferramentas.qmd e en/tools.qmd.
//
// Sem JavaScript a pagina continua completa: todas as ferramentas e todas as
// etapas aparecem em sequencia. O script so esconde o que nao esta ativo.
(function () {
  function init() {
    var root = document.querySelector("[data-tools]");
    if (!root) return;
    root.classList.add("is-ready");

    var picks = root.querySelectorAll(".tool-pick");
    var panels = root.querySelectorAll(".tool-panel");

    // ---------------------------------------------------------------- abas ---
    function show(id, focar) {
      var achou = false;
      for (var i = 0; i < picks.length; i++) {
        var ativo = picks[i].getAttribute("data-tool") === id;
        achou = achou || ativo;
        picks[i].setAttribute("aria-selected", ativo ? "true" : "false");
        picks[i].setAttribute("tabindex", ativo ? "0" : "-1");
        if (ativo && focar) picks[i].focus();
      }
      if (!achou) return false;
      for (var j = 0; j < panels.length; j++) {
        panels[j].hidden = panels[j].id !== id;
      }
      return true;
    }

    for (var i = 0; i < picks.length; i++) {
      picks[i].addEventListener("click", function () {
        var id = this.getAttribute("data-tool");
        show(id);
        // mantem o link compartilhavel (ferramentas.html#vapor) sem rolar
        if (history.replaceState) history.replaceState(null, "", "#" + id);
      });
      picks[i].addEventListener("keydown", function (ev) {
        var lista = Array.prototype.slice.call(picks);
        var k = lista.indexOf(this);
        if (ev.key === "ArrowRight" || ev.key === "ArrowDown") k = (k + 1) % lista.length;
        else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") k = (k - 1 + lista.length) % lista.length;
        else return;
        ev.preventDefault();
        lista[k].click();
        lista[k].focus();
      });
    }

    function doHash() {
      var id = decodeURIComponent(window.location.hash.slice(1));
      if (!id || !show(id)) show(picks[0].getAttribute("data-tool"));
    }
    window.addEventListener("hashchange", doHash);
    doHash();

    // o id da ferramenta tambem e' o id do painel, entao o navegador rola ate
    // ele ao abrir ferramentas.html#vapor e esconde as abas. Volta ao topo.
    var alvo = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    if (alvo && alvo.classList.contains("tool-panel")) {
      window.addEventListener("load", function () { window.scrollTo(0, 0); });
    }

    // -------------------------------------------------------------- etapas ---
    var rotEtapas = root.getAttribute("data-label-steps") || "steps";
    var rotProgs = root.getAttribute("data-label-progs") || "tools";

    var flows = root.querySelectorAll("[data-flow]");
    for (var f = 0; f < flows.length; f++) montarFluxo(flows[f]);

    function montarFluxo(flow) {
      var steps = flow.querySelectorAll(".flow-step");
      var details = flow.querySelectorAll(".flow-detail");

      function ativar(n) {
        for (var s = 0; s < steps.length; s++) {
          steps[s].setAttribute("aria-pressed", s === n ? "true" : "false");
          steps[s].classList.toggle("is-done", s < n);
        }
        for (var d = 0; d < details.length; d++) details[d].hidden = d !== n;
      }

      for (var s = 0; s < steps.length; s++) {
        (function (n) {
          steps[n].addEventListener("click", function () { ativar(n); });
        })(s);
      }
      ativar(0);

      // contagem no titulo da secao: "6 etapas · 32 programas"
      var panel = flow.closest(".tool-panel");
      var conta = panel && panel.querySelector("[data-count]");
      if (conta) {
        var nomes = {};
        // so' programas contam; .flow-chips-plain (texto) e .flow-chips-flags
        // (opcoes de linha de comando) ficam de fora
        var chips = flow.querySelectorAll(".flow-chips:not(.flow-chips-plain):not(.flow-chips-flags) li");
        for (var c = 0; c < chips.length; c++) nomes[chips[c].textContent.trim()] = 1;
        var nProgs = Object.keys(nomes).length;
        // o painel pode trocar o rotulo das etapas (ex.: "comandos")
        conta.textContent = steps.length + " " + (conta.getAttribute("data-label-steps") || rotEtapas) +
          (nProgs ? " · " + nProgs + " " + rotProgs : "");
      }

      // filtro por tipo de leitura (curtas / longas)
      var toggle = flow.querySelector("[data-reads-toggle]");
      if (!toggle) return;
      var botoes = toggle.querySelectorAll("button");
      for (var b = 0; b < botoes.length; b++) {
        botoes[b].addEventListener("click", function () {
          var tipo = this.getAttribute("data-reads");
          for (var x = 0; x < botoes.length; x++) {
            botoes[x].setAttribute("aria-pressed", botoes[x] === this ? "true" : "false");
          }
          var marcados = flow.querySelectorAll(".flow-chips li[data-reads]");
          for (var y = 0; y < marcados.length; y++) {
            var fora = tipo !== "all" && marcados[y].getAttribute("data-reads") !== tipo;
            marcados[y].classList.toggle("is-dimmed", fora);
          }
        });
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

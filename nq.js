/* ATR % DEL NQ (sesión regular) Y STOP DE LA ESTRATEGIA NET GEX FONDEOS */
(()=>{
  const LIMIT = 1.65;
  const anchor = document.getElementById("chart");
  const chartPanel = anchor && anchor.closest(".panel");
  if (!chartPanel) return;

  const box = document.createElement("div");
  box.className = "panel";
  box.id = "nqAtrPanel";
  box.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">
      <div>
        <small class="status">NQ · 14D ATR as % of Close (sesión regular)</small><br>
        <strong id="nqAtrValue" style="font-size:30px;color:var(--blue)">—</strong>
        <div class="status" id="nqAtrDate">Cargando datos del NQ...</div>
      </div>
      <div id="nqStop" style="font-size:20px;font-weight:800;padding:10px 16px;border-radius:10px;border:1px solid var(--border)">—</div>
    </div>
    <div class="note">Stop 25 pts por debajo de ${LIMIT.toFixed(2).replace(".",",")}% · Stop 50 pts desde ${LIMIT.toFixed(2).replace(".",",")}%. Valor calculado con el cierre de la última sesión: es el que vale para la siguiente.</div>`;
  chartPanel.insertAdjacentElement("afterend", box);

  const el = id => document.getElementById(id);
  const fmt = n => n.toFixed(2).replace(".", ",");

  fetch("./data/nq_daily.csv?t=" + Date.now())
    .then(r => { if (!r.ok) throw new Error(r.status); return r.text(); })
    .then(text => {
      const lines = text.trim().split(/\r?\n/);
      const head = lines.shift().split(",").map(x => x.trim().toLowerCase());
      const ix = k => head.indexOf(k);
      const d = lines.map(l => {
        const c = l.split(",");
        return { date: c[ix("date")], high: +c[ix("high")], low: +c[ix("low")], close: +c[ix("close")] };
      }).filter(x => x.date && [x.high, x.low, x.close].every(Number.isFinite))
        .sort((a, b) => a.date.localeCompare(b.date));
      if (d.length < 15) throw new Error("pocos datos");

      const tr = d.map((x, i) => i === 0 ? x.high - x.low :
        Math.max(x.high - x.low, Math.abs(x.high - d[i-1].close), Math.abs(x.low - d[i-1].close)));
      const last = d[d.length - 1];
      const atr = tr.slice(-14).reduce((a, b) => a + b, 0) / 14;
      const pct = atr / last.close * 100;

      el("nqAtrValue").textContent = fmt(pct) + "%";
      const [y, m, dd] = last.date.split("-");
      el("nqAtrDate").textContent = "Última sesión " + dd + "/" + m + "/" + y + " · ATR " + Math.round(atr) + " pts";

      const stop = el("nqStop");
      const high = pct >= LIMIT;
      stop.textContent = "Stop " + (high ? 50 : 25) + " pts" + (Math.abs(pct - LIMIT) < 0.05 ? " · cerca del límite" : "");
      stop.style.color = high ? "var(--yellow)" : "var(--green)";
      stop.style.borderColor = high ? "var(--yellow)" : "var(--green)";
    })
    .catch(() => {
      el("nqAtrDate").textContent = "Datos del NQ no disponibles todavía.";
    });
})();

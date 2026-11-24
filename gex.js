/* Strike Wall Analytics · Niveles gamma SPX (datos: data/gex_levels.json) */
(function(){
  const css="/* NIVELES GAMMA SPX */\n.gex-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}\n.gex-badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:800;letter-spacing:.4px}\n.gex-badge.neg{background:#3a1820;color:var(--red);border:1px solid #713d48}\n.gex-badge.pos{background:#10302a;color:var(--green);border:1px solid #1f6b55}\n.gex-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}\n.gex-card{background:#0d1522;border:1px solid var(--border);border-radius:10px;padding:12px}\n.gex-card small{display:block;color:var(--muted);font-size:11px;margin-bottom:6px}\n.gex-card strong{font-size:22px}\n.gex-card .sub{color:var(--muted);font-size:11px;margin-top:4px}\n.gex-zero strong{color:var(--yellow)}.gex-put strong{color:var(--green)}.gex-call strong{color:var(--red)}\n.gex-read{margin-top:14px;font-size:13px;line-height:1.6}\n.gex-levels{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}\n.gex-levels span{background:#0d1522;border:1px solid var(--border);border-radius:7px;padding:5px 9px;font-size:12px}\n.gex-chart{width:100%;height:240px;margin-top:14px}\n@media(max-width:800px){.gex-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}\n";
  const html="  <div class=\"panel\" id=\"gexPanel\">\n    <div class=\"gex-head\">\n      <div>\n        <h2 style=\"margin-bottom:4px\">Niveles gamma SPX \u00b7 hoy</h2>\n        <div class=\"note\" id=\"gexStatus\">Cargando niveles...</div>\n      </div>\n      <span class=\"gex-badge\" id=\"gexRegime\">\u2014</span>\n    </div>\n    <div class=\"gex-grid\">\n      <div class=\"gex-card\"><small>Precio de referencia</small><strong id=\"gexSpot\">\u2014</strong><div class=\"sub\" id=\"gexSpotSrc\"></div></div>\n      <div class=\"gex-card gex-zero\"><small>Zero Gamma</small><strong id=\"gexZero\">\u2014</strong><div class=\"sub\" id=\"gexZeroDist\"></div></div>\n      <div class=\"gex-card gex-put\"><small>Put Wall</small><strong id=\"gexPut\">\u2014</strong><div class=\"sub\" id=\"gexPutDist\"></div></div>\n      <div class=\"gex-card gex-call\"><small>Call Wall</small><strong id=\"gexCall\">\u2014</strong><div class=\"sub\" id=\"gexCallDist\"></div></div>\n      <div class=\"gex-card\"><small>Gamma neto ($M por 1 %)</small><strong id=\"gexNet\">\u2014</strong></div>\n      <div class=\"gex-card\"><small>Delta neto ($bn)</small><strong id=\"gexDelta\">\u2014</strong></div>\n      <div class=\"gex-card\"><small>IV ATM 0DTE</small><strong id=\"gexIv\">\u2014</strong></div>\n      <div class=\"gex-card\"><small>Movimiento impl\u00edcito 0DTE</small><strong id=\"gexMove\">\u2014</strong><div class=\"sub\" id=\"gexRange\"></div></div>\n    </div>\n    <div class=\"gex-read\" id=\"gexRead\"></div>\n    <svg class=\"gex-chart\" id=\"gexChart\" preserveAspectRatio=\"none\"></svg>\n    <div class=\"note\">Strikes con m\u00e1s gamma:</div>\n    <div class=\"gex-levels\" id=\"gexLevels\"></div>\n    <p class=\"note\" id=\"gexSource\">Calculado cada ma\u00f1ana antes de la apertura con el open interest del cierre anterior. Convenci\u00f3n: dealers largos de calls y cortos de puts. Orientativo, no es una recomendaci\u00f3n.</p>\n  </div>\n";
  const st=document.createElement("style");st.textContent=css;document.head.appendChild(st);
  const main=document.querySelector("main");
  main.insertAdjacentHTML("afterbegin",html);
})();
/* NIVELES GAMMA SPX */
(function(){
  const $=id=>document.getElementById(id);
  const fmt=(v,d=0)=>v==null?"—":Number(v).toLocaleString("es-ES",{minimumFractionDigits:d,maximumFractionDigits:d});
  const dist=(lvl,spot)=>lvl==null?"":((lvl-spot>=0?"+":"")+fmt(lvl-spot,1)+" pts");
  fetch("./data/gex_levels.json?v="+Date.now(),{cache:"no-store"})
    .then(r=>{if(!r.ok)throw new Error("Todavía no hay niveles calculados.");return r.json();})
    .then(d=>{
      const s=d.spot;
      const todayNY=new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York"}).format(new Date());
      $("gexStatus").textContent="Actualizado "+d.updated_madrid+" (hora España) · sesión "+d.session+(d.session!==todayNY?" · ⚠️ no es la sesión de hoy":"");
      const neg=d.regime==="negativo";
      $("gexRegime").textContent="GAMMA "+d.regime.toUpperCase();
      $("gexRegime").className="gex-badge "+(neg?"neg":"pos");
      $("gexSpot").textContent=fmt(s,2);
      $("gexSpotSrc").textContent=d.spot_source;
      $("gexZero").textContent=fmt(d.zero_gamma,2);
      $("gexZeroDist").textContent=dist(d.zero_gamma,s);
      $("gexPut").textContent=fmt(d.put_wall);
      $("gexPutDist").textContent=dist(d.put_wall,s);
      $("gexCall").textContent=fmt(d.call_wall);
      $("gexCallDist").textContent=dist(d.call_wall,s);
      $("gexNet").textContent=fmt(d.net_gex_m,1);
      $("gexNet").style.color=d.net_gex_m<0?"var(--red)":"var(--green)";
      $("gexDelta").textContent=fmt(d.net_delta_bn,2);
      $("gexDelta").style.color=d.net_delta_bn<0?"var(--red)":"var(--green)";
      $("gexIv").textContent=fmt(d.iv_atm_0dte,1)+" %";
      $("gexMove").textContent="±"+fmt(d.implied_move,1)+" pts";
      $("gexRange").textContent=fmt(s-d.implied_move)+" – "+fmt(s+d.implied_move)+" · "+d.implied_move_method;
      let read;
      if(d.zero_gamma==null){read="No hay cambio de signo del gamma en ±8 % del precio: régimen "+d.regime+" en todo el rango.";}
      else{
        const below=s<d.zero_gamma;
        read="El SPX está <b>"+fmt(Math.abs(s-d.zero_gamma),1)+" puntos "+(below?"POR DEBAJO":"POR ENCIMA")+"</b> del Zero Gamma. "+
          (below?"Por debajo del Zero Gamma la cobertura de los dealers tiende a amplificar los movimientos.":"Por encima del Zero Gamma la cobertura de los dealers tiende a frenar los movimientos.");
      }
      $("gexRead").innerHTML=read+" Rango entre muros: "+fmt(d.put_wall)+" – "+fmt(d.call_wall)+".";
      $("gexLevels").innerHTML=(d.top_levels||[]).map(l=>'<span>'+fmt(l.strike)+' · <b style="color:'+(l.gex_m<0?"var(--red)":"var(--green)")+'">'+fmt(l.gex_m,0)+'M</b></span>').join("");
      $("gexSource").textContent="Fuente: "+d.source+". Calculado antes de la apertura con el open interest del cierre anterior ("+d.options_used+" opciones, vencimientos ≤45 días). Convención: dealers largos de calls y cortos de puts. Orientativo, no es una recomendación.";
      drawChart(d);
    })
    .catch(e=>{$("gexStatus").textContent=e.message;});

  function drawChart(d){
    const svg=$("gexChart"),bars=d.by_strike||[];
    if(!bars.length){svg.style.display="none";return;}
    const W=1000,H=240,P=28;
    svg.setAttribute("viewBox","0 0 "+W+" "+H);
    const xs=bars.map(b=>b.strike),min=Math.min(...xs),max=Math.max(...xs);
    const m=Math.max(...bars.map(b=>Math.abs(b.gex_m)))||1;
    const x=k=>P+(k-min)/(max-min||1)*(W-2*P),mid=(H-20)/2;
    const bw=Math.max(1.5,(W-2*P)/bars.length*0.7);
    let out='<line x1="'+P+'" x2="'+(W-P)+'" y1="'+mid+'" y2="'+mid+'" stroke="#263447"/>';
    bars.forEach(b=>{const h=Math.abs(b.gex_m)/m*(mid-8);
      out+='<rect x="'+(x(b.strike)-bw/2)+'" y="'+(b.gex_m>=0?mid-h:mid)+'" width="'+bw+'" height="'+h+'" fill="'+(b.gex_m>=0?"#31c995":"#ff7777")+'" opacity=".85"><title>'+b.strike+': '+b.gex_m+'M</title></rect>';});
    const mark=(v,c,t)=>{if(v==null||v<min||v>max)return;out+='<line x1="'+x(v)+'" x2="'+x(v)+'" y1="4" y2="'+(H-22)+'" stroke="'+c+'" stroke-dasharray="4 3"/><text x="'+x(v)+'" y="'+(H-6)+'" fill="'+c+'" font-size="12" text-anchor="middle">'+t+'</text>';};
    mark(d.spot,"#65b5ff","Precio");mark(d.zero_gamma,"#f2bd55","ZG");
    mark(d.put_wall,"#31c995","PW");mark(d.call_wall,"#ff7777","CW");
    svg.innerHTML=out;
  }
})();

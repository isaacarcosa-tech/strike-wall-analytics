"""
Niveles de gamma del SPX (GEX) para Strike Wall Analytics.

Se ejecuta cada mañana con GitHub Actions, antes de la apertura de Nueva York.
El open interest se publica una vez al día (de madrugada), así que con el OI
del cierre anterior + el precio estimado premarket se calculan:

  - Gamma neto (GEX, $M por 1 % de movimiento)
  - Delta neto de las opciones abiertas
  - Zero Gamma (precio donde el GEX total cambia de signo)
  - Put Wall / Call Wall
  - IV ATM y movimiento implícito del 0DTE
  - Strikes con más gamma

Convención GEX habitual: dealers largos de calls (+) y cortos de puts (-).
Fuente principal: CBOE (cadena retrasada, gratis). Respaldo: Yahoo Finance.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

OUT_JSON = Path("data/gex_levels.json")
OUT_HIST = Path("data/gex_history.csv")

NY = ZoneInfo("America/New_York")
MADRID = ZoneInfo("Europe/Madrid")

MAX_DTE = 45          # vencimientos incluidos en el GEX
STRIKE_RANGE = 0.15   # ±15 % alrededor del spot
RATE = 0.04           # tipo libre de riesgo aproximado
CONTRACT = 100

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json"


# ---------------------------------------------------------------- utilidades

def norm_pdf(x):
    return np.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def norm_cdf(x):
    return 0.5 * (1 + np.vectorize(math.erf)(x / math.sqrt(2)))


def expiry_datetime(exp: date) -> datetime:
    # SPXW vence a las 16:00 de Nueva York
    return datetime.combine(exp, time(16, 0), tzinfo=NY)


def years_to_expiry(exp: date, now: datetime) -> float:
    secs = (expiry_datetime(exp) - now).total_seconds()
    return max(secs, 3600.0) / (365.0 * 24 * 3600)


def parse_occ(symbol: str):
    """SPXW261124C07200000 -> (date, 'C', 7200.0)"""
    tail = symbol[-15:]
    exp = datetime.strptime(tail[:6], "%y%m%d").date()
    return exp, tail[6], int(tail[7:]) / 1000.0


# ------------------------------------------------------------------- fuentes

def load_cboe() -> tuple[pd.DataFrame, float | None]:
    import requests

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.cboe.com/",
    }
    r = requests.get(CBOE_URL, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()["data"]

    rows = []
    for o in data["options"]:
        exp, kind, strike = parse_occ(o["option"])
        rows.append({
            "expiry": exp,
            "type": kind,
            "strike": strike,
            "iv": float(o.get("iv") or 0),
            "oi": float(o.get("open_interest") or 0),
            "bid": float(o.get("bid") or 0),
            "ask": float(o.get("ask") or 0),
        })
    spot = data.get("current_price") or data.get("close")
    return pd.DataFrame(rows), (float(spot) if spot else None)


def load_yahoo(today: date) -> tuple[pd.DataFrame, float | None]:
    import yfinance as yf

    t = yf.Ticker("^SPX")
    rows = []
    for exp_str in t.options:
        exp = datetime.strptime(exp_str, "%Y-%m-%d").date()
        if (exp - today).days > MAX_DTE:
            break
        if exp < today:
            continue
        chain = t.option_chain(exp_str)
        for kind, df in (("C", chain.calls), ("P", chain.puts)):
            for _, o in df.iterrows():
                rows.append({
                    "expiry": exp,
                    "type": kind,
                    "strike": float(o["strike"]),
                    "iv": float(o.get("impliedVolatility") or 0),
                    "oi": float(o.get("openInterest") or 0),
                    "bid": float(o.get("bid") or 0),
                    "ask": float(o.get("ask") or 0),
                })
    return pd.DataFrame(rows), None


def spx_reference() -> tuple[float, str]:
    """
    Precio de referencia del SPX antes de la apertura:
    ES (futuro) actual menos la base ES-SPX del último cierre.
    Si falla, último cierre del SPX.
    """
    import yfinance as yf

    spx = yf.Ticker("^GSPC").history(period="5d", interval="1d")
    spx_close = float(spx["Close"].dropna().iloc[-1])

    try:
        es_daily = yf.Ticker("ES=F").history(period="5d", interval="1d")
        es_intra = yf.Ticker("ES=F").history(period="2d", interval="5m",
                                             prepost=True)
        spx_last_day = spx.index[-1].date()
        es_daily = es_daily[es_daily.index.date <= spx_last_day]
        basis = float(es_daily["Close"].dropna().iloc[-1]) - spx_close
        es_now = float(es_intra["Close"].dropna().iloc[-1])
        est = es_now - basis
        if abs(est / spx_close - 1) < 0.08:
            return est, "SPX estimado premarket (ES − base)"
    except Exception as e:  # noqa: BLE001
        print("Aviso: no se pudo estimar con ES:", e)

    return spx_close, "Último cierre del SPX"


# ------------------------------------------------------------------- cálculo

def gamma_bs(S, K, T, iv):
    sqrtT = np.sqrt(T)
    d1 = (np.log(S / K) + (RATE + 0.5 * iv * iv) * T) / (iv * sqrtT)
    return norm_pdf(d1) / (S * iv * sqrtT), d1


def compute(df: pd.DataFrame, spot: float, now: datetime) -> dict:
    today = now.astimezone(NY).date()

    df = df[(df["expiry"] >= today)
            & ((df["expiry"] - today).apply(lambda d: d.days) <= MAX_DTE)
            & (df["oi"] > 0) & (df["iv"] > 0.01) & (df["iv"] < 5)
            & (df["strike"].between(spot * (1 - STRIKE_RANGE),
                                    spot * (1 + STRIKE_RANGE)))].copy()
    if len(df) < 200:
        raise RuntimeError(f"Muy pocas opciones válidas: {len(df)}")

    df["T"] = df["expiry"].apply(lambda e: years_to_expiry(e, now))
    sign = np.where(df["type"] == "C", 1.0, -1.0)
    K, T, iv, oi = (df[c].to_numpy(float) for c in ("strike", "T", "iv", "oi"))

    # GEX y delta en el spot actual
    g, d1 = gamma_bs(spot, K, T, iv)
    gex = sign * g * oi * CONTRACT * spot * spot * 0.01      # $ por 1 %
    delta = np.where(sign > 0, norm_cdf(d1), norm_cdf(d1) - 1)
    df["gex"] = gex

    by_strike = df.groupby("strike")["gex"].sum()
    # Walls: concentración de gamma en cada strike si el precio llegara allí
    # (gamma evaluada con S = K), para no favorecer solo a los strikes
    # pegados al precio actual.
    gK, _ = gamma_bs(K, K, T, iv)
    df["gex_at_k"] = gK * oi * CONTRACT * K * K * 0.01
    calls = df[df["type"] == "C"].groupby("strike")["gex_at_k"].sum()
    puts = df[df["type"] == "P"].groupby("strike")["gex_at_k"].sum()

    # Perfil de gamma para el Zero Gamma
    grid = np.linspace(spot * 0.92, spot * 1.08, 321)
    profile = []
    for S in grid:
        gs, _ = gamma_bs(S, K, T, iv)
        profile.append(float(np.sum(sign * gs * oi * CONTRACT * S * S * 0.01)))
    profile = np.array(profile)

    zero_gamma = None
    crossings = np.where(np.diff(np.sign(profile)) != 0)[0]
    if len(crossings):
        i = crossings[np.argmin(np.abs(grid[crossings] - spot))]
        x0, x1, y0, y1 = grid[i], grid[i + 1], profile[i], profile[i + 1]
        zero_gamma = float(x0 - y0 * (x1 - x0) / (y1 - y0))

    # 0DTE: IV ATM y movimiento implícito
    exp0 = df["expiry"].min()
    d0 = df[df["expiry"] == exp0]
    atm = float(d0.iloc[(d0["strike"] - spot).abs().argsort()]["strike"].iloc[0])
    atm_rows = d0[d0["strike"] == atm]
    iv_atm = float(atm_rows["iv"].mean())
    mids = [(r.bid + r.ask) / 2 for r in atm_rows.itertuples()
            if r.bid > 0 and r.ask > 0]
    T0 = years_to_expiry(exp0, now)
    if len(mids) == 2:
        implied_move = float(sum(mids))
        move_method = "Straddle ATM (precio medio)"
    else:
        implied_move = float(spot * iv_atm * math.sqrt(T0) * math.sqrt(2 / math.pi))
        move_method = "Estimado con IV ATM"

    top = by_strike.reindex(by_strike.abs().sort_values(ascending=False).index)
    top_levels = [{"strike": float(k), "gex_m": round(float(v) / 1e6, 1)}
                  for k, v in top.head(8).items()]

    net_gex = float(gex.sum())
    return {
        "spot": round(spot, 2),
        "net_gex_m": round(net_gex / 1e6, 1),
        "regime": "positivo" if net_gex >= 0 else "negativo",
        "net_delta_bn": round(float(np.sum(delta * oi * CONTRACT * spot)) / 1e9, 2),
        "zero_gamma": round(zero_gamma, 2) if zero_gamma else None,
        "call_wall": float(calls.idxmax()),
        "put_wall": float(puts.idxmax()),
        "iv_atm_0dte": round(iv_atm * 100, 1),
        "implied_move": round(implied_move, 2),
        "implied_move_method": move_method,
        "expiry_0dte": exp0.isoformat(),
        "atm_strike": atm,
        "top_levels": sorted(top_levels, key=lambda x: -x["strike"]),
        "profile": {
            "spot": [round(float(x), 1) for x in grid[::4]],
            "gex_m": [round(float(y) / 1e6, 1) for y in profile[::4]],
        },
        "by_strike": [
            {"strike": float(k), "gex_m": round(float(v) / 1e6, 1)}
            for k, v in by_strike.items()
            if abs(k - spot) <= spot * 0.05
        ],
        "options_used": int(len(df)),
    }


# ---------------------------------------------------------------------- main

def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(NY).date()

    spot, spot_source = spx_reference()
    print(f"Referencia: {spot:.2f} ({spot_source})")

    source = "CBOE (cadena retrasada)"
    try:
        chain, _ = load_cboe()
        if chain.empty:
            raise RuntimeError("CBOE sin datos")
    except Exception as e:  # noqa: BLE001
        print("CBOE no disponible, uso Yahoo Finance:", e)
        chain, _ = load_yahoo(today)
        source = "Yahoo Finance"

    result = compute(chain, spot, now)
    result.update({
        "updated_utc": now.isoformat(timespec="seconds"),
        "updated_madrid": now.astimezone(MADRID).strftime("%d/%m/%Y %H:%M"),
        "session": today.isoformat(),
        "source": source,
        "spot_source": spot_source,
    })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    tmp.replace(OUT_JSON)

    # Histórico (una fila por sesión)
    fields = ["session", "spot", "zero_gamma", "put_wall", "call_wall",
              "net_gex_m", "net_delta_bn", "iv_atm_0dte", "implied_move"]
    rows = []
    if OUT_HIST.exists():
        with OUT_HIST.open() as f:
            rows = [r for r in csv.DictReader(f) if r["session"] != result["session"]]
    rows.append({k: result[k] for k in fields})
    with OUT_HIST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(json.dumps({k: result[k] for k in fields + ["source"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

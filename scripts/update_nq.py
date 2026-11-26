from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path("data/nq_daily.csv")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("Descargando velas de 30 min del NQ (NQ=F)...")

    df = yf.download(
        "NQ=F",
        period="60d",
        interval="30m",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
        timeout=30,
    )
    if df is None or df.empty:
        raise RuntimeError("Yahoo Finance no devolvió datos del NQ.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    idx = pd.to_datetime(df.index)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert("America/New_York")

    # Sesión regular 9:30-16:00 NY (velas de 30 min que empiezan entre 9:30 y 15:30)
    rth = df.between_time("09:30", "15:30")
    day = rth.groupby(rth.index.date).agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        n=("Close", "size"),
    )
    day = day[day["n"] >= 4].drop(columns="n").dropna()
    day.index.name = "Date"
    day = day.reset_index()
    day["Date"] = pd.to_datetime(day["Date"]).dt.strftime("%Y-%m-%d")

    if OUT.exists():
        old = pd.read_csv(OUT)
        day = pd.concat([old[~old["Date"].isin(day["Date"])], day])
    day = day.sort_values("Date")

    if len(day) < 15:
        raise RuntimeError(f"Histórico insuficiente: {len(day)} sesiones.")

    day.to_csv(OUT, index=False, float_format="%.2f")
    print(f"CSV guardado: {OUT} | {len(day)} sesiones | última {day['Date'].iloc[-1]}")


if __name__ == "__main__":
    main()

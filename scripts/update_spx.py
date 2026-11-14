
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

OUT = Path("data/spx_daily.csv")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    print("Descargando datos diarios del S&P 500 (^GSPC)...")

    df = yf.download(
        "^GSPC",
        period="5y",
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
        timeout=30,
    )

    if df is None or df.empty:
        raise RuntimeError("Yahoo Finance no devolvió datos.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise RuntimeError(f"Faltan columnas: {missing}")

    df = df[required].dropna().copy()
    df.index = pd.to_datetime(df.index)

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df.index.name = "Date"
    df = df.reset_index()

    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)

    if len(df) < 900:
        raise RuntimeError(
            f"Histórico insuficiente: {len(df)} sesiones."
        )

    latest = pd.to_datetime(df["Date"].iloc[-1]).date()
    age = (datetime.now(timezone.utc).date() - latest).days

    if age > 7:
        raise RuntimeError(
            f"Última sesión demasiado antigua: {latest}"
        )

    for _, row in df.iterrows():
        if row["High"] < max(row["Open"], row["Close"], row["Low"]):
            raise RuntimeError(f"OHLC inválido en {row['Date']}")

        if row["Low"] > min(row["Open"], row["Close"], row["High"]):
            raise RuntimeError(f"OHLC inválido en {row['Date']}")

    temp = OUT.with_suffix(".tmp")
    df.to_csv(temp, index=False, float_format="%.6f")
    temp.replace(OUT)

    print(
        f"CSV guardado: {OUT} | "
        f"{len(df)} sesiones | "
        f"{df['Date'].iloc[0]} a {df['Date'].iloc[-1]}"
    )


if __name__ == "__main__":
    main()

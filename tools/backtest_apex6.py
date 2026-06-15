"""
backtest_apex6.py — Resumen de desempeño de APEX6.

Uso:
    python tools/backtest_apex6.py [--days 90]

Lee outputs/performance.csv y muestra:
  - Tasa de acierto (hits_quiniela_top12 >= 1) global y por categoría
  - Desglose por lotería/sorteo
  - Comparación contra la línea base de azar (~30.6%)

Sirve para revisar periódicamente si los umbrales calibrados
(NUCLEO: signal 0.009-0.029, a11 2-4 | VIGILANCIA: signal 0.005-0.035, a11 2-4)
siguen siendo válidos a medida que se acumulan más datos.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

import pandas as pd

RANDOM_BASELINE = 0.306  # ~1 - (97/100)^12, probabilidad de acierto por azar puro


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90, help="Ventana de días a analizar")
    parser.add_argument("--path", type=str, default="outputs/performance.csv")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"No se encontró {args.path}. Aún no hay datos para analizar.")
        return

    df = pd.read_csv(args.path)
    if df.empty:
        print("performance.csv está vacío. Aún no hay sorteos calificados.")
        return

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    cutoff = datetime.now() - timedelta(days=args.days)
    df = df[df["date"] >= cutoff].copy()

    if df.empty:
        print(f"No hay datos en los últimos {args.days} días.")
        return

    df["hit"] = (df["hits_quiniela_top12"].fillna(0) >= 1).astype(int)

    print(f"=== APEX6 — Desempeño últimos {args.days} días ({len(df)} sorteos) ===\n")
    print(f"Línea base de azar (referencia): {RANDOM_BASELINE:.1%}\n")

    overall = df["hit"].mean()
    print(f"Tasa de acierto global: {overall:.1%}  (n={len(df)})")
    print(f"  vs. azar: {overall - RANDOM_BASELINE:+.1%}\n")

    if "categoria" in df.columns:
        print("Por categoría:")
        for cat, sub in df.groupby("categoria"):
            print(f"  {cat:12s}: {sub['hit'].mean():.1%}  (n={len(sub)})")
        print()

    print("Por lotería/sorteo:")
    g = df.groupby(["lottery", "draw"]).agg(n=("hit", "size"), hitrate=("hit", "mean"))
    print(g.sort_values("hitrate", ascending=False))

    if "pale_hits" in df.columns:
        pale_rate = (df["pale_hits"].fillna(0) > 0).mean()
        print(f"\nTasa de acierto en pales: {pale_rate:.1%}  (n={len(df)})")


if __name__ == "__main__":
    main()

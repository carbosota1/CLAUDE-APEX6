"""
sync_histories.py — Upsert de historiales XLSX descargados desde CLAUDE-LOTMIX.

Llamado desde el step "Sync historiales" de apex6.yml.
Los archivos temporales /tmp/*.lotmix.xlsx deben existir previamente
(descargados por el curl en el mismo step).
"""
import os
import sys
import traceback

sys.path.insert(0, "src")

import pandas as pd
from io_xlsx import upsert_history_xlsx, ensure_dir, read_history_xlsx

LOG = "data/sync_status.txt"


def log(msg):
    print(msg)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


dst_dir = "data/histories"
ensure_dir(dst_dir)

jobs = [
    ("/tmp/anguilla.lotmix.xlsx",   os.path.join(dst_dir, "Anguilla history.xlsx")),
    ("/tmp/laprimera.lotmix.xlsx",  os.path.join(dst_dir, "La Primera History.xlsx")),
    ("/tmp/lanacional.lotmix.xlsx", os.path.join(dst_dir, "La nacional history.xlsx")),
    ("/tmp/lasuerte.lotmix.xlsx",   os.path.join(dst_dir, "La suerte history.xlsx")),
]

for src_path, dst_path in jobs:
    fname = os.path.basename(dst_path)
    if not os.path.exists(src_path):
        log(f"[SKIP] {fname}: no descargado")
        continue
    try:
        xls_src = pd.ExcelFile(src_path, engine="openpyxl")
        log(f"[INFO] {fname} hojas LOTMIX: {xls_src.sheet_names}")
        sheet = "history" if "history" in xls_src.sheet_names else xls_src.sheet_names[0]
        df_src = pd.read_excel(src_path, sheet_name=sheet, dtype=str, engine="openpyxl")
        df_src.columns = [c.strip().lower() for c in df_src.columns]
        log(f"[INFO] {fname} cols LOTMIX: {list(df_src.columns)[:8]}")

        needed = {"fecha", "sorteo", "primero", "segundo", "tercero"}
        missing = needed - set(df_src.columns)
        if missing:
            log(f"[WARN] {fname}: faltan cols {missing}")
            continue

        df_src = df_src[["fecha", "sorteo", "primero", "segundo", "tercero"]].fillna("")
        log(f"[INFO] {fname} LOTMIX filas totales: {len(df_src)}")

        df_old = read_history_xlsx(dst_path)
        log(f"[INFO] {fname} APEX6 filas antes: {len(df_old)}")
        by_old = df_old.groupby("sorteo").size().to_dict()
        by_src = df_src.groupby("sorteo").size().to_dict()
        for s in sorted(set(by_old) | set(by_src)):
            diff = by_src.get(s, 0) - by_old.get(s, 0)
            log(f"    {s}: APEX6={by_old.get(s,0)} LOTMIX={by_src.get(s,0)} diff=+{diff}")

        upsert_history_xlsx(dst_path, df_src)

        df_after = read_history_xlsx(dst_path)
        added = len(df_after) - len(df_old)
        log(f"[OK] {fname}: {len(df_old)} -> {len(df_after)} filas (+{added})")

    except Exception as e:
        log(f"[ERROR] {fname}: {e}")
        traceback.print_exc()

log("[DONE] Sync completado")

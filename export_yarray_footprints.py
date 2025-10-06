"""
Exporta contornos Yarray a CSVs por pie (izquierdo y derecho) por participante.

Para cada carpeta data/PXX que contenga uno o más archivos *_tests_*.csv, este script:
  - Lee los registros de pasos (filas) y decodifica el campo Yarray como una serie de valores.
  - Escala robustamente esa serie a [Ybottom_cm, Ytop_cm] (ancho lateral de la pisada) usando percentiles 1–99.
  - Genera N puntos (x_cm, y_cm) por registro (N = longitud de Yarray), donde:
      x_cm = posición lateral (0..~61 cm)
      y_cm = posición longitudinal (0..~488 cm)
    Nota: y_cm se construye como un linspace entre Xback_cm y Xfront_cm.
  - Escribe los puntos en dos ficheros por participante: footprints_left.csv (Foot=0) y footprints_right.csv (Foot=1).

Salida por participante (en data/PXX/):
  - footprints_left.csv
  - footprints_right.csv

Columnas del CSV de salida:
  participant, source_file, gait_id, event, foot, sample_idx, x_cm, y_cm,
  xback_cm, xfront_cm, ybottom_cm, ytop_cm, n_samples

Uso:
  python scripts/export_yarray_footprints.py [--data-root data] [--conv 1.27] [--overwrite]

Requisitos: pandas, numpy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


def robust_minmax(vals: np.ndarray) -> tuple[float, float]:
    """Devuelve (lo, hi) usando percentiles 1 y 99; si colapsan, usa min/max reales.

    vals debe ser float y no vacío.
    """
    if vals.size == 0:
        return 0.0, 1.0
    p1, p99 = np.percentile(vals, [1, 99])
    if not np.isfinite(p1) or not np.isfinite(p99) or p99 <= p1:
        p1, p99 = float(np.min(vals)), float(np.max(vals))
    if p99 == p1:
        # Evitar división por cero más adelante
        p99 = p1 + 1e-9
    return float(p1), float(p99)


def decode_yarray_to_xy(
    yarray_raw: str,
    Xback_cm: float,
    Xfront_cm: float,
    Ybottom_cm: float,
    Ytop_cm: float,
) -> Optional[pd.DataFrame]:
    """Decodifica Yarray a una serie de puntos (x_cm, y_cm) en orientación vertical.

    - Convierte cada carácter a ord() -> escala robusta a [0,1] -> proyecta a ancho [Ybottom_cm, Ytop_cm].
    - y_cm es linspace entre [Xback_cm, Xfront_cm].

    Devuelve un DataFrame con columnas: sample_idx, x_cm, y_cm (o None si no hay datos válidos).
    """
    if not isinstance(yarray_raw, str) or len(yarray_raw) == 0:
        return None

    vals = np.fromiter((ord(c) for c in yarray_raw), dtype=float, count=len(yarray_raw))
    if vals.size == 0 or not np.isfinite(vals).all():
        return None

    lo, hi = robust_minmax(vals)
    vals_norm = (vals - lo) / (hi - lo)

    # Ancho lateral (x)
    dx = (Ytop_cm - Ybottom_cm)
    dy = (Xfront_cm - Xback_cm)
    if abs(dx) < 1e-9 or abs(dy) < 1e-9:
        return None

    x_cm = Ybottom_cm + vals_norm * dx
    N = vals.shape[0]
    y_cm = np.linspace(Xback_cm, Xfront_cm, N)

    df = pd.DataFrame({
        "sample_idx": np.arange(N, dtype=int),
        "x_cm": x_cm.astype(float),
        "y_cm": y_cm.astype(float),
    })
    return df


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def process_participant(
    participant_dir: Path,
    conv: float,
    overwrite: bool = False,
) -> dict:
    """Procesa una carpeta de participante (data/PXX) y genera CSVs por pie.

    Devuelve resumen con contadores.
    """
    left_out = participant_dir / "footprints_left.csv"
    right_out = participant_dir / "footprints_right.csv"

    if not overwrite and (left_out.exists() or right_out.exists()):
        # Para evitar mezclar múltiples ejecuciones si hay varios *_tests_*.csv,
        # exigimos overwrite o borrado previo.
        return {
            "participant": participant_dir.name,
            "skipped": True,
            "reason": "output_exists",
        }

    # Preparar acumuladores por pie
    accum: Dict[int, list] = {0: [], 1: []}
    rows_total = 0
    steps_used = {0: 0, 1: 0}

    tests_csvs = sorted(participant_dir.glob("*_tests_*.csv"))
    if not tests_csvs:
        return {
            "participant": participant_dir.name,
            "skipped": True,
            "reason": "no_tests_csv",
        }

    for csv_path in tests_csvs:
        try:
            df = pd.read_csv(csv_path, sep=";")
        except Exception as e:
            print(f"[WARN] No se pudo leer {csv_path}: {e}", file=sys.stderr)
            continue

        required_cols = {"Gait_Id", "Event", "Foot", "Xback", "Xfront", "Ybottom", "Ytop", "Yarray"}
        missing = required_cols - set(df.columns)
        if missing:
            print(f"[WARN] Faltan columnas {missing} en {csv_path}", file=sys.stderr)
            continue

        # Orden estable por Gait/Event
        df = df.sort_values(["Gait_Id", "Event"]).reset_index(drop=True)
        participant = participant_dir.name

        for _, r in df.iterrows():
            try:
                foot = int(r["Foot"]) if pd.notna(r["Foot"]) else None
            except Exception:
                foot = None
            if foot not in (0, 1):
                continue

            try:
                Xback_cm = float(r["Xback"]) * conv
                Xfront_cm = float(r["Xfront"]) * conv
                Ybottom_cm = float(r["Ybottom"]) * conv
                Ytop_cm = float(r["Ytop"]) * conv
            except Exception:
                continue

            yarray_raw = str(r["Yarray"]) if pd.notna(r["Yarray"]) else ""
            df_xy = decode_yarray_to_xy(yarray_raw, Xback_cm, Xfront_cm, Ybottom_cm, Ytop_cm)
            if df_xy is None or df_xy.empty:
                continue

            rows_total += int(df_xy.shape[0])
            steps_used[foot] += 1

            df_xy["participant"] = participant
            df_xy["source_file"] = csv_path.name
            df_xy["gait_id"] = int(r["Gait_Id"]) if pd.notna(r["Gait_Id"]) else None
            df_xy["event"] = int(r["Event"]) if pd.notna(r["Event"]) else None
            df_xy["foot"] = foot
            df_xy["xback_cm"] = Xback_cm
            df_xy["xfront_cm"] = Xfront_cm
            df_xy["ybottom_cm"] = Ybottom_cm
            df_xy["ytop_cm"] = Ytop_cm
            df_xy["n_samples"] = int(df_xy.shape[0])

            accum[foot].append(df_xy)

    # Concatenar y escribir
    summary = {
        "participant": participant_dir.name,
        "skipped": False,
        "rows_total": rows_total,
        "steps_left": steps_used[0],
        "steps_right": steps_used[1],
    }

    # Crear carpeta por si no existe
    ensure_parent(left_out)

    for foot, out_path in ((0, left_out), (1, right_out)):
        if accum[foot]:
            out_df = pd.concat(accum[foot], ignore_index=True)
            # Orden por gait/event/sample_idx
            out_df = out_df.sort_values(["gait_id", "event", "sample_idx"]).reset_index(drop=True)
            out_df.to_csv(out_path, index=False)
        else:
            # Si no hubo pasos de ese pie, borrar si existía para evitar confusión
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta contornos Yarray a CSV por pie y por participante")
    parser.add_argument("--data-root", type=str, default="data", help="Ruta a la carpeta de datos (default: data)")
    parser.add_argument("--conv", type=float, default=1.27, help="Factor de conversión a cm (default: 1.27)")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescribir footprints_*.csv si ya existen")
    parser.add_argument(
        "--only",
        action="append",
        help="Procesar solo participantes específicos (p.ej., --only P5 o --only P5 --only P10 o --only P5,P10)",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    if not data_root.exists() or not data_root.is_dir():
        print(f"[ERROR] Carpeta de datos no encontrada: {data_root}", file=sys.stderr)
        return 2

    participants: list[Path]
    if args.only:
        requested: list[str] = []
        for part in args.only:
            requested.extend([x.strip() for x in part.split(",") if x.strip()])
        participants = []
        for name in requested:
            p = (data_root / name)
            if p.is_dir():
                participants.append(p)
            else:
                print(f"[WARN] Carpeta de participante no encontrada: {p}", file=sys.stderr)
    else:
        participants = []
        for p in data_root.iterdir():
            if not p.is_dir():
                continue
            name = p.name.upper()
            if not name.startswith("P"):
                continue
            # Soportar tanto PXX como PXX_ (con guión bajo al final)
            rest = name[1:]
            if rest.isdigit():  # Patrón PXX
                participants.append(p)
            elif rest.endswith("_") and rest[:-1].isdigit():  # Patrón PXX_
                participants.append(p)
    if not participants:
        print(f"[WARN] No se encontraron carpetas PXX o PXX_ bajo {data_root}")
        return 0

    def extract_participant_number(path: Path) -> int:
        """Extrae el número del participante de nombres como P1, P10, P1_, P10_, etc."""
        name = path.name.upper()
        if name.startswith("P"):
            rest = name[1:]
            if rest.isdigit():
                return int(rest)
            elif rest.endswith("_") and rest[:-1].isdigit():
                return int(rest[:-1])
        return 0
    
    totals = []
    for pdir in sorted(participants, key=extract_participant_number):
        res = process_participant(pdir, conv=args.conv, overwrite=args.overwrite)
        totals.append(res)
        if res.get("skipped"):
            reason = res.get("reason", "")
            print(f"- {pdir.name}: SKIPPED ({reason})")
        else:
            print(
                f"- {pdir.name}: filas={res['rows_total']} pasos_left={res['steps_left']} pasos_right={res['steps_right']}"
            )

    # Resumen final
    done = [t for t in totals if not t.get("skipped")]
    skipped = [t for t in totals if t.get("skipped")]
    print("\nResumen:")
    print(f"  Procesados: {len(done)} participantes, Omitidos: {len(skipped)}")
    if done:
        total_rows = sum(t.get("rows_total", 0) for t in done)
        total_left = sum(t.get("steps_left", 0) for t in done)
        total_right = sum(t.get("steps_right", 0) for t in done)
        print(f"  Total puntos exportados: {total_rows}")
        print(f"  Total pasos (Left/Right): {total_left}/{total_right}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

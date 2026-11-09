"""Aggregate failure rates per line and station from the Bosch Production Line
Performance data (Kaggle).

Column names look like L3_S32_F3850: line 3, station 32, feature 3850.
A part "passed" a station if it has at least one measurement there.
Response = 1 means the part failed the final quality check.

The raw file is about 2 GB, so it is read in chunks straight from the zip and
only the counts are kept in memory. Raw data is never written to this repo.

Usage:
    python prepare_data.py path/to/train_numeric.csv.zip
    python prepare_data.py <zip> --sample 100000   # random subset of parts
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).parent / "data"
CHUNK_SIZE = 50_000
COL_PATTERN = re.compile(r"^L(\d+)_S(\d+)_F\d+$")


def station_columns(columns):
    """Map 'L3_S32' -> list of feature columns of that station."""
    stations = defaultdict(list)
    for col in columns:
        m = COL_PATTERN.match(col)
        if m:
            stations[f"L{m.group(1)}_S{m.group(2)}"].append(col)
    return dict(sorted(stations.items(), key=lambda kv: (int(kv[0][1:].split("_S")[0]), int(kv[0].split("_S")[1]))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="path to train_numeric.csv.zip (or .csv)")
    parser.add_argument("--sample", type=int, default=None, help="number of parts to sample")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    header = pd.read_csv(args.source, nrows=0).columns
    stations = station_columns(header)
    print(f"{len(stations)} stations found")

    # 1,183,747 parts in train_numeric. Keep each with this probability.
    keep_prob = None if args.sample is None else min(1.0, args.sample / 1_183_747)
    rng = np.random.default_rng(args.seed)

    parts = defaultdict(int)
    failed = defaultdict(int)
    line_parts = defaultdict(int)
    line_failed = defaultdict(int)
    total_parts = total_failed = 0

    reader = pd.read_csv(args.source, chunksize=CHUNK_SIZE, dtype=np.float32)
    for i, chunk in enumerate(reader):
        if keep_prob is not None:
            chunk = chunk[rng.random(len(chunk)) < keep_prob]
        is_fail = chunk["Response"].to_numpy() == 1
        total_parts += len(chunk)
        total_failed += int(is_fail.sum())

        line_passed = defaultdict(lambda: np.zeros(len(chunk), dtype=bool))
        for station, cols in stations.items():
            passed = chunk[cols].notna().any(axis=1).to_numpy()
            parts[station] += int(passed.sum())
            failed[station] += int((passed & is_fail).sum())
            line_passed[station.split("_")[0]] |= passed
        for line, passed in line_passed.items():
            line_parts[line] += int(passed.sum())
            line_failed[line] += int((passed & is_fail).sum())
        print(f"chunk {i + 1}: {total_parts:,} parts so far", end="\r")
    print()

    overall_rate = total_failed / total_parts
    df = pd.DataFrame({
        "station_id": list(stations),
        "parts": [parts[s] for s in stations],
        "failed_parts": [failed[s] for s in stations],
    })
    df["line"] = df["station_id"].str.split("_").str[0]
    df["station"] = df["station_id"].str.split("_").str[1]
    df = df[df["parts"] > 0]
    df["failure_rate"] = df["failed_parts"] / df["parts"]
    # lift > 1: parts through this station fail more often than average
    df["lift"] = df["failure_rate"] / overall_rate
    # Every part passes many stations, so raw failure counts mostly show traffic.
    # Excess failures = failures above what the average rate would predict.
    df["excess_failures"] = (df["failed_parts"] - df["parts"] * overall_rate).round(1)
    df = df[["line", "station", "station_id", "parts", "failed_parts", "failure_rate", "lift", "excess_failures"]]

    # A part counts for a line if it passed any station of that line.
    lines = pd.DataFrame({
        "line": sorted(line_parts),
        "parts": [line_parts[l] for l in sorted(line_parts)],
        "failed_parts": [line_failed[l] for l in sorted(line_parts)],
    })
    lines["stations"] = lines["line"].map(df["line"].value_counts())
    lines["failure_rate"] = lines["failed_parts"] / lines["parts"]

    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / "station_failure_rates.csv", index=False)
    lines.to_csv(OUT_DIR / "line_failure_rates.csv", index=False)
    df[["line", "station"]].to_csv(OUT_DIR / "valid_stations.csv", index=False)
    pd.DataFrame([{"parts": total_parts, "failed_parts": total_failed, "failure_rate": overall_rate}]).to_csv(
        OUT_DIR / "overall.csv", index=False
    )

    print(f"parts: {total_parts:,}  failed: {total_failed:,}  rate: {overall_rate:.4%}")
    print(df.sort_values("excess_failures", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()

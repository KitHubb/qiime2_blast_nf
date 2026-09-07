#!/usr/bin/env python3
"""
Select strict local BLAST candidates by ASV.

Expected headerless BLAST columns:
qacc, staxids, sacc, evalue, bitscore, qcovus, pident, length
"""

import argparse
from pathlib import Path
import pandas as pd

COLS = [
    "qacc", "staxids", "sacc", "evalue",
    "bitscore", "qcovus", "pident", "length"
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blast-raw", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--max-evalue", type=float, default=1e-10)
    ap.add_argument("--min-pident", type=float, default=99.0)
    ap.add_argument("--min-qcovus", type=float, default=80.0)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.blast_raw, sep="\t", header=None, names=COLS, comment="#", dtype=str)
    if df.empty:
        raise SystemExit("[ERROR] BLAST input is empty.")

    df["TaxID"] = df["staxids"].fillna("").str.split(";").str[0]
    df["TaxID"] = df["TaxID"].where(df["TaxID"].str.fullmatch(r"\d+"), "")

    for col in ["evalue", "bitscore", "qcovus", "pident", "length"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    valid = df.loc[
        (df["TaxID"] != "")
        & (df["evalue"] <= args.max_evalue)
        & (df["pident"] >= args.min_pident)
        & (df["qcovus"] >= args.min_qcovus)
    ].copy()

    valid = valid.sort_values(
        ["qacc", "evalue", "bitscore", "pident", "qcovus", "length", "sacc"],
        ascending=[True, True, False, False, False, False, True],
        kind="mergesort",
    )
    valid["candidate_rank"] = valid.groupby("qacc").cumcount() + 1

    top = valid.loc[valid["candidate_rank"] <= args.top_n].copy()
    selected = top.loc[top["candidate_rank"] == 1].copy()

    report = df.groupby("qacc").size().rename("raw_hit_count").reset_index()
    report = report.rename(columns={"qacc": "ASV"})
    report["strict_cutoff_pass_hit_count"] = (
        report["ASV"].map(valid.groupby("qacc").size()).fillna(0).astype(int)
    )
    report["retained_top_n_count"] = (
        report["ASV"].map(top.groupby("qacc").size()).fillna(0).astype(int)
    )
    report["selection_status"] = report["strict_cutoff_pass_hit_count"].map(
        lambda n: "candidate_available" if n else "no_strict_cutoff_pass_hit"
    )

    top.to_csv(out / "blast_candidates_top5.tsv", sep="\t", index=False)
    selected.to_csv(out / "blast_selected_hits.tsv", sep="\t", index=False)
    report.to_csv(out / "blast_selection_report.tsv", sep="\t", index=False)

    taxids = sorted(top["TaxID"].drop_duplicates().tolist())
    (out / "blast_candidate_taxids.txt").write_text(
        "\n".join(taxids) + ("\n" if taxids else ""),
        encoding="utf-8",
    )

    print(f"[INFO] Top-{args.top_n} candidate rows: {len(top)}")
    print(f"[INFO] Selected representative hits: {len(selected)}")

if __name__ == "__main__":
    main()

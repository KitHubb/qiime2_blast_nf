#!/usr/bin/env python3
"""
Build BLAST taxonomy evidence from strict BLAST candidates and TaxonKit lineage.

Inputs:
  --candidates        blast_candidates_top5.tsv
  --lineage           taxonkit_lineage.tsv
  --selection-report  blast_selection_report.tsv
  --output-dir        output directory
"""

import argparse
from pathlib import Path
import pandas as pd

RANKS = ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"]

def clean_taxon(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    return "" if x.lower() in {"", "na", "nan", "none", "null"} else "_".join(x.split())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--lineage", required=True)
    ap.add_argument("--selection-report", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cand = pd.read_csv(args.candidates, sep="\t", dtype=str, keep_default_na=False)
    if cand.empty:
        pd.DataFrame().to_csv(out / "blast_candidates_taxonomy.tsv", sep="\t", index=False)
        pd.DataFrame().to_csv(out / "blast_taxonomy.tsv", sep="\t", index=False)
        print("[INFO] No strict BLAST candidates were available.")
        return

    required = {
        "qacc", "TaxID", "sacc", "evalue", "bitscore",
        "qcovus", "pident", "length", "candidate_rank"
    }
    missing = required - set(cand.columns)
    if missing:
        raise ValueError("Candidate TSV missing columns: " + ", ".join(sorted(missing)))

    lineage = pd.read_csv(args.lineage, sep="\t", dtype=str, keep_default_na=False)
    expected = set(["TaxID"] + RANKS)
    missing = expected - set(lineage.columns)
    if missing:
        raise ValueError("Lineage TSV missing columns: " + ", ".join(sorted(missing)))

    report = pd.read_csv(args.selection_report, sep="\t", dtype=str, keep_default_na=False)
    if not {"ASV", "selection_status"}.issubset(report.columns):
        raise ValueError("Selection report requires ASV and selection_status columns.")

    for col in ["evalue", "bitscore", "qcovus", "pident", "length", "candidate_rank"]:
        cand[col] = pd.to_numeric(cand[col], errors="coerce")

    cand["TaxID"] = cand["TaxID"].astype(str)
    lineage["TaxID"] = lineage["TaxID"].astype(str)
    for rank in RANKS:
        lineage[rank] = lineage[rank].map(clean_taxon)

    x = (
        cand.merge(lineage[["TaxID", *RANKS]].drop_duplicates("TaxID"), on="TaxID", how="left", validate="many_to_one")
        .merge(report[["ASV", "selection_status"]].rename(columns={"ASV": "qacc"}), on="qacc", how="left", validate="many_to_one")
        .sort_values(["qacc", "candidate_rank"], kind="mergesort")
        .reset_index(drop=True)
    )

    x = x.rename(columns={
        "qacc": "ASV",
        "sacc": "BLAST_Accession",
        "evalue": "BLAST_Evalue",
        "bitscore": "BLAST_Bitscore",
        "qcovus": "BLAST_Qcovus",
        "pident": "BLAST_Pident",
        "length": "BLAST_AlignmentLength",
        "candidate_rank": "BLAST_CandidateRank",
        "TaxID": "BLAST_TaxID",
        **{rank: f"BLAST_{rank}" for rank in RANKS},
    })
    x.to_csv(out / "blast_candidates_taxonomy.tsv", sep="\t", index=False)

    rows = []
    for asv, g in x.groupby("ASV", sort=True):
        g = g.reset_index(drop=True)
        top1 = g.iloc[0]
        top2 = g.iloc[1] if len(g) > 1 else None

        ambiguous = False
        if top2 is not None:
            different_species = clean_taxon(top1["BLAST_Species"]).lower() != clean_taxon(top2["BLAST_Species"]).lower()
            same_scores = all(
                float(top1[c]) == float(top2[c])
                for c in [
                    "BLAST_Evalue",
                    "BLAST_Bitscore",
                    "BLAST_Pident",
                    "BLAST_Qcovus",
                    "BLAST_AlignmentLength",
                ]
            )
            ambiguous = different_species and same_scores

        row = {
            "ASV": asv,
            "BLAST_Top1_Accession": top1["BLAST_Accession"],
            "BLAST_Top1_TaxID": top1["BLAST_TaxID"],
            "BLAST_Top1_Evalue": top1["BLAST_Evalue"],
            "BLAST_Top1_Bitscore": top1["BLAST_Bitscore"],
            "BLAST_Top1_Pident": top1["BLAST_Pident"],
            "BLAST_Top1_Qcovus": top1["BLAST_Qcovus"],
            "BLAST_Top1_AlignmentLength": top1["BLAST_AlignmentLength"],
            "BLAST_AmbiguousTopHit": ambiguous,
            "BLAST_SelectionStatus": top1["selection_status"],
        }
        for rank in RANKS:
            row[f"BLAST_Top1_{rank}"] = top1[f"BLAST_{rank}"]

        for out_col, in_col in {
            "BLAST_Top2_Accession": "BLAST_Accession",
            "BLAST_Top2_Species": "BLAST_Species",
            "BLAST_Top2_Evalue": "BLAST_Evalue",
            "BLAST_Top2_Bitscore": "BLAST_Bitscore",
            "BLAST_Top2_Pident": "BLAST_Pident",
            "BLAST_Top2_Qcovus": "BLAST_Qcovus",
            "BLAST_Top2_AlignmentLength": "BLAST_AlignmentLength",
        }.items():
            row[out_col] = "" if top2 is None else top2[in_col]
        rows.append(row)

    final = pd.DataFrame(rows)
    final.to_csv(out / "blast_taxonomy.tsv", sep="\t", index=False)

    print(f"[INFO] Candidate taxonomy rows: {len(x)}")
    print(f"[INFO] Representative BLAST rows: {len(final)}")
    print(f"[INFO] Exact-score ambiguous ASVs: {int(final['BLAST_AmbiguousTopHit'].sum())}")

if __name__ == "__main__":
    main()

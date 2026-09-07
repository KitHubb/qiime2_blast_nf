#!/usr/bin/env python3
"""
Reconcile normalized QIIME/UNITE taxonomy with BLAST taxonomy evidence.

Default mode: species_missing_rescue
  - Preserve existing resolved QIIME/UNITE species-level assignments.
  - If QIIME/UNITE species is missing, unresolved, or placeholder-like,
    replace with BLAST top1 species only when the BLAST hit passes
    species-level thresholds.
  - Ambiguous BLAST top-hit conflicts are not rescued.

Alternative mode: species_missing_top1_rescue
  - Preserve existing resolved QIIME/UNITE species-level assignments.
  - If QIIME/UNITE species is missing, unresolved, or placeholder-like,
    replace with BLAST top1 species when the BLAST hit passes species-level thresholds,
    even if the BLAST top hit is marked ambiguous.

Alternative mode: same_genus_only
  - Replace with BLAST species only when QIIME/UNITE genus and BLAST genus match.
"""

import argparse
import math
from pathlib import Path
import pandas as pd

RANKS = ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"]
PREFIX = {
    "Kingdom": "k__",
    "Phylum": "p__",
    "Class": "c__",
    "Order": "o__",
    "Family": "f__",
    "Genus": "g__",
    "Species": "s__",
}
MISSING = {"", ".", "na", "nan", "none", "null", "unassigned", "unclassified", "unknown"}
PLACEHOLDER_ENDINGS = ("_k", "_p", "_c", "_o", "_f", "_g")


def clean_taxon(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    if x.lower() in MISSING:
        return ""
    return "_".join(x.split())


def to_float(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return math.nan
        return float(x)
    except Exception:
        return math.nan


def is_placeholder_value(x):
    x = clean_taxon(x)
    if not x:
        return True
    return x.lower().endswith(PLACEHOLDER_ENDINGS)


def has_resolved_genus(row):
    return clean_taxon(row.get("QIIME_Genus", "")) != "" and not is_placeholder_value(row.get("QIIME_Genus", ""))


def has_resolved_species(row):
    return clean_taxon(row.get("QIIME_Species", "")) != "" and not is_placeholder_value(row.get("QIIME_Species", ""))


def final_taxon_string(row, prefix="Final"):
    parts = []
    for rank in RANKS:
        val = clean_taxon(row.get(f"{prefix}_{rank}", ""))
        if val:
            parts.append(f"{PREFIX[rank]}{val}")
    return "; ".join(parts) if parts else "Unassigned"


def normalize_blast_kingdom(qiime_kingdom, blast_kingdom):
    q = clean_taxon(qiime_kingdom)
    b = clean_taxon(blast_kingdom)
    if q:
        return q
    if b.lower() == "eukaryota":
        return "Fungi"
    return b


def blast_passes(row, max_evalue, min_pident, min_qcovus):
    e = to_float(row.get("BLAST_Top1_Evalue", ""))
    p = to_float(row.get("BLAST_Top1_Pident", ""))
    q = to_float(row.get("BLAST_Top1_Qcovus", ""))
    if math.isnan(e) or math.isnan(p) or math.isnan(q):
        return False
    return e <= max_evalue and p >= min_pident and q >= min_qcovus


def use_blast_lineage(row):
    final = {}
    for rank in RANKS:
        b = clean_taxon(row.get(f"BLAST_Top1_{rank}", ""))
        q = clean_taxon(row.get(f"QIIME_{rank}", ""))
        if rank == "Kingdom":
            final[rank] = normalize_blast_kingdom(q, b)
        else:
            final[rank] = b if b else q
    return final


def use_qiime_lineage(row):
    return {rank: clean_taxon(row.get(f"QIIME_{rank}", "")) for rank in RANKS}


def decide(row, args):
    qiime_genus = clean_taxon(row.get("QIIME_Genus", ""))
    blast_genus = clean_taxon(row.get("BLAST_Top1_Genus", ""))
    blast_species = clean_taxon(row.get("BLAST_Top1_Species", ""))

    ambiguous = str(row.get("BLAST_AmbiguousTopHit", "")).lower() in {"true", "1", "yes"}
    cutoff_pass = blast_passes(row, args.species_max_evalue, args.species_min_pident, args.species_min_qcovus)
    genus_match = bool(qiime_genus and blast_genus and qiime_genus.lower() == blast_genus.lower())
    qiime_genus_resolved = has_resolved_genus(row)
    qiime_species_resolved = has_resolved_species(row)

    if not blast_species:
        return False, "qiime_retained_no_blast_species", "No BLAST species-level top hit was available.", cutoff_pass, genus_match

    if not cutoff_pass:
        return False, "qiime_retained_blast_cutoff_fail", "BLAST top hit did not pass species-level replacement cutoffs.", cutoff_pass, genus_match

    if args.reconcile_mode == "species_missing_rescue":
        if ambiguous:
            return False, "qiime_retained_ambiguous_blast", "BLAST top hit was ambiguous with an exact-score species conflict.", cutoff_pass, genus_match
        if not qiime_species_resolved:
            return True, "blast_species_rescued_missing_qiime_species", "QIIME/UNITE species was missing or placeholder-like and BLAST species passed high-confidence cutoffs.", cutoff_pass, genus_match
        return False, "qiime_retained_resolved_species", "QIIME/UNITE already had a resolved species-level assignment; BLAST did not overwrite it in species_missing_rescue mode.", cutoff_pass, genus_match

    if args.reconcile_mode == "species_missing_top1_rescue":
        if not qiime_species_resolved:
            if ambiguous:
                return True, "blast_top1_species_rescued_ambiguous_missing_qiime_species", "QIIME/UNITE species was missing or placeholder-like and BLAST top1 species passed cutoffs; top1 was used despite ambiguous top-hit conflict.", cutoff_pass, genus_match
            return True, "blast_top1_species_rescued_missing_qiime_species", "QIIME/UNITE species was missing or placeholder-like and BLAST top1 species passed high-confidence cutoffs.", cutoff_pass, genus_match
        return False, "qiime_retained_resolved_species", "QIIME/UNITE already had a resolved species-level assignment; BLAST did not overwrite it in species_missing_top1_rescue mode.", cutoff_pass, genus_match

    if args.reconcile_mode == "same_genus_only":
        if ambiguous:
            return False, "qiime_retained_ambiguous_blast", "BLAST top hit was ambiguous with an exact-score species conflict.", cutoff_pass, genus_match
        if genus_match:
            return True, "blast_species_replaced_same_genus", "BLAST species passed cutoffs and BLAST genus matched QIIME/UNITE genus.", cutoff_pass, genus_match
        if qiime_genus_resolved:
            return False, "qiime_retained_genus_mismatch", "BLAST species passed cutoffs but BLAST genus did not match the resolved QIIME/UNITE genus.", cutoff_pass, genus_match
        return False, "qiime_retained_no_resolved_genus_match", "QIIME/UNITE genus was unresolved and same_genus_only mode requires an explicit genus match.", cutoff_pass, genus_match

    raise ValueError(f"Unsupported reconcile mode: {args.reconcile_mode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qiime-normalized", required=True)
    ap.add_argument("--blast-taxonomy", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--max-evalue", type=float, default=1e-10, help="Kept for backward compatibility.")
    ap.add_argument("--min-pident", type=float, default=99.0, help="Kept for backward compatibility.")
    ap.add_argument("--min-qcovus", type=float, default=80.0, help="Kept for backward compatibility.")
    ap.add_argument(
        "--reconcile-mode",
        choices=["species_missing_rescue", "species_missing_top1_rescue", "same_genus_only"],
        default="species_missing_rescue"
    )
    ap.add_argument("--species-max-evalue", type=float, default=None)
    ap.add_argument("--species-min-pident", type=float, default=99.0)
    ap.add_argument("--species-min-qcovus", type=float, default=99.0)
    args = ap.parse_args()

    if args.species_max_evalue is None:
        args.species_max_evalue = args.max_evalue

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    qi = pd.read_csv(args.qiime_normalized, sep="\t", dtype=str, keep_default_na=False)
    bl = pd.read_csv(args.blast_taxonomy, sep="\t", dtype=str, keep_default_na=False)

    required_qiime = {"Feature ID", "Taxon", "Confidence", "Taxon_Original", *RANKS}
    missing = required_qiime - set(qi.columns)
    if missing:
        raise ValueError("Normalized QIIME taxonomy missing columns: " + ", ".join(sorted(missing)))

    if bl.empty:
        bl = pd.DataFrame(columns=["ASV"])
    if "ASV" not in bl.columns:
        raise ValueError("BLAST taxonomy table must contain ASV column.")

    qi = qi.rename(columns={
        "Feature ID": "ASV",
        "Taxon": "QIIME_Taxon_Normalized",
        "Taxon_Original": "QIIME_Taxon_Original",
        "Confidence": "QIIME_Confidence",
        **{rank: f"QIIME_{rank}" for rank in RANKS},
    })

    merged = qi.merge(bl, on="ASV", how="left", validate="one_to_one")
    for col in ["BLAST_Top1_Evalue", "BLAST_Top1_Pident", "BLAST_Top1_Qcovus", "BLAST_AmbiguousTopHit"]:
        if col not in merged.columns:
            merged[col] = ""
    for rank in RANKS:
        col = f"BLAST_Top1_{rank}"
        if col not in merged.columns:
            merged[col] = ""

    final_rows = []
    evidence_rows = []
    for _, row in merged.iterrows():
        replace, status, reason, cutoff_pass, genus_match = decide(row, args)
        lineage = use_blast_lineage(row) if replace else use_qiime_lineage(row)

        final_row = {"ASV": row["ASV"], **lineage}
        row_mut = row.copy()
        for rank in RANKS:
            row_mut[f"Final_{rank}"] = lineage[rank]
        final_row["Final_Taxon"] = final_taxon_string(row_mut, prefix="Final")
        final_row["Replacement_Status"] = status
        final_row["Replacement_Reason"] = reason
        final_rows.append(final_row)

        ev = row.to_dict()
        ev["QIIME_ConfidenceNumeric"] = to_float(ev.get("QIIME_Confidence", ""))
        ev["QIIME_GenusResolved"] = has_resolved_genus(row)
        ev["QIIME_SpeciesResolved"] = has_resolved_species(row)
        ev["Reconcile_Mode"] = args.reconcile_mode
        ev["Species_Min_Pident"] = args.species_min_pident
        ev["Species_Min_Qcovus"] = args.species_min_qcovus
        ev["Species_Max_Evalue"] = args.species_max_evalue
        ev["BLAST_CutoffPass"] = cutoff_pass
        ev["BLAST_GenusMatch"] = genus_match
        ev.update({f"Final_{rank}": lineage[rank] for rank in RANKS})
        ev["Final_Taxon"] = final_row["Final_Taxon"]
        ev["Replacement_Status"] = status
        ev["Replacement_Reason"] = reason
        evidence_rows.append(ev)

    final = pd.DataFrame(final_rows)
    evidence = pd.DataFrame(evidence_rows)

    qiime_out = final[["ASV", "Final_Taxon"]].merge(
        qi[["ASV", "QIIME_Confidence"]], on="ASV", how="left", validate="one_to_one"
    )
    qiime_out = qiime_out.rename(columns={"ASV": "Feature ID", "Final_Taxon": "Taxon", "QIIME_Confidence": "Confidence"})

    changed = evidence.loc[
        evidence["Replacement_Status"].astype(str).str.startswith("blast_species_")
        | evidence["Replacement_Status"].astype(str).str.startswith("blast_top1_species_")
        | evidence["Replacement_Status"].astype(str).str.contains("mismatch|conflict", case=False, na=False)
    ].copy()

    report = []
    report.append(("total_asvs", len(final)))
    report.append(("reconcile_mode", args.reconcile_mode))
    report.append(("species_min_pident", args.species_min_pident))
    report.append(("species_min_qcovus", args.species_min_qcovus))
    report.append(("species_max_evalue", args.species_max_evalue))
    for status, n in final["Replacement_Status"].value_counts(dropna=False).sort_index().items():
        report.append((status, int(n)))
    report.append(("blast_cutoff_pass", int(evidence["BLAST_CutoffPass"].sum())))
    report.append(("blast_genus_match", int(evidence["BLAST_GenusMatch"].sum())))

    final.to_csv(out / "taxonomy_blast.tsv", sep="\t", index=False)
    qiime_out.to_csv(out / "taxonomy_blast_qiime.tsv", sep="\t", index=False)
    evidence.to_csv(out / "taxonomy_blast_evidence.tsv", sep="\t", index=False)
    changed.to_csv(out / "taxonomy_blast_changed.tsv", sep="\t", index=False)
    pd.DataFrame(report, columns=["Metric", "Value"]).to_csv(out / "taxonomy_blast_report.tsv", sep="\t", index=False)

    replacements = int(
        final["Replacement_Status"].astype(str).str.startswith("blast_species_").sum()
        + final["Replacement_Status"].astype(str).str.startswith("blast_top1_species_").sum()
    )
    print(f"[INFO] Reconciled ASVs: {len(final)}")
    print(f"[INFO] Reconcile mode: {args.reconcile_mode}")
    print(f"[INFO] Species rescue cutoff: pident >= {args.species_min_pident}, qcovus >= {args.species_min_qcovus}, evalue <= {args.species_max_evalue}")
    print(f"[INFO] BLAST replacements/rescues: {replacements}")


if __name__ == "__main__":
    main()
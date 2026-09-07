#!/usr/bin/env python3
"""
Normalize exported QIIME taxonomy TSV before BLAST reconciliation.

Input columns:
  Feature ID, Taxon, Confidence

Outputs:
  taxonomy_normalized.tsv
  taxonomy_normalization_evidence.tsv
"""

import argparse
import re
from pathlib import Path

import pandas as pd


RANKS = ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"]
PREFIX_TO_RANK = {
    "k": "Kingdom", "p": "Phylum", "c": "Class", "o": "Order",
    "f": "Family", "g": "Genus", "s": "Species"
}
RANK_TO_PREFIX = {
    "Kingdom": "k__", "Phylum": "p__", "Class": "c__", "Order": "o__",
    "Family": "f__", "Genus": "g__", "Species": "s__"
}
MISSING = {"", ".", "na", "nan", "none", "null", "unassigned", "unclassified", "unknown"}


def clean(x):
    if pd.isna(x):
        return ""
    x = str(x).strip()
    if x.lower() in MISSING:
        return ""
    x = re.sub(r"^[kpcofgs]__", "", x, flags=re.I)
    x = re.sub(r"[;:]sh__.*$", "", x, flags=re.I).strip()
    return "" if x.lower() in MISSING else x


def is_sp(x):
    return bool(re.search(r"(^|_)sp\.?$", clean(x).lower()))


def parse_taxon(taxon):
    ranks = {r: "" for r in RANKS}
    for part in [x.strip() for x in str(taxon).split(";") if x.strip()]:
        if re.match(r"^sh__", part, flags=re.I):
            continue
        m = re.match(r"^([kpcofgs])__(.*)$", part, flags=re.I)
        if m:
            ranks[PREFIX_TO_RANK[m.group(1).lower()]] = clean(m.group(2))
    return ranks


def apply_unite_rules(ranks, profile):
    actions = []

    if profile == "unite" and is_sp(ranks["Species"]):
        for rank in ["Phylum", "Class", "Order", "Family", "Genus"]:
            if "incertae_sedis" in ranks[rank].lower():
                for lower_rank in RANKS[RANKS.index(rank):]:
                    ranks[lower_rank] = ""
                actions.append(f"incertae_sedis_cleanup_from_{rank.lower()}")
                break

    if is_sp(ranks["Species"]):
        ranks["Species"] = ""
        actions.append("species_sp_removed")

    if not ranks["Kingdom"]:
        return ranks, actions

    fill_steps = [
        ("Phylum", "Kingdom", "_k", ["Phylum", "Class", "Order", "Family", "Genus", "Species"]),
        ("Class", "Phylum", "_p", ["Class", "Order", "Family", "Genus", "Species"]),
        ("Order", "Class", "_c", ["Order", "Family", "Genus", "Species"]),
        ("Family", "Order", "_o", ["Family", "Genus", "Species"]),
        ("Genus", "Family", "_f", ["Genus", "Species"]),
        ("Species", "Genus", "_g", ["Species"]),
    ]

    for missing_rank, parent_rank, suffix, targets in fill_steps:
        if not ranks[missing_rank]:
            value = f"{ranks[parent_rank]}{suffix}"
            for target in targets:
                ranks[target] = value
            actions.append(f"{parent_rank.lower()}_placeholder_added")
            break

    return ranks, actions


def taxon_string(ranks):
    if all(not ranks[r] for r in RANKS):
        return "Unassigned"
    return "; ".join(f"{RANK_TO_PREFIX[r]}{ranks[r]}" for r in RANKS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--profile", choices=["unite", "eukaryome", "generic"], default="unite")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input, sep="\t", dtype=str, keep_default_na=False)
    required = {"Feature ID", "Taxon", "Confidence"}
    if not required.issubset(df.columns):
        raise ValueError("Input TSV must contain Feature ID, Taxon, and Confidence.")

    normalized = []
    evidence = []

    for _, row in df.iterrows():
        ranks = parse_taxon(row["Taxon"])
        ranks, actions = apply_unite_rules(ranks, args.profile)
        normalized_taxon = taxon_string(ranks)

        normalized.append({
            "Feature ID": row["Feature ID"],
            "Taxon": normalized_taxon,
            "Confidence": row["Confidence"],
            "Taxon_Original": row["Taxon"],
            **ranks,
        })

        evidence.append({
            "Feature ID": row["Feature ID"],
            "Taxon_Original": row["Taxon"],
            "Taxon_Normalized": normalized_taxon,
            "Confidence": row["Confidence"],
            "Profile": args.profile,
            "Normalization_Actions": ";".join(actions) if actions else "none",
        })

    pd.DataFrame(normalized).to_csv(out / "taxonomy_normalized.tsv", sep="\t", index=False)
    pd.DataFrame(evidence).to_csv(out / "taxonomy_normalization_evidence.tsv", sep="\t", index=False)

    print(f"[INFO] Normalized ASVs: {len(normalized)}")


if __name__ == "__main__":
    main()

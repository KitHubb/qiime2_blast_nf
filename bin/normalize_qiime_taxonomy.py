#!/usr/bin/env python3
"""
Normalize QIIME taxonomy TSV or QZA, independently or before BLAST reconciliation.

Input columns:
  Feature ID, Taxon; optional Confidence

Outputs:
  taxonomy_normalized.tsv
  taxonomy_normalized_qiime.tsv (QIIME import format)
  taxonomy_normalization_evidence.tsv
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import io
import zipfile

PROFILES = ['auto', 'silva', 'silva138', 'gtdb', 'gtdb_r220', 'gg2', 'unite', 'eukaryome', 'generic']
BACTERIAL_PROFILES = {'silva', 'silva138', 'gtdb', 'gtdb_r220', 'gg2'}


RANKS = ["Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"]
PREFIX_TO_RANK = {
    "d": "Kingdom", "k": "Kingdom", "p": "Phylum", "c": "Class", "o": "Order",
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
    x = re.sub(r"^[dkpcofgs]__", "", x, flags=re.I)
    x = re.sub(r"[;:]sh__.*$", "", x, flags=re.I).strip()
    return "" if x.lower() in MISSING else x


def is_sp(x):
    return bool(re.search(r"(^|[ _])sp\.?$", clean(x).lower()))


def parse_taxon(taxon):
    ranks = {r: "" for r in RANKS}
    seen = {}
    if clean(taxon) == "":
        return ranks
    for part in [x.strip() for x in str(taxon).split(";") if x.strip()]:
        if re.match(r"^sh__", part, flags=re.I):
            continue
        m = re.match(r"^([dkpcofgs])__(.*)$", part, flags=re.I)
        if m:
            rank = PREFIX_TO_RANK[m.group(1).lower()]
            value = clean(m.group(2))
            if rank in seen and seen[rank] != value:
                raise ValueError(f"Conflicting rank labels in {taxon!r}")
            seen[rank] = value
            ranks[rank] = value
        else:
            raise ValueError(f"Unrecognised taxonomy token {part!r}; expected rank prefixes")
    return ranks


def apply_unite_rules(ranks, profile):
    """Compatibility API: normalization only parses ranks; final filling is separate."""
    return ranks, []


def top_prefix(taxon, profile="auto"):
    if profile in BACTERIAL_PROFILES or re.search(r"(?:^|;)\s*d__", str(taxon), re.I):
        return "d"
    return "k"


def taxon_string(ranks, domain_prefix="k"):
    if all(not ranks[r] for r in RANKS):
        return "Unassigned"
    prefixes = dict(RANK_TO_PREFIX, Kingdom=domain_prefix + "__")
    return "; ".join(f"{prefixes[r]}{ranks[r]}" for r in RANKS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--profile", choices=PROFILES, default="auto")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.input.lower().endswith(".qza"):
        with zipfile.ZipFile(args.input) as archive:
            names = [n for n in archive.namelist() if re.fullmatch(r"[^/]+/data/taxonomy.tsv", n)]
            if len(names) != 1:
                raise ValueError("Expected exactly one root data/taxonomy.tsv in QZA")
            source = io.StringIO(archive.read(names[0]).decode("utf-8-sig"))
            df = pd.read_csv(source, sep="\t", dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(args.input, sep="\t", dtype=str, keep_default_na=False)
    has_confidence = "Confidence" in df.columns
    if not has_confidence:
        df["Confidence"] = ""
    if "Feature ID" in df.columns and (df.empty or df["Feature ID"].str.strip().eq("").any() or df["Feature ID"].duplicated().any()):
        raise ValueError("Input must contain nonempty unique feature IDs and at least one row")
    required = {"Feature ID", "Taxon", "Confidence"}
    if not required.issubset(df.columns):
        raise ValueError("Input taxonomy must contain Feature ID and Taxon.")

    normalized = []
    evidence = []

    for _, row in df.iterrows():
        ranks = parse_taxon(row["Taxon"])
        ranks, actions = apply_unite_rules(ranks, args.profile)
        prefix = top_prefix(row["Taxon"], args.profile)
        normalized_taxon = taxon_string(ranks, prefix)

        normalized.append({
            "Feature ID": row["Feature ID"],
            "Taxon": normalized_taxon,
            "Confidence": row["Confidence"],
            "Taxon_Original": row["Taxon"],
            "Top_Rank_Prefix": prefix,
            "Profile": args.profile,
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

    qiime_columns = ["Feature ID", "Taxon"] + (["Confidence"] if has_confidence else [])
    pd.DataFrame(normalized)[qiime_columns].to_csv(out / "taxonomy_normalized_qiime.tsv", sep="\t", index=False)
    pd.DataFrame(normalized).to_csv(out / "taxonomy_normalized.tsv", sep="\t", index=False)
    pd.DataFrame(evidence).to_csv(out / "taxonomy_normalization_evidence.tsv", sep="\t", index=False)

    print(f"[INFO] Normalized ASVs: {len(normalized)}")


if __name__ == "__main__":
    main()

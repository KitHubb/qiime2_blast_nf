#!/usr/bin/env python3
"""Fill missing final taxonomy cells from their nearest assigned ancestor.

The report's Species cell is g_Bacillus, never s__g_Bacillus. This wide
report is distinct from QIIME taxonomy artifacts. Accepts QZA, QIIME TSV,
reconciled TSV, and its own wide TSV for repeatable postprocessing.
"""
import argparse
import collections
import csv
import io
import json
import re
import zipfile
from pathlib import Path

from normalize_qiime_taxonomy import RANKS, PROFILES, MISSING, parse_taxon, top_prefix, is_sp


def read_input(path):
    path = Path(path)
    if path.suffix.lower() == '.qza':
        with zipfile.ZipFile(str(path)) as archive:
            names = [n for n in archive.namelist() if re.fullmatch(r'[^/]+/data/taxonomy.tsv', n)]
            if len(names) != 1:
                raise ValueError('Expected exactly one root data/taxonomy.tsv in QZA')
            text = archive.read(names[0]).decode('utf-8-sig')
    else:
        text = path.read_text(encoding='utf-8-sig')
    reader = csv.DictReader(io.StringIO(text), delimiter='\t')
    fields = reader.fieldnames or []
    id_column = 'Feature ID' if 'Feature ID' in fields else 'ASV'
    if id_column not in fields:
        raise ValueError('Expected Feature ID or ASV column')
    rows = list(reader)
    identifiers = [r.get(id_column, '') for r in rows]
    if not rows or any(not str(i).strip() for i in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError('Expected at least one row with unique nonempty feature IDs')
    return rows, fields, id_column


def plain(value):
    return '' if value is None else str(value).strip()


def missing(value, rank):
    return plain(value).lower() in MISSING or (rank == 'Species' and is_sp(value))


def extract_ranks(row, profile):
    # Prefer final reconciliation fields over any original/normalized Taxon.
    taxon = row.get('Final_Taxon', row.get('Taxon', ''))
    if all('Final_' + rank in row for rank in RANKS):
        ranks = {r: plain(row['Final_' + r]) for r in RANKS}
    elif all(rank in row for rank in RANKS):
        ranks = {r: plain(row[r]) for r in RANKS}
    elif 'Taxon' in row or 'Final_Taxon' in row:
        ranks = parse_taxon(taxon)
    else:
        raise ValueError('Expected Taxon, Final_Taxon, or all seven rank columns')
    prefix = row.get('Top_Rank_Prefix', '')
    if prefix not in ('d', 'k'):
        prefix = top_prefix(taxon, profile)
    return ranks, prefix


def fill_ranks(ranks, prefix):
    """Fill only unresolved cells. Filled cells never become new ancestors."""
    output, changes = {}, []
    ancestor = None
    abbreviations = [prefix, 'p', 'c', 'o', 'f', 'g', 's']
    for index, rank in enumerate(RANKS):
        value = plain(ranks[rank])
        legacy = False
        if ancestor is not None:
            ancestor_rank, ancestor_prefix, ancestor_name = ancestor
            # Convert old Name_g only when corroborated by the actual ancestor.
            legacy = value == ancestor_name + '_' + ancestor_prefix
        if missing(value, rank) or legacy:
            result = ancestor[1] + '_' + ancestor[2] if ancestor else 'Unassigned'
            if result != value:
                changes.append({'Rank': rank, 'Original_Value': value, 'Final_Value': result,
                                'Source_Rank': ancestor[0] if ancestor else '',
                                'Source_Name': ancestor[2] if ancestor else '',
                                'Reason': 'legacy_suffix_to_prefix' if legacy else
                                          'nearest_assigned_ancestor' if ancestor else 'no_assigned_ancestor'})
        else:
            result = value
            # On re-entry, preserve our parent-derived labels without treating
            # them as genuine assignments at a lower rank.
            inherited = re.fullmatch(r'([dkpcofg])_(?!_)(.+)', value)
            if inherited and inherited.group(1) in abbreviations[:index]:
                source_index = abbreviations.index(inherited.group(1))
                ancestor = (RANKS[source_index], inherited.group(1), inherited.group(2))
            else:
                ancestor = (rank, abbreviations[index], value)
        output[rank] = result
    return output, changes


def write_tsv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def process(input_path, output_dir, profile='auto'):
    rows, fields, id_column = read_input(input_path)
    confidence_column = 'Confidence' if 'Confidence' in fields else 'QIIME_Confidence' if 'QIIME_Confidence' in fields else None
    output, audit = [], []
    changed_asvs = 0
    for row in rows:
        identifier = row[id_column]
        try:
            ranks, prefix = extract_ranks(row, profile)
            filled, changes = fill_ranks(ranks, prefix)
        except ValueError as error:
            raise ValueError('{}: {}'.format(identifier, error))
        final = dict({'Feature ID': identifier, 'Top_Rank_Prefix': prefix}, **filled)
        if confidence_column:
            final['Confidence'] = row[confidence_column]
        output.append(final)
        changed_asvs += bool(changes)
        audit.extend(dict({'Feature ID': identifier}, **change) for change in changes)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_tsv(out / 'taxonomy_postprocessed.tsv', output,
              ['Feature ID', 'Top_Rank_Prefix'] + RANKS + (['Confidence'] if confidence_column else []))
    write_tsv(out / 'taxonomy_postprocess_changes.tsv', audit,
              ['Feature ID', 'Rank', 'Original_Value', 'Final_Value', 'Source_Rank', 'Source_Name', 'Reason'])
    summary = {'input': str(input_path), 'profile': profile, 'asvs': len(rows),
               'changed_asvs': changed_asvs, 'changed_cells': len(audit),
               'filled_cells_by_rank': dict(collections.Counter(a['Rank'] for a in audit if a['Source_Rank'])),
               'unassigned_asvs': sum(all(r[k] == 'Unassigned' for k in RANKS) for r in output)}
    (out / 'taxonomy_postprocess_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print('[INFO] Postprocessed {} ASVs; {} changed cells'.format(len(rows), len(audit)))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='Taxonomy QZA or TSV; BLAST is not needed')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--profile', choices=PROFILES, default='auto')
    args = parser.parse_args()
    process(args.input, args.output_dir, args.profile)


if __name__ == '__main__':
    main()

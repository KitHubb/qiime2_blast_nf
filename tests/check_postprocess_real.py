#!/usr/bin/env python3
"""Independently check every source cell against the final table, then rerun."""
import argparse
import csv
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--output-dir', required=True)
parser.add_argument('--profile', required=True)
args = parser.parse_args()
source = Path(args.input)
out = Path(args.output_dir)
if source.suffix == '.qza':
    with zipfile.ZipFile(str(source)) as archive:
        name = next(n for n in archive.namelist() if re.fullmatch(r'[^/]+/data/taxonomy.tsv', n))
        text = archive.read(name).decode('utf-8-sig')
else:
    text = source.read_text(encoding='utf-8-sig')
original = list(csv.DictReader(io.StringIO(text), delimiter='\t'))
with (out/'taxonomy_postprocessed.tsv').open() as f:
    final = list(csv.DictReader(f, delimiter='\t'))
assert len(original) == len(final)
ranks = ['Kingdom','Phylum','Class','Order','Family','Genus','Species']
known = changed_species = 0
examples = []
for raw, result in zip(original, final):
    assert raw['Feature ID'] == result['Feature ID']
    if 'Confidence' in raw:
        assert raw['Confidence'] == result['Confidence']
    tokens = {}
    for token in raw['Taxon'].split(';'):
        token = token.strip()
        if '__' in token:
            prefix, value = token.split('__', 1)
            tokens[prefix] = value
    prefixes = ['d' if 'd' in tokens or args.profile in ['silva138','gtdb_r220','gg2'] else 'k', 'p','c','o','f','g','s']
    parent = None
    for rank, prefix in zip(ranks, prefixes):
        value = tokens.get(prefix, '')
        empty = value.lower() in {'', '.', 'na', 'nan', 'none', 'null', 'unassigned', 'unclassified', 'unknown'}
        if rank == 'Species' and re.search(r'(^|[ _])sp\.?$', value, re.I):
            empty = True
        expected = (parent[0] + '_' + parent[1] if parent else 'Unassigned') if empty else value
        assert result[rank] == expected, (raw['Feature ID'], rank, result[rank], expected)
        if not empty:
            parent = (prefix, value)
            known += 1
        if rank == 'Species' and expected != value and expected != 'Unassigned':
            changed_species += 1
            if len(examples) < 3:
                examples.append({'ASV': raw['Feature ID'], 'Genus': result['Genus'], 'Species': result['Species']})
        if empty:
            assert '__' not in result[rank]
script = Path(__file__).resolve().parents[1] / 'bin/postprocess_taxonomy.py'
subprocess.run([sys.executable, str(script), '--input', str(out/'taxonomy_postprocessed.tsv'),
                '--output-dir', str(out/'repeat_check'), '--profile', args.profile], check=True)
assert (out/'taxonomy_postprocessed.tsv').read_bytes() == (out/'repeat_check/taxonomy_postprocessed.tsv').read_bytes()
assert json.loads((out/'repeat_check/taxonomy_postprocess_summary.json').read_text())['changed_cells'] == 0
report = {'passed': True, 'asvs': len(final), 'assigned_cells_preserved': known,
          'species_filled': changed_species, 'idempotent': True, 'examples': examples}
(out/'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))

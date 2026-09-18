"""Compare actual workflow output with a hand-written expected table."""
import csv
import sys
from pathlib import Path

def read(path):
    with open(path, newline='') as handle:
        return list(csv.reader(handle, delimiter='\t'))
actual, expected = map(read, sys.argv[1:3])
if actual != expected:
    raise SystemExit('FAIL: workflow taxonomy differs from tests/data/expected.tsv')
Path('test_report.txt').write_text('PASS: 5 ASVs; ancestor labels, assigned species, suffixes, IDs and Confidence verified.\n')
print('PASS: workflow output matches expected taxonomy')

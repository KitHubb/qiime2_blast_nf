import importlib.util
import sys
import csv
import subprocess
import tempfile
import zipfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
import normalize_qiime_taxonomy as norm
import reconcile_qiime_blast_species as rec

class TaxonomyTests(unittest.TestCase):
    def test_d_and_k_preserve_top_rank(self):
        for text, prefix in [('d__Bacteria;p__Firmicutes', 'd'), ('k__Fungi;p__Ascomycota', 'k')]:
            ranks = norm.parse_taxon(text)
            out = norm.taxon_string(ranks, norm.top_prefix(text))
            self.assertTrue(out.startswith(prefix + '__'))
            self.assertEqual(len(out.split(';')), 7)

    def test_internal_gaps_never_shift(self):
        ranks = norm.parse_taxon('d__Bacteria;p__;c__Bacilli;g__Bacillus;s__')
        out = norm.taxon_string(ranks, 'd')
        self.assertEqual(out.split('; ')[1], 'p__')
        self.assertEqual(out.split('; ')[2], 'c__Bacilli')
        row = {'QIIME_Taxon_Original': 'd__Bacteria'}
        row.update({'Final_' + k: v for k, v in ranks.items()})
        self.assertEqual(rec.final_taxon_string(row), out)

    def test_reference_labels_survive(self):
        for genus, species in [('Pseudomonas_E', 'Pseudomonas_E sp000123456'),
                               ('Pseudomonas_E_647464', 'Pseudomonas_E_647464 sp000123456'),
                               ('Example_G', 'Example_G species_P')]:
            text = 'd__Bacteria;g__' + genus + ';s__' + species
            ranks, _ = norm.apply_unite_rules(norm.parse_taxon(text), 'gtdb_r220')
            self.assertEqual(ranks['Genus'], genus)
            self.assertEqual(ranks['Species'], species)
            self.assertFalse(rec.is_placeholder_value(species))
            self.assertEqual(rec.use_qiime_lineage({'QIIME_Species': species})['Species'], species)

    def test_unresolved_and_conflicting_labels(self):
        self.assertEqual(norm.taxon_string(norm.parse_taxon('Unassigned')), 'Unassigned')
        self.assertTrue(rec.is_placeholder_value('Bacillus sp.'))
        self.assertTrue(rec.is_placeholder_value('uncultured'))
        self.assertFalse(rec.is_placeholder_value('Bacillus sp000123456'))
        with self.assertRaises(ValueError):
            norm.parse_taxon('d__Bacteria;k__Archaea')
        with self.assertRaises(ValueError):
            norm.parse_taxon('Bacteria;Firmicutes')

    def test_no_fungal_inference(self):
        self.assertEqual(rec.normalize_blast_kingdom('', 'Eukaryota'), 'Eukaryota')

class CommandTests(unittest.TestCase):
    def run_script(self, script, *args):
        subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'bin' / script)] + list(args),
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_missing_confidence_qza_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = 'Feature ID\tTaxon\nx\td__Bacteria;g__Pseudomonas_E;s__Pseudomonas_E sp000123456\n'
            qza = root / 'input.qza'
            with zipfile.ZipFile(str(qza), 'w') as archive:
                archive.writestr('test/data/taxonomy.tsv', text)
            self.run_script('normalize_qiime_taxonomy.py', '--input', str(qza), '--output-dir', str(root/'out'), '--profile', 'gtdb_r220')
            with (root/'out/taxonomy_normalized_qiime.tsv').open() as f:
                reader = csv.DictReader(f, delimiter='\t')
                self.assertEqual(reader.fieldnames, ['Feature ID', 'Taxon'])
                self.assertIn('s__Pseudomonas_E sp000123456', list(reader)[0]['Taxon'])
            tsv = root/'duplicate.tsv'
            tsv.write_text(text + text.splitlines(True)[1])
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_script('normalize_qiime_taxonomy.py', '--input', str(tsv), '--output-dir', str(root/'bad'))

    def test_reconcile_species_only_and_retained_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'input.tsv'
            source.write_text('Feature ID\tTaxon\tConfidence\n'
                'match\td__Bacteria;p__SILVA_name;g__Bacillus;s__\t0.9\n'
                'mismatch\td__Bacteria;g__Bacillus_A;s__\t0.8\n'
                'missing\td__Bacteria;p__;c__Bacilli;g__;s__\t0.7\n'
                'resolved\td__Bacteria;g__Bacillus;s__Bacillus sp000123456\t0.6\n')
            self.run_script('normalize_qiime_taxonomy.py', '--input', str(source), '--output-dir', str(root/'norm'), '--profile', 'gtdb_r220')
            blast = root/'blast.tsv'
            blast.write_text('ASV\tBLAST_Top1_Genus\tBLAST_Top1_Species\tBLAST_Top1_Phylum\tBLAST_Top1_Evalue\tBLAST_Top1_Pident\tBLAST_Top1_Qcovus\tBLAST_AmbiguousTopHit\n' +
                ''.join(i+'\tBacillus\tBacillus_subtilis\tNCBI_name\t0\t100\t100\tFalse\n' for i in ['match','mismatch','resolved']))
            self.run_script('reconcile_qiime_blast_species.py', '--qiime-normalized', str(root/'norm/taxonomy_normalized.tsv'), '--blast-taxonomy', str(blast), '--output-dir', str(root/'final'))
            with (root/'final/taxonomy_blast_evidence.tsv').open() as f:
                rows = {r['ASV']:r for r in csv.DictReader(f, delimiter='\t')}
            self.assertEqual(rows['match']['Final_Phylum'], 'SILVA_name')
            self.assertEqual(rows['match']['Final_Species'], 'Bacillus subtilis')
            self.assertEqual(rows['mismatch']['Final_Species'], '')
            self.assertEqual(rows['mismatch']['Replacement_Status'], 'qiime_retained_genus_mismatch')
            self.assertEqual(rows['resolved']['Final_Species'], 'Bacillus sp000123456')
            for r in rows.values():
                self.assertEqual(len(r['Final_Taxon'].split(';')), 7)
                self.assertTrue(r['Final_Taxon'].startswith('d__Bacteria;'))
            self.assertIn('; p__; c__Bacilli;', rows['missing']['Final_Taxon'])

if __name__ == '__main__':
    unittest.main()

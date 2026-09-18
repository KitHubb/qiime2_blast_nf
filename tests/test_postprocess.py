import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
from normalize_qiime_taxonomy import RANKS, parse_taxon
from postprocess_taxonomy import fill_ranks, process


class PostprocessTests(unittest.TestCase):
    def test_genus_to_species_exact_value(self):
        result, changes = fill_ranks(parse_taxon('d__Bacteria;g__Bacillus;s__'), 'd')
        self.assertEqual(result['Species'], 'g_Bacillus')
        self.assertNotIn('__', result['Species'])
        self.assertEqual(changes[-1]['Source_Rank'], 'Genus')

    def test_family_to_both_ranks(self):
        result, _ = fill_ranks(parse_taxon('d__Bacteria;f__Bacillaceae;g__;s__'), 'd')
        self.assertEqual(result['Genus'], 'f_Bacillaceae')
        self.assertEqual(result['Species'], 'f_Bacillaceae')

    def test_all_ancestor_levels(self):
        for top in ['d', 'k']:
            prefixes = [top, 'p', 'c', 'o', 'f', 'g', 's']
            for level in range(6):
                ranks = dict.fromkeys(RANKS, '')
                ranks[RANKS[level]] = 'KnownName'
                result, _ = fill_ranks(ranks, top)
                for rank in RANKS[level + 1:]:
                    self.assertEqual(result[rank], prefixes[level] + '_KnownName')
                for rank in RANKS[:level]:
                    self.assertEqual(result[rank], 'Unassigned')

    def test_gaps_do_not_overwrite_known_descendants(self):
        result, _ = fill_ranks(parse_taxon('d__Bacteria;p__;c__Bacilli;g__Bacillus;s__'), 'd')
        self.assertEqual(result['Phylum'], 'd_Bacteria')
        self.assertEqual(result['Class'], 'Bacilli')
        self.assertEqual(result['Family'], 'c_Bacilli')
        self.assertEqual(result['Genus'], 'Bacillus')
        self.assertEqual(result['Species'], 'g_Bacillus')

    def test_real_names_and_unresolved_species(self):
        for name in ['Pseudomonas_E', 'Pseudomonas_E_647464', 'Example_G']:
            ranks = parse_taxon('d__Bacteria;g__' + name + ';s__' + name + ' sp000123456')
            result, _ = fill_ranks(ranks, 'd')
            self.assertEqual(result['Genus'], name)
            self.assertEqual(result['Species'], name + ' sp000123456')
        result, _ = fill_ranks(parse_taxon('d__Bacteria;g__Bacillus;s__Bacillus sp.'), 'd')
        self.assertEqual(result['Species'], 'g_Bacillus')

    def test_unassigned_and_repeat_processing(self):
        for taxon in ['Unassigned', 'd__Bacteria;f__Bacillaceae', 'd__Bacteria;p__;g__Bacillus']:
            once, _ = fill_ranks(parse_taxon(taxon), 'd')
            twice, changes = fill_ranks(once, 'd')
            self.assertEqual(once, twice)
            self.assertEqual(changes, [])
        result, _ = fill_ranks(parse_taxon('Unassigned'), 'd')
        self.assertEqual(set(result.values()), {'Unassigned'})

    def test_legacy_suffix_requires_matching_ancestor(self):
        ranks = parse_taxon('d__Bacteria;g__Bacillus;s__Bacillus_g')
        result, _ = fill_ranks(ranks, 'd')
        self.assertEqual(result['Species'], 'g_Bacillus')
        ranks['Species'] = 'Something_G'
        result, _ = fill_ranks(ranks, 'd')
        self.assertEqual(result['Species'], 'Something_G')

    def test_cli_tables_and_confidence_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.tsv'
            source.write_text('Feature ID\tTaxon\tConfidence\nx\td__Bacteria;g__Bacillus;s__\t0.999999\n')
            for profile in ['silva138', 'gtdb_r220', 'gg2']:
                out = root/profile
                process(source, out, profile)
                with (out/'taxonomy_postprocessed.tsv').open() as f:
                    row = next(csv.DictReader(f, delimiter='\t'))
                self.assertEqual(row['Species'], 'g_Bacillus')
                self.assertEqual(row['Confidence'], '0.999999')
                process(out/'taxonomy_postprocessed.tsv', out/'again', profile)
                self.assertEqual((out/'taxonomy_postprocessed.tsv').read_bytes(),
                                 (out/'again/taxonomy_postprocessed.tsv').read_bytes())
                self.assertEqual(json.loads((out/'again/taxonomy_postprocess_summary.json').read_text())['changed_cells'], 0)

    def test_final_evidence_columns_take_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.tsv'
            source.write_text('ASV\tFinal_Taxon\tTaxon\tQIIME_Confidence\nx\td__Bacteria;g__Bacillus;s__Bacillus subtilis\td__Bacteria;g__WrongGenus\t0.5\n')
            process(source, root/'out')
            with (root/'out/taxonomy_postprocessed.tsv').open() as f:
                row = next(csv.DictReader(f, delimiter='\t'))
            self.assertEqual(row['Species'], 'Bacillus subtilis')
            self.assertEqual(row['Genus'], 'Bacillus')


if __name__ == '__main__':
    unittest.main()

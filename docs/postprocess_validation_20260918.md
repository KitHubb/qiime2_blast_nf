# Postprocessing validation: 2026-09-18

Repository: `/data/software/nextflow/QIIME_blast`.

`--postprocess_only true` accepts taxonomy QZA/TSV without BLAST. All workflow branches, including `--normalize_only true`, now produce the common final report. Standalone entry point: `bin/postprocess_taxonomy.py`.

Missing Species under Bacillus becomes exactly `g_Bacillus`. Missing Genus and Species under Bacillaceae both become `f_Bacillaceae`. No destination prefix is added. Intermediate QIIME artifacts retain QIIME syntax. Per-cell changes are recorded separately.

## Actual data verification

Original inputs: `/data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy`.
Results: `/data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy_postprocess_check_20260918.Mn2jGe`.
Original files were not overwritten.

| Reference | ASVs | Species filled | Fully unassigned |
|---|---:|---:|---:|
| SILVA 138 | 26,045 | 26,037 | 8 |
| GTDB r220 | 26,045 | 13,787 | 1 |
| GG2 | 26,045 | 9,387 | 0 |

All three completed actual Nextflow postprocess-only runs. The independent checker `tests/check_postprocess_real.py` compared every rank with original data, checked IDs and Confidence, and confirmed assigned names were preserved. Reprocessing produced byte-identical tables and zero changed cells.

GTDB additionally completed the normalize-only Nextflow workflow, producing QZA, QZV and the final TSV. The final TSV was byte-identical to direct postprocessing.

An existing corrected native BLAST SILVA result also passed: 26,045 ASVs, 11,646 Species cells filled, assigned cells preserved, byte-identical reprocessing. No new full BLAST search or QIIME BLAST backend execution was performed during this validation.

Output subdirectories: `silva138`, `gtdb_r220`, `gg2`, `normalize_gtdb`, `native_reconciled`. Each contains `postprocessed/taxonomy_postprocessed.tsv`; the three direct reference runs and native result also contain `postprocessed/validation.json`.

All 16 unit tests passed. `git diff --check` passed.

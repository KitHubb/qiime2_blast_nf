# QIIME_blast

Standalone Nextflow DSL2 workflow derived from ITSdetector for BLAST-based taxonomy analysis of ASV representative sequences.

## Backends and current scope

| Backend | Reference input | Behavior |
| --- | --- | --- |
| `native` | Formatted BLAST database prefix and NCBI taxdump | Run blastn, select candidates, resolve TaxIDs with TaxonKit, reconcile existing taxonomy, export TSV/QZA/QZV |
| `qiime` | Reference sequence and taxonomy QZA artifacts | Run QIIME 2 classify-consensus-blast and export its classification and search results |

The QIIME backend currently does **not** reconcile its classification with the original taxonomy or generate the native reconciliation report. A shared result matrix and reconciliation stage for both backends is not yet implemented.

## Inputs and containers

Both backends require:

- `--repseq_qza`: `FeatureData[Sequence]` artifact, e.g. `rep-seqs.qza`.
- `--taxonomy_qza`: existing `FeatureData[Taxonomy]` artifact, e.g. `taxonomy_SILVA.qza`.
- `--outdir`: output directory (default: `results`).

Filenames are arbitrary. Inputs are exported internally to FASTA and TSV. The native backend uses these exports; the QIIME backend uses the original sequence QZA directly. Existing taxonomy is currently used for reconciliation only by the native backend.

| Container parameter | Default path |
| --- | --- |
| `--blast_taxonomy_sif` | `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif` |
| `--qiime_sif` | `/data/software/singularity/qiime2_amplicon_2025.7.sif` |

Containers are stored separately and excluded from Git. Nextflow and Singularity must be available. QIIME export/import stages use writable task-local cache directories. Native BLAST uses 8 CPUs/32 GB, QIIME BLAST 8 CPUs/32 GB, and QIIME export/import 1 CPU/4 GB by default.

## Run native BLAST and reconcile taxonomy

```bash
cd /data/home2/ksy/260811_DT_swab

nextflow run /data/software/nextflow/QIIME_blast/main.nf \
  --backend native \
  --repseq_qza /data/home2/ksy/260811_DT_swab/Output/HN00182797/05_dada2/rep-seqs.qza \
  --taxonomy_qza /data/home2/ksy/260811_DT_swab/Output/HN00182797/06_taxonomy/taxonomy_SILVA.qza \
  --outdir /data/home2/ksy/260811_DT_swab/Output/HN00182797/09_BLAST \
  --blast_db /data/Reference/BLAST/16S/20241203/16S_ribosomal_RNA \
  --taxdump_dir /data/Reference/BLAST/taxdump \
  --taxonomy_profile generic \
  --blast_reconcile_mode species_missing_rescue \
  --blast_species_min_pident 99 \
  --blast_species_min_qcovus 99 \
  --blast_species_max_evalue 1e-10 \
  -work-dir /data/home2/ksy/260811_DT_swab/work_blast/HN00182797 \
  -resume
```

`--blast_db` is a database **prefix**, not a directory or a `.nin` filename. Taxdump is the directory used by TaxonKit.

For SILVA input, explicitly use `--taxonomy_profile generic`. The current configuration default is `silva`, but the normalization script only accepts `generic`, `unite`, and `eukaryome`; omitting this override currently causes native processing to fail.

## BLAST modification / reconciliation options

Select a policy with `--blast_reconcile_mode`:

| Mode | Existing resolved species | Missing/unresolved species | Genus agreement | Ambiguous top hit |
| --- | --- | --- | --- | --- |
| `species_missing_rescue` (default) | Preserve | Replace if species cutoffs pass | Not required | Preserve original taxonomy |
| `species_missing_top1_rescue` | Preserve | Replace if species cutoffs pass | Not required | Accept top1 if species cutoffs pass |
| `same_genus_only` | May replace | May replace | Explicit matching nonempty genus required | Preserve original taxonomy |

All modes require a nonempty BLAST top1 species and passing species-level cutoffs. Missing/placeholder detection follows the normalization and reconciliation scripts; it is not an independent assessment of biological species resolution.

When replacement is selected, the code uses BLAST lineage values from phylum through species where available and falls back to the original values where BLAST ranks are absent. The original kingdom is retained if present. Thus a rescue can change upper ranks, not just fill the species field. The inherited ITS fallback maps BLAST Eukaryota to Fungi when the original kingdom is absent.

### Candidate selection and final replacement thresholds

| Parameter | Default | Purpose |
| --- | --- | --- |
| `--blast_retrieval_n` | `20` | Native blastn max_target_seqs |
| `--blast_top_n` | `5` | Native retained candidate rows per ASV; QIIME maxaccepts |
| `--blast_min_pident` | `99.0` | Native candidate identity minimum (%) |
| `--blast_min_qcovus` | `80.0` | Native candidate query coverage minimum (%) |
| `--blast_max_evalue` | `1e-10` | Native candidate E-value maximum; QIIME search E-value |
| `--blast_species_min_pident` | `99.0` | Final native replacement identity minimum (%) |
| `--blast_species_min_qcovus` | `99.0` | Final native replacement coverage minimum (%) |
| `--blast_species_max_evalue` | `1e-10` | Final native replacement E-value maximum |
| `--blast_min_qiime_confidence` | `0.7` | Accepted by the script but currently unused in replacement decisions |

Candidate filters run before replacement thresholds. Lowering only a species threshold cannot recover a hit already removed by candidate selection.

Native candidates require a valid TaxID and are sorted by E-value ascending, then bit score, identity, coverage, and alignment length descending, then accession ascending. Top1 is the first retained row. Ambiguity currently compares **only top1 and top2**: different species with identical E-value, bit score, identity, coverage, and alignment length. It does not inspect all tied candidates; with `--blast_top_n 1`, this ambiguity check cannot detect a conflict.

The exported `Confidence` retains the original QIIME confidence even when taxonomy changes. It is not a confidence estimate for the BLAST replacement.

## Run QIIME BLAST

```bash
nextflow run /data/software/nextflow/QIIME_blast/main.nf \
  --backend qiime \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --reference_reads /path/to/ref-seqs.qza \
  --reference_taxonomy /path/to/ref-taxonomy.qza \
  --outdir results/qiime \
  -resume
```

Reference artifacts must contain `FeatureData[Sequence]` and `FeatureData[Taxonomy]` with matching reference IDs. To compare against the same database as sklearn, supply the reference sequences and labels used to train that classifier, not the trained classifier QZA itself.

Identity and coverage settings use percentages at the Nextflow interface and are converted to proportions for QIIME. QIIME coverage is per HSP (`query-cov`); native coverage is `qcovus`. They are not interchangeable measurements. QIIME uses `blast_top_n` as maxaccepts and a fixed minimum consensus of 0.51; native species-replacement settings do not apply to this backend.

## Expected outputs

Native output files are placed directly under `--outdir`:

| File | Format / content |
| --- | --- |
| `taxonomy_blast.qza` | Final reconciled `FeatureData[Taxonomy]`; validated at level=max |
| `taxonomy_blast.qzv` | Tabulated final taxonomy visualization |
| `taxonomy_blast_qiime.tsv` | `Feature ID`, `Taxon`, `Confidence`; source for QZA import |
| `taxonomy_blast.tsv` | One row per original taxonomy ASV; final lineage and decision |
| `taxonomy_blast_evidence.tsv` | Original classification, BLAST evidence, thresholds and final decision per ASV |
| `taxonomy_blast_changed.tsv` | Selected decision rows; see definition below |
| `taxonomy_blast_report.tsv` | Two-column Metric/Value reconciliation summary |
| `blast_hits_raw.tsv` | Headerless raw blastn output |
| `blast_candidates_top5.tsv` | Filtered/ranked candidates; filename stays top5 even if blast_top_n changes |
| `blast_taxonomy.tsv` | Top1 lineage, top2 evidence and ambiguity flag per ASV with candidates |
| `taxonkit_lineage.tsv` | TaxID-to-lineage mapping |
| `inputs/dna-sequences.fasta` | Exported input representative sequences |
| `inputs/taxonomy.tsv` | Exported original taxonomy |

Final taxonomy is based on the original taxonomy ASV set. The changed table has the same columns as the evidence table and selects statuses starting with `blast_species_` or `blast_top1_species_`, or containing `mismatch`/`conflict`. It is **not** a strict before/after taxonomy difference table: replacement decisions may leave identical text, and retained genus mismatches may appear. `qiime_retained_ambiguous_blast` is not included by that status filter; inspect the full evidence table for ambiguity.

QIIME backend outputs are `taxonomy_qiime_blast.qza`, `taxonomy_qiime_blast.qzv`, `taxonomy_qiime_blast.tsv`, and `blast_search_results.qza` (`FeatureData[BLAST6]`), plus input exports. These represent the independent QIIME BLAST classification, not the native reconciled result.

### Matrix columns

`taxonomy_blast.tsv`:

```text
ASV  Kingdom  Phylum  Class  Order  Family  Genus  Species  Final_Taxon  Replacement_Status  Replacement_Reason
```

Raw hits are tab-delimited with no header, in this order:

```text
qacc  staxids  sacc  evalue  bitscore  qcovus  pident  length
```

The candidate matrix has those eight columns plus `TaxID` and `candidate_rank`. Evidence columns include:

| Group | Fields |
| --- | --- |
| Original taxonomy | `ASV`, `QIIME_Taxon_Original`, `QIIME_Taxon_Normalized`, `QIIME_Confidence`, `QIIME_<rank>` |
| Top1 evidence | `BLAST_Top1_Accession`, `BLAST_Top1_TaxID`, `BLAST_Top1_Evalue`, `BLAST_Top1_Bitscore`, `BLAST_Top1_Pident`, `BLAST_Top1_Qcovus`, `BLAST_Top1_AlignmentLength`, `BLAST_Top1_<rank>` |
| Alternative hit | `BLAST_Top2_Accession`, `BLAST_Top2_Species`, and top2 alignment metrics |
| Decision context | `BLAST_AmbiguousTopHit`, `BLAST_SelectionStatus`, `QIIME_ConfidenceNumeric`, `QIIME_GenusResolved`, `QIIME_SpeciesResolved`, `Reconcile_Mode`, `Species_Min_Pident`, `Species_Min_Qcovus`, `Species_Max_Evalue`, `BLAST_CutoffPass`, `BLAST_GenusMatch` |
| Final result | `Final_<rank>`, `Final_Taxon`, `Replacement_Status`, `Replacement_Reason` |

`<rank>` means Kingdom, Phylum, Class, Order, Family, Genus, or Species. The displays above use spaces for readability; actual tables use tabs.

## BLAST report format

The report filename is `taxonomy_blast_report.tsv`. It is a long-format TSV with header `Metric\tValue`. Value contains either a string, a threshold, or a count depending on Metric.

Illustrative example (counts are examples, not expected values for every run):

```tsv
Metric	Value
total_asvs	100
reconcile_mode	species_missing_rescue
species_min_pident	99.0
species_min_qcovus	99.0
species_max_evalue	1e-10
blast_species_rescued_missing_qiime_species	20
qiime_retained_ambiguous_blast	5
qiime_retained_blast_cutoff_fail	10
qiime_retained_no_blast_species	60
qiime_retained_resolved_species	5
blast_cutoff_pass	30
blast_genus_match	25
```

| Metric | Interpretation |
| --- | --- |
| `total_asvs` | Number of ASVs in the final table, derived from the original taxonomy |
| `reconcile_mode` | Selected replacement policy |
| `species_min_pident`, `species_min_qcovus`, `species_max_evalue` | Applied final species cutoffs |
| Replacement/retention status rows | Count of ASVs assigned each decision status; only observed statuses are emitted |
| `blast_cutoff_pass` | ASVs whose top1 passes all species numeric cutoffs; not necessarily replaced |
| `blast_genus_match` | ASVs with nonempty, case-insensitively matching original and BLAST genus; not necessarily replaced |

Status counts sum to total_asvs. The last two metrics overlap those statuses and must not be added to that total. A passing numeric cutoff alone does not guarantee usable species taxonomy or replacement.

Possible decision statuses:

| Status | Meaning |
| --- | --- |
| `blast_species_rescued_missing_qiime_species` | Missing species rescued in default mode |
| `blast_top1_species_rescued_missing_qiime_species` | Missing species rescued in top1 mode without ambiguity |
| `blast_top1_species_rescued_ambiguous_missing_qiime_species` | Missing species rescued despite ambiguous top1/top2 |
| `blast_species_replaced_same_genus` | Replacement accepted under matching-genus policy |
| `qiime_retained_no_blast_species` | No usable top1 species available |
| `qiime_retained_blast_cutoff_fail` | Top1 species available but species cutoffs failed |
| `qiime_retained_ambiguous_blast` | Ambiguous top1/top2 prevented replacement |
| `qiime_retained_resolved_species` | Existing species preserved in a missing-species rescue mode |
| `qiime_retained_genus_mismatch` | Resolved original genus did not match BLAST genus |
| `qiime_retained_no_resolved_genus_match` | No explicit genus match for same_genus_only |

Decisions are evaluated in order: missing BLAST species, numeric cutoffs, then policy-specific conditions. Consequently a status is the selected decision reason, not a list of every condition that applies to an ASV.

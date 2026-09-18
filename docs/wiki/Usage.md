# QIIME_blast

[English](#english) | [한국어](#한국어)

## English

Standalone Nextflow DSL2 workflow derived from ITSdetector for BLAST-based taxonomy analysis of ASV representative sequences.

## Getting started with Nextflow

Nextflow runs the analysis steps and manages their inputs, outputs and task directories. Start with the official [installation guide](https://docs.seqera.io/nextflow/install) and [command-line guide](https://docs.seqera.io/nextflow/cli).

Check `nextflow -version`, `java -version` and `singularity --version` before using the workflow. The configured SIF container files must exist on your system; override their paths if necessary. Python-only commands require Python 3 and pandas, without Nextflow or QIIME.

The examples below use this installation's absolute pipeline path. Replace input and output paths with your own. `-C` selects this repository's configuration explicitly; `--` options are pipeline parameters. `-work-dir` selects the task directory and `-resume` reuses eligible cached tasks. Keep the work directory and Nextflow cache for resuming. Use a separate output directory for each reference and analysis.

| Task | Option | Required inputs |
| --- | --- | --- |
| Final report only, without BLAST | `--postprocess_only true` | One taxonomy QZA or TSV |
| Normalize, create QIIME artifacts, and produce final report without BLAST | `--normalize_only true` | One taxonomy QZA or TSV |
| Native BLAST and reconciliation, then final report | `--backend native` | Representative sequences QZA, taxonomy QZA, BLAST database prefix, taxdump |
| QIIME BLAST classification, then final report | `--backend qiime` | Representative sequences QZA, taxonomy QZA, reference reads QZA, reference taxonomy QZA |

## Final taxonomy postprocessing

All execution paths now end with the same postprocessing step: native BLAST,
QIIME BLAST, normalization without BLAST, and postprocessing-only mode.
The final **wide TSV** retains assigned taxon names and fills each unresolved
cell with the nearest assigned ancestor's rank abbreviation followed by its name.
A filled cell never becomes a new ancestor. Known lower ranks survive internal gaps.

| Final classification | Report value |
| --- | --- |
| Genus `Bacillus`, species missing | Species = `g_Bacillus` |
| Family `Bacillaceae`, genus/species missing | Genus = Species = `f_Bacillaceae` |
| Domain `Bacteria` only | Each lower rank = `d_Bacteria` |
| Assigned species | Keep the assigned species |
| No assigned ancestor | `Unassigned` |

The Species cell is exactly **`g_Bacillus`**. It is not `s__g_Bacillus` or
`s__g__Bacillus`. Assigned cells contain the names without QIIME rank prefixes.
GTDB/GG2 suffixes such as `Pseudomonas_E` and `Pseudomonas_E_647464` are preserved.
A bare `sp`/`sp.` species is unresolved; `sp000123456` remains assigned.
A legacy suffix such as `Bacillus_g` is converted only when it matches an actual
ancestor name and rank. Running the output through postprocessing again leaves
the table unchanged. This is a reporting convention, not a new biological assignment.

### Postprocess existing results without BLAST

Only a taxonomy QZA or TSV is needed; no representative sequences or BLAST database.

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --postprocess_only true \
  --taxonomy_qza /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/silva_138_99/taxonomy.qza \
  --taxonomy_profile silva138 \
  --outdir results/postprocessed_silva
```

Use `gtdb_r220` or `gg2` with the corresponding reference's taxonomy. For TSV,
replace `--taxonomy_qza` with `--taxonomy_tsv`. The two options are mutually exclusive.
`--postprocess_only` and `--normalize_only` are also mutually exclusive.
Normalization-only runs additionally create QIIME artifacts; both modes create
the final postprocessed table. No BLAST search runs in either mode.

To run just the Python postprocessor (Python 3 with pandas, no Nextflow/QIIME needed):

```bash
python3 /data/software/nextflow/QIIME_blast/bin/postprocess_taxonomy.py \
  --input /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gg2.qza \
  --profile gg2 --output-dir results/postprocessed_gg2
```

Inputs may be QIIME taxonomy TSV/QZA, the native reconciled TSV/evidence table,
or the postprocessed wide table. When final and original columns coexist, final
classification takes precedence. Confidence is copied unchanged when present.

Nextflow publishes these files under `<outdir>/postprocessed/`; the standalone
script writes them directly under `--output-dir`:

- `taxonomy_postprocessed.tsv`: one ASV per row, `Kingdom` through `Species`,
  `Top_Rank_Prefix`, and optional `Confidence`. With `d__` input, the compatibility
  column `Kingdom` represents Domain, indicated by `Top_Rank_Prefix=d`.
- `taxonomy_postprocess_changes.tsv`: each changed cell, its original/final value,
  and the ancestor used.
- `taxonomy_postprocess_summary.json`: row counts and filled cells per rank.

QIIME artifacts remain analysis inputs with positional rank slots. The postprocessed
wide table is the final report and is not automatically imported back into QIIME.

## Normalize only (without BLAST)

Use `--normalize_only true` with exactly one taxonomy QZA or TSV. Representative sequences, a BLAST database and NCBI taxdump are not required. Nextflow uses the QIIME container for normalization, QZA import and metadata visualization. The standalone Python script requires Python 3 and pandas and writes TSVs only.

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --normalize_only true \
  --taxonomy_qza /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gtdb_r220.qza \
  --taxonomy_profile gtdb_r220 \
  --outdir results/normalized_gtdb_r220

python3 /data/software/nextflow/QIIME_blast/bin/normalize_qiime_taxonomy.py \
  --input /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gg2.qza \
  --profile gg2 --output-dir results/normalized_gg2
```

For SILVA, use `--taxonomy_profile silva138` with `silva_138_99/taxonomy.qza`. For exported TSV input, replace `--taxonomy_qza` with `--taxonomy_tsv`; the Python `--input` accepts both formats. Use different output directories for each reference.

Outputs:

- `normalized/taxonomy_normalized.tsv`: original text, rank columns and profile metadata.
- `normalized/taxonomy_normalized_qiime.tsv`: import-ready taxonomy, optional original Confidence.
- `normalized/taxonomy_normalization_evidence.tsv`: normalization audit.
- `postprocessed/`: final report, per-cell changes and summary (Nextflow only).
- `taxonomy_normalized.qza` and `taxonomy_normalized.qzv`: Nextflow only; the QZV is a taxonomy table, not an abundance bar plot.

The Python command writes its three TSV files directly under `--output-dir` (without the `normalized/` subdirectory).

Intermediate QIIME taxonomy retains empty rank slots, such as `d__Bacteria; p__...; ...; g__; s__`, so missing ranks never shift other ranks upward. The final report fills unresolved cells using the common postprocessing rules. See [reference rules and official sources](../taxonomy_profiles.md).

## Backends and current scope

| Backend | Reference input | Behavior |
| --- | --- | --- |
| `native` | Formatted BLAST database prefix and NCBI taxdump | Run blastn, select candidates, resolve TaxIDs with TaxonKit, reconcile existing taxonomy, export TSV/QZA/QZV |
| `qiime` | Reference sequence and taxonomy QZA artifacts | Run QIIME 2 classify-consensus-blast and export its classification and search results |

The QIIME backend currently does **not** reconcile its classification with the original taxonomy or generate the native reconciliation report. Both backends now produce the same final postprocessed table format, but their upstream classification and reconciliation behavior remains different.

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

nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --backend native \
  --repseq_qza /data/home2/ksy/260811_DT_swab/Output/HN00182797/05_dada2/rep-seqs.qza \
  --taxonomy_qza /data/home2/ksy/260811_DT_swab/Output/HN00182797/06_taxonomy/taxonomy_SILVA.qza \
  --outdir /data/home2/ksy/260811_DT_swab/Output/HN00182797/09_BLAST \
  --blast_db /data/Reference/BLAST/16S/20241203/16S_ribosomal_RNA \
  --taxdump_dir /data/Reference/BLAST/taxdump \
  --taxonomy_profile silva138 \
  --blast_reconcile_mode species_missing_rescue \
  --blast_species_min_pident 99 \
  --blast_species_min_qcovus 99 \
  --blast_species_max_evalue 1e-10 \
  -work-dir /data/home2/ksy/260811_DT_swab/work_blast/HN00182797 \
  -resume
```

`--blast_db` is a database **prefix**, not a directory or a `.nin` filename. Taxdump is the directory used by TaxonKit.

Choose `--taxonomy_profile silva138`, `gtdb_r220`, or `gg2` for the corresponding input. The default `auto` preserves input rank prefixes without guessing the database. See [reference rules and official sources](../taxonomy_profiles.md).

## BLAST modification / reconciliation options

Select a policy with `--blast_reconcile_mode`:

| Mode | Existing resolved species | Missing/unresolved species | Genus agreement | Ambiguous top hit |
| --- | --- | --- | --- | --- |
| `species_missing_rescue` (default) | Preserve | Replace if species cutoffs pass | Required under default species_only | Preserve original taxonomy |
| `species_missing_top1_rescue` | Preserve | Replace if species cutoffs pass | Required under default species_only | Accept top1 if species cutoffs pass |
| `same_genus_only` | May replace | May replace | Explicit matching nonempty genus required | Preserve original taxonomy |

All modes require a nonempty BLAST top1 species and passing species-level cutoffs. Missing/placeholder detection follows the normalization and reconciliation scripts; it is not an independent assessment of biological species resolution.

By default, `--blast_lineage_policy species_only` keeps the original Domain through Genus and requires an exact genus match before adding a BLAST species. GTDB/GG2 suffixes are not stripped. The policy table above describes the rescue decision; this additional genus gate applies to every mode under `species_only`. Use `--blast_lineage_policy blast_lineage` only to explicitly request whole-lineage replacement. Empty ranks retain their positions for both replaced and retained rows. Original Domain prefixes and reference-specific names are preserved; Eukaryota is not assumed to be Fungi.

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

Candidate filters run before replacement thresholds. Lowering only a species threshold cannot recover a hit already removed by candidate selection.

Native candidates require a valid TaxID and are sorted by E-value ascending, then bit score, identity, coverage, and alignment length descending, then accession ascending. Top1 is the first retained row. Ambiguity currently compares **only top1 and top2**: different species with identical E-value, bit score, identity, coverage, and alignment length. It does not inspect all tied candidates; with `--blast_top_n 1`, this ambiguity check cannot detect a conflict.

The exported `Confidence` retains the original QIIME confidence even when taxonomy changes. It is not a confidence estimate for the BLAST replacement.

## Run QIIME BLAST

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
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

Native runs publish the following files under `--outdir`, including the common final report:

```text
results/
  taxonomy_blast.qza
  taxonomy_blast_report.tsv
  taxonomy_blast_changed.tsv
  taxonomy_blast_evidence.tsv
  postprocessed/
    taxonomy_postprocessed.tsv
    taxonomy_postprocess_changes.tsv
    taxonomy_postprocess_summary.json
```

Other generated files (QZV, exported FASTA/TSV, raw hits, candidates, lineage and the QZA import TSV) remain in task directories under `work/` or `-work-dir`. These directories support inspection and `-resume` until explicitly cleaned. No save-intermediates option is currently implemented. Files already published by earlier runs are not automatically removed.

The following table describes both published and intermediate files; the native top-level published files are the four listed above, in addition to the common `postprocessed/` outputs:

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
| `repseq_export/dna-sequences.fasta` | Exported input representative sequences |
| `taxonomy_export/taxonomy.tsv` | Exported original taxonomy |

Final taxonomy is based on the original taxonomy ASV set. The changed table has the same columns as the evidence table and selects statuses starting with `blast_species_` or `blast_top1_species_`, or containing `mismatch`/`conflict`. It is **not** a strict before/after taxonomy difference table: replacement decisions may leave identical text, and retained genus mismatches may appear. `qiime_retained_ambiguous_blast` is not included by that status filter; inspect the full evidence table for ambiguity.

QIIME backend outputs are `taxonomy_qiime_blast.qza`, `taxonomy_qiime_blast.qzv`, `taxonomy_qiime_blast.tsv`, and `blast_search_results.qza` (`FeatureData[BLAST6]`), with input exports retained only in the export task work directory. These represent the independent QIIME BLAST classification, not the native reconciled result.

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

---

## 한국어

QIIME_blast는 ASV 대표 서열의 BLAST 기반 분류 분석을 수행하는 독립형 Nextflow DSL2 파이프라인입니다. ITSdetector에서 파생되었으며, 기존 taxonomy 보정과 BLAST 없는 정규화·최종 후가공을 지원합니다.

### 1. Nextflow를 처음 사용하는 경우

Nextflow는 분석 단계를 순서와 의존관계에 따라 실행하고 입력·출력·작업 디렉터리를 관리합니다. 설치는 [공식 설치 안내](https://docs.seqera.io/nextflow/install), 실행 옵션은 [공식 명령행 안내](https://docs.seqera.io/nextflow/cli)를 참고하세요.

먼저 다음 명령으로 설치 상태를 확인하세요.

```bash
nextflow -version
java -version
singularity --version
```

현재 설정은 Singularity와 미리 준비된 SIF 컨테이너를 사용합니다. 컨테이너는 Git에 포함되어 있지 않으므로 아래 파일이 있는지 확인하거나 옵션으로 경로를 지정해야 합니다.

| 컨테이너 옵션 | 기본 경로 |
| --- | --- |
| `--blast_taxonomy_sif` | `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif` |
| `--qiime_sif` | `/data/software/singularity/qiime2_amplicon_2025.7.sif` |

Native BLAST와 QIIME BLAST는 기본 8 CPU/32 GB, QIIME 입출력 단계는 1 CPU/4 GB를 사용합니다. Python 스크립트만 실행할 때는 Python 3와 pandas가 필요하며 Nextflow나 QIIME 설치는 필요하지 않습니다.

아래 명령의 입력·출력 경로는 환경에 맞게 바꾸세요. `-C`는 이 저장소의 설정 파일을 명시적으로 선택합니다. `--`로 시작하는 옵션은 파이프라인에 전달됩니다. `-work-dir`는 중간 작업 디렉터리, `-resume`은 재사용 가능한 이전 작업을 활용하는 옵션입니다. 재실행하려면 작업 디렉터리와 Nextflow 캐시를 유지하세요. DB별·분석별로 출력 디렉터리를 구분하세요.

### 2. 실행 방식 선택

| 목적 | 옵션 | 필요한 입력 |
| --- | --- | --- |
| BLAST 없이 최종 후가공만 수행 | `--postprocess_only true` | taxonomy QZA 또는 TSV 하나 |
| BLAST 없이 정규화·QZA/QZV 생성·최종 후가공 | `--normalize_only true` | taxonomy QZA 또는 TSV 하나 |
| Native BLAST로 기존 분류 보정 후 최종 후가공 | `--backend native` | 대표 서열 QZA, taxonomy QZA, BLAST DB prefix, taxdump |
| QIIME BLAST로 분류 후 최종 후가공 | `--backend qiime` | 대표 서열 QZA, taxonomy QZA, 참조 서열 QZA, 참조 taxonomy QZA |

`--postprocess_only`와 `--normalize_only`는 동시에 사용할 수 없습니다. 두 모드에서는 `--taxonomy_qza`와 `--taxonomy_tsv` 중 하나만 지정합니다. 대표 서열이나 BLAST DB는 필요하지 않으며 BLAST 검색을 실행하지 않습니다.

### 3. 모든 DB에 적용하는 최종 후가공 규칙

Native BLAST, QIIME BLAST, 정규화 전용, 후가공 전용 실행 모두 마지막에 같은 후가공을 적용합니다. 최종 보고용 TSV에서 미분류 칸을 **가장 가까운, 실제로 분류된 상위 계급의 약어와 이름**으로 채웁니다.

| 입력 상태 | 최종 보고용 값 |
| --- | --- |
| Genus가 `Bacillus`, Species가 비어 있음 | Species = **`g_Bacillus`** |
| Family가 `Bacillaceae`, Genus·Species가 비어 있음 | Genus와 Species 모두 **`f_Bacillaceae`** |
| Domain `Bacteria`만 있음 | 아래 미분류 칸은 `d_Bacteria` |
| Species가 이미 분류됨 | 기존 Species 유지 |
| 사용할 상위 분류가 없음 | `Unassigned` |

약어는 Domain `d`, Kingdom `k`, Phylum `p`, Class `c`, Order `o`, Family `f`, Genus `g`입니다. Species 칸에는 **`g_Bacillus`만** 들어갑니다. `s__g_Bacillus`나 `s__g__Bacillus`를 만들지 않습니다. 기존에 분류된 칸도 QIIME 계급 접두사를 제외한 이름으로 표시합니다.

- 이미 채운 칸을 새로운 상위 분류 근거로 사용하지 않습니다.
- 중간 계급이 비어 있어도 그 아래의 기존 분류명은 보존합니다.
- GTDB/GG2 고유 이름인 `Pseudomonas_E`, `Pseudomonas_E_647464` 등의 접미사를 유지합니다.
- Species의 `sp`/`sp.` 표기는 미분류로 처리하지만 `sp000123456` 같은 이름은 유지합니다.
- 과거의 `Bacillus_g` 표기는 실제 상위 분류명과 계급이 일치할 때만 `g_Bacillus`로 바꿉니다.
- 완전 미분류는 `Unassigned`로 남고, 결과를 다시 처리해도 같은 표가 나옵니다.
- 이 표기는 보고용 규칙이며 새로운 생물학적 분류를 확정하는 의미는 아닙니다.

QIIME용 중간 taxonomy는 `d__Bacteria; p__...; ...; g__; s__`처럼 비어 있는 계급의 위치를 유지합니다. 최종 후가공 표는 별도 TSV로 제공하며 QIIME artifact에 자동으로 다시 넣지 않습니다. `d__` 입력의 Domain은 기존 표 구조와의 호환을 위해 `Kingdom` 열에 저장하고 `Top_Rank_Prefix=d`로 구분합니다.

### 4. BLAST 없이 후가공만 실행

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --postprocess_only true \
  --taxonomy_qza /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/silva_138_99/taxonomy.qza \
  --taxonomy_profile silva138 \
  --outdir results/postprocessed_silva
```

GTDB r220은 `--taxonomy_profile gtdb_r220`, GG2는 `--taxonomy_profile gg2`를 사용합니다. TSV 입력은 `--taxonomy_qza`를 `--taxonomy_tsv`로 바꾸면 됩니다. 기본값 `auto`는 DB를 추측하지 않고 입력 계급 접두사를 보존합니다. DB별 처리 근거는 [공식 자료 기반 규칙](../taxonomy_profiles.md)에 정리되어 있습니다.

Python만으로 후가공할 수도 있습니다.

```bash
python3 /data/software/nextflow/QIIME_blast/bin/postprocess_taxonomy.py \
  --input /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gg2.qza \
  --profile gg2 \
  --output-dir results/postprocessed_gg2
```

입력은 QIIME taxonomy QZA/TSV, native 보정 TSV/evidence 표, 이미 후가공한 표를 지원합니다. 원본과 최종 분류 열이 함께 있으면 최종 분류를 우선 사용합니다. Confidence가 있으면 그대로 복사합니다.

Nextflow는 `<outdir>/postprocessed/`에, Python 단독 실행은 `--output-dir` 바로 아래에 다음 파일을 저장합니다.

| 파일 | 내용 |
| --- | --- |
| `taxonomy_postprocessed.tsv` | ASV별 최종 분류 표: Feature ID, Top_Rank_Prefix, Kingdom~Species, 선택적 Confidence |
| `taxonomy_postprocess_changes.tsv` | 변경한 칸의 원래 값·최종 값·근거 상위 분류 |
| `taxonomy_postprocess_summary.json` | ASV 수, 변경 수, 계급별 보완 수 |

### 5. BLAST 없이 정규화와 QIIME artifact 생성

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --normalize_only true \
  --taxonomy_qza /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gtdb_r220.qza \
  --taxonomy_profile gtdb_r220 \
  --outdir results/normalized_gtdb_r220
```

정규화는 계급 위치를 정리하고 원래 이름을 보존합니다. 미분류 칸이 있다고 Phylum이 Kingdom으로 이동하지 않습니다. 이후 최종 후가공 단계가 보고용 빈칸을 채웁니다.

| 출력 | 내용 |
| --- | --- |
| `normalized/taxonomy_normalized.tsv` | 원본 문자열, 계급별 열, 프로필 정보 |
| `normalized/taxonomy_normalized_qiime.tsv` | QIIME import용 taxonomy와 선택적 원본 Confidence |
| `normalized/taxonomy_normalization_evidence.tsv` | 정규화 처리 기록 |
| `taxonomy_normalized.qza` | 정규화된 QIIME taxonomy artifact |
| `taxonomy_normalized.qzv` | taxonomy 표 시각화이며 abundance bar plot은 아님 |
| `postprocessed/` | 최종 후가공 표, 변경 기록, 요약 |

정규화 스크립트도 독립 실행할 수 있습니다.

```bash
python3 /data/software/nextflow/QIIME_blast/bin/normalize_qiime_taxonomy.py \
  --input /data/home2/ksy/260903_AT_multi_Re/bacteria/results/taxonomy/taxonomy_gg2.qza \
  --profile gg2 \
  --output-dir results/normalized_gg2
```

이 Python 명령은 정규화 TSV 세 개만 출력 디렉터리 바로 아래에 생성합니다. QZA/QZV 생성과 최종 후가공은 실행하지 않으므로, 최종 보고용 표가 필요하면 `postprocess_taxonomy.py`를 추가 실행하거나 Nextflow의 `--normalize_only true`를 사용하세요.

### 6. Native BLAST 실행 및 기존 분류 보정

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --backend native \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile silva138 \
  --blast_db /data/Reference/BLAST/16S/20241203/16S_ribosomal_RNA \
  --taxdump_dir /data/Reference/BLAST/taxdump \
  --blast_reconcile_mode species_missing_rescue \
  --blast_lineage_policy species_only \
  --blast_species_min_pident 99 \
  --blast_species_min_qcovus 99 \
  --blast_species_max_evalue 1e-10 \
  --outdir results/native \
  -work-dir work_native \
  -resume
```

대표 서열은 `FeatureData[Sequence]`, taxonomy는 `FeatureData[Taxonomy]` QZA를 사용합니다. 파일 이름 자체에는 제한이 없습니다. 내부에서 FASTA/TSV로 export합니다. `--blast_db`는 디렉터리나 `.nin` 파일이 아니라 포맷된 BLAST DB의 **prefix**입니다. `--taxdump_dir`는 TaxonKit에서 사용할 NCBI taxdump 디렉터리입니다.

기본값 `--blast_lineage_policy species_only`는 원래 Domain~Genus를 유지하고, 원래 Genus와 BLAST Genus가 일치할 때만 Species 보완을 허용합니다. 비교 시 대소문자는 구분하지 않으며 GTDB/GG2 접미사는 제거하지 않습니다. 전체 계통 교체가 필요하면 `--blast_lineage_policy blast_lineage`를 명시합니다. Eukaryota를 자동으로 Fungi로 바꾸지 않습니다.

#### 보정 모드

| `--blast_reconcile_mode` | 기존 Species가 있을 때 | 미분류 Species | 모호한 최상위 hit |
| --- | --- | --- | --- |
| `species_missing_rescue` (기본값) | 유지 | 기준 통과 시 보완 | 원본 유지 |
| `species_missing_top1_rescue` | 유지 | 기준 통과 시 보완 | 기준을 통과한 top1 허용 |
| `same_genus_only` | 교체 가능 | 보완 가능 | 원본 유지 |

모든 모드는 사용할 수 있는 BLAST Species와 수치 기준 통과가 필요합니다. `species_only`에서는 모든 모드에 Genus 일치 조건을 추가 적용합니다. `same_genus_only`는 명시적으로 분류된 비어 있지 않은 Genus의 일치를 요구합니다.

#### 후보 검색·선별과 Species 교체 기준

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--blast_retrieval_n` | `20` | native blastn의 max_target_seqs |
| `--blast_top_n` | `5` | native 후보 보존 수, QIIME maxaccepts |
| `--blast_min_pident` | `99.0` | native 후보 최소 identity (%) |
| `--blast_min_qcovus` | `80.0` | native 후보 최소 query coverage (%) |
| `--blast_max_evalue` | `1e-10` | native 후보 최대 E-value, QIIME 검색 E-value |
| `--blast_species_min_pident` | `99.0` | native Species 교체 최소 identity (%) |
| `--blast_species_min_qcovus` | `99.0` | native Species 교체 최소 coverage (%) |
| `--blast_species_max_evalue` | `1e-10` | native Species 교체 최대 E-value |

후보 선별을 먼저 수행하므로 Species 기준만 낮춰도 이미 제외된 hit는 복원되지 않습니다. Native 후보는 유효한 TaxID가 있어야 하며 E-value 오름차순, bit score·identity·coverage·정렬 길이 내림차순, accession 오름차순으로 정렬합니다.

모호성 검사는 **top1과 top2만** 비교합니다. Species가 다르면서 위 수치가 모두 같으면 모호한 결과로 처리합니다. 동률 후보 전체를 검사하지 않으며 `--blast_top_n 1`에서는 충돌을 검출할 수 없습니다.

Confidence는 taxonomy 변경 여부와 관계없이 원래 QIIME 값을 유지합니다. BLAST 보정의 신뢰도를 새로 계산한 값이 아닙니다.

### 7. QIIME BLAST 실행

```bash
nextflow -C /data/software/nextflow/QIIME_blast/nextflow.config run /data/software/nextflow/QIIME_blast/main.nf \
  --backend qiime \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --reference_reads /path/to/ref-seqs.qza \
  --reference_taxonomy /path/to/ref-taxonomy.qza \
  --outdir results/qiime \
  -resume
```

참조 서열과 taxonomy는 서로 ID가 일치하는 `FeatureData[Sequence]` 및 `FeatureData[Taxonomy]` artifact여야 합니다. sklearn과 같은 DB를 비교하려면 학습된 classifier QZA 자체가 아니라 학습에 사용한 참조 서열과 분류표를 넣으세요.

QIIME backend는 `classify-consensus-blast`로 독립적인 분류를 생성합니다. Native와 같은 원래 taxonomy 보정이나 native 보정 보고서는 생성하지 않습니다. 두 backend 모두 공통 최종 후가공 표는 생성합니다.

Identity와 coverage는 Nextflow 옵션에서 백분율로 입력하고 QIIME 실행 시 비율로 변환합니다. QIIME coverage는 HSP별 `query-cov`, native coverage는 `qcovus`로 서로 다른 측정값입니다. QIIME의 최소 consensus는 0.51이며 native Species 교체 옵션은 적용되지 않습니다.

### 8. 출력 파일과 해석

Native 실행의 기본 출력은 다음과 같습니다.

```text
results/
  taxonomy_blast.qza
  taxonomy_blast_report.tsv
  taxonomy_blast_changed.tsv
  taxonomy_blast_evidence.tsv
  postprocessed/
    taxonomy_postprocessed.tsv
    taxonomy_postprocess_changes.tsv
    taxonomy_postprocess_summary.json
```

Native의 QZV, `taxonomy_blast_qiime.tsv`, `taxonomy_blast.tsv`, 원시 hit, 후보, lineage 및 입력 FASTA/TSV는 작업 디렉터리에 남습니다. 중간 파일 전체를 출력 폴더에 복사하는 옵션은 현재 없습니다. 이전 실행에서 이미 출력된 파일은 자동 삭제하지 않습니다.

| 파일 | 내용 |
| --- | --- |
| `taxonomy_blast.qza` | 보정된 QIIME taxonomy; 최대 수준 유효성 검사 수행 |
| `taxonomy_blast.qzv` | 보정 taxonomy 표 시각화; native 작업 디렉터리에 보존 |
| `taxonomy_blast_qiime.tsv` | Feature ID, Taxon, Confidence; QZA import 입력 |
| `taxonomy_blast.tsv` | 원본 ASV별 최종 계급과 보정 판단 |
| `taxonomy_blast_evidence.tsv` | 원본·BLAST 근거·기준·최종 판단 |
| `taxonomy_blast_changed.tsv` | 특정 판단 상태를 선택한 표 |
| `taxonomy_blast_report.tsv` | Metric/Value 형태의 보정 요약 |
| `blast_hits_raw.tsv` | 헤더 없는 원시 blastn 결과 |
| `blast_candidates_top5.tsv` | 선별·정렬된 후보; top_n을 바꿔도 파일명은 동일 |
| `blast_taxonomy.tsv` | top1 계통, top2 근거, 모호성 여부 |
| `taxonkit_lineage.tsv` | TaxID별 lineage |
| `repseq_export/dna-sequences.fasta` | 입력 대표 서열 export |
| `taxonomy_export/taxonomy.tsv` | 입력 taxonomy export |

최종 native 분류는 원본 taxonomy의 ASV 집합을 기준으로 합니다. `taxonomy_blast_changed.tsv`는 상태가 `blast_species_` 또는 `blast_top1_species_`로 시작하거나 `mismatch`/`conflict`를 포함하는 행을 선택합니다. 실제 문자열 변경만 모은 표가 아니므로 유지된 Genus 불일치도 포함할 수 있습니다. `qiime_retained_ambiguous_blast`는 이 선택 조건에 포함되지 않으므로 전체 evidence 표에서 확인하세요. 최종 후가공의 칸별 실제 변경은 `taxonomy_postprocess_changes.tsv`에서 확인합니다.

QIIME backend는 `taxonomy_qiime_blast.qza`, `taxonomy_qiime_blast.qzv`, `taxonomy_qiime_blast.tsv`, `blast_search_results.qza`와 공통 `postprocessed/` 파일을 출력합니다. 검색 artifact의 타입은 `FeatureData[BLAST6]`입니다.

#### 상세 표의 열

`taxonomy_blast.tsv`의 열은 다음과 같습니다. 실제 파일은 탭으로 구분됩니다.

```text
ASV  Kingdom  Phylum  Class  Order  Family  Genus  Species  Final_Taxon  Replacement_Status  Replacement_Reason
```

원시 hit의 열 순서는 다음과 같으며 후보 표에는 `TaxID`, `candidate_rank`가 추가됩니다.

```text
qacc  staxids  sacc  evalue  bitscore  qcovus  pident  length
```

Evidence 표는 원본 `QIIME_*`, 최상위 hit `BLAST_Top1_*`, 대안 hit `BLAST_Top2_*`, 기준 통과·Genus 일치·모호성 등의 판단 근거, `Final_<rank>`, `Final_Taxon`, `Replacement_Status`, `Replacement_Reason`을 담습니다. `<rank>`는 Kingdom~Species의 일곱 계급입니다.

#### 보정 보고서

`taxonomy_blast_report.tsv`는 `Metric`과 `Value` 두 열의 긴 형식 TSV입니다.

| Metric | 해석 |
| --- | --- |
| `total_asvs` | 원본 taxonomy 기준 최종 ASV 수 |
| `reconcile_mode` | 선택한 보정 정책 |
| `species_min_pident`, `species_min_qcovus`, `species_max_evalue` | 최종 Species 기준 |
| 각 보정·유지 상태 | 해당 상태의 ASV 수; 관측된 상태만 출력 |
| `blast_cutoff_pass` | top1이 Species 수치 기준을 통과한 ASV 수 |
| `blast_genus_match` | 원본·BLAST Genus가 비어 있지 않고 대소문자 무시 비교에서 일치한 ASV 수 |

상태별 수의 합은 `total_asvs`입니다. 마지막 두 지표는 상태별 수와 겹치므로 합산하지 않습니다. 수치 기준 통과만으로 교체가 보장되지는 않습니다.

| 상태 | 의미 |
| --- | --- |
| `blast_species_rescued_missing_qiime_species` | 기본 모드에서 미분류 Species 보완 |
| `blast_top1_species_rescued_missing_qiime_species` | top1 모드에서 모호성 없이 보완 |
| `blast_top1_species_rescued_ambiguous_missing_qiime_species` | 모호한 top1/top2를 허용해 보완 |
| `blast_species_replaced_same_genus` | 동일 Genus 정책에서 교체 |
| `qiime_retained_no_blast_species` | 사용할 BLAST Species가 없어 유지 |
| `qiime_retained_blast_cutoff_fail` | Species 수치 기준 미달로 유지 |
| `qiime_retained_ambiguous_blast` | 모호한 hit 때문에 유지 |
| `qiime_retained_resolved_species` | 기존에 분류된 Species 유지 |
| `qiime_retained_genus_mismatch` | 원본과 BLAST Genus 불일치로 유지 |
| `qiime_retained_no_resolved_genus_match` | same_genus_only에서 명시적 Genus 일치가 없어 유지 |

판단 순서는 BLAST Species 유무, 수치 기준, 정책별 조건입니다. 상태는 선택된 판단 이유 하나를 나타내며 해당 ASV에 적용 가능한 모든 조건의 목록은 아닙니다.

# QIIME_blast

[English](#english) | [한국어](#한국어) · [Detailed documentation / 상세 문서](docs/wiki/Home.md)

## English

### 1. Purpose

QIIME_blast is a standalone Nextflow DSL2 workflow, derived from ITSdetector, for BLAST-based taxonomy analysis of **full-length 16S rRNA amplicon sequence variants (ASVs)**. It takes representative sequences and existing QIIME taxonomy, evaluates BLAST evidence, and produces classification tables and QIIME artifacts.

The native backend can rescue unresolved Species while retaining the original upper ranks. Existing taxonomy can also be normalized and postprocessed **without running BLAST**. A common final reporting step handles missing ranks consistently across SILVA 138, GTDB r220 and GG2.

**Current scope: full-length 16S rRNA data only.** Applying the BLAST reconciliation workflow to short-region 16S amplicons (for example, V3–V4 or V4) requires additional consideration and validation of the target region, reference database, identity/coverage thresholds and achievable taxonomic resolution. The current defaults should not be assumed to transfer directly. Related discussion: [QIIME 2 Forum — genus-level classification from 16S](https://forum.qiime2.org/t/how-to-find-the-genus-level-from-bacteria-with-from-16s-method/33791/4?u=soyeon_kim).

### 2. Nextflow and tool environment

Nextflow manages the analysis steps and their intermediate files. The current configuration runs tools in **Singularity containers**, so tools inside the images do not need separate host installations. For beginners: [Nextflow installation](https://docs.seqera.io/nextflow/install) · [Command-line guide](https://docs.seqera.io/nextflow/cli).

| Component | Version / environment | Role |
| --- | --- | --- |
| Nextflow | 26.04.2, DSL2; tested version | Workflow execution and resuming |
| Java | Temurin OpenJDK 17.0.10; tested version | Nextflow runtime |
| Singularity CE | 3.9.2; tested version | Container execution |
| QIIME 2 Amplicon | **2025.7** | QIIME artifact handling and BLAST classification |
| QIIME 2 / q2cli / feature-classifier | **2025.7.0** | Installed QIIME framework, CLI and classifier plugin |
| Python in QIIME image | 3.10.14 | Normalization and postprocessing |
| Native BLAST image recipe | Python 3.10, BLAST 2.16.0, TaxonKit 0.18.0, csvtk 0.30.0 | Search, TaxID lineage resolution and table processing |
| Native Python packages in recipe | pandas 2.2.3, NumPy 1.26.4, PyYAML 6.0.2 | Taxonomy data processing |

QIIME 2 **2025.7 is the supported environment for this release**; other QIIME versions have not been verified. Workflow tests exercise normalization, QZA import/validation, QZV generation and postprocessing; they do not run a full QIIME BLAST search. Native image versions above are specified by its build recipe.

| Container option | Default local path |
| --- | --- |
| `--qiime_sif` | `/data/software/singularity/qiime2_amplicon_2025.7.sif` |
| `--blast_taxonomy_sif` | `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif` |

Override these paths for your installation. SIF binaries are excluded from Git. The QIIME image comes from `quay.io/qiime2/amplicon:2025.7`; the custom native image recipe is included in [containers/blast_taxonomy.def](containers/blast_taxonomy.def). See [container setup](docs/wiki/Containers.md). Default resources are 8 CPUs/32 GB for either BLAST backend and 1 CPU/4 GB for QIIME export/import and taxonomy processing.

### 3. Supported features

#### Execution modes and inputs

| Mode | Required inputs | Behavior |
| --- | --- | --- |
| `--backend native` | Representative sequence QZA, taxonomy QZA, formatted BLAST DB prefix, NCBI taxdump | blastn search, candidate selection, TaxonKit lineage resolution, original taxonomy reconciliation and final reporting |
| `--backend qiime` | Representative sequence QZA, taxonomy QZA, reference sequence/taxonomy QZAs | QIIME `classify-consensus-blast`, independent classification and final reporting |
| `--normalize_only true` | One taxonomy QZA or TSV | Rank normalization, QZA/QZV generation and final reporting without BLAST |
| `--postprocess_only true` | One taxonomy QZA or TSV | Final reporting without BLAST |

Representative sequences must be `FeatureData[Sequence]` and taxonomy must be `FeatureData[Taxonomy]`. In no-BLAST modes, provide exactly one of `--taxonomy_qza` or `--taxonomy_tsv`; the two no-BLAST modes are mutually exclusive. The QIIME backend currently does **not** reconcile its classification with the original taxonomy or produce native reconciliation reports. Reference reads and labels must have matching IDs; provide reference artifacts, not a trained sklearn classifier QZA.

#### Native BLAST and reconciliation

Run from the repository directory, replacing the input paths:

```bash
nextflow -C nextflow.config run main.nf \
  --backend native \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile silva138 \
  --blast_db /path/to/blast_db_prefix \
  --taxdump_dir /path/to/taxdump \
  --blast_reconcile_mode species_missing_rescue \
  --blast_lineage_policy species_only \
  --outdir results/native -work-dir work/native -resume
```

`--blast_db` is a database **prefix**, not a directory or a `.nin` file. `-C` selects this repository's configuration; `-work-dir` stores intermediate tasks and `-resume` reuses eligible cached work. Preserve the task directory and Nextflow cache to resume.

| `--blast_reconcile_mode` | Behavior |
| --- | --- |
| `species_missing_rescue` (default) | Keep assigned Species; rescue missing Species when cutoffs pass and the top hit is unambiguous |
| `species_missing_top1_rescue` | Keep assigned Species; allow a qualifying top1 even when top1/top2 are ambiguous |
| `same_genus_only` | Allow Species replacement when explicit, nonempty genera match and the top hit is unambiguous |

Default `--blast_lineage_policy species_only` preserves Domain through Genus and requires genus agreement in every mode. Genus comparison ignores case but preserves DB-specific suffixes. Use `--blast_lineage_policy blast_lineage` to explicitly allow upper-lineage replacement. Original Confidence is retained; it is not a newly calculated BLAST confidence.

| Threshold | Candidate selection | Final Species replacement |
| --- | --- | --- |
| Identity | `--blast_min_pident 99` | `--blast_species_min_pident 99` |
| Query coverage | `--blast_min_qcovus 80` | `--blast_species_min_qcovus 99` |
| E-value | `--blast_max_evalue 1e-10` | `--blast_species_max_evalue 1e-10` |

Native search retrieves up to 20 targets (`--blast_retrieval_n`) and retains up to 5 candidate rows (`--blast_top_n`) by default. Candidate filters run first. Ambiguity detection compares only top1 and top2; a single retained candidate cannot reveal a tie conflict. Full selection and report details are in the [usage guide](docs/wiki/Usage.md).

#### QIIME BLAST

```bash
nextflow -C nextflow.config run main.nf \
  --backend qiime \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --reference_reads /path/to/ref-seqs.qza \
  --reference_taxonomy /path/to/ref-taxonomy.qza \
  --outdir results/qiime -resume
```

QIIME uses `--blast_top_n` as maxaccepts and minimum consensus 0.51. Identity and coverage options take percentages; QIIME coverage is per HSP (`query-cov`), while native coverage uses `qcovus`. Native Species replacement thresholds do not apply to this backend.

#### Normalization and postprocessing without BLAST

```bash
nextflow -C nextflow.config run main.nf \
  --normalize_only true \
  --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile gtdb_r220 --outdir results/normalized

nextflow -C nextflow.config run main.nf \
  --postprocess_only true \
  --taxonomy_tsv /path/to/taxonomy.tsv \
  --taxonomy_profile silva138 --outdir results/postprocessed
```

Choose `silva138`, `gtdb_r220` or `gg2` for the corresponding reference. `auto` preserves input rank prefixes without guessing the DB; generic, UNITE and EUKARYOME profiles are also available. Normalization keeps empty QIIME rank positions and reference-specific names. Both Python scripts can also run independently with Python 3 and pandas; see [reference rules](docs/taxonomy_profiles.md) and [standalone usage](docs/wiki/Usage.md).

All execution modes produce a common final wide TSV:

| Taxonomy state | Final reporting value |
| --- | --- |
| Genus `Bacillus`, Species missing | Species = **`g_Bacillus`** |
| Family `Bacillaceae`, Genus and Species missing | Both = **`f_Bacillaceae`** |
| Assigned name | Preserve it, including GTDB/GG2 suffixes |
| No assigned ancestor | `Unassigned` |

Filled cells use the nearest genuinely assigned ancestor and never gain a destination prefix such as `s__`. This is a reporting convention, not a new taxonomic assignment. Reprocessing the final table leaves it unchanged. QIIME artifacts remain separate; Domain is stored in the compatibility `Kingdom` column with `Top_Rank_Prefix=d` in wide reports.

#### Outputs and tests

| Mode | Main published outputs |
| --- | --- |
| All modes | `postprocessed/taxonomy_postprocessed.tsv`, `taxonomy_postprocess_changes.tsv`, `taxonomy_postprocess_summary.json` (all under `postprocessed/`) |
| Native | `taxonomy_blast.qza`, `taxonomy_blast_report.tsv`, `taxonomy_blast_changed.tsv`, `taxonomy_blast_evidence.tsv` |
| QIIME | `taxonomy_qiime_blast.qza`, `.qzv`, `.tsv`, and `blast_search_results.qza` |
| Normalize only | `normalized/` TSVs, `taxonomy_normalized.qza`, `taxonomy_normalized.qzv` |

Native raw hits, candidates, lineage, import TSV and QZV remain in task directories. The native `changed` table selects decision statuses and is not a strict before/after difference table; inspect the evidence table for full decisions. The final postprocessing change log records actual changed cells.

```bash
nextflow -C nextflow.config run main.nf -profile test
nextflow -C nextflow.config run main.nf -profile test_postprocess
```

These profiles use bundled synthetic inputs and check output against an expected table. `test` includes normalization and QIIME artifact generation; `test_postprocess` checks final postprocessing directly. Neither needs a BLAST DB. A mismatch fails the workflow; success writes `<outdir>/test/test_report.txt`. [Test details](docs/wiki/Tests.md)

---

## 한국어

### 1. 도구의 목적

QIIME_blast는 ITSdetector에서 파생된 독립형 Nextflow DSL2 파이프라인으로, **full-length 16S rRNA ASV(앰플리콘 서열 변이)**의 대표 서열과 기존 QIIME taxonomy를 받아 BLAST 근거를 평가하고 분류표와 QIIME artifact를 생성합니다.

Native backend에서는 기존 상위 분류를 유지하면서 미분류 Species를 보완할 수 있습니다. **BLAST 없이 기존 taxonomy만 정규화하거나 후가공하는 기능**도 제공합니다. SILVA 138·GTDB r220·GG2 결과의 빈 계급을 같은 규칙으로 처리해 최종 보고용 표를 만듭니다.

**현재 지원 범위는 full-length 16S rRNA 데이터 전용입니다.** V3–V4, V4처럼 짧은 영역을 증폭한 16S amplicon에 BLAST 보정 기능을 적용하려면 대상 영역, 참조 DB, identity·coverage 기준 및 가능한 분류 해상도를 추가로 검토·검증해야 합니다. 현재 기본값을 그대로 적용할 수 있다고 가정하지 않습니다. 관련 논의: [QIIME 2 포럼 — 16S 기반 Genus 분류](https://forum.qiime2.org/t/how-to-find-the-genus-level-from-bacteria-with-from-16s-method/33791/4?u=soyeon_kim).

### 2. Nextflow 및 내부 도구 환경·버전

Nextflow는 분석 단계와 중간 파일을 관리합니다. 현재 설정은 **Singularity 컨테이너**에서 도구를 실행하므로 컨테이너 내부 도구를 호스트에 각각 설치할 필요가 없습니다. 처음 사용한다면 Nextflow [공식 설치 안내](https://docs.seqera.io/nextflow/install)와 [명령행 안내](https://docs.seqera.io/nextflow/cli)를 참고하세요.

| 구성 요소 | 버전·환경 | 역할 |
| --- | --- | --- |
| Nextflow | 26.04.2, DSL2; 실행 확인 버전 | 워크플로 실행·재개 |
| Java | Temurin OpenJDK 17.0.10; 실행 확인 버전 | Nextflow 실행 환경 |
| Singularity CE | 3.9.2; 실행 확인 버전 | 컨테이너 실행 |
| QIIME 2 Amplicon | **2025.7** | QIIME artifact 처리·BLAST 분류 |
| QIIME 2 / q2cli / feature-classifier | **2025.7.0** | QIIME 프레임워크·명령행·분류 플러그인 |
| QIIME 이미지의 Python | 3.10.14 | 정규화·후가공 |
| Native BLAST 이미지 빌드 정의 | Python 3.10, BLAST 2.16.0, TaxonKit 0.18.0, csvtk 0.30.0 | 검색·TaxID 계통 확인·표 처리 |
| Native 이미지의 Python 패키지 지정값 | pandas 2.2.3, NumPy 1.26.4, PyYAML 6.0.2 | 분류 데이터 처리 |

현재 **지원 기준은 QIIME 2 2025.7**이며 다른 QIIME 버전은 미검증입니다. 워크플로 테스트는 정규화, QZA import·유효성 검사, QZV 생성, 후가공을 확인하며 QIIME BLAST 전체 검색은 포함하지 않습니다. Native 이미지 버전은 빌드 정의에 지정된 값입니다.

| 컨테이너 옵션 | 기본 로컬 경로 |
| --- | --- |
| `--qiime_sif` | `/data/software/singularity/qiime2_amplicon_2025.7.sif` |
| `--blast_taxonomy_sif` | `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif` |

다른 환경에서는 위 옵션으로 경로를 바꾸세요. SIF 파일 자체는 Git에 포함하지 않습니다. QIIME 이미지는 `quay.io/qiime2/amplicon:2025.7`에서 받을 수 있고, 직접 만든 native 이미지는 [빌드 정의](containers/blast_taxonomy.def)를 제공합니다. [컨테이너 준비 방법](docs/wiki/Containers.md)을 참고하세요. 기본 자원은 BLAST 단계 각각 8 CPU/32 GB, QIIME 입출력·taxonomy 처리 단계 1 CPU/4 GB입니다.

### 3. 지원 기능

#### 실행 모드와 입력

| 모드 | 필요한 입력 | 수행 기능 |
| --- | --- | --- |
| `--backend native` | 대표 서열 QZA, taxonomy QZA, 포맷된 BLAST DB prefix, NCBI taxdump | blastn 검색 → 후보 선별 → TaxonKit 계통 확인 → 원본 taxonomy 보정 → 최종 후가공 |
| `--backend qiime` | 대표 서열 QZA, taxonomy QZA, 참조 서열·taxonomy QZA | QIIME `classify-consensus-blast` 분류 → 최종 후가공 |
| `--normalize_only true` | taxonomy QZA 또는 TSV 하나 | BLAST 없이 정규화 → QZA/QZV 생성 → 최종 후가공 |
| `--postprocess_only true` | taxonomy QZA 또는 TSV 하나 | BLAST 없이 최종 후가공만 실행 |

대표 서열은 `FeatureData[Sequence]`, taxonomy는 `FeatureData[Taxonomy]` 타입을 사용합니다. BLAST 없는 모드에서는 `--taxonomy_qza`와 `--taxonomy_tsv` 중 하나만 지정하며, 정규화 전용·후가공 전용 옵션을 동시에 사용하지 않습니다.

현재 QIIME backend는 독립적인 BLAST 분류를 수행하며 **원본 taxonomy와의 보정 및 native 보정 보고서 생성은 지원하지 않습니다.** 참조 서열과 분류표의 ID는 일치해야 하며, 학습된 sklearn classifier QZA 자체를 입력하는 방식은 아닙니다.

#### Native BLAST 및 원본 taxonomy 보정

저장소 디렉터리에서 입력 경로를 바꿔 실행하세요.

```bash
nextflow -C nextflow.config run main.nf \
  --backend native \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile silva138 \
  --blast_db /path/to/blast_db_prefix \
  --taxdump_dir /path/to/taxdump \
  --blast_reconcile_mode species_missing_rescue \
  --blast_lineage_policy species_only \
  --outdir results/native -work-dir work/native -resume
```

`--blast_db`에는 디렉터리나 `.nin` 파일이 아닌 DB **prefix**를 넣습니다. `-C`는 저장소 설정 선택, `-work-dir`는 중간 작업 위치, `-resume`은 재사용 가능한 작업의 재개 옵션입니다. 재개하려면 작업 디렉터리와 Nextflow 캐시를 유지하세요.

| `--blast_reconcile_mode` | 동작 |
| --- | --- |
| `species_missing_rescue` (기본값) | 기존 Species는 유지하고 기준을 통과한 모호하지 않은 hit로 미분류 Species 보완 |
| `species_missing_top1_rescue` | 기존 Species는 유지하고 top1/top2가 모호해도 기준을 통과한 top1 허용 |
| `same_genus_only` | 비어 있지 않은 명시적 Genus가 일치하고 hit가 모호하지 않으면 Species 교체 허용 |

기본 `--blast_lineage_policy species_only`는 Domain~Genus를 유지하며 모든 모드에 Genus 일치 조건을 적용합니다. 대소문자는 구분하지 않지만 DB 고유 접미사는 제거하지 않습니다. 상위 계통까지 교체하려면 `--blast_lineage_policy blast_lineage`를 명시하세요. Confidence는 원래 QIIME 값을 유지하며 BLAST 보정 신뢰도를 새로 계산하지 않습니다.

| 기준 | 후보 선별 | 최종 Species 교체 |
| --- | --- | --- |
| Identity | `--blast_min_pident 99` | `--blast_species_min_pident 99` |
| Query coverage | `--blast_min_qcovus 80` | `--blast_species_min_qcovus 99` |
| E-value | `--blast_max_evalue 1e-10` | `--blast_species_max_evalue 1e-10` |

기본 검색 대상 수는 20(`--blast_retrieval_n`), 보존 후보 수는 5(`--blast_top_n`)입니다. 후보 선별이 먼저 실행되므로 Species 기준만 낮춰도 제외된 후보가 복원되지는 않습니다. 모호성 검사는 top1·top2만 비교하며 후보가 하나면 동률 충돌을 확인할 수 없습니다. 상세 선별 규칙과 보고서 해석은 [상세 사용법](docs/wiki/Usage.md)에 있습니다.

#### QIIME BLAST 분류

```bash
nextflow -C nextflow.config run main.nf \
  --backend qiime \
  --repseq_qza /path/to/rep-seqs.qza \
  --taxonomy_qza /path/to/taxonomy.qza \
  --reference_reads /path/to/ref-seqs.qza \
  --reference_taxonomy /path/to/ref-taxonomy.qza \
  --outdir results/qiime -resume
```

QIIME는 `--blast_top_n`을 maxaccepts로 사용하고 최소 consensus는 0.51입니다. Identity·coverage는 백분율로 입력합니다. QIIME coverage는 HSP별 `query-cov`, native는 `qcovus`이므로 같은 측정값이 아닙니다. Native Species 교체 기준은 이 backend에 적용되지 않습니다.

#### BLAST 없는 정규화·후가공

```bash
nextflow -C nextflow.config run main.nf \
  --normalize_only true \
  --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile gtdb_r220 --outdir results/normalized

nextflow -C nextflow.config run main.nf \
  --postprocess_only true \
  --taxonomy_tsv /path/to/taxonomy.tsv \
  --taxonomy_profile silva138 --outdir results/postprocessed
```

DB에 따라 `silva138`, `gtdb_r220`, `gg2`를 선택합니다. 기본 `auto`는 DB를 추측하지 않고 입력 계급 접두사를 보존하며 generic·UNITE·EUKARYOME 프로필도 제공합니다. 정규화는 빈 계급의 위치와 DB 고유 이름을 유지합니다. 두 Python 스크립트는 Python 3와 pandas만으로 독립 실행할 수도 있습니다. [DB별 규칙](docs/taxonomy_profiles.md) · [독립 실행 방법](docs/wiki/Usage.md)

모든 실행 모드는 마지막에 같은 보고용 TSV를 생성합니다.

| 분류 상태 | 최종 보고용 값 |
| --- | --- |
| Genus가 `Bacillus`, Species가 비어 있음 | Species = **`g_Bacillus`** |
| Family가 `Bacillaceae`, Genus·Species가 비어 있음 | 두 칸 모두 **`f_Bacillaceae`** |
| 기존 분류명이 있음 | GTDB/GG2 고유 접미사를 포함해 유지 |
| 사용할 상위 분류가 없음 | `Unassigned` |

가장 가까운 실제 상위 분류를 근거로 채우며 **`s__g_Bacillus`처럼 목적지 계급 접두사를 덧붙이지 않습니다.** 보고용 표기이며 새 분류를 확정한다는 뜻은 아닙니다. 같은 결과를 다시 후가공해도 표는 바뀌지 않습니다. QIIME artifact와 별도 산출물이며, Domain은 표의 기존 구조와 호환되도록 `Kingdom` 열에 저장하고 `Top_Rank_Prefix=d`로 표시합니다.

#### 출력 및 테스트

| 모드 | 주요 출력 |
| --- | --- |
| 공통 | `postprocessed/` 아래 `taxonomy_postprocessed.tsv`, `taxonomy_postprocess_changes.tsv`, `taxonomy_postprocess_summary.json` |
| Native | `taxonomy_blast.qza`, `taxonomy_blast_report.tsv`, `taxonomy_blast_changed.tsv`, `taxonomy_blast_evidence.tsv` |
| QIIME | `taxonomy_qiime_blast.qza`, `.qzv`, `.tsv`, `blast_search_results.qza` |
| 정규화 전용 | `normalized/`의 TSV, `taxonomy_normalized.qza`, `taxonomy_normalized.qzv` |

Native의 원시 hit·후보·lineage·import TSV·QZV는 작업 디렉터리에 남습니다. Native의 `changed` 표는 판단 상태로 선택한 행이므로 실제 문자열 변경만을 의미하지 않습니다. 전체 판단 근거는 evidence 표에서, 최종 후가공의 실제 칸별 변경은 `taxonomy_postprocess_changes.tsv`에서 확인하세요.

```bash
nextflow -C nextflow.config run main.nf -profile test
nextflow -C nextflow.config run main.nf -profile test_postprocess
```

내장 합성 입력으로 실제 결과와 예상 표를 비교합니다. `test`는 정규화와 QIIME artifact 생성까지, `test_postprocess`는 후가공 경로를 검사합니다. BLAST DB는 필요하지 않습니다. 결과가 다르면 워크플로가 실패하고, 성공하면 `<outdir>/test/test_report.txt`를 생성합니다. [테스트 상세](docs/wiki/Tests.md)

### 4. 추가 예정 기능

**외부 native BLAST 대신 QIIME 2 `feature-classifier`의 BLAST 분류 결과를 이용해 원본 taxonomy를 보정하는 기능**을 추가할 예정입니다. QIIME 참조 서열·taxonomy artifact를 사용하며, 현재 제공하는 독립 BLAST 분류에 원본과의 비교·보정 단계를 연결할 계획입니다.

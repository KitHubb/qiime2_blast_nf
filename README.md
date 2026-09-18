# QIIME_blast

[English](#english) | [한국어](#한국어) · [Detailed documentation / 상세 문서](docs/wiki/Home.md)

## English

### 1. Purpose

QIIME_blast is a Nextflow DSL2 pipeline that uses BLAST to correct QIIME `taxonomy.qza` results from full-length 16S rRNA ASV analysis.
It supports SILVA 138, GTDB r220 and GG2 taxonomy formats.
It can also process Unassigned or NA values for downstream analysis without running BLAST.

Applying BLAST correction to short-region 16S amplicons such as V3–V4 or V4 requires further checks of the target region, reference DB, identity and coverage thresholds, and the taxonomic resolution that the region allows. [QIIME 2 Forum: genus-level classification from 16S](https://forum.qiime2.org/t/how-to-find-the-genus-level-from-bacteria-with-from-16s-method/33791/4?u=soyeon_kim).

### 2. Nextflow and tool environment

Nextflow manages the analysis steps and their intermediate files. The current configuration runs tools in Singularity containers, so tools inside the images do not need separate host installations. For beginners: [Nextflow installation](https://docs.seqera.io/nextflow/install) · [Command-line guide](https://docs.seqera.io/nextflow/cli).

| Component | Version / environment | Role |
| --- | --- | --- |
| Nextflow | 26.04.2, DSL2; tested version | Workflow execution and resuming |
| Java | Temurin OpenJDK 17.0.10; tested version | Nextflow runtime |
| Singularity CE | 3.9.2; tested version | Container execution |
| QIIME 2 Amplicon | 2025.7 | QIIME artifact handling and BLAST classification |
| Native BLAST image recipe | Python 3.10, BLAST 2.16.0, TaxonKit 0.18.0, csvtk 0.30.0, pandas 2.2.3, NumPy 1.26.4, PyYAML 6.0.2 | Search, TaxID lineage resolution and table processing |

The supported QIIME version is 2025.7. Other versions have not been tested.
The native image tool versions listed above are specified in its build recipe.

The container files are stored at these paths in our lab:

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

Representative sequences must be `FeatureData[Sequence]` and taxonomy must be `FeatureData[Taxonomy]`. In no-BLAST modes, provide exactly one of `--taxonomy_qza` or `--taxonomy_tsv`; the two no-BLAST modes are mutually exclusive. The QIIME backend currently does not reconcile its classification with the original taxonomy or produce native reconciliation reports.

#### Native BLAST and reconciliation

Run from the repository directory with your input paths:

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

Set `--blast_db` to the database prefix rather than a directory or `.nin` file.
`-C` selects the configuration file, and `-work-dir` sets the directory for intermediate task files.

##### BLAST correction options

There are three correction modes:

| `--blast_reconcile_mode` | Behavior |
| --- | --- |
| `species_missing_rescue` (default) | Keep assigned Species. Fill missing Species from a qualifying BLAST hit, unless the top two hits tie but identify different species. |
| `species_missing_top1_rescue` | Keep assigned Species. Fill missing Species from the first qualifying hit, even when the top two hits tie. |
| `same_genus_only` | Allow replacement of an assigned Species when the original and BLAST genera are both assigned and match. Cutoffs must pass, and tied hits must not identify different species. |

The default policy, `--blast_lineage_policy species_only`, preserves Domain through Genus and requires genus agreement in every mode. Genus comparison ignores case but preserves DB-specific suffixes. Use `--blast_lineage_policy blast_lineage` to explicitly allow upper-lineage replacement.

`species_only` is the default, so you can omit it from the command. The correction mode controls when Species can change; `blast_lineage_policy` controls which ranks can change. Unlike the default correction mode, `same_genus_only` can replace an already assigned Species when the genera match.

##### BLAST result thresholds

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

QIIME BLAST classification is available; using its results to correct the original taxonomy is not yet supported. Supplying the reference sequences and taxonomy used to train a QIIME naive Bayes classifier lets you compare probability-based and alignment-based classification against the same DB. The two methods can still produce different results. If native BLAST uses a different reference DB, account for that difference as well.

#### Normalization and postprocessing without BLAST

This mode processes missing values in the taxonomy table without BLAST correction. Normalization preserves rank positions; postprocessing fills NA values with names from higher ranks.

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

All execution modes produce the same final report format.

##### Postprocessing examples

| Taxonomy state | Final reporting value |
| --- | --- |
| Genus `Bacillus`, Species missing | Species = `g_Bacillus` |
| Family `Bacillaceae`, Genus and Species missing | Both = `f_Bacillaceae` |
| Assigned name | Preserve it, including GTDB/GG2 suffixes |
| No assigned ancestor | `Unassigned` |

NA values are filled using the nearest assigned higher rank.

#### Nextflow outputs

| Mode | Main published outputs |
| --- | --- |
| All modes | `postprocessed/taxonomy_postprocessed.tsv`, `taxonomy_postprocess_changes.tsv`, `taxonomy_postprocess_summary.json` (all under `postprocessed/`) |
| Native | `taxonomy_blast.qza`, `taxonomy_blast_report.tsv`, `taxonomy_blast_changed.tsv`, `taxonomy_blast_evidence.tsv` |
| QIIME | `taxonomy_qiime_blast.qza`, `.qzv`, `.tsv`, and `blast_search_results.qza` |
| Normalize only | `normalized/` TSVs, `taxonomy_normalized.qza`, `taxonomy_normalized.qzv` |

Native raw hits, candidates, lineage, import TSV and QZV remain in task directories. The native `changed` table contains rows selected by decision status and is not a strict before/after difference table; inspect the evidence table for full decisions. The final postprocessing change log records actual changed cells.

#### Test run

```bash
nextflow -C nextflow.config run main.nf -profile test
nextflow -C nextflow.config run main.nf -profile test_postprocess
```

These profiles use bundled synthetic inputs and check output against an expected table. `test` includes normalization and QIIME artifact generation; `test_postprocess` checks final postprocessing directly. Neither needs a BLAST DB. A mismatch fails the workflow; success writes `<outdir>/test/test_report.txt`. [Test details](docs/wiki/Tests.md)

## 한국어

### 1. 도구의 목적

QIIME_blast는 full-length 16S rRNA ASV 분석에서 얻은 QIIME `taxonomy.qza`를 BLAST 기반으로 보정하는 Nextflow DSL2 파이프라인입니다.
Reference는 SILVA 138·GTDB r220·GG2 형식을 지원합니다.
BLAST 보정 없이도 taxonomy 결과의 Unassigned나 NA 값을 정리해 downstream 분석에 사용할 수 있습니다.

V3–V4, V4처럼 짧은 영역을 증폭한 16S amplicon에 BLAST 보정 기능을 적용하려면 대상 영역, 참조 DB, identity·coverage 기준 및 해당 영역에서 얻을 수 있는 분류 해상도를 추가로 검토·검증해야 합니다. [QIIME 2 포럼: 16S 기반 Genus 분류](https://forum.qiime2.org/t/how-to-find-the-genus-level-from-bacteria-with-from-16s-method/33791/4?u=soyeon_kim).

### 2. Nextflow 및 내부 도구 환경·버전

Nextflow는 분석 단계와 중간 파일을 관리합니다. 현재 설정은 Singularity 컨테이너에서 도구를 실행하므로 컨테이너 내부 도구를 호스트에 각각 설치할 필요가 없습니다. 처음 사용한다면 Nextflow [공식 설치 안내](https://docs.seqera.io/nextflow/install)와 [명령행 안내](https://docs.seqera.io/nextflow/cli)를 참고하세요.

| 구성 요소 | 버전·환경 | 역할 |
| --- | --- | --- |
| Nextflow | 26.04.2, DSL2; 실행 확인 버전 | 워크플로 실행·재개 |
| Java | Temurin OpenJDK 17.0.10; 실행 확인 버전 | Nextflow 실행 환경 |
| Singularity CE | 3.9.2; 실행 확인 버전 | 컨테이너 실행 |
| QIIME 2 Amplicon | 2025.7 | QIIME artifact 처리·BLAST 분류 |
| Native BLAST 이미지 빌드 정의 | Python 3.10, BLAST 2.16.0, TaxonKit 0.18.0, csvtk 0.30.0, pandas 2.2.3, NumPy 1.26.4, PyYAML 6.0.2 | 검색·TaxID 계통 확인·표 처리 |

현재 지원 기준은 QIIME 2 2025.7이며, 다른 QIIME 버전은 검증하지 않았습니다.
위에 언급한 Native 이미지 내부 도구의 버전은 빌드 정의에 지정된 값입니다.

연구실 내 파일 위치는 다음과 같습니다.

| 컨테이너 옵션 | 기본 로컬 경로 |
| --- | --- |
| `--qiime_sif` | `/data/software/singularity/qiime2_amplicon_2025.7.sif` |
| `--blast_taxonomy_sif` | `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif` |

외부 환경에서 사용할 때는 위 옵션으로 경로를 바꿀 수 있습니다.
SIF 파일 자체는 Git에 포함하지 않지만, QIIME 이미지는 `quay.io/qiime2/amplicon:2025.7`에서 받을 수 있고,
직접 만든 native 이미지의 [빌드 정의](containers/blast_taxonomy.def)도 제공합니다. [컨테이너 준비 방법](docs/wiki/Containers.md)을 참고하세요.
기본 자원은 BLAST 단계 각각 8 CPU/32 GB, QIIME 입출력·taxonomy 처리 단계 1 CPU/4 GB입니다.

### 3. 지원 기능

#### 실행 모드와 입력

| 모드 | 필요한 입력 | 수행 기능 |
| --- | --- | --- |
| `--backend native` | 대표 서열 QZA, taxonomy QZA, 포맷된 BLAST DB prefix, NCBI taxdump | blastn 검색 → 후보 선별 → TaxonKit 계통 확인 → 원본 taxonomy 보정 → 최종 후가공 |
| `--backend qiime` | 대표 서열 QZA, taxonomy QZA, 참조 서열·taxonomy QZA | QIIME `classify-consensus-blast` 분류 → 최종 후가공 |
| `--normalize_only true` | taxonomy QZA 또는 TSV 하나 | BLAST 없이 정규화 → QZA/QZV 생성 → 최종 후가공 |
| `--postprocess_only true` | taxonomy QZA 또는 TSV 하나 | BLAST 없이 최종 후가공만 실행 |

대표 서열은 `FeatureData[Sequence]`, taxonomy는 `FeatureData[Taxonomy]` 타입을 사용합니다.
BLAST 없는 모드에서는 `--taxonomy_qza`와 `--taxonomy_tsv` 중 하나만 지정하며, 정규화 전용·후가공 전용 옵션을 동시에 사용하지 않습니다.

💡 현재 QIIME backend는 BLAST 분류를 지원하지만, 그 결과로 원본 taxonomy를 보정하거나 native 보정 보고서를 만드는 기능은 아직 지원하지 않습니다.

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

`--blast_db`에는 디렉터리나 `.nin` 파일이 아닌 DB prefix를 입력합니다.
`-C`는 저장소 설정 파일을, `-work-dir`는 중간 작업 파일을 저장할 위치를 지정합니다.

##### BLAST 보정 옵션

taxonomy 보정에는 다음 세 가지 옵션을 사용할 수 있습니다.

| `--blast_reconcile_mode` | 동작 |
| --- | --- |
| `species_missing_rescue` (기본값) | 이미 분류된 Species는 유지합니다. Species가 비어 있으면 기준을 통과한 BLAST 결과로 채우되, 상위 두 hit가 동률인데 Species가 다르면 유지합니다. |
| `species_missing_top1_rescue` | 이미 분류된 Species는 유지합니다. Species가 비어 있으면 상위 두 hit가 동률이어도 기준을 통과한 첫 번째 hit로 채웁니다. |
| `same_genus_only` | 원본과 BLAST의 Genus가 모두 분류되어 있고 서로 같으면 기존 Species도 바꿀 수 있습니다. 수치 기준을 통과해야 하며, 동률 hit의 Species가 다르면 유지합니다. |

기본 정책인 `--blast_lineage_policy species_only`는 Domain~Genus를 유지하며 모든 모드에 Genus 일치 조건을 적용합니다.
대소문자는 구분하지 않지만 DB 고유 접미사는 제거하지 않습니다. 상위 계통까지 교체하려면 `--blast_lineage_policy blast_lineage`를 명시하세요.
`species_only`는 기본값이므로 따로 입력하지 않아도 됩니다. 위의 보정 모드는 Species를 언제 바꿀지 정하고, `blast_lineage_policy`는 어느 계급까지 바꿀지 정합니다. `same_genus_only`는 Genus가 같을 때 이미 분류된 Species도 바꿀 수 있다는 점에서 기본 모드와 다릅니다.

##### BLAST 결과의 사용 기준

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

현재 QIIME BLAST 분류는 지원하며, 그 결과로 원본 taxonomy를 보정하는 기능은 아직 지원하지 않습니다. QIIME naive Bayes classifier의 학습에 사용한 참조 서열과 taxonomy를 넣으면 같은 DB를 기준으로 확률 기반 분류와 alignment 기반 분류를 비교할 수 있습니다. 같은 DB를 써도 두 방법의 결과가 같다는 뜻은 아닙니다. Native BLAST에서 다른 reference DB를 사용한다면 DB 차이도 감안해야 합니다.

#### BLAST 없는 정규화·후가공
BLAST 결과로 보정하지 않고 taxonomy table의 빈값을 정리하는 방법입니다. 정규화는 계급 위치를 유지하고, 후가공은 NA 값을 상위 분류명으로 채웁니다.

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

DB에 따라 `silva138`, `gtdb_r220`, `gg2`를 선택합니다. 기본 `auto`는 DB를 추측하지 않고 입력 계급 접두사를 보존하며 generic·UNITE·EUKARYOME 프로필도 제공합니다.
정규화는 빈 계급의 위치와 DB 고유 이름을 유지합니다. 두 Python 스크립트는 Python 3와 pandas만으로 독립 실행할 수도 있습니다. [DB별 규칙](docs/taxonomy_profiles.md) · [독립 실행 방법](docs/wiki/Usage.md)

모든 실행 모드는 마지막에 같은 보고용 TSV를 생성합니다.

##### 후가공 결과 예시

| 분류 상태 | 최종 보고용 값 |
| --- | --- |
| Genus가 `Bacillus`, Species가 비어 있음 | Species = `g_Bacillus` |
| Family가 `Bacillaceae`, Genus·Species가 비어 있음 | 두 칸 모두 `f_Bacillaceae` |
| 기존 분류명이 있음 | GTDB/GG2 고유 접미사를 포함해 유지 |
| 사용할 상위 분류가 없음 | `Unassigned` |

NA 값은 가장 가까운 상위 분류를 기준으로 채웁니다.

#### Nextflow 출력 결과

| 모드 | 주요 출력 |
| --- | --- |
| 공통 | `postprocessed/` 아래 `taxonomy_postprocessed.tsv`, `taxonomy_postprocess_changes.tsv`, `taxonomy_postprocess_summary.json` |
| Native | `taxonomy_blast.qza`, `taxonomy_blast_report.tsv`, `taxonomy_blast_changed.tsv`, `taxonomy_blast_evidence.tsv` |
| QIIME | `taxonomy_qiime_blast.qza`, `.qzv`, `.tsv`, `blast_search_results.qza` |
| 정규화 전용 | `normalized/`의 TSV, `taxonomy_normalized.qza`, `taxonomy_normalized.qzv` |

Native의 원시 hit·후보·lineage·import TSV·QZV는 작업 디렉터리에 남습니다. Native의 `changed` 표에는 판단 상태에 따라 선택한 행이 들어가므로 실제 문자열이 바뀌지 않은 행도 포함될 수 있습니다. 전체 판단 근거는 evidence 표에서, 최종 후가공의 실제 칸별 변경은 `taxonomy_postprocess_changes.tsv`에서 확인하세요.

#### Test run

```bash
nextflow -C nextflow.config run main.nf -profile test
nextflow -C nextflow.config run main.nf -profile test_postprocess
```

내장 합성 입력으로 실제 결과와 예상 표를 비교합니다. `test`는 정규화와 QIIME artifact 생성까지, `test_postprocess`는 후가공 경로를 검사합니다.
BLAST DB는 필요하지 않습니다. 결과가 다르면 워크플로가 실패하고, 성공하면 `<outdir>/test/test_report.txt`를 생성합니다. [테스트 상세](docs/wiki/Tests.md)

### 4. 추가 예정 기능

QIIME 2 `feature-classifier`의 BLAST 분류 결과를 이용해 원본 taxonomy를 보정하는 기능을 추가할 예정입니다.
QIIME 참조 서열·taxonomy artifact를 사용하며, 현재 제공하는 독립 BLAST 분류에 원본과의 비교·보정 단계를 연결할 계획입니다.

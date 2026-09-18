# QIIME_blast

[English](#english) | [한국어](#한국어) · [Detailed guide / 상세 문서](docs/wiki/Home.md)

## English

Nextflow workflow for BLAST taxonomy analysis, normalization and final reporting.

- Native BLAST can rescue missing Species while preserving the original upper ranks.
- Normalize or postprocess existing taxonomy **without BLAST**.
- SILVA 138, GTDB r220 and GG2 profiles preserve rank positions and reference names.
- Final missing ranks inherit their nearest assigned ancestor: **`g_Bacillus`**, or **`f_Bacillaceae`** when only Family is known. Assigned names remain unchanged.

### Requirements

Nextflow, compatible Java and Singularity. **Supported/tested environment: QIIME 2 Amplicon 2025.7 (QIIME 2, q2cli and feature-classifier 2025.7.0).** Other releases are not yet verified; workflow tests cover normalization and postprocessing, not an end-to-end QIIME BLAST search.

New to Nextflow? See the official [installation](https://docs.seqera.io/nextflow/install) and [command-line](https://docs.seqera.io/nextflow/cli) guides. SIF files are not committed; see [container setup](docs/wiki/Containers.md) for the official QIIME image and native BLAST build recipe.

### Run

From this repository directory, replace the example paths with your inputs:

```bash
# Final postprocessing without BLAST
nextflow -C nextflow.config run main.nf \
  --postprocess_only true --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile silva138 --outdir results/silva

# Small workflow test: normalization, QIIME artifacts and final report
nextflow -C nextflow.config run main.nf -profile test
```

| Task | Options |
| --- | --- |
| Normalize and postprocess without BLAST | `--normalize_only true` with taxonomy QZA or TSV |
| Postprocess only | `--postprocess_only true` with taxonomy QZA or TSV |
| Native BLAST and reconciliation | `--backend native --repseq_qza … --taxonomy_qza … --blast_db … --taxdump_dir …` |
| QIIME BLAST classification | `--backend qiime --repseq_qza … --taxonomy_qza … --reference_reads … --reference_taxonomy …` |

Use `--taxonomy_tsv` for TSV input and `gtdb_r220` or `gg2` for those references. Final report: `<outdir>/postprocessed/taxonomy_postprocessed.tsv`, with a per-cell change log and summary. The report is separate from QIIME artifacts. [Options and outputs](docs/wiki/Usage.md) · [Tests](docs/wiki/Tests.md)

---

## 한국어

BLAST 분류 분석, taxonomy 정규화와 최종 보고용 후가공을 수행하는 Nextflow 파이프라인입니다.

- Native BLAST로 기존 상위 분류를 유지하면서 미분류 Species를 보완합니다.
- **BLAST 없이도** 기존 taxonomy를 정규화하거나 후가공할 수 있습니다.
- SILVA 138·GTDB r220·GG2의 계급 위치와 고유 분류명을 보존합니다.
- 빈칸은 가장 가까운 상위 분류로 채웁니다. Species는 **`g_Bacillus`**, Family까지만 알면 **`f_Bacillaceae`**가 됩니다. `s__`를 추가하지 않습니다.

### 실행 환경

Nextflow, 호환 Java, Singularity가 필요합니다. **지원·검증 기준: QIIME 2 Amplicon 2025.7 (QIIME 2·q2cli·feature-classifier 2025.7.0).** 다른 버전은 미검증이며, 워크플로 테스트 범위는 정규화·후가공입니다. QIIME BLAST 전체 검색은 포함하지 않습니다.

처음 사용한다면 Nextflow [공식 설치 안내](https://docs.seqera.io/nextflow/install)와 [명령행 안내](https://docs.seqera.io/nextflow/cli)를 참고하세요. SIF 파일 대신 공식 이미지 다운로드 방법과 native BLAST 빌드 정의를 제공합니다. [컨테이너 준비](docs/wiki/Containers.md)

### 실행

저장소 디렉터리에서 입력 경로를 바꿔 실행하세요.

```bash
# BLAST 없이 최종 후가공
nextflow -C nextflow.config run main.nf \
  --postprocess_only true --taxonomy_qza /path/to/taxonomy.qza \
  --taxonomy_profile silva138 --outdir results/silva

# 소규모 워크플로 테스트: 정규화, QIIME artifact, 최종 표
nextflow -C nextflow.config run main.nf -profile test
```

| 목적 | 옵션 |
| --- | --- |
| BLAST 없이 정규화와 후가공 | `--normalize_only true` + taxonomy QZA/TSV |
| 후가공만 수행 | `--postprocess_only true` + taxonomy QZA/TSV |
| Native BLAST 및 보정 | `--backend native --repseq_qza … --taxonomy_qza … --blast_db … --taxdump_dir …` |
| QIIME BLAST 분류 | `--backend qiime --repseq_qza … --taxonomy_qza … --reference_reads … --reference_taxonomy …` |

TSV 입력은 `--taxonomy_tsv`, 다른 DB는 `--taxonomy_profile gtdb_r220` 또는 `gg2`를 사용하세요. 최종 표는 `<outdir>/postprocessed/taxonomy_postprocessed.tsv`이며 변경 기록과 요약도 생성합니다. QIIME artifact와 별도 파일입니다. [상세 옵션·출력](docs/wiki/Usage.md) · [테스트](docs/wiki/Tests.md)

## Planned feature / 추가 기능 예고

**English:** Taxonomy reconciliation after BLAST classification through QIIME 2's `feature-classifier`, using QIIME reference artifacts. The current QIIME backend classifies reads; reconciliation with the original taxonomy is planned.

**한국어:** 외부 native BLAST 대신 **QIIME 2 `feature-classifier` 기반 BLAST 분류 후 원본 taxonomy를 보정하는 기능**을 추가할 예정입니다. 현재 QIIME backend는 분류까지 지원하며, 원본과의 보정 단계는 개발 예정입니다.

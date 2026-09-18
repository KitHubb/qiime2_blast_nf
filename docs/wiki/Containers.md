# Containers and versions / 컨테이너와 버전

## QIIME 2

Supported/tested environment: QIIME 2 Amplicon **2025.7**, with QIIME 2, q2cli and feature-classifier **2025.7.0**. Versions were read with `qiime info` inside the configured SIF. Normalization, artifact import/validation, visualization and postprocessing have been exercised; a complete QIIME BLAST search is not part of the workflow tests. Other QIIME releases have not been verified.

The local QIIME SIF was built from `quay.io/qiime2/amplicon:2025.7`. Download it rather than committing a large binary:

```bash
mkdir -p containers
singularity pull containers/qiime2_amplicon_2025.7.sif docker://quay.io/qiime2/amplicon:2025.7
nextflow -C nextflow.config run main.nf -profile test \
  --qiime_sif "$PWD/containers/qiime2_amplicon_2025.7.sif"
```

Official reference: [QIIME 2 container guidance](https://forum.qiime2.org/t/how-to-install-qiime2-through-docker-did-you-met-this-issue/33496/9).

## Native BLAST runtime

The native backend uses a custom image. Its embedded build recipe is preserved at [containers/blast_taxonomy.def](../../containers/blast_taxonomy.def). It includes Python 3.10, BLAST 2.16.0, TaxonKit 0.18.0, csvtk 0.30.0, pandas 2.2.3, NumPy 1.26.4 and PyYAML 6.0.2.

On a system with Singularity build privileges (or an appropriately configured fakeroot builder):

```bash
sudo singularity build containers/blast_taxonomy.sif containers/blast_taxonomy.def
```

Pass `--blast_taxonomy_sif /absolute/path/to/blast_taxonomy.sif` for native runs. The definition was extracted from the existing working image; a fresh build has not been tested here, and dependency solving may vary over time. BLAST databases and NCBI taxdump are separate inputs and are not included in this image.

## What to distribute

Commit the source, test fixtures, configuration and build definition. `*.sif` remains ignored by Git. The official QIIME image can be downloaded; native users need either the recipe and build access or a separately hosted prebuilt image. A recipe reproduces the declared environment, not a byte-identical SIF. For exact binary reuse, publish a versioned SIF with a checksum via a registry or suitable artifact storage. No image upload has been performed.

## 한국어

- 지원·검증 기준은 **QIIME 2 Amplicon 2025.7 / QIIME 2·q2cli·feature-classifier 2025.7.0**입니다. 다른 버전의 호환성은 아직 확인하지 않았습니다.
- QIIME SIF는 위 공식 이미지에서 다운로드할 수 있으므로 Git에 함께 올릴 필요가 없습니다.
- Native BLAST는 직접 만든 이미지이므로 **빌드 정의 또는 별도 이미지 배포 경로가 필요**합니다. 기존 이미지에서 추출한 `containers/blast_taxonomy.def`를 포함했습니다.
- 빌드는 Singularity 빌드 권한이 있는 환경에서 수행하세요. 이번 변경에서 이미지를 새로 빌드하지는 않았으며, 정의 파일만으로 기존 SIF와 바이트 단위 동일성을 보장하지는 않습니다.
- BLAST DB와 taxdump는 별도로 준비해야 합니다. SIF 업로드는 수행하지 않았습니다.

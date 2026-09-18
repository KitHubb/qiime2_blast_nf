# Taxonomy profiles and source references

Reviewed 2026-09-18. These profiles normalize existing rank-labelled QIIME classification results; they do not reclassify sequences or translate between reference taxonomies. A profile label records the intended reference family, not proof of its version. All three supplied artifacts contain 26,045 ASVs. The SILVA artifact provenance contains SILVA 138.1; the GTDB artifact filename identifies R220. Do not infer the GG2 release number from its taxonomy suffixes.

## Official sources

- [SILVA release 138](https://www.arb-silva.de/documentation/release-138) and [138.1](https://www.arb-silva.de/documentation/release-1381/): SILVA-curated taxonomy, using GTDB as an additional curation resource since 138. This does not make SILVA names interchangeable with GTDB or NCBI names.
- [GTDB FAQ](https://gtdb.ecogenomic.org/faq) and [R220 release](https://gtdb.ecogenomic.org/stats/r220): alphabetic suffixes distinguish taxa; species names such as `Agrobacterium sp000192635` identify genome-based species clusters. They are not missing values.
- [Greengenes2 official site](https://greengenes2.ucsd.edu/) and [maintainer repository](https://github.com/biocore/greengenes2): taxonomy uses a GTDB-derived seed augmented with Living Tree Project information and tree decoration. See also the [official paper](https://www.nature.com/articles/s41587-023-01845-1). GG2 is not identical to a GTDB release.

## Rules implemented from sources and observed artifacts

| Profile | Top rank emitted | Names retained exactly |
| --- | --- | --- |
| `silva138` / `silva` | `d__` (Domain) | SILVA names, including organelle labels and unresolved labels from the reference |
| `gtdb_r220` / `gtdb` | `d__` (Domain) | Alphabetic suffixes, e.g. `Pseudomonas_E`, and `sp` followed by digits |
| `gg2` | `d__` (Domain) | Alphabetic/numeric suffixes, e.g. observed `Pseudomonas_E_647464`, without stripping or merging |
| `auto` / `generic` | Input `d__` or `k__` | Input names; no database/version guessing |
| `unite` | Input top-rank prefix | Rank parsing only; shared final reporting step fills missing cells |
| `eukaryome` | Input top-rank prefix | Input labels without UNITE parent propagation |

For the three supplied bacterial references, QIIME taxonomy is ordered Domain, Phylum, Class, Order, Family, Genus, Species (`d,p,c,o,f,g,s`). The wide table keeps its legacy `Kingdom` column for compatibility; for `d__` input that column stores **Domain**, not a separate biological Kingdom. `Top_Rank_Prefix` makes this explicit and allows reconciliation to preserve `d__`.

Normalization maps **prefixes**, never nonempty token positions. Missing ranks remain empty in the matrix and become prefix-only tokens (`p__`, `g__`, `s__`) in the serialized taxonomy. Internal gaps never move a lower rank upward. Completely unassigned rows remain `Unassigned`. Conflicting duplicate ranks (including incompatible `d__`/`k__`) or unprefixed taxonomy are rejected rather than silently discarded. All source names, whitespace inside names, case, suffixes, feature IDs and original Confidence are preserved, and unspecified `sp`/`sp.` labels are preserved at this stage. The final reporting step treats unspecified species as unresolved. Original strings and normalization actions remain in the evidence table.

An empty species is unresolved, not a taxon called `NA`. No parent names are inserted into the intermediate QIIME taxonomy. The final wide report applies the user-defined ancestor naming convention described in README: for example Species = `g_Bacillus`, without an `s__` wrapper. These are serialization and preservation rules, not claims that the databases define biological taxa in exactly the same way.

## BLAST reconciliation

The default `--blast_lineage_policy species_only` preserves source Domain through Genus. It adds a BLAST species only after the selected rescue policy passes **and** source/BLAST genera agree exactly (case-insensitive). GTDB/GG2 suffixes are not stripped to force a match. A genus mismatch retains the original taxonomy and is recorded in the evidence. This conservative gate avoids constructing a named NCBI species under a different GTDB/GG2 genus. It cannot prove species identity from sequence identity thresholds alone.

`--blast_lineage_policy blast_lineage` explicitly opts into the previous whole-lineage replacement behavior; its outputs can mix reference naming systems. BLAST Eukaryota is no longer automatically converted to Fungi. Retained rows always preserve seven positional rank slots. Resolved GTDB `spNNN` species and uppercase suffixes are not treated as missing. Original QIIME Confidence remains source evidence, not a probability assigned to the BLAST result.

## 한국어 안내

세 DB 모두 제공된 QZA에서 `d/p/c/o/f/g/s` 순서를 사용합니다. `d__`는 Domain이며, 기존 TSV 호환을 위해 표의 `Kingdom` 열에 저장하되 `Top_Rank_Prefix`와 출력 문자열에서는 `d__`를 유지합니다. 프로필은 DB 버전을 자동 검증하거나 이름을 다른 DB로 변환하는 옵션이 아닙니다.

GTDB의 `_E`, `sp000123456` 및 GG2의 `_E_647464` 같은 이름은 그대로 보존합니다. 빈 계급은 표에서는 빈칸, QIIME 문자열에서는 `g__; s__`처럼 위치를 유지합니다. 이 설명은 QIIME용 중간 산출물 기준입니다. 최종 보고용 표에서는 공통 후가공을 통해 빈 칸을 `g_Bacillus`, `f_Bacillaceae`처럼 채우며 앞에 `s__` 등을 덧붙이지 않습니다. BLAST 미실행 또는 미채택일 때도 이 원칙이 동일합니다.

기본 BLAST 정책은 상위 계급을 유지하며 genus가 일치할 때 species만 보충합니다. 이름 접미사를 지워 NCBI와 강제로 맞추지 않습니다. 전체 NCBI 계보로 교체하려면 `--blast_lineage_policy blast_lineage`를 명시해야 합니다.

## Validation on supplied artifacts

2026-09-18: normalized all 26,045 rows in each of SILVA, GTDB r220 and GG2 (78,135 total). Every feature ID, Confidence value and assigned reference name matched its source. All partially classified rows had seven rank slots; entirely unassigned rows remained `Unassigned`.

| Input | Rows | Empty species among assigned rows | Entirely unassigned |
| --- | ---: | ---: | ---: |
| SILVA | 26,045 | 26,037 | 8 |
| GTDB r220 | 26,045 | 13,787 | 1 |
| GG2 | 26,045 | 9,387 | 0 |

GTDB was also run through the actual normalization-only Nextflow branch with QIIME 2 Amplicon 2025.7. QZA import, maximum-level artifact validation and metadata QZV creation passed; the imported QZA retained all 26,045 feature IDs and rank positions. The earlier seven regression tests cover rank gaps, d/k handling, suffixes, unspecified species, standalone QZA input, duplicate IDs, optional Confidence, BLAST genus mismatch, species-only rescue and unchanged resolved species. Run them with `python3 -m unittest discover -s tests -v`.

Validation outputs were written under `/tmp/qiime-blast-update.ey1cpE`; the existing analysis result directories were not overwritten.

Reconciliation was also checked against all 26,045 SILVA rows using existing BLAST hit evidence: 14,391 species rescues, every source upper rank preserved, every retained row identical to normalized taxonomy, and no shifted rank slots. This differs from the previous 16,729 rescues because 2,338 genus mismatches are retained by the new species-only policy. No new BLAST search was performed.

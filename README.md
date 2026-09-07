# QIIME_blast

Standalone Nextflow workflow for applying two BLAST-based taxonomic assignments to 16S ASV representative sequences.

`--backend native` runs `blastn` against a formatted BLAST database and reconciles hits with the existing QIIME taxonomy. `--backend qiime` runs QIIME 2 `feature-classifier classify-consensus-blast` using reference sequence and taxonomy artifacts.

Native example:

```bash
nextflow run main.nf --backend native --repseq_qza rep-seqs.qza \
  --taxonomy_qza taxonomy.qza --blast_db /data/Reference/BLAST/16S/db \
  --taxdump_dir /data/Reference/BLAST/taxdump --outdir results/native
```

QIIME example:

```bash
nextflow run main.nf --backend qiime --repseq_qza rep-seqs.qza \
  --taxonomy_qza taxonomy.qza --reference_reads ref-seqs.qza \
  --reference_taxonomy ref-taxonomy.qza --outdir results/qiime
```

The native backend emits raw hits, selected candidates, BLAST taxonomy, reconciled taxonomy, and changed/report tables. The QIIME backend emits a taxonomy artifact, visualization, and exported TSV. A later integration step can normalize both outputs into one matrix and apply the same merge policy.

Inputs are QIIME 2 artifacts: `--repseq_qza` must contain `FeatureData[Sequence]`, and `--taxonomy_qza` must contain `FeatureData[Taxonomy]`. Filenames are arbitrary. Both are exported internally to FASTA/TSV under `results/inputs`; the QIIME backend uses the original sequence QZA directly. The existing taxonomy is currently used for reconciliation only by the native backend.

Identity and coverage parameters use percentages (e.g. 99 and 80); the QIIME backend converts these to proportions. QIIME coverage is per HSP, whereas native coverage uses qcovus.

The native BLAST container is stored separately from this Git repository at `/data/software/singularity/qiime_blast/blast_taxonomy_2026-06.sif`. Override it with `--blast_taxonomy_sif /path/to/container.sif`. QZA export and the QIIME backend use `--qiime_sif` (default: `/data/software/singularity/qiime2_amplicon_2025.7.sif`). Container images are not committed to Git.

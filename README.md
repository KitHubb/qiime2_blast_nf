# QIIME_blast

Standalone Nextflow workflow for applying two BLAST-based taxonomic assignments to 16S ASV representative sequences.

`--backend native` runs `blastn` against a formatted BLAST database and reconciles hits with the existing QIIME taxonomy. `--backend qiime` runs QIIME 2 `feature-classifier classify-consensus-blast` using reference sequence and taxonomy artifacts.

Native example:

```bash
nextflow run main.nf --backend native --repseq_fasta rep-seqs.fasta \
  --taxonomy_tsv taxonomy.tsv --blast_db /data/Reference/BLAST/16S/db \
  --taxdump_dir /data/Reference/BLAST/taxdump --outdir results/native
```

QIIME example:

```bash
nextflow run main.nf --backend qiime --repseq_fasta rep-seqs.fasta \
  --taxonomy_tsv taxonomy.tsv --reference_reads ref-seqs.qza \
  --reference_taxonomy ref-taxonomy.qza --outdir results/qiime
```

The native backend emits raw hits, selected candidates, BLAST taxonomy, reconciled taxonomy, and changed/report tables. The QIIME backend emits a taxonomy artifact, visualization, and exported TSV. A later integration step can normalize both outputs into one matrix and apply the same merge policy.

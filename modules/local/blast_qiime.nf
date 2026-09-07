process QIIME_BLAST {
    tag "qiime_consensus_blast"
    label 'qiime_blast'
    container params.qiime_sif
    publishDir params.outdir, mode: 'copy', overwrite: true
    input:
    path repseq
    path taxonomy
    path reference_reads
    path reference_taxonomy
    output:
    path '*.qza', emit: artifacts
    path '*.qzv', emit: visualizations
    path '*.tsv', emit: tables
    script:
    """
    set -euo pipefail
    qiime feature-classifier classify-consensus-blast --i-query ${repseq} --i-reference-reads ${reference_reads} --i-reference-taxonomy ${reference_taxonomy} --p-maxaccepts ${params.blast_top_n} --p-perc-identity ${params.blast_min_pident} --p-query-cover ${params.blast_min_qcovus} --p-min-consensus 0.51 --o-classification taxonomy_qiime_blast.qza
    qiime metadata tabulate --m-input-file taxonomy_qiime_blast.qza --o-visualization taxonomy_qiime_blast.qzv
    qiime tools export --input-path taxonomy_qiime_blast.qza --output-path taxonomy_export
    cp taxonomy_export/taxonomy.tsv taxonomy_qiime_blast.tsv
    """
}

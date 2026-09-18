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
    path 'taxonomy_qiime_blast.qza', emit: artifacts
    path 'blast_search_results.qza', emit: search_results
    path '*.qzv', emit: visualizations
    path '*.tsv', emit: tables
    path 'taxonomy_qiime_blast.tsv', emit: taxonomy_qiime
    script:
    def identity = (params.blast_min_pident as double) / 100.0
    def coverage = (params.blast_min_qcovus as double) / 100.0
    """
    set -euo pipefail
    export TMPDIR="\$PWD/qiime_tmp"
    export TMP="\$TMPDIR"
    export TEMP="\$TMPDIR"
    export NUMBA_CACHE_DIR="\$PWD/numba_cache"
    export MPLCONFIGDIR="\$PWD/matplotlib_cache"
    export XDG_CACHE_HOME="\$PWD/xdg_cache"
    mkdir -p "\$TMPDIR" "\$NUMBA_CACHE_DIR" "\$MPLCONFIGDIR" "\$XDG_CACHE_HOME"

    qiime feature-classifier classify-consensus-blast --i-query ${repseq} --i-reference-reads ${reference_reads} --i-reference-taxonomy ${reference_taxonomy} --p-maxaccepts ${params.blast_top_n} --p-perc-identity ${identity} --p-query-cov ${coverage} --p-evalue ${params.blast_max_evalue} --p-num-threads ${task.cpus} --p-min-consensus 0.51 --o-classification taxonomy_qiime_blast.qza --o-search-results blast_search_results.qza
    qiime metadata tabulate --m-input-file taxonomy_qiime_blast.qza --o-visualization taxonomy_qiime_blast.qzv
    qiime tools export --input-path taxonomy_qiime_blast.qza --output-path taxonomy_export
    cp taxonomy_export/taxonomy.tsv taxonomy_qiime_blast.tsv
    """
}

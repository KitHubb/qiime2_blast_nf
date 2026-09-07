process IMPORT_RECONCILED_TAXONOMY {
    tag 'import_reconciled_taxonomy'
    label 'qiime_export'
    container params.qiime_sif
    publishDir params.outdir, mode: 'copy', overwrite: true, pattern: 'taxonomy_blast.qza'

    input:
    path taxonomy_tsv

    output:
    path 'taxonomy_blast.qza', emit: taxonomy
    path 'taxonomy_blast.qzv', emit: visualization

    script:
    """
    export TMPDIR="\$PWD/qiime_tmp"
    export TMP="\$TMPDIR"
    export TEMP="\$TMPDIR"
    export NUMBA_CACHE_DIR="\$PWD/numba_cache"
    export MPLCONFIGDIR="\$PWD/matplotlib_cache"
    export XDG_CACHE_HOME="\$PWD/xdg_cache"
    mkdir -p "\$TMPDIR" "\$NUMBA_CACHE_DIR" "\$MPLCONFIGDIR" "\$XDG_CACHE_HOME"

    qiime tools import --type 'FeatureData[Taxonomy]' --input-format TSVTaxonomyFormat --input-path "${taxonomy_tsv}" --output-path taxonomy_blast.qza
    qiime tools validate taxonomy_blast.qza --level max
    qiime metadata tabulate --m-input-file taxonomy_blast.qza --o-visualization taxonomy_blast.qzv
    """
}

process NORMALIZE_TAXONOMY {
    tag "normalize:${params.taxonomy_profile}"
    label 'qiime_export'
    container params.qiime_sif
    publishDir params.outdir, mode: 'copy', overwrite: true

    input:
    path taxonomy

    output:
    path 'normalized/taxonomy_normalized.tsv', emit: table
    path 'normalized/taxonomy_normalized_qiime.tsv', emit: qiime_tsv
    path 'normalized/taxonomy_normalization_evidence.tsv', emit: evidence

    script:
    """
    python3 ${projectDir}/bin/normalize_qiime_taxonomy.py \
      --input "${taxonomy}" --output-dir normalized --profile ${params.taxonomy_profile}
    """
}

process IMPORT_NORMALIZED_TAXONOMY {
    tag 'import_normalized_taxonomy'
    label 'qiime_export'
    container params.qiime_sif
    publishDir params.outdir, mode: 'copy', overwrite: true

    input:
    path taxonomy_tsv

    output:
    path 'taxonomy_normalized.qza', emit: taxonomy
    path 'taxonomy_normalized.qzv', emit: visualization

    script:
    """
    export TMPDIR="\$PWD/qiime_tmp"
    export TMP="\$TMPDIR"
    export TEMP="\$TMPDIR"
    export NUMBA_CACHE_DIR="\$PWD/numba_cache"
    export MPLCONFIGDIR="\$PWD/matplotlib_cache"
    export XDG_CACHE_HOME="\$PWD/xdg_cache"
    mkdir -p "\$TMPDIR" "\$NUMBA_CACHE_DIR" "\$MPLCONFIGDIR" "\$XDG_CACHE_HOME"
    qiime tools import --type 'FeatureData[Taxonomy]' --input-format TSVTaxonomyFormat \
      --input-path "${taxonomy_tsv}" --output-path taxonomy_normalized.qza
    qiime tools validate taxonomy_normalized.qza --level max
    qiime metadata tabulate --m-input-file taxonomy_normalized.qza --o-visualization taxonomy_normalized.qzv
    """
}

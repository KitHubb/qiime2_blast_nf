process POSTPROCESS_TAXONOMY {
    tag "postprocess:${params.taxonomy_profile}"
    label 'qiime_export'
    container params.qiime_sif
    publishDir "${params.outdir}/postprocessed", mode: 'copy', overwrite: true

    input:
    path taxonomy

    output:
    path 'taxonomy_postprocessed.tsv', emit: table
    path 'taxonomy_postprocess_changes.tsv', emit: changes
    path 'taxonomy_postprocess_summary.json', emit: summary

    script:
    """
    python3 "${projectDir}/bin/postprocess_taxonomy.py" \
      --input "${taxonomy}" --output-dir . --profile ${params.taxonomy_profile}
    """
}

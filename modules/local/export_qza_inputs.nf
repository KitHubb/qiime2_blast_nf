process EXPORT_QZA_INPUTS {
    tag 'export_qza_inputs'
    label 'qiime_export'
    container params.qiime_sif
    publishDir "${params.outdir}/inputs", mode: 'copy'

    input:
    path repseq_qza, stageAs: 'repseq_input.qza'
    path taxonomy_qza, stageAs: 'taxonomy_input.qza'

    output:
    path 'repseq_export/dna-sequences.fasta', emit: repseq_fasta
    path 'taxonomy_export/taxonomy.tsv', emit: taxonomy_tsv

    script:
    """
    qiime tools export --input-path "${repseq_qza}" --output-path repseq_export
    qiime tools export --input-path "${taxonomy_qza}" --output-path taxonomy_export
    """
}

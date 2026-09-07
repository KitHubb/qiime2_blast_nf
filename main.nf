nextflow.enable.dsl=2

include { NATIVE_BLAST } from './modules/local/blast_native'
include { QIIME_BLAST } from './modules/local/blast_qiime'
include { EXPORT_QZA_INPUTS } from './modules/local/export_qza_inputs'

workflow {
    if (!params.repseq_qza || !params.taxonomy_qza)
        error 'Provide --repseq_qza and --taxonomy_qza'
    repseq = file(params.repseq_qza, checkIfExists: true)
    taxonomy = file(params.taxonomy_qza, checkIfExists: true)
    if (!(params.backend in ['native', 'qiime']))
        error '--backend must be native or qiime'
    if (params.backend == 'native' && (!params.blast_db || !params.taxdump_dir))
        error 'Native backend requires --blast_db and --taxdump_dir'
    if (params.backend == 'qiime' && (!params.reference_reads || !params.reference_taxonomy))
        error 'QIIME backend requires --reference_reads and --reference_taxonomy'
    EXPORT_QZA_INPUTS(repseq, taxonomy)
    if (params.backend == 'native') {
        NATIVE_BLAST(EXPORT_QZA_INPUTS.out.repseq_fasta, EXPORT_QZA_INPUTS.out.taxonomy_tsv)
    } else if (params.backend == 'qiime') {
        reads = file(params.reference_reads, checkIfExists: true)
        ref_tax = file(params.reference_taxonomy, checkIfExists: true)
        QIIME_BLAST(repseq, EXPORT_QZA_INPUTS.out.taxonomy_tsv, reads, ref_tax)
    } else { error "--backend must be native or qiime" }
}

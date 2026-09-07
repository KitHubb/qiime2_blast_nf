nextflow.enable.dsl=2

include { NATIVE_BLAST } from './modules/local/blast_native'
include { QIIME_BLAST } from './modules/local/blast_qiime'

workflow {
    if (!params.repseq_fasta || !params.taxonomy_tsv)
        error 'Provide --repseq_fasta and --taxonomy_tsv'
    repseq = file(params.repseq_fasta, checkIfExists: true)
    taxonomy = file(params.taxonomy_tsv, checkIfExists: true)
    if (params.backend == 'native') {
        NATIVE_BLAST(repseq, taxonomy)
    } else if (params.backend == 'qiime') {
        reads = file(params.reference_reads, checkIfExists: true)
        ref_tax = file(params.reference_taxonomy, checkIfExists: true)
        QIIME_BLAST(repseq, taxonomy, reads, ref_tax)
    } else { error "--backend must be native or qiime" }
}

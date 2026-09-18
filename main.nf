nextflow.enable.dsl=2

include { VERIFY_TEST } from './modules/local/verify_test'

include { IMPORT_RECONCILED_TAXONOMY } from './modules/local/import_taxonomy'
include { POSTPROCESS_TAXONOMY } from './modules/local/postprocess_taxonomy'
include { NATIVE_BLAST } from './modules/local/blast_native'
include { QIIME_BLAST } from './modules/local/blast_qiime'
include { EXPORT_QZA_INPUTS } from './modules/local/export_qza_inputs'
include { NORMALIZE_TAXONOMY; IMPORT_NORMALIZED_TAXONOMY } from './modules/local/normalize_taxonomy'

workflow {
    def normalizeOnly = params.normalize_only.toString().toBoolean()
    def postprocessOnly = params.postprocess_only.toString().toBoolean()
    def profiles = ['auto', 'generic', 'silva', 'silva138', 'gtdb', 'gtdb_r220', 'gg2', 'unite', 'eukaryome']
    if (!(params.taxonomy_profile in profiles))
        error "Unsupported --taxonomy_profile: ${params.taxonomy_profile}"
    if (normalizeOnly && postprocessOnly)
        error 'Choose either --normalize_only or --postprocess_only, not both'
    if (normalizeOnly || postprocessOnly) {
        if ((!params.taxonomy_qza && !params.taxonomy_tsv) || (params.taxonomy_qza && params.taxonomy_tsv))
            error 'Provide exactly one of --taxonomy_qza or --taxonomy_tsv'
        inputTaxonomy = file(params.taxonomy_qza ?: params.taxonomy_tsv, checkIfExists: true)
        if (postprocessOnly) {
            finalTaxonomy = Channel.value(inputTaxonomy)
        } else {
            NORMALIZE_TAXONOMY(inputTaxonomy)
            IMPORT_NORMALIZED_TAXONOMY(NORMALIZE_TAXONOMY.out.qiime_tsv)
            finalTaxonomy = NORMALIZE_TAXONOMY.out.qiime_tsv
        }
    } else {
        if (!params.repseq_qza || !params.taxonomy_qza)
            error 'Provide --repseq_qza and --taxonomy_qza'
        if (params.taxonomy_tsv)
            error '--taxonomy_tsv requires --normalize_only true or --postprocess_only true'
        if (!(params.backend in ['native', 'qiime']))
            error '--backend must be native or qiime'
        if (!(params.blast_lineage_policy in ['species_only', 'blast_lineage']))
            error '--blast_lineage_policy must be species_only or blast_lineage'
        if (params.backend == 'native' && (!params.blast_db || !params.taxdump_dir))
            error 'Native backend requires --blast_db and --taxdump_dir'
        if (params.backend == 'qiime' && (!params.reference_reads || !params.reference_taxonomy))
            error 'QIIME backend requires --reference_reads and --reference_taxonomy'
        repseq = file(params.repseq_qza, checkIfExists: true)
        taxonomy = file(params.taxonomy_qza, checkIfExists: true)
        EXPORT_QZA_INPUTS(repseq, taxonomy)
        if (params.backend == 'native') {
            NATIVE_BLAST(EXPORT_QZA_INPUTS.out.repseq_fasta, EXPORT_QZA_INPUTS.out.taxonomy_tsv)
            IMPORT_RECONCILED_TAXONOMY(NATIVE_BLAST.out.taxonomy_qiime)
            finalTaxonomy = NATIVE_BLAST.out.taxonomy_qiime
        } else {
            reads = file(params.reference_reads, checkIfExists: true)
            ref_tax = file(params.reference_taxonomy, checkIfExists: true)
            QIIME_BLAST(repseq, EXPORT_QZA_INPUTS.out.taxonomy_tsv, reads, ref_tax)
            finalTaxonomy = QIIME_BLAST.out.taxonomy_qiime
        }
    }
    POSTPROCESS_TAXONOMY(finalTaxonomy)
    if (params.test_run.toString().toBoolean()) {
        VERIFY_TEST(POSTPROCESS_TAXONOMY.out.table,
                    file("${projectDir}/tests/verify_workflow.py"),
                    file("${projectDir}/tests/data/expected.tsv"))
    }
}

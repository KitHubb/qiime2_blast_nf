process VERIFY_TEST {
    label 'qiime_export'
    container params.qiime_sif
    publishDir "${params.outdir}/test", mode: 'copy', overwrite: true
    input:
    path taxonomy
    path checker
    path expected
    output:
    path 'test_report.txt'
    script:
    """
    python3 "${checker}" "${taxonomy}" "${expected}"
    """
}

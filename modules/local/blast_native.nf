process NATIVE_BLAST {
    tag "native_blast"
    label 'blast_taxonomy'
    container params.blast_taxonomy_sif
    containerOptions '--bind /data:/data'
    publishDir params.outdir, mode: 'copy', overwrite: true
    input:
    path repseq
    path taxonomy
    output:
    path '*.tsv', emit: tables
    script:
    def scripts = "${projectDir}/bin"
    """
    set -euo pipefail
    python3 ${scripts}/normalize_qiime_taxonomy.py --input ${taxonomy} --output-dir normalized --profile ${params.taxonomy_profile}
    blastn -query ${repseq} -db ${params.blast_db} -task blastn -dust no -num_threads ${task.cpus} \\
      -max_target_seqs ${params.blast_retrieval_n} -outfmt '6 qacc staxids sacc evalue bitscore qcovus pident length' -out blast_hits_raw.tsv
    python3 ${scripts}/select_blast_hits.py --blast-raw blast_hits_raw.tsv --output-dir blast_selection --top-n ${params.blast_top_n} --max-evalue ${params.blast_max_evalue} --min-pident ${params.blast_min_pident} --min-qcovus ${params.blast_min_qcovus}
    printf 'TaxID\\tKingdom\\tPhylum\\tClass\\tOrder\\tFamily\\tGenus\\tSpecies\\n' > taxonkit_lineage.tsv
    if [ -s blast_selection/blast_candidate_taxids.txt ]; then taxonkit reformat -I 1 -F -f '{k}\\t{p}\\t{c}\\t{o}\\t{f}\\t{g}\\t{s}' --data-dir ${params.taxdump_dir} < blast_selection/blast_candidate_taxids.txt | cut -f1-8 >> taxonkit_lineage.tsv; fi
    python3 ${scripts}/build_blast_taxonomy.py --candidates blast_selection/blast_candidates_top5.tsv --lineage taxonkit_lineage.tsv --selection-report blast_selection/blast_selection_report.tsv --output-dir blast_taxonomy
    python3 ${scripts}/reconcile_qiime_blast_species.py --qiime-normalized normalized/taxonomy_normalized.tsv --blast-taxonomy blast_taxonomy/blast_taxonomy.tsv --output-dir final_taxonomy --min-qiime-confidence ${params.blast_min_qiime_confidence} --max-evalue ${params.blast_max_evalue} --min-pident ${params.blast_min_pident} --min-qcovus ${params.blast_min_qcovus} --reconcile-mode ${params.blast_reconcile_mode} --species-min-pident ${params.blast_species_min_pident} --species-min-qcovus ${params.blast_species_min_qcovus} --species-max-evalue ${params.blast_species_max_evalue}
    cp blast_selection/blast_candidates_top5.tsv .; cp blast_taxonomy/blast_taxonomy.tsv .; cp final_taxonomy/taxonomy_blast*.tsv .
    """
}

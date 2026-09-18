# Workflow tests / 워크플로 테스트

Run from the repository root with Nextflow, Singularity and the QIIME 2025.7 container available:

```bash
nextflow -C nextflow.config run main.nf -profile test
nextflow -C nextflow.config run main.nf -profile test_postprocess
python3 -m unittest discover -s tests -p 'test_*.py'
```

`test` executes normalization, QZA import/validation, QZV generation, final postprocessing and output assertions. `test_postprocess` executes postprocessing and the same assertions directly. Both use five synthetic ASVs in `tests/data/taxonomy.tsv`, require no external database, and run real commands (not stubs). An assertion failure makes Nextflow fail. Success produces `<outdir>/test/test_report.txt`.

These tests cover the no-BLAST workflow paths. They do not perform BLAST searches or validate reference database compatibility. Override `--qiime_sif /path/to/image.sif` when necessary. Do not combine these test profiles with production input parameters.

`test`는 정규화부터 QZA 검증·QZV 생성·최종 후가공·결과 비교까지 실제 실행합니다. `test_postprocess`는 후가공 경로를 검사합니다. 외부 DB 없이 합성 ASV 5개를 사용하며, 수기로 작성한 예상 표와 다르면 Nextflow가 실패합니다. 성공 기록은 `<outdir>/test/test_report.txt`입니다. BLAST 검색 자체는 이 테스트에 포함되지 않습니다. 실제 분석 입력과 테스트 프로필을 섞지 마세요.

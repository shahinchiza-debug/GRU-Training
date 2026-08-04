# Stage 2 Output

Detta steg innehåller resultatet efter strukturfiltret.

- `valid_templates/`
  - Mallar som passerar steg 2-reglerna.

- `invalid_templates/`
  - Mallar som stoppas i steg 2, med valideringsorsaker.
  - Här hamnar också duplikatstrukturer när `D_1/D_2` bara skiljer sig i ordning.

- `stage2_filter_report.json`
  - Sammanfattning av hur många som blev giltiga respektive ogiltiga.
  - Visar också antal duplikatstrukturer och vilken 2D-policy som användes.

- `stage2_metadata.json`
  - Metadata om senaste körningen.

Reglerna för detta steg läses från:

- `input/stage2_rules.json`

Scriptet för detta steg är:

- `scripts/filter_stage2_templates.py`

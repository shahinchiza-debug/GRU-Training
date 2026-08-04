# Stage 3 Output

Detta steg delar upp giltiga mallar från steg 2 i tre delar baserat på antal deviations.

- `del_1_0d/`
  - Mallar med `0` deviations.

- `del_2_1d/`
  - Mallar med `1` deviation.

- `del_3_2d/`
  - Mallar med `2` deviations.

- `stage3_split_report.json`
  - Sammanfattning av hur många mallar som hamnade i varje del.

- `stage3_metadata.json`
  - Metadata om senaste körningen.

Indata för detta steg läses från:

- `stage2_output/valid_templates`

Scriptet för detta steg är:

- `scripts/split_stage3_by_deviation_count.py`

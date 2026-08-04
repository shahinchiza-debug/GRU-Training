# Stage 4 Output

Detta steg fördelar steg-3-mallarna på turn-count-buckets enligt den godkända distributionsmatrisen.

Strukturen är:

- `del_1_0d/`
  - `turn_6/`, `turn_8/`, `turn_9/`, `turn_10/`, `turn_12/`, `turn_14/`, `turn_18/`, `turn_25/`

- `del_2_1d/`
  - `turn_6/`, `turn_8/`, `turn_9/`, `turn_10/`, `turn_12/`, `turn_14/`, `turn_18/`, `turn_25/`

- `del_3_2d/`
  - `turn_6/`, `turn_8/`, `turn_9/`, `turn_10/`, `turn_12/`, `turn_14/`, `turn_18/`, `turn_25/`

- `stage4_distribution_report.json`
  - Sammanfattning per grupp och totalsumma per turn count.

- `stage4_metadata.json`
  - Metadata om senaste körningen.

Indata för detta steg läses från:

- `stage3_output`

Konfigurationen för detta steg läses från:

- `input/stage4_turn_distribution.json`

Scriptet för detta steg är:

- `scripts/distribute_stage4_turn_counts.py`

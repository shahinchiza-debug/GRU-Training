# Stage 5 Output

Detta steg fördelar steg-4-mallarna på språkstilar enligt den godkända matrisen.

Strukturen är nu språk först:

- `formell_fin_svenska/`
  - `turn_6/`
  - `turn_8/`
  - `turn_9/`
  - `turn_10/`
  - `turn_12/`
  - `turn_14/`
  - `turn_18/`
  - `turn_25/`

- `orten_svenska/`
  - `turn_6/`
  - `turn_8/`
  - `turn_9/`
  - `turn_10/`
  - `turn_12/`
  - `turn_14/`
  - `turn_18/`
  - `turn_25/`

- `vardaglig_svenska/`
  - `turn_6/`
  - `turn_8/`
  - `turn_9/`
  - `turn_10/`
  - `turn_12/`
  - `turn_14/`
  - `turn_18/`
  - `turn_25/`

- `brytande_svenska/`
  - `turn_6/`
  - `turn_8/`
  - `turn_9/`
  - `turn_10/`
  - `turn_12/`
  - `turn_14/`
  - `turn_18/`
  - `turn_25/`

- `stage5_language_distribution_report.json`
  - Sammanfattning per turn count och totalsumma per språkstil.

- `stage5_metadata.json`
  - Metadata om senaste körningen.

Indata för detta steg läses från:

- `stage4_output`

Konfigurationen för detta steg läses från:

- `input/stage5_language_distribution.json`

Scriptet för detta steg är:

- `scripts/distribute_stage5_languages.py`


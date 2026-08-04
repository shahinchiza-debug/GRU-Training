# Stage 6 Output

Detta steg lagger till formprofilerna `A1-A2`.

Varje mall far:

- en formprofil (`A1`, `A2`)
- fasta turer for `P1`, `P3` och `P5`
- en `remaining_turn_budget`
- en lista med variabla delar som senare kan fordelas med `X/Y/Z/W`

De delar som fortfarande ar variabla i detta steg ar:

- `P2`
- `P4`
- vid `2D`: `D_slot_1` och `D_slot_2`

Mappstrukturen ar:

- `stage6_output/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Exempel:

- `stage6_output/vardaglig_svenska/turn_12/A2/RAW_000123.json`

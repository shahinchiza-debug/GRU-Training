# Stage 7 Output

Steg 7 lagger till faktisk turfordelning med Dirichlet.

Input:

- `stage6_output/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `stage7_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `stage7_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Vad som hander:

- `P1`, `P3` och `P5` behaller sina lasta turer fran steg 6
- `P2` och `P4` ar alltid aktiva rorliga delar
- aktiv `D_1` blir `D_slot_1`
- aktiv `D_2` blir `D_slot_2`
- varje aktiv rorlig del far minst `1` tur
- resterande turer fordelas token-for-token med symmetrisk Dirichlet

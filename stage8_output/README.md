# Stage 8 Output

Steg 8 tilldelar intent counts efter att turn counts beraknats i steg 7.

Input:

- `stage7_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `stage8_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `stage8_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Regeln som ar inbyggd:

- intent-tillatna faser ar `P2.1`, `P2.2`, `P2.3`, `P2.4`, `P4.2`, `P4.3`
- intent-tillaten avvikelse ar `D5`
- varje `P` och `D` i slutmallen far ett direkt `intent_count`-falt
- om staten ar `P2.2`, `P2.3`, `P4.3` eller `D5` hoppas regeln `intent_count <= turn_count` over
- annars galler:
  - om `turn_count = 3` blir intervallet `1-3`
  - om `turn_count >= 4` blir intervallet `1-4`

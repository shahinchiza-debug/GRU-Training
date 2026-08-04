# Stage 9 Output

Steg 9 laser giltiga mallar fran steg 8 och fyller dem med poolvard en.

Input:

- `stage8_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `stage9_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `stage9_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Vad steg 9 gor:

- drar ett slumpmassigt fornamn
- drar ett slumpmassigt telefonnummer
- drar en dag
- drar en tidspreferens av typen `exact_time`, `relative_time` eller `time_part`
- drar tjanster utan dubletter inom samma mall
- fyller `stage9.component_payloads` for relevanta noder

Viktig regel:

- om en tjanst redan har valts i samma mall far den inte valjas igen

Sarskild notering:

- `D3` behandlas som en service-addition i steg 9 och far minst ett nytt tjanstedrag
  aven om tidigare steg inte redan gav den ett intent count.

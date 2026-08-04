# Training Mall

Nuvarande projekt innehaller steg 1, steg 2, steg 3, steg 4, steg 5, steg 6, steg 7, steg 8 och steg 9.

## Mappstruktur

- `input/`
  - Indatafiler for stegen.
  - Viktiga filer:
  - `structure.json`
  - `stage2_rules.json`
  - `stage4_turn_distribution.json`
  - `stage5_language_distribution.json`
  - `stage6_form_distribution.json`
  - `stage7_dirichlet_turn_allocation.json`
  - `stage8_intent_distribution.json`
  - `stage9_pools.json`

- `scripts/`
  - Python-scripten for pipelinen.
  - Innehaller:
  - `generate_stage1_raw_combinations.py`
  - `filter_stage2_templates.py`
  - `split_stage3_by_deviation_count.py`
  - `distribute_stage4_turn_counts.py`
  - `distribute_stage5_languages.py`
  - `distribute_stage6_form_profiles.py`
  - `allocate_stage7_dirichlet_turns.py`
  - `assign_stage8_intents.py`
  - `populate_stage9_pools.py`

- `stage1_output/`
  - Raa mallar.

- `stage2_output/`
  - Giltiga och ogiltiga mallar efter filter.

- `stage3_output/`
  - Split av giltiga mallar i `0D`, `1D` och `2D`.

- `stage4_output/`
  - Turn-count-fordelning.

- `stage5_output/`
  - Sprakfordelning.

- `stage6_output/`
  - Formprofiler `A1-A2`.

- `stage7_output/`
  - Turfordelning med Dirichlet.

- `stage8_output/`
  - Intent-fordelning.

- `stage9_output/`
  - Poolsteg.
  - Just nu ligger bara README har, eftersom sjalva generatorn byggs senare.

- `docs/`
  - Dokumentation och arbetsanteckningar.

## Viktigaste filerna just nu

- `input/structure.json`
  - Source of truth for steg 1.

- `input/stage2_rules.json`
  - Source of truth for steg 2.
  - Har filterregler for ogiltiga kombinationer.

- `input/stage4_turn_distribution.json`
  - Source of truth for steg 4.
  - Styr hur `0D`, `1D` och `2D` fordelas pa turn counts.

- `input/stage5_language_distribution.json`
  - Source of truth for steg 5.
  - Styr hur turn counts fordelas pa sprakstilar.

- `input/stage6_form_distribution.json`
  - Source of truth for steg 6.
  - Styr hur mallar fordelas pa formprofilerna `A1-A2`.

- `input/stage7_dirichlet_turn_allocation.json`
  - Source of truth for steg 7.
  - Styr alpha-varden och hur rorliga delar identifieras.

- `input/stage8_intent_distribution.json`
  - Source of truth for steg 8.
  - Styr intentregler, turn-count-cap och undantag som `P2.2`, `P2.3`, `P4.3` och `D5`.

- `input/stage9_pools.json`
  - Source of truth for steg 9.
  - Innehaller pooler for tjanster, fornamn, telefonnummer, dagar och tid.
  - Innehaller ocksa regeln att samma tjanst inte far valjas tva ganger i samma mall.

## Stegen just nu

- `Steg 1`
  - Raa P/D-kombinationer.

- `Steg 2`
  - Strukturfilter.
  - Delar upp i giltigt och ogiltigt.

- `Steg 3`
  - Delar upp giltiga mallar i `0D`, `1D`, `2D`.

- `Steg 4`
  - Fordelar steg-3-mallarna pa turn-count-buckets.

- `Steg 5`
  - Fordelar steg-4-mallarna pa sprakstilar.

- `Steg 6`
  - Fordelar steg-5-mallarna pa formprofilerna `A1-A2`.
  - Lagger till fasta turer for `P1`, `P3`, `P5` och en resterande budget for variabla delar.

- `Steg 7`
  - Fordelar faktiska turer med Dirichlet.
  - Lagger till turn counts for `P2`, `P4` och aktiva `D`-slots.

- `Steg 8`
  - Tilldelar intent counts efter steg 7.
  - Anvander if/else-logiken for nar `intent_count <= turn_count` ska galla per fas.

- `Steg 9`
  - Pooltilldelning.
  - Drar fornamn, telefonnummer, dag, tidspreferens och tjanster utan dubletter.

## Hur du kor stegen

Steg 1:

```powershell
python .\scripts\generate_stage1_raw_combinations.py
```

Steg 2:

```powershell
python .\scripts\filter_stage2_templates.py
```

Steg 3:

```powershell
python .\scripts\split_stage3_by_deviation_count.py
```

Steg 4:

```powershell
python .\scripts\distribute_stage4_turn_counts.py
```

Steg 5:

```powershell
python .\scripts\distribute_stage5_languages.py
```

Steg 6:

```powershell
python .\scripts\distribute_stage6_form_profiles.py
```

Steg 7:

```powershell
python .\scripts\allocate_stage7_dirichlet_turns.py
```

Steg 8:

```powershell
python .\scripts\assign_stage8_intents.py
```

Steg 9:

```powershell
python .\scripts\populate_stage9_pools.py
```

## Vad steg 6 gor

Steg 6 laser fran:

- `stage5_output`

och anvander:

- `input/stage6_form_distribution.json`

for att skriva mallarna till:

- `stage6_output/<sprak>/turn_<antal>/A1`
- `stage6_output/<sprak>/turn_<antal>/A2`

Varje mall far ett nytt `stage6`-block med:

- vald formprofil
- fasta turer for `P1`, `P3`, `P5`
- `remaining_turn_budget`
- `variable_components`
- placeholders som `X`, `Y`, `Z`, `W`

I den uppdaterade modellen finns bara:

- `A1`: `P1=1`, `P3=1`, `P5=1`
- `A2`: `P1=1`, `P3=2`, `P5=1`

## Skillnaden mellan A1 och A2

`A1` och `A2` ar tva olika formprofiler.

- `A1` betyder:
  - `P1 = 1 tur`
  - `P3 = 1 tur`
  - `P5 = 1 tur`

- `A2` betyder:
  - `P1 = 1 tur`
  - `P3 = 2 turer`
  - `P5 = 1 tur`

Den enda strukturella skillnaden mellan `A1` och `A2` i steg 6 ar alltsa:

- `A1` har kort `P3`
- `A2` har langre `P3`

`P1` och `P5` ar samma i bade `A1` och `A2`.

## Vad som ar last i steg 6

Ja, i den nuvarande steg-6-modellen ar `P1` och `P5` lasta.

Mer exakt:

- `P1` ar alltid `1 tur`
- `P5` ar alltid `1 tur`
- `P3` ar det som skiljer `A1` och `A2`
- `P2` och `P4` ar fortfarande variabla delar
- vid `2D` ar aven `D_slot_1` och `D_slot_2` variabla delar

Det betyder att steg 6 inte bestammer exakt text eller exakt slutlig tur-fordelning. Det bestammer bara samtalets formprofil och vilken turn-budget som ar kvar att fordela pa de variabla delarna.

## Vad steg 7 gor

Steg 7 laser fran:

- `stage6_output`

och anvander:

- `input/stage7_dirichlet_turn_allocation.json`

Steg 7 gor detta per mall:

- hamtar total turbudget `T`
- summerar lasta turer `L`
- raknar `R = T - L`
- aktiverar alltid `P2` och `P4`
- lagger till `D_slot_1` om `D_1` ar aktiv
- lagger till `D_slot_2` om `D_2` ar aktiv
- ger varje aktiv rorlig del minst `1` tur
- fordelar resten med symmetrisk Dirichlet

Viktig detalj:

- steg 7 utgar fran faktiska aktiva avvikelser i mallen
- det betyder att en `1D`-mall kan fa `D_slot_1` i steg 7 aven om steg 6 bara beskrev ramformen

Output skrivs till:

- `stage7_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- `stage7_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

## Vad steg 8 gor

Steg 8 laser fran:

- `stage7_output/valid_templates`

och anvander:

- `input/stage8_intent_distribution.json`

Steg 8 gor detta per mall:

- evaluerar `P1`, `P2`, `P3`, `P4`, `P5`, `D_1`, `D_2`
- skriver in `intent_count` direkt pa varje `P` och `D` i slutmallen
- faser som kan fa intents ar:
  - `P2.1`, `P2.2`, `P2.3`, `P2.4`, `P4.2`, `P4.3`
- avvikelsetyp som kan fa intents ar:
  - `D5`
- kor if/else-regeln:
  - om staten ar `P2.2`, `P2.3`, `P4.3` eller `D5`: skippa regeln `intent_count <= turn_count`
  - annars: anvand regeln
- nar regeln anvands:
  - om `turn_count = 1` blir intervallet `1-1`
  - om `turn_count = 2` blir intervallet `1-2`
  - om `turn_count = 3` blir intervallet `1-3`
  - om `turn_count >= 4` blir intervallet `1-4`
- nar regeln skippas:
  - intervallet ar alltid `1-4`
- valjer sedan ett slumpmassigt intentantal inom giltigt intervall

Output skrivs till:

- `stage8_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- `stage8_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

## Template-layout

Varje template ar giltig JSON och anvander fasta huvudnycklar:

- `P1`, `P2`, `P3`, `P4`, `P5`
- `D_1`, `D_2`

Senare steg lagger till metadata som:

- `_validation`
- `stage4`
- `stage5`
- `stage6`
- `stage7`
- `stage8`

I steg 8 far ocksa varje toppniva-komponent:

- `P1.intent_count`
- `P2.intent_count`
- `P3.intent_count`
- `P4.intent_count`
- `P5.intent_count`
- `D_1.intent_count`
- `D_2.intent_count`

Om komponenten inte bar intent blir vardet `0`.

## Viktiga principer

- `P1-P5` ar fasta kategorier.
- Steg 1 genererar hela den raa rymden forst.
- Steg 2 avgor vilka kombinationer som ar giltiga.
- Steg 3 grupperar de giltiga mallarna efter antal deviations.
- Steg 4 fordelar mallarna pa turn counts via en separat configfil.
- Steg 5 fordelar mallarna pa sprak via en separat configfil.
- Steg 6 fordelar mallarna pa formprofiler via en separat configfil.
- Steg 7 fordelar faktiska turer med Dirichlet.
- Steg 8 fordelar intents efter turn counts.
- Steg 9 tilldelar faktiska poolvard en som fornamn, telefonnummer, tjanster, dag och tid.

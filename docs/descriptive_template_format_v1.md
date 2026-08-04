# Descriptive Template Format V1

Detta dokument visar ett konkret JSON-format dar:

- vanstersidan ar fasta kategorier
- hogersidan ar beskrivande valda vard en

Tanken ar att mallarna ska vara lasbara direkt, utan att varje template bara innehaller kryptiska koder som `P1.2`.

## 1. Definition / source of truth

Detta ar filtypen som beskriver vilka vard en som ar tillatna per kategori.

```json
{
  "p1_values": [
    "ai_minimal_intent",
    "ai_rik_intent",
    "kund_minimal_intent",
    "kund_rik_intent"
  ],
  "p2_values": [
    "en_tjanst",
    "flera_tjanster_samtidigt",
    "flera_tjanster_sekventiellt",
    "ai_promptad_flerbehov"
  ],
  "p3_values": [
    "ren_auth",
    "partiell_auth",
    "oklar_auth"
  ],
  "p4_values": [
    "ingen_korrigering",
    "en_mindre_korrigering",
    "flera_korrigeringar"
  ],
  "p5_values": [
    "ai_drivet_avslut",
    "kundinitierat_avslut"
  ],
  "d_values": [
    "ingen",
    "d1_infofraga_i_p3",
    "d1_infofraga_i_p4",
    "d2_enskild_korrigering_i_p3",
    "d2_enskild_korrigering_i_p4",
    "d3_tillagg_i_p3",
    "d3_tillagg_i_p4",
    "d5_flera_korrigeringar_i_p3",
    "d5_flera_korrigeringar_i_p4"
  ]
}
```

Detta ar regel-/definitionsnivan.

Har ar vanstersidan alltid fasta nycklar och hogersidan ar listor med tillatna vard en.

## 2. Genererad template

Detta ar en faktisk template som generatorn skulle kunna skriva ut.

```json
{
  "template_id": "T_000001",
  "p1": "kund_rik_intent",
  "p2": "ai_promptad_flerbehov",
  "p3": "partiell_auth",
  "p4": "en_mindre_korrigering",
  "p5": "kundinitierat_avslut",
  "d_1": "d3_tillagg_i_p3",
  "d_2": "ingen"
}
```

Har ar:

- vanstersidan fasta kategorier
- hogersidan ett valt beskrivande varde

## 3. Varfor detta format ar bra

Det ger tre fordelar:

- det ar lasbart for manniskor
- det ar lattare for AI att tolka direkt
- det finns fortfarande en separat source of truth med tillatna vard en

## 4. Viktig regel for D

Om ni behaller `d_1` och `d_2` som fasta falt men sager att ordningen inte ska raknas, da bor generatorn alltid skriva dem i en stabil ordning.

Exempel:

- sortera efter fas forst
- sedan efter `D`-typ

Da undviker ni att dessa tva templates raknas som olika fast de betyder samma sak:

```json
{
  "d_1": "d1_infofraga_i_p3",
  "d_2": "d3_tillagg_i_p4"
}
```

och

```json
{
  "d_1": "d3_tillagg_i_p4",
  "d_2": "d1_infofraga_i_p3"
}
```

## 5. Kort slutsats

Det format som verkar matcha chefens tanke bast ar:

- fasta kategorier pa vanster sida
- beskrivande innehall pa hoger sida
- separat definitionsfil som source of truth

Alltsa:

- inte bara `p1 = P1.2`
- hellre `p1 = kund_rik_intent`

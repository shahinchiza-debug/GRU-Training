# MallGuide

Detta dokument beskriver nulaget efter att modellen synkats mot `docs/ej klart.md`.

## Kort svar

Ja, du kan borja bygga mallar nu.

Men det ar viktigt att du bygger enligt den nya structure-only-modellen:

- inga `turns`
- inga turn-for-turn-mallar

## Vad som ar last nu

Detta ar nu genomfort:

- svenska tjanster
- svenska dagar
- svensk personalpool
- svensk booking-terminologi
- `P2` ar `4` strukturella states
- `P2` stoder upp till 4 tjanster internt
- `D4` ar borttagen
- `D` ar inject-lager i en fas
- `MLP1` och `MLP2` finns som labels only
- `formalitet` finns men raknas inte i unikhetsberakning
- auth genereras som svenskt namn + svenskt mobilnummer

## Vad en mall innehaller nu

Varje mall innehaller:

- `template_id`
- `schema_version`
- `macro`
- `meso`
- `micro`
- `labels`

### macro

- `formality`
- `phases`
- `has_deviation`

### meso

- `P1.state`
- `P2.state`
- `P2.service_count`
- `P3.state`
- `P4.state`
- `P5.state`
- `deviation.active`
- `deviation.type`
- `deviation.inject_phase`

### micro

- `services.base`
- `services.final`
- `booking.booking_type`
- `booking.day`
- `booking.time.kind`
- `booking.time.value`
- `booking.staff`
- `auth.name`
- `auth.phone`
- `faq_topics`
- `deviation_topic`

### labels

- `mlp1_labels`
- `mlp2_labels`

## Vad som inte finns langre

- `turns`
- `customer_turns` per template
- `D` som egen fas i `macro.phases`

## Hur deviation fungerar nu

Deviation beskrivs nu sa har:

- `macro.has_deviation = true/false`
- `meso.deviation.type = D1/D2/D3/D5 eller null`
- `meso.deviation.inject_phase = P2/P3/P4/P5 eller null`

Exempel:

- en mall kan ha `D3` i `P4`
- det betyder inte att `D` ligger som egen fas
- det betyder att `D3` injiceras i `P4`

## Hur unikhet raknas nu

Generatorn raknar inte dessa saker som unik struktur:

- `macro.formality`
- `labels.*`
- `micro.auth.name`
- `micro.auth.phone`
- `P2` raknas inte som `10`; det ar fortfarande `4` states med intern tjanstregel

Det betyder att samma struktur inte blir "ny" bara for att:

- formaliteten byts
- auth-namnet byts
- MLP-labels finns med

## Hur du kor generatorn

```powershell
python .\scripts\generate_templates_v1.py --count 100
```

## Hur du validerar

```powershell
python .\scripts\validate_template_v1.py .\templates\training_data_template_v1.example.json
```

## Viktig praktisk notering

Turn-antal ar fortfarande viktiga i teorin och finns som policy i master-filen, men de genereras inte som en del av varje strukturmall just nu.

Det betyder:

- denna version fokuserar pa strukturkombinationer
- inte pa dialogutspel tur for tur

## Slutsats

Ja, du kan borja bygga mallar nu.

Om du vill jobba vidare pa sjalva kombinationslogiken ar de tre viktigaste filerna:

- `templates/training_data_template_v1.master.json`
- `scripts/generate_templates_v1.py`
- `scripts/validate_template_v1.py`

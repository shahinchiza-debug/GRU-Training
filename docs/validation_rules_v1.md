# Validation Rules

Detta dokument beskriver reglerna for structure-only-modellen enligt `docs/ej klart.md`.

## 1. Huvudsekvens

`macro.phases` maste alltid vara:

- `P1 -> P2 -> P3 -> P4 -> P5`

`D` ligger inte i den sekvensen.

## 2. Deviation

Deviation styrs av:

- `macro.has_deviation`
- `meso.deviation.active`
- `meso.deviation.type`
- `meso.deviation.inject_phase`

Om deviation ar aktiv:

- `type` maste vara `D1`, `D2`, `D3` eller `D5`
- `inject_phase` maste vara satt
- `micro.deviation_topic` maste vara satt

Om deviation inte ar aktiv:

- `type = null`
- `inject_phase = null`
- `micro.deviation_topic = null`

## 3. Inject-giltighet

Giltiga faser per deviation:

- `D1`: `P2`, `P3`, `P4`
- `D2`: `P2`, `P3`
- `D3`: `P2`, `P3`, `P4`, `P5`
- `D5`: `P2`, `P3`

## 4. P2 och antal tjanster

`P2` ar fortfarande bara `4` strukturella states:

- `P2.1`
- `P2.2`
- `P2.3`
- `P2.4`

Antal tjanster ar en intern regel i `P2`, inte ett separat block som gor `P2` till `10`.

- `P2.1` = inga tjanster; endast `BOOK_001`
- `P2.2` = `1`, `2` eller `3` tjanster
- `P2.3` = `1`, `2` eller `3` tjanster
- `P2.4` = `1`, `2` eller `3` tjanster

`meso.P2.service_count` maste stamma med:

- `meso.P2.state`
- langden pa `micro.services.base`

## 5. D3-regel

`D3` ar tillagg.

Det betyder:

- `micro.deviation_topic` far inte redan finnas i `micro.services.base`
- `micro.services.final` maste vara `base + deviation_topic`

Om deviation inte ar `D3` maste:

- `micro.services.final = micro.services.base`

## 6. FAQ-regel

Bara `D1` far skapa FAQ-spor.

Det betyder:

- om `D1` ar aktiv:
  - `micro.faq_topics` maste innehalla exakt `deviation_topic`

- om deviation inte ar `D1`:
  - `micro.faq_topics` maste vara tom

## 7. Tid

`micro.booking.time.kind` maste vara en av:

- `exact_time`
- `relative_time`
- `time_part`

Om `exact_time`:

- `value` maste vara inom oppettider
- kvartsteg only

Om `time_part` eller `exact_time`:

- `micro.booking.day` maste vara satt

## 8. Labels

`MLP1` och `MLP2` ar labels only.

De valideras mot bookingtypen och eventuell FAQ:

- `bokning` -> `booking_action`
- `ombokning` -> `ombokning`
- `avbokning` -> `avbokning`
- `auth` finns alltid
- `smalltalk` finns alltid
- `faq` finns bara om `D1` ar aktiv

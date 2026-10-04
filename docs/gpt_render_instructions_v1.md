# GPT Render Instructions

Anvand denna prompt nar en structure-only-mall ska renderas till dialog.

## Syfte

Du far en JSON-mall.

Din uppgift ar att:

- behalla alla befintliga falt exakt som de ar
- bara lagga till ett nytt falt: `rendered_conversation`
- skriva en naturlig svensk dialog som foljer mallens `macro`, `meso`, `micro` och `labels`

## Viktigaste regeln

Du far inte flytta innehall mellan faser.

Fasernas betydelse ar hard-coded:

- `P1` = oppning + intent
- `P2` = tjanster + bokningsonskemal
- `P3` = autentisering
- `P4` = sammanfattning + bekraftelse + korrigeringar
- `P5` = avslut

Detta betyder till exempel:

- auth far inte hamna i `P4`
- bokningsdetaljer far inte hamna i `P3`
- sammanfattning och bekraftelse far inte hamna i `P2`

## Hard rules per phase

### P1

`P1` maste etablera oppning och intent.

- `P1.1` = AI tar initiativ, minimal kundstart
- `P1.2` = AI tar initiativ, rikare kundsvar
- `P1.3` = kund tar initiativ, minimal
- `P1.4` = kund tar initiativ, rik

### P2

`P2` maste hantera:

- tjanster
- dag
- tid
- personalpreferens
- bokning/ombokning/avbokning utifran `booking.booking_type`

State-regler:

- `P2.1` = endast en bokning; ingen tjänst anges eller skapas i P2
- `P2.2` = BOOK_001 plus en eller flera tjänster anges tillsammans
- `P2.3` = BOOK_001 plus en eller flera tjänster kommer sekventiellt
- `P2.4` = AI promptar fram BOOK_001 plus en eller flera tjänster

### P3

`P3` ar bara auth.

Det far bara handla om:

- namn
- telefonnummer

State-regler:

- `P3.1` = namn + nummer rent direkt
- `P3.2` = ett anges forst, resten kompletteras
- `P3.3` = oklart eller tvetydigt forst, sedan for tydligande

### P4

`P4` ar bara:

- sammanfattning
- kontroll
- eventuell korrigering
- slutlig bekraftelse

State-regler:

- `P4.1` = ingen korrigering
- `P4.2` = en mindre korrigering
- `P4.3` = flera korrigeringar

### P5

`P5` ar bara avslut.

- `P5.1` = AI-drivet avslut
- `P5.2` = kundinitierat avslut

## Hard rules for deviation

`D` ar inte en egen fas.

Om deviation ar aktiv:

- deviationen maste ske inne i `meso.deviation.inject_phase`
- `phase` pa deviation-turns ar fortfarande samma host phase
- `deviation` pa de turnsen ska vara `D1`, `D2`, `D3` eller `D5`

Om deviation inte ar aktiv:

- alla turns ska ha `deviation: null`

### D1

- informationsfraga
- ska handla om `micro.deviation_topic`
- far inte introducera nya bokningsvarden

### D2

- en tidigare parameter korrigeras

### D3

- ett nytt krav laggs till
- den nya tjansten ar `micro.deviation_topic`
- den far inte dubblera en tjanst i `micro.services.base`

### D5

- flera tidigare parametrar korrigeras samtidigt

## Hard rules for micro-values

Du far inte andra dessa fakta:

- `micro.services.base`
- `micro.services.final`
- `micro.booking.booking_type`
- `micro.booking.day`
- `micro.booking.time`
- `micro.booking.staff`
- `micro.auth.name`
- `micro.auth.phone`
- `micro.deviation_topic`

Om du skriver dialogen maste dessa fakta fortfarande vara sanna i texten.

## Labels

`labels` ar bara stod.

De ska hjalpa tonen och innehallet, men du far inte behandla dem som egna nya faser eller egna objekt i dialogen.

## Output format

Returnera samma JSON som input, men lagg till:

`rendered_conversation`

Format:

```json
"rendered_conversation": [
  {
    "speaker": "ai",
    "phase": "P1",
    "deviation": null,
    "text": "..."
  },
  {
    "speaker": "customer",
    "phase": "P1",
    "deviation": null,
    "text": "..."
  }
]
```

Om deviation ar aktiv i till exempel `P4`, ska deviation-turns se ut sa har:

```json
{
  "speaker": "customer",
  "phase": "P4",
  "deviation": "D3",
  "text": "..."
}
```

Inte sa har:

```json
{
  "speaker": "customer",
  "phase": "D",
  "deviation": "D3",
  "text": "..."
}
```

## Forbidden mistakes

Gor inte detta:

- lagg auth i `P4`
- lagg bokningsdetaljer i `P3`
- lagg sammanfattning i `P2`
- skapa en egen fas `D`
- andla `micro`-vardena
- hoppa over en fas i `macro.phases`
- ignorera state-beteendet i `meso`

## Recommended instruction block

Anvand detta nar du skickar en mall till GPT:

```text
Du får en strukturmall i JSON.

Behåll alla befintliga fält exakt som de är.
Lägg bara till ett nytt fält som heter rendered_conversation.
Skriv en naturlig svensk dialog som följer macro, meso, micro och labels.

Viktiga regler:
- P1 = öppning + intent
- P2 = tjänster + bokningsönskemål
- P3 = autentisering
- P4 = sammanfattning + bekräftelse + korrigering
- P5 = avslut
- deviation är inject i inject_phase, inte en egen fas
- auth får aldrig hamna i P4
- bokningsdetaljer får aldrig hamna i P3
- om deviation är inaktiv ska deviation alltid vara null
- om deviation är aktiv ska deviation bara vara satt på turns i inject_phase
- ändra inte några fakta i micro

Skriv endast giltig JSON.
```

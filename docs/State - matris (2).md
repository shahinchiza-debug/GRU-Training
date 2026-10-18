| State | Betydelse | `opening_intent_present` | `intent_count` | Nya objekt | Regler |
| --- | --- | --- | --- | --- | --- |
| P1.1 | AI inleder. Kunden svarar utan intent. | `false` | `0` | Inga | P2 behöver fråga fram behovet. |
| P1.3 | Kunden inleder med hälsning/vag öppning utan intent. | `false` | `0` | Inga | AI behöver hjälpa kunden in i P2. |

| State | Betydelse | Nya objekt | `intent_count` | Tillåtna grenar | Regler |
| --- | --- | --- | --- | --- | --- |
| P2.1 | Kunden uttrycker endast ett intent | `BOOK_001` | 1 | `Booking → boka` | Ingen tjänst skapas i P2.1 |
| P2.2 | Kunden uttrycker fler än ett intent. | `BOOK_001` + 1–3 `SVC_ID` | 2–4 | Samma | Tjänsterna uttrycks tillsammans |
| P2.3 | Kunden driver samtalet och uttrycker sina intents ett i taget. | `BOOK_001` + 1–3 `SVC_ID` | 2–4 | Samma | Kunden introducerar tjänster en i taget |
| P2.4 | AI driver samtalet genom följdfrågor för att få fram fler intents. | `BOOK_001` + 1–3 `SVC_ID` | 2–4 | Samma | AI frågar om kunden vill lägga till något |

```javascript
P2
├─ state
├─ intent_count
└─ intent_slots
   ├─ Booking
   │  └─ boka
   │     └─ BOOK_001
   │        ├─ day
   │        ├─ time
   │        └─ staff
   │
   └─ Tjänster
      └─ lägga till
         └─ SVC_00X
            └─ service

- P2 skapar exakt en BOOK_001.
- P2.1 skapar inga SVC_ID:n. P2.2–P2.4 skapar 1–3 SVC_ID:n.
- intent_count räknar alla nya intent_id:n: BOOK_001 plus varje SVC_ID.
- Samma tjänst får inte väljas två gånger.
- P2 har aldrig target_id.
- P2 använder bara Booking → boka och Tjänster → lägga till.
- Dag, tid och personal tillhör BOOK_001, inte tjänstens SVC_ID.
- Turantalet sätts senare av turfördelningen, inte av P2-hierarkin.
```

| State | Betydelse | Nya objekt | `intent_count` | Tillåten gren | Regel |
| --- | --- | --- | --- | --- | --- |
| P3.1 | Kunden anger både namn och telefonnummer i första tur. | `AUTH_001` | 1 | `Auth → skapa` | Kunden lämnar båda uppgifterna utan problem |
| P3.2 | Kunden anger namn och telefonnummer över två turer. | `AUTH_001` | 1 | `Auth → skapa` | AI frågar efter den saknade uppgiften |
| P3.3 | AI behöver förklara varför autentiseringsinformationen behövs och därefter samla in korrekt namn och telefonnummer. | `AUTH_001` | 1 | `Auth → skapa` | AI förtydligar och samlar in korrekt namn och nummer |

```javascript
P3
├─ state
├─ intent_count: 1
└─ intent_slot
   └─ Auth
      └─ skapa
         └─ AUTH_001
            ├─ name
            └─ phone
- P3 skapar exakt en AUTH_001.
- AUTH_001 innehåller alltid name och phone i slutmallen.
- P3 har aldrig target_id.
- P3 har inga tjänste-, boknings- eller FAQ-handlingar.
- Skillnaden mellan states är hur kontaktuppgifterna samlas in, inte vilket objekt som skapas.
- P3.2 och P3.3 behöver minst fler dialogturer än P3.1, men exakt turantal sätts senare av turfördelningen.
```

| State | Betydelse | `target_count` | Tillåtna ändringar | Regel |
| --- | --- | --- | --- | --- |
| P4.1 | Ingen tidigare information behöver korrigeras. | 0 | Inga | Kunden godkänner sammanfattningen |
| P4.2 | Exakt en tidigare informationsparameter behöver korrigeras. | 1 | Booking, Tjänster eller Auth | Exakt en korrigeringsslot |
| P4.3 | Två eller fler tidigare informationsparametrar behöver korrigeras. | 2–4 | Booking, Tjänster eller Auth | En slot per ändring |

```javascript
P4
├─ state
├─ target_count
└─ targets
   ├─ Booking
   │  ├─ ändra → target_id: BOOK_001
   │  └─ omboka → target_id: BOOK_001
   │
   ├─ Tjänster
   │  └─ byta ut → target_id: SVC_00X
   │
   └─ Auth
      └─ ändra → target_id: AUTH_001
- P4 skapar inga nya ID:n.
- target_id pekar alltid på ett tidigare intent_id: BOOK_001, SVC_00X eller AUTH_001.
- Samma tjänst får inte ändras två gånger inom samma P4-block.
- Samma bokning eller auth får inte ändras två gånger inom samma P4-block.
- P4.1 saknar target_count och targets i den färdiga mallen, eftersom inget sker.
- P4.2 och P4.3 innehåller bara de ändringar som faktiskt valts.
```

| State | Betydelse | `intent_count` | Nya objekt | Regler |
| --- | --- | --- | --- | --- |
| P5.1 | AI avslutar samtalet. | `0` | Inga | AI gör slutsammanfattning och avslut. |
| P5.2 | Kunden avslutar samtalet. | `0` | Inga | Kunden initierar avslutet, AI svarar kort eller bekräftar. |

| State | Betydelse | Count | MLP1 | MLP2 | Target-regel | Poolregel |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | Kunden ställer en informationsfråga (FAQ). Ingen tidigare uppgift ändras. | Ingen | FAQ | Ingen | `reference_id` vid referens-FAQ | Skapar och ändrar inget |

```javascript
D1
├─ FAQ
│  ├─ General
│  │  ├─ ingen reference_id
│  │  └─ fråga om allmän salongsinformation
│  │
│  └─ Referens
│     ├─ reference_id: BOOK_001 | SVC_00X | AUTH_001
│     └─ fråga om en tidigare bokning, tjänst eller authuppgift

- D1 har aldrig intent_count eller target_count.
- D1 skapar aldrig intent_id.
- D1 ändrar aldrig BOOK_001, SVC_ID eller AUTH_001.
- En tjänstekopplad FAQ använder reference_id som pekar på ett tidigare intent_id: BOOK_001, ett aktivt SVC_00X eller AUTH_001.
- General-FAQ kan genereras utan aktiv tjänst.
- En referens-FAQ får bara genereras när det valda reference_id:t redan finns.
- D1 får förekomma i P1, P2, P3, P4 och P5 enligt Rev A.
```

| State | Betydelse | `target_count` | Tillåtna grenar | Target-regel |
| --- | --- | --- | --- | --- |
| D2 | Kunden korrigerar information som tillhör exakt ett tidigare intent. Flera uppgifter inom samma intent kan korrigeras samtidigt. Exempelvis kan både tid och frisör ändras för samma tjänst eller bokningsintent. | 1 | Booking, Tjänster, Auth | `target_id` endast vid tjänsteändring |

```javascript
D2
├─ state: D2
├─ target_count: 1
└─ targets
   └─ korrigeringsslot
      ├─ Booking
      │  ├─ ändra → target_id: BOOK_001
      │  └─ omboka → target_id: BOOK_001
      │
      ├─ Tjänster
      │  └─ byta ut → target_id: SVC_00X
      │
      └─ Auth
         └─ ändra → target_id: AUTH_001
- D2 skapar inga nya ID:n.
- D2 har aldrig intent_count.
- Exakt en korrigering per D2.
- Tjänster → byta ut kräver minst ett aktivt SVC_ID.
- Booking → ändra/omboka kräver att BOOK_001 redan finns.
- Auth → ändra kräver att AUTH_001 redan finns.
- D2 får enligt Rev A ligga vid P3 eller P5.
- Om den nödvändiga informationen inte är etablerad ännu får generatorn inte välja grenen.
```

| State | Betydelse | `intent_count` | Tillåten gren | ID-regel |
| --- | --- | --- | --- | --- |
| D3 | Kunden lägger till en ny tjänst till den befintliga bokningen eller förfrågan. | 1 | `Tjänster → lägga till` | Skapar nästa lediga `SVC_00X` |

```javascript
D3
├─ state: D3
├─ intent_count: 1
└─ intent_slot
   └─ Tjänster
      └─ lägga till
         └─ SVC_00X skapas
            └─ service
- D3 skapar exakt ett nytt SVC_ID.
- D3 har aldrig target_count eller target_id.
- Den nya tjänsten får inte redan finnas i active_services.
- Den nya tjänsten läggs direkt till i active_services.
- D3 får enligt Rev A ligga vid P3, P4 eller P5.
- Två D3 i samma mall är tillåtna, men då måste två olika nya tjänster finnas tillgängliga i poolen.
```

| State | Betydelse | `target_count` | Tillåtna grenar | Target-regel |
| --- | --- | --- | --- | --- |
| D5 | Kunden korrigerar information som tillhör två eller fler tidigare intents. Flera uppgifter inom varje berört intent kan korrigeras samtidigt. Exempelvis kan tid och frisör ändras för ett intent samtidigt som tjänst eller dag ändras för ett annat intent. | 2+ | Booking, Tjänster, Auth | `target_id` endast vid tjänsteändring |

```javascript
D5
├─ state: D5
├─ target_count: 2+
└─ targets
   ├─ korrigeringsslot 1
   │  └─ Booking | Tjänster | Auth
   │
   ├─ korrigeringsslot 2
   │  └─ Booking | Tjänster | Auth
   │
   └─ ytterligare korrigeringsslotar vid behov
      └─ Booking | Tjänster | Auth
Booking
├─ ändra → target_id: BOOK_001
└─ omboka → target_id: BOOK_001

Tjänster
└─ byta ut → target_id: SVC_00X

Auth
└─ ändra → target_id: AUTH_001
- D5 skapar inga nya ID:n.
- D5 har aldrig intent_count.
- D5 innehåller minst två korrigeringsslotar.
- Samma tjänst får inte väljas två gånger i samma D5.
- Booking får bara ändras en gång i samma D5.
- Auth får bara ändras en gång i samma D5.
- Vid byta ut behåller tjänsten sitt SVC_ID, men får ett nytt servicevärde.
- D5 får enligt Rev A ligga vid P3 eller P5.
- D5 räknas som ett D-block, även om den innehåller flera korrigeringar.
```

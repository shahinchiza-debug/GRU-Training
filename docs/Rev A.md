D får användas endast efter informationen är etablerad.



P1 = öppning

P2 = behovsinsamling

P3 = kontaktinsamling

P4 = kontroll / genomgång

P5 = avslut


**P1**

| Kod | Definition |
| --- | --- |
| **P1.1** | AI öppnar, kunden ger inte intent direkt |
| **P1.2** | AI öppnar, kunden ger intent direkt |
| **P1.3** | Kunden öppnar enkelt, utan intent |
| **P1.4** | Kunden öppnar med intent direkt |


**P2**

| Kod | Definition |
| --- | --- |
| P2.1 | Enskilt ärende |
| P2.2 | Flera ärenden uttrycks direkt |
| P2.3 | Nytt ärende introduceras under P2 |
| P2.4 | AI initierar utökning av ärendet |

**P3**

| Kod | Definition | AI:s uppgift |
| --- | --- | --- |
| **P3.1** | Kunden ger all kontaktinfo utan problem | Ta emot och gå vidare |
| **P3.2** | Kunden ger bara del av kontaktinfo | Fråga efter saknad info |
| **P3.3** | Kunden är oklar/tveksam kring kontaktinfo | Förklara varför informationen behövs och samla in korrekt info |

**P4**

| Kod | Definition |
| --- | --- |
| P4.1 | Ingen korrigering |
| P4.2 | En parameter fel |
| P4.3 | Flera parametrar fel eller flera korrigeringsvarv |

**P5**

| Kod | Definition |
| --- | --- |
| P5.1 | Standardavslut |
| P5.2 | Kundinitierat avslut |

brb = har flyttat dem längs ner

# REV 2 – D-systemet

## Grundtanke

P beskriver **var i processen samtalet befinner sig**.

D beskriver **något som tillfälligt avviker från huvudflödet**.

Exempel:

```javascript
P1 → P2 → P3 → P4 → P5
```

är normalflödet.

Om kunden mitt i flödet:

- ställer en fråga
- korrigerar något
- lägger till något

då används D.




# Vad är ett D?

Ett D är en temporär avvikelse.

Dialogen lämnar inte huvudprocessen permanent.

Efter att D är hanterat fortsätter dialogen där den var.

Exempel:

```javascript
P3
↓
D1
↓
P3
```

eller

```javascript
P5
↓
D2
↓
P5
```




# D1 – FAQ-injektion

## Definition

Kunden ställer en informationsfråga.

Ingen bokningsinformation ändras.




## Exempel

```javascript
AI:
Vad heter du?

Kund:
Vad kostar fade?
```

eller

```javascript
AI:
Du är bokad fredag kl 14.

Kund:
Hur lång tid tar det?
```




## Varför D1 finns

Kunden gör ingen ändring.

Kunden vill bara veta något.

Därför behövs inte D2 eller D3.




## Tillåtna faser

| Fas | Tillåten |
| --- | --- |
| P1 | ✓ |
| P2 | ✓ |
| P3 | ✓ |
| P4 | ✓ |
| P5 | ✓ |




# D2 – Enskild korrigering

## Definition

Kunden ändrar en redan etablerad uppgift.




## Exempel

```javascript
Fredag → Torsdag
```

eller

```javascript
Ali → Amir
```

eller

```javascript
0701234567 → 0707654321
```




## Varför D2 finns

Bokningen ändras.

Men bara en sak ändras.




## Tillåtna faser

| Fas | Tillåten |
| --- | --- |
| P1 | ✗ |
| P2 | ✗ |
| P3 | ✓ |
| P4 | ✓ |
| P5 | ✓ |




# D3 – Tillägg

## Definition

Kunden lägger till något nytt.




## Exempel

```javascript
Fade
↓
Fade + Skägg
```

eller

```javascript
Herrklippning
↓
Herrklippning + Tvätt
```




## Varför D3 finns

Informationen fanns inte tidigare.

Den läggs till.




## Tillåtna faser

| Fas | Tillåten |
| --- | --- |
| P1 | ✗ |
| P2 | ✗ |
| P3 | ✓ |
| P4 | ✓ |
| P5 | ✓ |




# D5 – Flera korrigeringar

## Definition

Flera redan etablerade uppgifter ändras samtidigt.




## Exempel

```javascript
Fredag → Torsdag
14:00 → 16:00
```

eller

```javascript
Namn ändras
Telefon ändras
```




## Varför D5 finns

Mer än en sak korrigeras.




## Tillåtna faser

| Fas | Tillåten |
| --- | --- |
| P1 | ✗ |
| P2 | ✗ |
| P3 | ✓ |
| P4 | ✗ |
| P5 | ✓ |




# Varför D4 togs bort

D4 representerade motstånd/obstruktion.

Exempel:

```javascript
Jag vill inte ge nummer.
```

eller

```javascript
Varför behöver ni det?
```

Problemet:

- svår att definiera
- svår att räkna
- överlappar ofta FAQ
- förekommer relativt sällan

D4 skapade mer komplexitet än värde.

Därför togs den bort.




# Varför D inte används i P2

P2 är behovsinsamling.

Exempel:

```javascript
Jag vill boka fade.
Och skägg också.
```

Detta är inte D3.

Kunden håller fortfarande på att bygga bokningen.




Exempel:

```javascript
Jag vill boka fredag.
Nej vänta torsdag.
```

Detta behandlas fortfarande som vanlig behovsinsamling.

Inte som D2.




# Varför D används i P3

Vid P3 finns redan information.

Nu kan kunden:

- ändra
- lägga till
- fråga




# Varför D används i P4

P4 är kontrollfasen.

Korrigeringar under sammanfattningen betraktas som en naturlig del av P4 och inte som avvikelser.
D1 och D3 kan däremot fortfarande förekomma i P4.

Exempel:

```javascript
AI:
Du är bokad fredag kl 14.

Kund:
Nej, torsdag.
```

Detta är:

```javascript
P4.2
På samma sätt klassas:

Flera korrigeringar

som:

P4.3
```




# Varför D används i P5

Kunden kan komma på något i sista sekunden.

Exempel:

```javascript
AI:
Perfekt, då är allt klart.

Kund:
Vänta, lägg till skägg också.
```

Detta är:

```javascript
P5 + D3
```




# Regler för flera D

## Max 2 D per konversation

Tillåtet:

```javascript
D1
```

```javascript
D2
```

```javascript
D2 + D1
```

```javascript
D3 + D5
```

Inte:

```javascript
D1 + D2 + D3
```




# D får upprepas

Tillåtet:

```javascript
D1 + D1
```

```javascript
D2 + D2
```

```javascript
D3 + D3
```

```javascript
D5 + D5
```




# D-ordning räknas inte

Strukturellt är:

```javascript
D1 + D2
```

samma som:

```javascript
D2 + D1
```

Det är samma strukturfall.




# D kan användas i träningsdata

Textmässigt kan båda förekomma:

```javascript
D1 → D2
```

och

```javascript
D2 → D1
```

Men de tillhör samma strukturklass.




# D kan inte avbrytas av D

Tillåtet:

```javascript
P3
↓
D2 + D1
↓
P3
```

Inte:

```javascript
P3
↓
D2
↓
D1
↓
D2
↓
P3
```




# Efter D återgår man till samma fas

Exempel:

```javascript
P4
↓
D1
↓
P4
```

inte:

```javascript
P4
↓
D1
↓
P5
```

D är en paus.

Inte en fasövergång.




# Slutlig D-matris

| D | P1 | P2 | P3 | P4 | P5 |
| --- | --- | --- | --- | --- | --- |
| D1 | ✓ | ✓ | ✓ | ✓ | ✓ |
| D2 | ✗ | ✗ | ✓ | ✗ | ✓ |
| D3 | ✗ | ✗ | ✓ | ✓ | ✓ |
| D5 | ✗ | ✗ | ✓ | ✗ | ✓ |




# Slutlig filosofi

**P beskriver processen.**

```javascript
P1 → P2 → P3 → P4 → P5
```

**D beskriver avvikelser från processen.**

```javascript
FAQ
Korrigering
Tillägg
Flera korrigeringar
```

Detta är den REV 2-definition av D som vi har landat i efter granskningen.




**vaild eller invalid totalt**

Totala P =288 genom att 4x4x3x3x2 
288 x 91= 26208st 

| D | Tillåtna P | Antal |
| --- | --- | --- |
| D1 | P1, P2, P3, P4, P5 | 5 |
| D2 | P3, P5 | 2 |
| D3 | P3, P4, P5 | 3 |
| D5 | P3, P5 | 2 |

total 12st när vi kör med 1 D per konversation, kolla på tabellen. 1 fall där ingen D används.

vi har tillåtit 2 D per konverastion osv läs regler längre ner och det ger oss formula "D₂ = C(n+r-1 dela på r)"

D₂ = (13 × 12) / 2= 78 +1+12= 91 

n= antal 1st d per konversation 

r= antal tillåtna D per konversation 

-1= Det kommer från den klassiska "stars and bars"-beviset inom kombinatorik.


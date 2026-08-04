# TrÃ¤ningsdataarkitektur
### Intentklassificering â€” Inkommande Salongsamtal
`RITNING v4 â€” PÃ…GÃ…R`

---

## Makro
*Sessionsglobal. Definieras en gÃ¥ng per mall. BegrÃ¤nsar alla mesobeslut under.*

```yaml
formalitet:
  alternativ: [F1, F2, F3, F4]
  mall:       <enskilt vÃ¤rde>
  F1: formell      â€” "Jag skulle vilja boka en tid fÃ¶r en fade"
  F2: neutral      â€” "Hej, kan jag boka en fade?"
  F3: informell    â€” "Tjena, jag vill ha en fade"
  F4: komprimerad  â€” "En fade, lÃ¶rdag"

faser:
  sekvens: [P1, P2, P3, P4, P5]
  ordning: fast
  mall:    alla aktiva

avvikelse:
  nÃ¤rvarande: [true, false]
  typ:        [D1, D2, D3, D5]
  injiceras:  [P2, P3, P4, P5]
  mall:       <enskilt vÃ¤rde per parameter>

turer:
  tak:     25 kundturer per session  # AI-turer genereras men tas bort fÃ¶re trÃ¤ning
  rÃ¤knas:  endast kundturer

  intervall:           # begrÃ¤nsningar pÃ¥ arkitekturnivÃ¥
    P1:  1-3
    P2:  1-8
    P3:  1-5
    P4:  1-6
    P5:  1-2
    D:   1-4

  tilldelning:
    1. avvikelse nÃ¤rvarande? â†’ reservera D-budget fÃ¶rst
    2. fÃ¶rdela Ã¥terstÃ¥ende budget Ã¶ver P1-P5
    3. generatorn vÃ¤ljer enskilt vÃ¤rde per fas inom tilldelad del
    notering: intervallbegrÃ¤nsning och tak mÃ¥ste bÃ¥da gÃ¤lla samtidigt

  mall: <enskilt valt vÃ¤rde per fas>
```

---

## Meso
*FasnivÃ¥. Ett ramtillstÃ¥nd valt per aktiv fas per mall. TurvÃ¤rde skickas ned frÃ¥n makro som ett enskilt fast nummer.*

---

```yaml
P1 â€” Ã–ppning
ingÃ¥ng: samtal ansluts
utgÃ¥ng: fÃ¶rsta klassificerbara intent fÃ¥ngad ELLER Ã¶verlÃ¤mning till P2

  P1.1: initiativtagare=AI      tÃ¤thet=minimal  # ingen intent angiven
  P1.2: initiativtagare=AI      tÃ¤thet=rik      # intent angiven omedelbart
  P1.3: initiativtagare=Kund    tÃ¤thet=minimal  # vag eller enbart hÃ¤lsning
  P1.4: initiativtagare=Kund    tÃ¤thet=rik      # full intent angiven direkt

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  noter:
    SmallTalk hem: P1.1, P1.3
    P1.2 / P1.4: intentbÃ¤rande turer tillhÃ¶r Ã–ppning tills AI bÃ¶rjar strukturerad insamling
    P1 stÃ¤ngd fÃ¶r all avvikelse
```

---

```yaml
P2 â€” Behovsanalys
ingÃ¥ng: fÃ¶rsta intent fÃ¥ngad
utgÃ¥ng: alla intenter lÃ¶sta, Ã¶vergÃ¥ng till P3

  P2.1: intenter=enskild   upptÃ¤ckt=omedelbar
  P2.2: intenter=flera     upptÃ¤ckt=angivna tillsammans
  P2.3: intenter=flera     upptÃ¤ckt=sekventiell    # kunden driver
  P2.4: intenter=flera     upptÃ¤ckt=AI-promptad    # AI driver

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  noter:
    tjÃ¤nstepool drar N gÃ¥nger (N = intentantal)
    bokningspool drar en gÃ¥ng, delas Ã¶ver alla intenter
    D3 giltig endast efter P2:s naturliga stÃ¤ngningspunkt
    fÃ¶re stÃ¤ngningspunkt: tillÃ¤gg Ã¤r P2.3 eller P2.4 inte D3
```

---

```yaml
P3 â€” Autentisering
ingÃ¥ng: alla intenter fÃ¥ngade
utgÃ¥ng: namn och nummer insamlade

  P3.1: insamling=ren      # namn och nummer, fÃ¶rsta fÃ¶rsÃ¶ket
  P3.2: insamling=partiell # ett angivet, AI uppmanar till resten
  P3.3: insamling=oklar    # formateringsproblem eller tvetydighet

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  noter:
    namn och nummer endast â€” ingen systemsÃ¶kning
    autentiseringspool drar en gÃ¥ng, ingen interaktion med tjÃ¤nste- eller bokningspooler
```

---

```yaml
P4 â€” BekrÃ¤ftelse
ingÃ¥ng: fullstÃ¤ndig bokningspost insamlad
utgÃ¥ng: kunden bekrÃ¤ftar sammanfattning, Ã¶vergÃ¥ng till P5

  P4.1: korrigering=ingen         # kunden godkÃ¤nner fullstÃ¤ndig sammanfattning
  P4.2: korrigering=mindre        # en parameter fel
  P4.3: korrigering=betydande     # flera parametrar, flera korrigeringsvarv

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  noter:
    korrigeringar inom P4 = P4-turer med korrigerings-subintent â€” INTE avvikelse
    P4.2: en av [tid, tjÃ¤nst, dag] fel
    P4.3: flera parametrar fel
```

---

```yaml
P5 â€” Avslutning
ingÃ¥ng: bekrÃ¤ftelse klar, bokning slutfÃ¶rd
utgÃ¥ng: samtal avslutas

  P5.1: avslut=AI-drivet         # bekrÃ¤ftelse skickad, naturligt adjÃ¶
  P5.2: avslut=kundinitierat     # tidigt avslut

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  noter:
    fÃ¶rfrÃ¥gningar om ny information vid P5 = D3-inject, inte P5-variant
    D3 vid P5 Ã¤r enda fallet med partiell sekvensupprepning (P2 â†’ P3 â†’ P4)
    kan Ã¶verskrida sessionstaket i grÃ¤nsfall
```

---

```yaml
D â€” Avvikelse
natur:  andra dimensionella lagret â€” suspenderar primÃ¤rsekvensen, lÃ¶ser, Ã¥tergÃ¥r till suspensionspunkten
        ingen position i fassekvensen
        definierad identiskt med faser: tillstÃ¥nd + turbegrÃ¤nsning

ingÃ¥ng: avvikelsetrigger inom giltig fas
utgÃ¥ng: lÃ¶sning nÃ¥dd, primÃ¤rsekvensen Ã¥terupptas

  D1: typ=informationsfÃ¶rfrÃ¥gan  # fÃ¶rtydligande innan fortsÃ¤ttning
  D2: typ=enskild-korrigering    # en tidigare angiven parameter Ã¤ndrad
  D3: typ=tillÃ¤gg                # nytt krav som inte tidigare angetts
  D5: typ=flera-korrigeringar    # flera parametrar Ã¤ndrade samtidigt

  turer:  TBD
  mall:   <enskilt tillstÃ¥nd> <enskilt turvÃ¤rde>

  inject-giltighet:
          P1    P2    P3    P4    P5
    D1    âœ—     âœ“     âœ“     âœ“     âœ—
    D2    âœ—     âœ“     âœ“     âœ—     âœ—
    D3    âœ—     âœ“     âœ“     âœ“     âœ“
    D5    âœ—     âœ“     âœ“     âœ—     âœ—

  poolrelation:
    D1: refererar fÃ¶rbrukad â€” inga nya drag
    D2: krÃ¤ver fÃ¶rbrukad    â€” drar frÃ¥n fÃ¶rbrukad mÃ¤ngd, typat
    D3: utesluter fÃ¶rbrukad â€” drar utanfÃ¶r fÃ¶rbrukad mÃ¤ngd, typat
    D5: krÃ¤ver fÃ¶rbrukad    â€” flera drag frÃ¥n fÃ¶rbrukad mÃ¤ngd, typat

  dubbelmÃ¤rkning nÃ¤r aktiv:
    fas:       [nuvarande fas]
    avvikelse: [Dx]
    status:    aktiv | lÃ¶ser | stÃ¤ngd
```

---

## Mikro
*Generativt material. FullstÃ¤ndigt oberoende â€” redigering av poolinnehÃ¥ll pÃ¥verkar inte makro eller meso.*

---

```yaml
pooler:

  tjÃ¤nst:
    innehÃ¥ll: [fade, skÃ¤gg, fÃ¤rg, klippning, toner, behandling, slingor, rakning, styling, Ã¶gonbryn]
    drag:     N per session (N = intentantal frÃ¥n P2-tillstÃ¥nd)

  bokning:
    tid:      [09:00, 10:00, 11:00, 13:00, 14:00, 15:00, 16:00, 17:00]
    dag:      [mÃ¥ndag, tisdag, onsdag, torsdag, fredag, lÃ¶rdag]
    stylist:  [Ahmed, Khalid, ingen preferens]
    typ:      [boka, omboka, avboka]
    drag:     1 per session, delas Ã¶ver alla intenter

  autentisering:
    namn:     [svenska och vanliga fÃ¶rnamn]
    nummer:   [format: 07XXXXXXXX]
    drag:     1 per session
```

---

```yaml
fÃ¶rbrukad mÃ¤ngd:
  typning: pooltypat â€” ett fÃ¶rbrukat tidsvÃ¤rde begrÃ¤nsar inte tjÃ¤nstedrag
  scope:   fylls av fasdrag, lÃ¤ses av avvikelseram

  tjÃ¤nst:  []
  tid:     []
  dag:     []
  stylist: []
```

---

## Ã–ppet
```
â€” MÃ¶nsterexkluderingsregler pÃ¥ makronivÃ¥                    (TBD â€” efter generering)
â€” Distributionstargets per mesotillstÃ¥nd Ã¶ver korpus        (TBD)
â€” Mallgeneratorns giltighetsfunktion                        (TBD)
â€” Formalitet: sessionsglobal tillÃ¤mpning vs registerglidning (TBD)
â€” FÃ¶rbrukad mÃ¤ngd-timing inom fas                           (TBD)
```

---

## Exempel

TvÃ¥ block. FÃ¶rsta Ã¤r mallen generatorn producerar. Andra Ã¤r vad AI genererar frÃ¥n den â€” rÃ¥ dialog innan AI-turer tas bort.

```yaml
# MALL_0041

makro:
  formalitet: F2
  faser:      [P1, P2, P3, P4, P5]
  avvikelse:  false

  turer:
    P1: 1
    P2: 1
    P3: 1
    P4: 1
    P5: 1
    totala_kundturer: 5

meso:
  P1: tillstÃ¥nd=P1.2   # AI initierar, kunden anger intent omedelbart
  P2: tillstÃ¥nd=P2.1   # enskild intent, angiven omedelbart
  P3: tillstÃ¥nd=P3.1   # ren â€” namn och nummer fÃ¶rsta fÃ¶rsÃ¶ket
  P4: tillstÃ¥nd=P4.1   # ren bekrÃ¤ftelse
  P5: tillstÃ¥nd=P5.1   # rent avslut

mikro:
  drag:
    tjÃ¤nst: [fade]
    bokning:
      tid:     10:00
      dag:     fredag
      stylist: Ahmed
      typ:     boka
    autentisering:
      namn:    Erik
      nummer:  0734521890
```

```
# GENERERAD_0041
# formalitet: F2 â€” neutral
# AI-turer nÃ¤rvarande â€” tas bort fÃ¶re trÃ¤ning, visas hÃ¤r fÃ¶r koherens

[P1 â€” Ã–ppning]
AI:    Hej, vÃ¤lkommen till salongen! Hur kan jag hjÃ¤lpa dig idag?
Kund:  Hej, jag skulle vilja boka en fade.
       mlp1: x  mlp2: y

[P2 â€” Behovsanalys]
AI:    SjÃ¤lvklart! Har du nÃ¥gon tid, dag eller stylist du fÃ¶redrar?
Kund:  Ja, fredag kl 10 med Ahmed om det gÃ¥r.
       mlp1: x  mlp2: y

[P3 â€” Autentisering]
AI:    Perfekt, det ordnar vi. FÃ¥r jag ditt namn och telefonnummer?
Kund:  Erik Lindqvist, 0734521890.
       mlp1: x  mlp2: y

[P4 â€” BekrÃ¤ftelse]
AI:    Toppen! Jag bekrÃ¤ftar: en fade med Ahmed, fredag kl 10:00. StÃ¤mmer det?
Kund:  Ja, det stÃ¤mmer.
       mlp1: x  mlp2: y

[P5 â€” Avslutning]
AI:    UtmÃ¤rkt, bokningen Ã¤r klar! Du fÃ¥r en bekrÃ¤ftelse pÃ¥ ditt nummer. Ha en bra dag!
Kund:  Tack, det samma!
       mlp1: x  mlp2: y
```


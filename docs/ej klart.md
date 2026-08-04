För att 15, 12, 7, 5 är övergångsantal, inte oberoende block.
Man får alltså inte räkna:
15 × 12 × 7 × 5
Det skulle dubbelräkna P2, P3 och P4 flera gånger.
Rätt sätt:
1. P1→P2
15 giltiga par.
2. För varje P1→P2-par finns P3-fortsättning
P2 påverkar inte P3, så P3 kan vara:
P3.1, P3.2, P3.3 = 3 val
Då:
15 × 3 = 45
3. Lägg på P4 och P5 enligt reglerna
Om P3.1 → 5 möjliga P4/P5-slut
Om P3.2 → 5 möjliga P4/P5-slut
Om P3.3 → 2 möjliga P4/P5-slut
Alltså per P1→P2-par:
5 + 5 + 2 = 12 möjliga slut
4. Total
15 × 12 = 180
Det är därför siffran blir:
180 giltiga P-kedjor

Fördelning per P3
Eftersom varje P1→P2-par kan fortsätta med:
5 varianter via P3.1
5 varianter via P3.2
2 varianter via P3.3
blir det:
P3
Beräkning
Antal
P3.1
15 × 5
75
P3.2
15 × 5
75
P3.3
15 × 2
30
Total:
75 + 75 + 30 = 180

Just nu har vi:
Ny regel: max 2 D
P-strukturer:
180
D-lägen:
0 D
1
1 D
4 D-typer × 2 platser:
4 × 2 = 8
2 D
Totalt:
36
Därför:
1 + 8 + 36 = 45 D-lägen
Total:
180 × 45 = 8 100

Så:
Regel
Total
Max 1 D
1 620
Max 2 D
8100

D-regel
Antal
0 D
180
exakt 1 D
1 440
exakt 2 D
6 480
Totalt max 2 D
8 100
Beräkning:
180 + 1 440 + 6 480 = 8 100 

D-regler
Max 2 D per konversation
D kan ligga i P3 eller P4
D kan ligga båda i P3
D kan ligga båda i P4
D kan delas mellan P3 och P4
D får upprepas
D-ordning räknas inte
Två D i samma fas är tillåtet
P-varianten ändras inte av D
D3 + D3 kräver plats för två nya tjänster (poolregel)

nu när vi har 8100 unika utfall så tycker jag att resten alltså språk, antal turer och pooldrag ska komma in och då beräknar vi templets. 
antal template kommer öka eftersom bokning, avbokning och ombokning kräver olika mycket info.

alltså 
Pooldrag			Bokning		avbokning		ombokning


Tjänst				 ja			nej				nej

Dag				 	 ja			x				nej

Tid 				 ja			x				nej

Namn				 ja			ja				ja

Telefonnummer		 ja			ja				ja

Frisör				 x			nej				nej


D-beräkning

D-typer:

D1 = informationsförfrågan
D2 = enskild korrigering
D3 = tillägg
D5 = flera korrigeringar

Regler:

- Max 2 D per konversation
- D kan ligga i P3 eller P4
- D kan ligga båda i P3
- D kan ligga båda i P4
- D kan delas mellan P3 och P4
- D får upprepas
- D-ordning räknas inte i strukturberäkningen
- Två D i samma fas är tillåtet
- P-varianten ändras inte av D
- D3 + D3 kräver plats för två nya tjänster (poolregel)

D-kombinationer utan placering

0 D: 1

1 D:
D1
D2
D3
D5
Antal: 4
2 D:
D1 + D1
D1 + D2
D1 + D3
D1 + D5
D2 + D2
D2 + D3
D2 + D5
D3 + D3
D3 + D5
D5 + D5
Antal: 10
Totalt antal D-kombinationer utan placering:
1 + 4 + 10 = 15
D-lägen med placering
0 D: 1
1 D:4 
D-typer × 2 placeringar (P3 eller P4)
4 × 2 = 8
2 D:
Fyra lika par:
D1+D1
D2+D2
D3+D3
D5+D5
Varje par kan placeras på 3 sätt:
- båda i P3
- båda i P4
- en i P3 och en i P4
4 × 3 = 12
Sex olika par:
D1+D2
D1+D3
D1+D5
D2+D3
D2+D5
D3+D5
Varje par kan placeras på 4 sätt:
- båda i P3
- båda i P4
- första i P3 och andra i P4
- första i P4 och andra i P3
6 × 4 = 24
Totalt för 2 D:
12 + 24 = 36
Totalt antal D-lägen:
0 D = 1
1 D = 8
2 D = 36
1 + 8 + 36 = 45
Slutlig strukturberäkning
P-kedjor:
180
D-lägen:
45
Totalt:
180 × 45 = 8 100 strukturutfall

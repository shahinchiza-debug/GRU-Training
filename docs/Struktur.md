Generatorns struktur

Systemet består av två indatafiler, tre bearbetningssteg och en valideringsfas. Varje steg läser från föregående stegs utmapp och skriver till sin egen. Ingenting skickas i minnet mellan stegen, allt går via disk.


Indatafiler

structure.json är den låsta filen. Den innehåller alla giltiga tillstånd per fas, turintervallar, avvikelseregler, consumed set-regler, giltighetsmatris och distributionstargets per parameter. Den här filen förändras bara när arkitekturen förändras.

variables.json innehåller bara poolinnehåll utan någon logik. Tjänster, tider, dagar, personal, namn, telefonnummer. Den här filen kan ändras fritt utan att någonting i generatorn behöver röras.


Mappstruktur

/input
  structure.json
  variables.json

/stage1_output
  stage1_combinations.json

/stage2_output
  stage2_stamped.json

/stage3_output
  T_000001.json
  T_000002.json
  ...

/validation
  validation_report.json



Steg 1 — Strukturell enumeration

Läser från structure.json. Räknar upp alla unika meningsfulla kombinationer av fasstates, avvikelsetyp, injektionspunkt och intentantal per fas där intent förekommer. Varje kombination här är strukturellt distinkt från alla andra, inte bara en ytvariaton utan en faktisk skillnad i vad modellen behöver lära sig. Skriver resultatet till stage1_output.

Det här steget producerar den minsta möjliga mängden strukturellt unika sessioner. Ingenting läggs till, ingenting tas bort. Bara den kompletta strukturella rymden.

10k - vilka kombinationer ogiltiga.
efter alla x kombinatorer gjorda kör igenom alla x exemplar med filter (mamads logik) som excluderar alla från temp mappen tll tex. ogiltig mapp.
så steg ett blir 2 delar.

Steg 2 — Distributionslager

Läser från stage1_output och structure.json. Skapar inga nya strukturella kombinationer. Tar de befintliga kombinationerna från Steg 1 och stämplar varje mall med formalitet och turantal enligt de distributionstargets som är definierade i structure.json. Exempelvis får 25 procent av mallarna F1, 35 procent F2 och så vidare. 10 procent får turantal 8 på P2 och så vidare. Det här är lagret där du kontrollerar de distributionella egenskaperna i korpuset utan att röra strukturen. Skriver resultatet till stage2_output.


Steg 3 — Pooltilldelning

Läser från stage2_output och variables.json. Fyller i innehållsvariablerna per mall. Det enda som inte är rent slumpmässigt här är exekveringsordningen och consumed set-logiken inom en enskild mall.

Exekveringsordning inom varje mall är fast. Fasdragen sker först i fasordning, avvikelsedrag sker sist. Det beror på att avvikelsens poolregler är definierade relativt vad faserna redan förbrukat. Om avvikelsedraget sker först är consumed set tomt och begränsningen blir meningslös.

Consumed set är en enkel dictionary som skapas i början av varje mall, populeras i fasordning, läses vid avvikelsedraget och sedan kasseras. Mellan mallar nollställs allt, inget minne förs vidare.

Exekveringsordning per mall:

P1 drag → P2 drag → P3 drag → P4 drag → P5 drag → avvikelsedrag
consumed set kontrolleras endast vid avvikelsedraget
nollställs efter att mallen är klar


Skriver varje komplett mall som en egen JSON-fil till stage3_output.


Validering

Läser från stage3_output och structure.json. Kontrollerar strukturell giltighet, consumed set-integritet och att turtak på 25 kundturer efterlevs. Skriver en valideringsrapport till validation-mappen. Valideringen är helt oberoende av hur mallarna genererades, den kontrollerar bara om de är giltiga.


main.py

Enda startpunkten. Anropar Steg 1, Steg 2 och Steg 3 i sekvens och hanterar mappvägarna. Ingenting annat.


Metadata per steg

Varje steg skriver en liten metadatafil tillsammans med sin output. Tidsstämpel, antal producerade poster och eventuella varningar. Billigt att lägga till och mycket användbart när något ser fel ut i den slutliga outputen och du behöver veta vilket steg som introducerade problemet.
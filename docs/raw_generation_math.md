# Raw Generation Math

Detta dokument beskriver den helt råa steg-1-modellen.

Syftet här är att räkna upp alla möjliga råa mallar innan något filter används.

## Grundidé

I steg 1 behandlas `D_1` och `D_2` som två råa slots.

Ingen giltighetslogik används här.

Det betyder:

- ingen kontroll av om en viss `D` egentligen borde vara förbjuden i en viss fas
- ingen kontroll av om samma `D` upprepas
- ingen kontroll av om ordningen borde räknas som samma struktur
- ingen kontroll av om två `D` tillsammans borde bli ogiltiga

All sådan logik skjuts till steg 2.

## P-rummet

Antal fas-states:

- `P1 = 4`
- `P2 = 4`
- `P3 = 3`
- `P4 = 3`
- `P5 = 2`

Alltså:

```text
4 × 4 × 3 × 3 × 2 = 288
```

Så totalt antal råa `P`-kedjor är:

```text
288
```

## D-rummet

Aktiva deviation-typer i nuvarande modell:

- `D1` med faser `P1, P2, P3, P4, P5` = `5`
- `D2` med faser `P3, P5` = `2`
- `D3` med faser `P3, P4, P5` = `3`
- `D5` med faser `P3, P5` = `2`

Totalt antal atomära `D`-val:

```text
5 + 2 + 3 + 2 = 12
```

## 0 deviations

Inget `D` används:

```text
1
```

## 1 deviation

En deviation betyder att `D_1` fylls med ett av de `12` atomära valen och `D_2` lämnas tom.

Alltså:

```text
12
```

## 2 deviations

Två deviations i råmodellen betyder:

- `D_1` kan vara vilket som helst av `12` val
- `D_2` kan vara vilket som helst av `12` val

Ingen filtrering görs.

Alltså:

```text
12 × 12 = 144
```

Detta inkluderar även fall som senare kan bli ogiltiga, till exempel:

- samma `D` i båda slots
- `D` i faser som senare inte tillåts
- kombinationer som senare borde kollapsa till samma struktur

## Totalt D-rum

```text
0D = 1
1D = 12
2D = 144
```

Alltså:

```text
1 + 12 + 144 = 157
```

## Total rå rymd

```text
P = 288
D = 157
```

Alltså:

```text
288 × 157 = 45,216
```

## Slutsats

Steg 1 ska alltså generera:

```text
45,216 råa mallar
```

Steg 2 får sedan ta över och dela upp dem i:

- giltiga
- ogiltiga

Det är därför steg 1 medvetet får vara större och "smutsigare" än den slutliga giltiga strukturmängden.

# App

Den här mappen innehåller all aktiv kod för generatorn.

## Innehåll

- `main.py`
  - Huvudingång för pipelinen.

- `pipeline/`
  - Manifest, stage-katalog och orchestrator.

- `stages/`
  - Ett steg per undermapp.
  - Varje steg har en egen `run.py`.

- `shared/`
  - Reservyta för gemensamma helpers om ni senare vill bryta ut delad logik.

## Exempel

Kör kommandona från projektets rotmapp. Börja alltid med `--dry-run` när du vill kontrollera vad som kommer att köras.

```powershell
python .\app\main.py --list
python .\app\main.py --dry-run
python .\app\main.py --only stage1 stage2 stage3
```

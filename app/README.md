# App

Den har mappen innehaller all aktiv kod for generatorn.

## Innehall

- `main.py`
  - Huvudingang for pipelinen.

- `pipeline/`
  - Manifest, stage-katalog och orchestrator.

- `stages/`
  - Ett steg per undermapp.
  - Varje steg har en egen `run.py`.

- `shared/`
  - Reservyta for gemensamma helpers om ni senare vill bryta ut delad logik.

## Exempel

```powershell
python .\app\main.py --list
python .\app\main.py --dry-run
python .\app\main.py --only stage1 stage2 stage3
```

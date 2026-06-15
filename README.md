# APEX6

Sistema de pronóstico enfocado, derivado de **CLAUDE-LOTMIX** (motor `clotmix` /
`runner33.py`). Reutiliza el mismo motor de análisis (ventanas temporales,
MI condicional, Markov de orden 2 — `src/analyze.py`) pero reduce el alcance
a las **6 loterías/horarios con mejor desempeño real** medido sobre los
últimos 3 meses de datos, y añade una capa de filtrado/categorización
calibrada para decidir cuándo notificar.

Repo independiente: tiene su propio `data/picks_log.csv` y
`outputs/performance.csv`, totalmente separados de CLAUDE-LOTMIX, para poder
seguir ajustando parámetros sin afectar el sistema original.

## 1. Cobertura (SCHEDULE)

| Categoría     | Lotería      | Sorteo                      | Hora (RD)        |
|---------------|--------------|------------------------------|------------------|
| 🟢 NÚCLEO     | La Primera   | Quiniela La Primera          | 12:00            |
| 🟢 NÚCLEO     | Anguilla     | Anguila 1PM                  | 13:00            |
| 🟢 NÚCLEO     | Anguilla     | Anguila 6PM                  | 18:00            |
| 🟢 NÚCLEO     | Anguilla     | Anguila 9PM                  | 21:00            |
| 🟢 NÚCLEO     | La Nacional  | Lotería Nacional - Gana Más  | 14:30            |
| 🟡 VIGILANCIA | La Nacional  | Lotería Nacional - Noche     | 21:00 (18:00 domingos) |

## 2. Capa de filtrado / categorización

Después de que el motor genera el `top12` y calcula `best_signal` / `best_a11`
(igual que en CLAUDE-LOTMIX), `classify_pick()` decide si se notifica:

```python
THRESHOLDS = {
    "NUCLEO":     {"a11_min": 2, "a11_max": 4, "signal_min": 0.009, "signal_max": 0.029},
    "VIGILANCIA": {"a11_min": 2, "a11_max": 4, "signal_min": 0.005, "signal_max": 0.035},
}
```

- Si `best_a11` y `best_signal` caen dentro del rango de su categoría →
  `✅ JUGAR — NÚCLEO` o `🔍 JUGAR — VIGILANCIA` (se envía a Telegram).
- Si no → `❌ NO JUGAR` (se registra en `picks_log.csv` para análisis, pero
  **no** se envía a Telegram, para no saturar el canal).

Estos umbrales fueron calibrados sobre los datos de
`performance_clotmix.csv` (marzo-junio 2026):

- NÚCLEO: 41.5% de acierto en 94 sorteos (vs. ~30.6% esperado por azar)
- VIGILANCIA (Nacional Noche): 36.0% de acierto en 25 sorteos

Revisa `tools/backtest_apex6.py` periódicamente para confirmar que estos
rangos siguen siendo válidos con datos nuevos, y ajusta `THRESHOLDS` /
`CATEGORY` en `src/runner_apex6.py` si es necesario.

## 3. Instalación

### 3.1. Históricos (data/histories/)

Este repo necesita los archivos de histórico (`.xlsx`) de las 3 loterías
usadas (La Primera, Anguilla, La Nacional). **Cópialos desde CLAUDE-LOTMIX**
como punto de partida — a partir de ahí cada repo actualiza su propia copia
de forma independiente:

```bash
# Desde una copia local de CLAUDE-LOTMIX
cp "CLAUDE-LOTMIX/data/histories/La Primera History.xlsx"   "CLAUDE-APEX6/data/histories/"
cp "CLAUDE-LOTMIX/data/histories/Anguilla history.xlsx"      "CLAUDE-APEX6/data/histories/"
cp "CLAUDE-LOTMIX/data/histories/La nacional history.xlsx"   "CLAUDE-APEX6/data/histories/"
```

Sin estos archivos, el runner no tiene historial suficiente
(`MIN_SOURCE_ROWS = 1500`) y no generará picks la primera vez — solo hará
backfill de resultados nuevos.

### 3.2. Telegram (canal separado)

1. Crea un bot nuevo con [@BotFather](https://t.me/BotFather) (o reutiliza uno
   que no esté en uso) → obtén el `TELEGRAM_BOT_TOKEN`.
2. Crea un canal/grupo nuevo de Telegram para APEX6, añade el bot como
   administrador, y obtén el `TELEGRAM_CHAT_ID` (puedes usar
   `https://api.telegram.org/bot<token>/getUpdates` después de enviar un
   mensaje de prueba al canal).
3. Configura ambos valores como **secrets** del repo.

### 3.3. Gitea

1. Crea el repo `CLAUDE-APEX6` en Gitea y sube todo este contenido.
2. En **Settings → Actions → Secrets**, agrega:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GITEA_TOKEN` (token con permiso `write:repository` para que el workflow
     pueda hacer commit/push de los datos actualizados)
3. El workflow `.gitea/workflows/apex6.yml` corre automáticamente según el
   cron configurado, o manualmente desde **Actions → APEX6 → Run workflow**.

### 3.4. GitHub (espejo)

1. Crea el repo `CLAUDE-APEX6` en GitHub y sube el mismo contenido (o
   configura un mirror desde Gitea).
2. En **Settings → Secrets and variables → Actions**, agrega:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   (`GITHUB_TOKEN` ya está disponible automáticamente, no hace falta crearlo).
3. El workflow `.github/workflows/apex6.yml` corre con el mismo cron.

> ⚠️ Si tienes **ambos** workflows activos (Gitea y GitHub) apuntando al mismo
> repo remoto, los dos intentarán hacer commit de `data/` y `outputs/` y
> pueden generar conflictos. Recomendación: dejar **uno solo** como la
> instancia "viva" que escribe datos (por ejemplo Gitea, igual que
> CLAUDE-LOTMIX), y el otro espejo solo para respaldo de código
> (deshabilita su `schedule` o el job de commit).

## 4. Ejecución manual / pruebas

```bash
pip install -r requirements.txt

# Backfill de históricos + grading, sin enviar Telegram (FORCE_NOTIFY=0)
python src/runner_apex6.py

# Forzar notificación de prueba a Telegram
FORCE_NOTIFY=1 python src/runner_apex6.py

# Revisar desempeño acumulado
python tools/backtest_apex6.py --days 90
```

## 5. Estructura

```
CLAUDE-APEX6/
├── .gitea/workflows/apex6.yml
├── .github/workflows/apex6.yml
├── data/
│   ├── histories/          # .xlsx — copiar desde CLAUDE-LOTMIX (ver 3.1)
│   ├── picks_log.csv        # log de picks generados (propio, independiente)
│   └── state.json           # se crea automáticamente
├── outputs/
│   ├── performance.csv      # resultado calificado de cada pick (propio)
│   ├── picks.json
│   └── picks_all.json
├── src/
│   ├── runner_apex6.py      # orquestador principal
│   ├── analyze.py           # motor de análisis (idéntico a CLAUDE-LOTMIX)
│   ├── io_xlsx.py
│   ├── telegram.py
│   └── scrapers/
│       ├── scraper_base.py
│       ├── anguilla_scraper.py
│       ├── laprimera_scraper.py
│       └── lanacional_scraper.py
├── tools/
│   └── backtest_apex6.py
└── requirements.txt
```

## 6. Próximos ajustes

Este sistema está pensado para iterar: a medida que `outputs/performance.csv`
acumule datos propios, usa `tools/backtest_apex6.py` para revisar si:

- Los rangos de `THRESHOLDS` (NÚCLEO/VIGILANCIA) siguen siendo óptimos.
- `Loteria Nacional - Noche` (VIGILANCIA) debería pasar a NÚCLEO, mantenerse,
  o salir del sistema.
- Alguna lotería del NÚCLEO se está debilitando y debería bajar a
  VIGILANCIA o salir.

Todos estos ajustes se hacen editando `CATEGORY` y `THRESHOLDS` en
`src/runner_apex6.py` — no requieren tocar el motor de análisis.

# Weather-Aware Truck Routing

A dispatcher enters an origin, a destination, a departure time, and a load weight. The app asks a routing service for three driving routes, samples the forecast along each one at the truck's estimated arrival time, and recommends the route with the least dangerous weather. A map shows the routes and the checkpoints. A slider plays the next 48 hours of weather along the corridor without calling the server again.

## Architecture

The browser is a React app (Vite, TypeScript, Leaflet). It only collects the trip and draws the result.

The API is Django and Django REST framework. One `POST /api/plan/` does the work:

1. Ask OSRM for driving alternatives.
2. If that is fewer than three distinct routes, ask again through a via point.
3. Walk each route and drop a checkpoint every 10, 25, or 50 miles.
4. Ask Open-Meteo once for those points and for a corridor grid, from the departure hour through 48 hours (or the end of the trip, whichever is later).
5. Classify every checkpoint, total the miles, and rank the routes.

Routing, sampling, unit conversion, risk, and ranking are plain functions under `backend/planner/logic/`. The HTTP calls live in `backend/planner/services/`. The views check the form and return JSON.

```
browser  -- POST /api/plan/ -->  Django
                                  |-- OSRM (routes)
                                  |-- Open-Meteo (one batched forecast)
                                  '-- risk + ranking
browser  <-- routes, checkpoints, 48-hour grid
slider   -- redraws the grid locally, no new request
```

## Risk rules

A checkpoint's risk is the worst of wind, rain, and snow. Clear weather is Low. There is no separate "none" class.

Weather values are continuous, so the table's ranges are applied like this. A number that sits on two columns takes the worse class. Wind has no overlap: each band runs up to, but not including, the next threshold. So 34.9 mph is moderate and 35.0 mph is high. There is no gap between 34 and 35.

| | Low | Moderate | High | Severe | No travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 ≤ x < 35 | 35 ≤ x < 45 | 45 ≤ x < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 ≤ x < 0.25 | 0.25 ≤ x < 0.50 | 0.50 ≤ x ≤ 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 ≤ x < 1.0 | 1.0 ≤ x < 2.0 | 2.0 ≤ x ≤ 3.0 | > 3.0 |

Rain at exactly 1.00 in/hr is severe, and snow at exactly 3.0 in/hr is severe, because no-travel for those two is only *above* the top of the severe column. Wind no-travel starts at 55, and 55 is included.

Negative weather readings are treated as zero.

### Load

Load changes wind only, and only upward.

- Wind ≥ 55 mph is no-travel for any load.
- 45 ≤ wind < 55 and the load is over 30,000 lb: no-travel.
- 35 ≤ wind < 45 and the load is over 40,000 lb: severe.
- Exactly 30,000 lb or exactly 40,000 lb does not trigger the rule. The spec says "greater than."

Rain and snow are not affected by the load. After the wind class is adjusted, the checkpoint is still the worst of the three.

### Miles

Checkpoints sit on the road, including the origin and the destination. The destination is kept even when the length is not a multiple of the interval.

Each mile is classified by the nearest checkpoint. An interior checkpoint owns the road halfway back to the previous one and halfway forward to the next one, so one bad sample counts about one interval, and the pieces add up to the route length.

Average risk is the mile-weighted score: low 1, moderate 2, high 3, severe 4, no-travel 5.

Miles are rounded to 0.1, average risk to 0.01, and duration to the nearest minute before the routes are compared, so the order matches the numbers on the card.

## Recommendation

Best route first:

1. Fewest no-travel miles.
2. Fewest severe miles.
3. Fewest high miles.
4. Lowest average risk.
5. Shortest travel time.

No-travel is its own first key, ahead of severe miles. A stretch that should not be driven is worse than a severe stretch, so any no-travel miles lose to a route that has none, even if that other route has many more severe miles.

If every factor ties, the first route returned is shown.

The card explains the first factor that separated the winner from the closest other route.

Worked example. Two 100-mile routes, checkpoints every 25 miles, all in the same conditions:

- Windy: 36 mph, no rain. At 10,000 lb that wind is high, so the route has 0 severe miles.
- Wet: calm wind, 0.80 in/hr of rain. That is severe for the whole distance.

Windy wins, because severe miles are checked before travel time. Raise the load to 50,000 lb and the 36 mph wind becomes severe. Both routes now have the same severe miles, the same high miles, and the same average risk. The wet route is shorter, so it wins. The load rule changed the recommendation.

## Assumptions

- Durations come from OSRM's driving profile (a car, not a truck). Hours of service and truck speed limits are not modeled. The ETA at a checkpoint is the sum of the step durations up to that point, spread along the step by distance.
- Wind is the sustained 10 m wind, not the gust. The 55 mph cutoff is the usual sustained-wind line.
- Rain is Open-Meteo's `rain` plus `showers`, so a thunderstorm is not ignored. It is not `precipitation`, which also contains the water in snow and would double-count the snow column.
- Snow is centimeters of snowfall converted to inches by dividing by 2.54. It is not the liquid water equivalent, and it is not treated as millimeters. The forecast is requested in km/h, mm, and cm so the conversion stays in our code, where it is tested. `precipitation_unit=inch` has historically divided snowfall by 25.4.
- Open-Meteo wind at a timestamp is the wind at that moment. Rain and snow at a timestamp are the totals for the preceding hour. For an ETA of 14:20, wind comes from 14:00 and rain and snow come from 15:00 (the sum from 14:00 to 15:00). If that next hour is missing, rain and snow fall back to 14:00.
- A missing reading is treated as zero and flagged on the checkpoint.
- Weather coordinates are rounded to 0.01 degree (about 0.7 mile) before the request. That matches the forecast grid and lets nearby points share a cell. Uncached cells go out in batches of 40, a few batches at a time. Results are cached in the API process for 20 minutes.
- The heatmap is the same load-aware severity, drawn as a continuous 0–1 score (wind / 55, rain / 1 inch, snow / 3 inches, worst of the three, with the load rules as a floor). The slider is hours after the departure hour. All 49 hours are in the first response.
- Two OSRM routes count as the same if they stay under 8 miles apart on average. A via point is kept when it is at least that far from the routes already chosen, and we prefer one that is not more than 1.85 times the fastest route.
- Geocoding is biased toward the United States. A `lat, lon` pair can be pasted directly.
- Departure has to fall between 2 days ago and 7 days ahead, which is inside the Open-Meteo window we can actually request.

## APIs

No keys.

| Job | Service |
|---|---|
| Routes | [OSRM](https://router.project-osrm.org) public driving API, `alternatives=true`, full geometry and steps |
| Forecast | [Open-Meteo](https://open-meteo.com/) hourly forecast, batched, up to 40 locations per call |
| Places | [Photon](https://photon.komoot.io/) first, [Nominatim](https://nominatim.openstreetmap.org/) if Photon is empty. User-Agent is set. The box waits 300 ms after typing. |

The public OSRM server often returns only two alternatives. The third route is then built through a point offset to the side of the fastest route, and the response says so.

## Local setup

Backend, from `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py test
python manage.py runserver
```

Frontend, from `frontend/`:

```bash
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to `http://127.0.0.1:8000`, so leave `VITE_API_URL` unset. Set it (see `frontend/.env.example`) only when the API is on another host.

`python manage.py test` covers the wind, rain, and snow boundaries, the load cutoffs at 30,000 and 40,000 lb, sampling distances (including a bend, so the sample follows the road), unit conversion, the forecast hour, and the recommendation order.

## Deploy

Host the site and the API together on Vercel's Hobby plan. No credit card, and no database. `render.yaml` is still in the repo if you already have a Render account.

### Vercel

One project. The page and `/api` share the deployment URL, so leave `VITE_API_URL` empty.

1. Import this repository at [vercel.com/new](https://vercel.com/new) on the Hobby plan.
2. Root Directory: the repository root. Leave the field blank. Do not choose `frontend` or `backend`.
3. Framework Preset: **Other**. The root `vercel.json` defines the two services, so leave Build Command, Output Directory, and Install Command empty. If the form filled them in, clear them.
4. Environment variables: none are required. The table below is the full list.
5. Deploy. Open the Vercel URL. `https://<your-app>.vercel.app/api/health/` returns `{"status":"ok"}`.

You do not type the build settings. `vercel.json` does:

| Service | Root directory | Framework preset | Build | Output |
|---|---|---|---|---|
| frontend | `frontend/` | Vite | `npm run build` | `dist` |
| backend | `backend/` | Django | `pip install -r requirements.txt` | none, it is a Python function |

The Django entrypoint is `config.wsgi:application` (`backend/config/wsgi.py`). `/api/*` is routed to that function and the path is kept, so Django still sees `/api/plan/`, `/api/geocode/`, and `/api/health/`. Every other path is the Vite build. `frontend/vercel.json` sends unknown frontend paths to `index.html`.

The function `maxDuration` is 60 seconds, which is inside the Hobby limit (300 seconds with fluid compute). Open-Meteo requests run a few batches at a time, and the forecast is cached in memory for 20 minutes. Django is given a sqlite file at `/tmp/db.sqlite3` only because it wants a `DATABASES` entry. Nothing reads it. Static files are not collected for the API on Vercel.

| Variable | Required | What to set |
|---|---|---|
| `SECRET_KEY` | no | Leave unset for this demo. The fallback is `dev-only-not-a-secret`, and it is not a secret. The app has no accounts and no sessions. Set a long random value before you add either. |
| `DEBUG` | no | Defaults to `false` on Vercel. Set `true` only while reading a traceback. |
| `VITE_API_URL` | no | Leave unset so the site calls `/api` on the same host. Set it, with no trailing slash, only when the API is somewhere else, then redeploy. Vite reads it at build time. |
| `ALLOWED_HOSTS` | no | `.vercel.app` is already allowed. Set a comma-separated list only to add another host. |
| `CORS_ALLOWED_ORIGINS` | no | `https://*.vercel.app` and localhost are already allowed. Set a comma-separated origin list, no trailing slash, if another site calls the API. `*` allows every origin. |

### Render

Optional. Render's free web service asks for a card, which is why the steps above are the ones to use. `render.yaml` still describes the API.

1. Push the repo and create a Blueprint from `render.yaml`, or a new Web Service with root directory `backend`.
2. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
3. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
4. Set `DEBUG` to `false`, `ALLOWED_HOSTS` to `*`, and let Render generate `SECRET_KEY`. The blueprint does this.
5. After the service has a URL, set `CORS_ALLOWED_ORIGINS` to the site origin, for example `https://your-app.vercel.app`. No trailing slash. Several origins can be comma-separated. Localhost is always allowed.
6. Deploy. `GET /api/health/` should return `{"status":"ok"}`.

The free instance sleeps. The first plan after a sleep can take a minute.

To put only the site on Vercel and the API on Render, make a second Vercel project. Root directory `frontend`, framework preset Vite, output `dist`, build `npm run build`. Set `VITE_API_URL` to the Render origin with no trailing slash, and set Render's `CORS_ALLOWED_ORIGINS` to that Vercel origin.

## Limitations

- OSRM's public server is a demo. It rate-limits, it has no uptime promise, and it routes cars rather than trucks.
- Open-Meteo and Photon are free public services with the same kind of limit.
- A quiet forecast makes travel time the decider. That is what the order says, and it is common on a calm day.
- The corridor heatmap is a sample beside the routes, not a full model grid. It is smooth because the points are blurred, not because every square mile was fetched.
- Routes that cross the antimeridian are not handled. This is aimed at trips inside the US road network.
- There are no accounts and no saved trips.

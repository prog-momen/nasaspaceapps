# Astro EARTH demo plan: forecasting first (3 minutes, no slides)

Team: **Astro Crash**. Two people: one speaks, one drives the screen. The forecast is the part nobody else will have, so it gets the most time.

**One-line pitch for the forecast:** "Most tools draw a forecast line and say nothing about how far to trust it. Ours says where it was tested, where it is only an extension of the trend, and where it is mathematics only."

## Before the interview (10 minutes)

1. Start both services: `npm run dev:all` (the AI service needs about a minute to load).
2. Warm the cache: `node scripts/prewarm.mjs`.
3. Open these tabs in order:
   - `/` (start screen)
   - `/dashboard?lat=32.22&lon=35.25&name=Nablus&variable=T2M&start=1990&end=2025`
   - `/forecast?lat=32.22&lon=35.25&name=Nablus&variable=T2M&start=1990&end=2025&horizon=5`
   - `/chat`
4. Run each question once with the exact wording you will use.
5. Record a 30–60 second screen video of the same path as a backup.

## Timeline

| Time | Screen | Say | Do |
|---|---|---|---|
| 0:00 – 0:15 | Start screen | "We built Astro EARTH so anyone can check what is changing in their own place, and how far a forecast can be trusted." | Click the logo, then Palestine on the globe |
| 0:15 – 0:45 | Dashboard, chapter 3 (Nablus) | "First, what happened: the trend, and two independent tests that agree." | Point to the verdict and the **Sources** line |
| 0:45 – 2:15 | **Forecast page, 5 years** | see below | main part |
| 2:15 – 2:50 | Chat | Ask in Arabic: "توقع درجة الحرارة في نابلس خلال سنتين" | Show the chart, the monthly table and the Sources block |
| 2:50 – 3:00 | Back on the globe | "Open source, NASA data, honest limits. Try any place." | Stop |

**The forecast minute and a half (0:45 – 2:15)**

1. **From today (15 s).** "A 5-year forecast starts from today, not from the last data month. NASA data end in 2025, so the months in between are forecast too and marked as missing." Point to the *Asked* line.
2. **Three zones (45 s).** "Up to 5 years was tested against the last 60 real months: for Nablus the error was 1.12 °C against 1.56 °C for a plain seasonal average. From 5 to 10 years it only extends the trend. Beyond 10 years it is computation only." Click **2**, **5**, then **20** and show the highlighted box move.
3. **What it is not (15 s).** "A statistical extension of the past, not a climate model."
4. **Invite a request (15 s).** "Pick any place and a horizon; I will tell you the zone before I press Enter."

Cut Manaus and the comparison if you are short on time.

## If a judge asks for a specific request

Say the boundary first, then run it:

| They ask for | Say first | What the app does |
|---|---|---|
| A trend for a place | "Any point on Earth, from 1981, at least 5 years." | Runs it. Land-only variables over the sea say so. |
| A forecast up to 2 years | "This is inside the tested range." | Chat or Forecast page; backtest shown. |
| A forecast of 2 to 5 years | "Still inside the tested range of the Forecast page (5 years), but in chat we stop at 24 months." | Forecast page, first box highlighted. |
| A forecast of 5 to 10 years | "Beyond the tested range this extends the trend; it is a scenario, not a validated prediction." | Forecast page, second box. |
| A forecast over 10 years | "We can compute it, but it is mathematics only, with far lower confidence." | Forecast page, third box. Do not present it as a prediction. |
| Weather for a few days | "Up to 16 days, from Open-Meteo, not from the trend model." | Chat. |
| Fire danger next month | "Only places we prepared: Nablus, Gaza, Amman." | Chat. Other places take minutes; do not run them live. |
| A whole country | "The result is for one 50 km cell, a representative point, not a country average." | Runs for the point; say it. |
| "Why did it change?" | "We describe what happened, not the cause." | The assistant will not claim a cause. |

Rule for the room: choose place, variable and horizon together, then name the zone before pressing Enter.

## Forecast numbers you can quote

Backtest on the last 60 months of real data, default period 1990–2025, 5-year forecast. Lower error is better.

| Place | Model error | Seasonal-average error | Better by |
|---|---|---|---|
| Nablus | 1.12 °C | 1.56 °C | 28% |
| Japan (representative point) | 1.40 °C | 1.64 °C | 14% |
| Cairo | 1.15 °C | 1.32 °C | 13% |
| Svalbard | 1.99 °C | 2.27 °C | 12% |
| Amman (maximum temperature) | 2.04 °C | 2.16 °C | 5.5% |
| Niamey (precipitation) | 0.83 mm/day | 0.84 mm/day | 1.9% (almost no gain, avoid for this claim) |

Say the limits yourself: one place, one test window, and overlapping windows, so this is evidence for that place, not a general guarantee. The forecast values and the 95% bands were recomputed independently and match.

Trend numbers (1990–2024): Amman maximum temperature +0.58 °C per decade; Svalbard +0.73 °C per decade; Niamey rainfall +0.11 mm/day per decade; Manaus soil wetness not significant. All verified against scipy and pymannkendall.

## If something breaks

- Chat is slow: keep explaining the zones; the answer appears after 5–17 seconds.
- AI service is down: the chat shows an offline mode; the dashboard and forecast page are unaffected.
- Internet is down: use the recorded video.

# Astro EARTH demo plan (3 minutes, no slides)

Team: **Astro Crash**. Two people: one speaks, one drives the screen. Keep it simple: the product proves itself.

## Before the interview (10 minutes)

1. Start both services: `npm run dev:all` (the AI service needs about a minute to load).
2. Warm the cache: `node scripts/prewarm.mjs`.
3. Open four tabs in this order: `/` (start screen), `/earth`, `/dashboard?lat=31.95&lon=35.9&name=Amman&variable=T2M_MAX&start=1990&end=2025`, `/chat`.
4. Try each question you will ask once, with the exact wording.
5. Record a 30–60 second screen video of the same path as a backup.

## Timeline

| Time | Screen | Say | Show |
|---|---|---|---|
| 0:00 – 0:15 | Start screen | "Everyone hears that the climate is changing. We built Astro EARTH so anyone can check it for their own place." | Click the logo: stars rush, the Earth appears |
| 0:15 – 0:35 | Globe | "Click any point on Earth. Each point is a 50 km NASA grid cell." | Click Jordan, then **View Dashboard** |
| 0:35 – 1:25 | Dashboard, chapter 3 | "Amman's hottest days rise 0.58 °C per decade. Two independent tests agree, so we call it significant." | Point to the verdict, then to the **Sources** line: "every result tells you what it relies on and what it used" |
| 1:25 – 1:50 | Switch to Manaus (Amazon, soil wetness) | "Here the line goes down, but we refuse to call it a trend: 420 months behave like 26 independent ones. Not significant is a valid answer." | Click the Manaus scenario |
| 1:50 – 2:25 | Forecast page, 5 years | "The forecast starts from today, not from the last data month. The three boxes say how far to trust it." | Show the zones: tested, extrapolation, computation only |
| 2:25 – 2:55 | Chat | Ask in Arabic: "هل ارتفعت درجة الحرارة في عمان بين 1990 و2024؟" then "والقاهرة؟" | "The AI writes the words; the numbers come from code and are checked." Point to the Sources block |
| 2:55 – 3:00 | Back on the globe | "Open source, NASA data, honest limits. Try any place." | Stop |

If time is short, drop Manaus. If a step is slow, keep talking about the method and let it finish.

## If a judge asks for a specific request

Give the boundaries first, then run it:

| They ask for | Say first | What the app does |
|---|---|---|
| A trend for a place | "Any point on Earth, from 1981, at least 5 years." | Runs it. Land-only variables over the sea say so. |
| A forecast up to 2 years | "This is the tested range." | Chat or Forecast page; backtest shown. |
| A forecast of 5 to 10 years | "Beyond the tested range this is an extension of the trend, not a validated prediction." | Forecast page, second box highlighted. |
| A forecast over 10 years | "We can compute it, but it is mathematics only, with far lower confidence." | Forecast page, third box highlighted. Do not present it as a prediction. |
| Weather for a few days | "Up to 16 days, from Open-Meteo, not from the trend model." | Chat. |
| Fire danger next month | "Only places we prepared: Nablus, Gaza, Amman." | Chat. Other places take minutes; do not run them live. |
| A whole country | "Results are for one 50 km cell, a representative point, not a country average." | Runs for the point; say it. |
| "Why did it change?" | "We describe what happened, not the cause." | The assistant will not claim a cause. |

Rule for the room: pick a place, a variable and a horizon together, then say which of the three zones it falls in before pressing Enter.

## Numbers you can quote (1990–2024, computed by the app)

| Place | Variable | Result |
|---|---|---|
| Amman | Maximum air temperature | +0.58 °C per decade, significant |
| Svalbard | Air temperature | +0.73 °C per decade, significant |
| Niamey | Precipitation | +0.11 mm/day per decade, significant (p = 0.006 and 0.044) |
| Manaus | Root zone soil wetness | falling slope, not significant (p = 0.425 and 0.132) |

These trend numbers were recomputed independently with scipy and pymannkendall and match exactly.

## If something breaks

- Chat is slow: keep explaining the method; the answer appears after 5–17 seconds.
- AI service is down: the chat shows an offline mode and the dashboard is unaffected.
- Internet is down: use the recorded video.

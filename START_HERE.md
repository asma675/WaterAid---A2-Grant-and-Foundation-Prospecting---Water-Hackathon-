# Start GrantCurrent v0.7 Classic

## 1. Stop any older GrantCurrent container

From the old project folder:

```powershell
docker compose down
```

Or inspect ports:

```powershell
docker ps --filter "publish=5173"
docker ps --filter "publish=8000"
```

## 2. Start v0.7 Classic

Open PowerShell in the extracted `GrantCurrent_v7_Classic` folder:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Check:

```powershell
docker compose ps
```

Both `frontend` and `backend` should show **Up**.

## 3. Open

- Main app: `http://localhost:5173`
- Health check: `http://localhost:8000/health`
- API documentation: `http://localhost:8000/docs`

## 4. Recommended demo journey

1. **Overview** — show dynamically calculated historical intelligence and the synthetic-data safeguard.
2. **Pipeline Explorer** — drill from a KPI into the 104 source records.
3. **Funder Intelligence** — show historical patterns without fabricating current eligibility.
4. **Opportunity Matching** — show the requested filter panel and a complete G1–G8 / C1–C7 briefing note.
5. Create a scored opportunity and show **Funding stage** versus optional **TRL**.
6. **Fundraising Analytics** — toggle out the largest award.
7. **Project Funding Planner** — create a project and run a staff-hour scenario.
8. **FundScope Advisor** — ask a grounded strategy question.
9. **Reports & Pitch Mode** — print/save the executive report.
10. **Administration** — add/remove a country, show TRL reference, roles and evidence sources.

## 5. If the app says “Could not load the API”

Run:

```powershell
Invoke-RestMethod http://localhost:8000/health
docker compose ps -a
docker compose logs backend --tail 100
```

Do not browse to `0.0.0.0`; use `localhost`.

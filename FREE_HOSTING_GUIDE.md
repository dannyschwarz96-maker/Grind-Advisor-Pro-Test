# Kostenloses Hosting – Schritt für Schritt

## Überblick
Du hostest die App komplett im Free-Tier:

1. **Neon** für Postgres
2. **Render** für FastAPI
3. **Vercel** für das Frontend

## A. Neon
1. Konto erstellen
2. neues Free-Projekt anlegen
3. Connection String kopieren
4. Connection String in Render unter `DATABASE_URL` eintragen

## B. Render
1. GitHub-Repo verbinden
2. `backend/` als Root Directory wählen
3. Docker Web Service anlegen
4. folgende Variablen setzen:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `FRONTEND_ORIGIN`
   - `MODEL_DIR=/tmp/models`
5. Deploy starten
6. prüfen: `https://dein-service.onrender.com/health`

## C. Vercel
1. GitHub-Repo verbinden
2. Root Directory `frontend/`
3. Deploy
4. in `app.js` `API_BASE` auf die Render-URL setzen
5. erneut deployen

## D. CORS
Die Vercel-URL musst du in Render als `FRONTEND_ORIGIN` hinterlegen.

## E. Test
- registrieren
- Bohne anlegen
- Shot speichern
- Empfehlung berechnen
- JSON importieren

## Kostenlose Grenzen
Free-Tiers ändern sich manchmal. Prüfe vor dem Deploy immer die offiziellen Preis-/Free-Plan-Seiten der Anbieter.

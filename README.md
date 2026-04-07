# Grind Advisor Cloud Starter

Dieses Paket ist ein Startpunkt, um dein aktuelles Desktop-/Electron-Projekt auf eine **Server-Lösung mit Mehrnutzer-Login** umzubauen.

## Was enthalten ist

- `backend/`: FastAPI-Backend mit
  - Benutzer-Registrierung und Login
  - PostgreSQL-Anbindung
  - Bohnen-, Shot-, Import- und Predict-Endpunkten
  - Wiederverwendung deiner bestehenden ML-Dateien
- `frontend/`: mobile-first Web-App in HTML/CSS/JS
- `backend/render.yaml`: Beispiel für Render
- `backend/.env.example`: Umgebungsvariablen
- `backend/Dockerfile`: Docker-Build für Render

## Zielarchitektur

- Frontend als statische Web-App
- Backend als FastAPI-Service
- PostgreSQL als zentrale Datenbank
- pro User getrennte Daten und pro User eigenes Modell

## Lokales Starten

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 10000
```

### Frontend
Nimm einen simplen Static Server:
```bash
cd frontend
python -m http.server 5173
```

Dann in `frontend/app.js`:
- `API_BASE` auf dein Backend setzen, z. B. `http://localhost:10000/api`

## Kostenloses Hosting

### Empfohlene Gratis-Kombination
- Frontend: Vercel Hobby
- Backend: Render Free Web Service
- Datenbank: Neon Free Postgres

### 1. Neon
- kostenloses Postgres-Projekt anlegen
- Connection String kopieren
- diesen später als `DATABASE_URL` in Render eintragen

### 2. Render
- neues Web Service aus GitHub Repo
- Root Directory: `backend`
- Environment: Docker
- `render.yaml` verwenden oder Werte manuell setzen
- Environment Variables:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `FRONTEND_ORIGIN`
  - `MODEL_DIR=/tmp/models`

### 3. Vercel
- `frontend/` als Projekt deployen
- danach die öffentliche Frontend-URL in Render als `FRONTEND_ORIGIN` setzen
- in `frontend/app.js` die API-URL auf deine Render-URL setzen

## Wichtige Hinweise

- Render Free ist gut für Hobby- und Testprojekte. Free Services können schlafen.
- Das Paket ist ein **Starter**, kein komplett fertiges SaaS-Produkt.
- Für echtes Production-Niveau solltest du noch ergänzen:
  - Alembic-Migrationen
  - Rate Limiting
  - E-Mail-Verifikation
  - Passwort-Reset
  - sauberere Frontend-Komponenten
  - Datei-Storage für Imports

## Wie du dein bestehendes Projekt übernimmst

1. Deine bestehende ML-Logik ist bereits eingebunden.
2. Dein Importformat wird über `machine_json.py` weiter verwendet.
3. Dein bisheriges Frontend kann danach schrittweise an `/api/*` umgestellt werden.

## Nächster Schritt

- zuerst lokal starten
- dann GitHub Repo anlegen
- dann Neon + Render + Vercel verbinden

services:
  - type: web
    name: grind-advisor-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
    envVars:
      - key: DATABASE_URL
        sync: false          # Set manually in Render dashboard (Neon connection string)
      - key: JWT_SECRET
        generateValue: true  # Render generates a secure random value
      - key: FRONTEND_URL
        sync: false          # Your Vercel URL, e.g. https://grind-advisor.vercel.app

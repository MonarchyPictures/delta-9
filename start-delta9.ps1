# -----------------------------
# Delta-9 Local Dev Startup Script
# -----------------------------

# 1️⃣ Set environment variables
$env:PIPELINE_MODE = "bootstrap"
$env:PIPELINE_CATEGORY = "vehicles"
$env:VITE_API_URL = "http://localhost:8000"
$env:VITE_API_KEY = "d9_prod_secret_key_2024"

# 2️⃣ Start backend (FastAPI) in bootstrap mode
Write-Host "🚀 Starting Delta-9 backend in bootstrap mode..."
Start-Process powershell -ArgumentList "-NoExit", "-Command cd `"$PWD`"; python -m uvicorn app.main:app --reload --reload-exclude '*.db' --reload-exclude '*.db-wal' --reload-exclude '*.db-shm' --reload-exclude '*.log' --host 0.0.0.0 --port 8000"

# 3️⃣ Start frontend (React/Vite) in a separate window
Write-Host "🚀 Starting Delta-9 frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command cd `"$PWD\frontend`"; npm run dev"

Write-Host "✅ Both backend and frontend started."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000"
Write-Host "💡 Hard refresh your browser (CTRL+SHIFT+R) to load latest env values."

# Start StudyLens locally: backend on :8000 and frontend on :5173, each in its own window.
#   powershell -ExecutionPolicy Bypass -File start.ps1
# LLM_CACHE=1 replays lessons that were already generated (instant, free); new pages still call OpenAI.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = "Set-Location '$root\backend'; `$env:LLM_CACHE = '1'; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000"
$frontend = "Set-Location '$root\frontend'; npm run dev -- --port 5173 --strictPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontend
Start-Sleep -Seconds 6
Start-Process "http://localhost:5173"

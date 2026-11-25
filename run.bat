@echo off
REM VIBE_CODE golden path — single-process, NO Docker required.
REM Frozen ports: hr-directory 8001, it-service 8002. Never 8008/8009/8000.
REM Golden path (3 cmds, <60s warm):
REM   git clone ^<repo-url^> ^&^& cd VIBE_CODE
REM   pip install -r requirements.txt
REM   run.bat
SETLOCAL

echo [run] HR  : http://localhost:8001/hr ^(/docs ^/openapi.json^)
echo [run] IT  : http://localhost:8002/it ^(/docs ^/openapi.json^)
echo [run] DB  : SQLite files (hr_service/hr.db, it_service/it.db) — auto-created, offline.
echo [run] Docs: plan.md S1 + research/build/01-architecture.md S2 (frozen ports)

where uvicorn >NUL 2>&1
IF ERRORLEVEL 1 (
  echo [run] ERROR: uvicorn not found. Run: pip install -r requirements.txt
  EXIT /B 1
)

REM Start both APIs in separate windows (single-process each, SQLite).
start "hr-directory :8001" uvicorn hr_service.main:app --host 127.0.0.1 --port 8001
start "ticketing-sla :8002" uvicorn it_service.main:app --host 127.0.0.1 --port 8002

echo [run] Waiting 5s for boot...
timeout /t 5 /nobreak >NUL

echo [run] Probing HR...
curl -s -o NUL -w "HR candidates [%%{http_code} %%{time_total}s]\n" "http://localhost:8001/hr/candidates?limit=1" || echo [run] WARN: HR not up yet — see hr-directory window.

echo [run] Probing IT...
curl -s -o NUL -w "IT breaches   [%%{http_code} %%{time_total}s]\n" "http://localhost:8002/it/tickets/breaches" || echo [run] WARN: IT not up yet — see ticketing-sla window.

echo [run] Done. Open http://localhost:8001/docs and http://localhost:8002/docs
echo [run] Share mirror (optional): scripts\share.sh or ngrok http 8001 --domain=%NGROK_DOMAIN%
ENDLOCAL

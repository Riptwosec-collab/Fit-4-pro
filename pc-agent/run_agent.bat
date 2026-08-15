@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 pc_agent.py) || (python pc_agent.py)
pause

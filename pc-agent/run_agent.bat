@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 pc_agent_pro.py) || (python pc_agent_pro.py)
pause

@echo off
rem Tim folder agent that (co dj_agent\main.py). Goi bang: call "%~dp0_tim-agent.cmd"
set "AGENT="
if exist "D:\dj-hrm\apps\agent\dj_agent\main.py" set "AGENT=D:\dj-hrm\apps\agent"
if not defined AGENT if exist "D:\dj-hrm\agent\dj_agent\main.py" set "AGENT=D:\dj-hrm\agent"
if not defined AGENT if exist "%~dp0..\apps\agent\dj_agent\main.py" (
  for %%I in ("%~dp0..\apps\agent") do set "AGENT=%%~fI"
)
if not defined AGENT (
  echo LOI: Khong thay D:\dj-hrm\apps\agent  ^(thieu dj_agent\main.py^)
  echo Copy apps\agent tu may .123 sang USB, dán vào D:\dj-hrm\apps\agent\
  echo KHONG copy folder .venv
)

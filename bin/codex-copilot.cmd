@echo off
setlocal DisableDelayedExpansion
where py.exe >nul 2>nul
if errorlevel 1 goto python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 goto python
py -3 "%~dp0codex-copilot.py" %*
exit /b %errorlevel%
:python
where python.exe >nul 2>nul
if errorlevel 1 goto missing
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 goto missing
python "%~dp0codex-copilot.py" %*
exit /b %errorlevel%
:missing
echo Codex-Copilot requires Python 3.11+ available as py -3 or python. 1>&2
exit /b 127

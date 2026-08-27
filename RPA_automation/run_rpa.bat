@echo off
cd /d "%~dp0"
call .\env_hw2\Scripts\activate.bat
python RPA_automation.py
exit

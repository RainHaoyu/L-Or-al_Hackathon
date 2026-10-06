@echo off
rem Thin entry point (double-click me). All logic lives in the
rem ASCII-named core, so that no .bat file has to spell a Chinese
rem filename: cmd.exe decodes .bat bytes with the OEM codepage.
call "%~dp0scripts\start-backend.bat" %*

@REM This batch script is for allowing dragging files/folders onto the file's icon to easily use them as input for the Python script.

@REM Turn off displaying of commands.
@ECHO OFF

@REM SETLOCAL

@REM %scriptDrive%
@REM CD "%scriptFolder%"

@REM WARNING: %~dp0 seems to return first parameter's folder instead of script's folder when the batch file is called by a different script.
@REM https://stackoverflow.com/a/16144756
@py -3 "%~dpn0.py" %*

@REM PAUSE

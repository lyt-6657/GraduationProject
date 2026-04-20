@echo off
"""
检测 MongoDB 备份功能是否正常
"""

setlocal enabledelayedexpansion

REM 备份目录
set BACKUP_DIR=./backups

REM 日志文件
set LOG_FILE=./logs/backup_check.log

REM 当前时间
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value') do set datetime=%%i
set CURRENT_TIME=!datetime:~0,4!-!datetime:~4,2!-!datetime:~6,2! !datetime:~8,2!:!datetime:~10,2!:!datetime:~12,2!

REM 检查备份目录是否存在
if not exist "%BACKUP_DIR%" (
    echo [%CURRENT_TIME%] 错误: 备份目录不存在 >> "%LOG_FILE%"
    exit /b 1
)

REM 检查最近的备份文件
for /f "delims=" %%a in ('dir /b /o-d "%BACKUP_DIR%\*.gz" 2^>nul') do (
    set LATEST_BACKUP=%%a
    goto :found
)
:found
if not defined LATEST_BACKUP (
    echo [%CURRENT_TIME%] 错误: 没有找到备份文件 >> "%LOG_FILE%"
    exit /b 1
)

REM 检查备份文件大小
for /f "tokens=3" %%a in ('dir "%BACKUP_DIR%\%LATEST_BACKUP%" ^| findstr /i "%LATEST_BACKUP%"') do (
    set BACKUP_SIZE=%%a
)

REM 检查备份文件是否完整（尝试解压）
tar -tzf "%BACKUP_DIR%\%LATEST_BACKUP%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%CURRENT_TIME%] 错误: 备份文件损坏 >> "%LOG_FILE%"
    exit /b 1
)

REM 检查备份文件的修改时间
for /f "tokens=1,2" %%a in ('dir /t:w "%BACKUP_DIR%\%LATEST_BACKUP%" ^| findstr /i "%LATEST_BACKUP%"') do (
    set BACKUP_DATE=%%a
    set BACKUP_TIME=%%b
)

REM 输出检测结果
echo [%CURRENT_TIME%] 备份检测结果: >> "%LOG_FILE%"
echo - 最新备份文件: %LATEST_BACKUP% >> "%LOG_FILE%"
echo - 备份文件大小: %BACKUP_SIZE% >> "%LOG_FILE%"
echo - 备份时间: %BACKUP_DATE% %BACKUP_TIME% >> "%LOG_FILE%"
echo - 备份文件状态: 完整 >> "%LOG_FILE%"
echo - 备份功能: 正常 >> "%LOG_FILE%"

exit /b 0

@echo off

:: MongoDB 备份脚本
:: 该脚本用于定期备份 MongoDB 数据库

:: 配置参数
set MONGODB_HOST=%MONGODB_HOST% 
if "%MONGODB_HOST%"=="" set MONGODB_HOST=localhost

set MONGODB_PORT=%MONGODB_PORT%
if "%MONGODB_PORT%"=="" set MONGODB_PORT=27017

set MONGODB_USERNAME=%MONGODB_USERNAME%
set MONGODB_PASSWORD=%MONGODB_PASSWORD%
set MONGODB_DB_NAME=%MONGODB_DB_NAME%
if "%MONGODB_DB_NAME%"=="" set MONGODB_DB_NAME=graduation_project

:: 备份目录
set BACKUP_DIR=%BACKUP_DIR%
if "%BACKUP_DIR%"=="" set BACKUP_DIR=%~dp0\mongodb_backups

:: 创建时间戳
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ("%TIME%") do (set mytime=%%a%%b)
set TIMESTAMP=%mydate%_%mytime%
set BACKUP_PATH=%BACKUP_DIR%\%MONGODB_DB_NAME%_%TIMESTAMP%

:: 创建备份目录
mkdir "%BACKUP_DIR%" 2>nul

:: 构建 mongodump 命令
if not "%MONGODB_USERNAME%"=="" if not "%MONGODB_PASSWORD%"=="" (
    set MONGODUMP_CMD=mongodump --host %MONGODB_HOST% --port %MONGODB_PORT% --username %MONGODB_USERNAME% --password %MONGODB_PASSWORD% --authenticationDatabase admin --db %MONGODB_DB_NAME% --out "%BACKUP_PATH%"
) else (
    set MONGODUMP_CMD=mongodump --host %MONGODB_HOST% --port %MONGODB_PORT% --db %MONGODB_DB_NAME% --out "%BACKUP_PATH%"
)

:: 执行备份
echo 开始备份 MongoDB 数据库 %MONGODB_DB_NAME%...
echo 执行命令: %MONGODUMP_CMD%

:: 运行备份命令
%MONGODUMP_CMD%

:: 检查备份结果
if %errorlevel% equ 0 (
    echo 备份成功! 备份文件保存在: %BACKUP_PATH%
    
    :: 压缩备份文件
    echo 正在压缩备份文件...
    powershell Compress-Archive -Path "%BACKUP_PATH%" -DestinationPath "%BACKUP_PATH%.zip" -Force
    
    :: 删除未压缩的备份目录
    rmdir /s /q "%BACKUP_PATH%"
    
    echo 备份文件已压缩: %BACKUP_PATH%.zip
    
    :: 清理旧备份（保留最近7天的备份）
    echo 清理7天前的备份文件...
    powershell Get-ChildItem "%BACKUP_DIR%" -Name "%MONGODB_DB_NAME%_*.zip" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force
    
    echo 备份完成!
) else (
    echo 备份失败!
    exit /b 1
)

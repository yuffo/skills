@echo off
chcp 65001 >nul

echo ===== Skills自动备份设置 =====
echo.

set SKILLS_DIR=C:\Users\yuff.DESKTOP-55AUCJG\.codebuddy\skills
set REPO_URL=https://github.com/yuffo/skills.git

cd /d "%SKILLS_DIR%"

REM 初始化git仓库
if not exist ".git" (
    echo 正在初始化git仓库...
    git init
    git remote add origin %REPO_URL%
    echo 已添加远程仓库: %REPO_URL%
) else (
    echo git仓库已存在
    git remote -v
)

echo.
echo 创建启动项...

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS_PATH=%STARTUP_DIR%\SkillsBackup.vbs
set BAT_PATH=%SKILLS_DIR%\backup_skills.py

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "python ""%BAT_PATH%""", 0, False
) > "%VBS_PATH%"

echo 已创建启动项: %VBS_PATH%
echo.
echo ===== 设置完成 =====
echo 重启后将自动备份
echo 或手动运行: python %BAT_PATH%
pause

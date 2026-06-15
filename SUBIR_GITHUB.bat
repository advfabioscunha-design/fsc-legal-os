@echo off
rem ============================================================
rem  SUBIR O FSC LEGAL OS PARA O GITHUB (1 duplo clique)
rem  Usuario: advfabioscunha-design  |  Repo: fsc-legal-os
rem  Pre-requisito: criar o repositorio PRIVADO "fsc-legal-os"
rem  em https://github.com/new (sem README, sem .gitignore)
rem ============================================================
cd /d "%~dp0"

rem Remove trava de indice deixada por processo anterior (NTFS/sandbox)
if exist ".git\index.lock" del /f /q ".git\index.lock" >nul 2>&1

where git >nul 2>&1
if errorlevel 1 (
    echo Instalando Git via winget...
    winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements
    set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)

echo Criando .gitignore...
(
echo .env
echo __pycache__/
echo node_modules/
echo .next/
echo *.pyc
) > .gitignore

echo INICIO %date% %time% > subir_log.txt
git init >> subir_log.txt 2>&1
git add -A >> subir_log.txt 2>&1
git -c user.name="Fabio Cunha" -c user.email="adv.fabios.cunha@gmail.com" commit -m "FSC Legal OS v4.1 - plataforma cloud completa" >> subir_log.txt 2>&1
git branch -M main >> subir_log.txt 2>&1
git remote remove origin >nul 2>&1
git remote add origin https://github.com/advfabioscunha-design/fsc-legal-os.git >> subir_log.txt 2>&1
echo.
echo Enviando... (uma janela do GitHub vai abrir: clique em "Sign in with browser" e depois "Authorize")
git push -u origin main >> subir_log.txt 2>&1
echo FIM %date% %time% >> subir_log.txt
echo.
echo CONCLUIDO! Confira em: https://github.com/advfabioscunha-design/fsc-legal-os
exit

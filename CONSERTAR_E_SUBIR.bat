@echo off
chcp 65001 >nul
cd /d "C:\Users\User\Desktop\PROJETO TRIADV\PROJETO JURIDICO\files\fsc-legal-os"
echo ===============================================================
echo   FC ADVOCACIA - CONSERTAR GIT E SUBIR PARA O GITHUB
echo ===============================================================
echo.

echo [1/6] Removendo trava e indice corrompido do git...
del /f /q ".git\index.lock" 2>nul
del /f /q ".git\index" 2>nul

echo [2/6] Reconstruindo o indice a partir do ultimo commit...
git reset

echo [3/6] Adicionando TODAS as alteracoes (arquivos novos e editados)...
git add -A

echo [4/6] Conferindo o que sera enviado...
git status --short

echo [5/6] Salvando as alteracoes (commit)...
git commit -m "FC Advocacia - site escuro, atendimento humanizado, area do cliente e contrato"

echo [6/6] Enviando para o GitHub...
git push origin main

echo.
echo ===============================================================
echo   CONCLUIDO. Leia as mensagens acima:
echo   - Se apareceu 'Everything up-to-date' ou um resumo de envio,
echo     deu certo.
echo   - Se pediu usuario/senha do GitHub, informe seu login/token.
echo ===============================================================
pause

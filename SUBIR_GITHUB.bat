@echo off
rem ============================================================
rem  SUBIR O FSC LEGAL OS PARA O GITHUB (1 duplo clique)
rem  Usuario: advfabioscunha-design  |  Repo: fsc-legal-os
rem
rem  Este arquivo foi escrito para o PRIMEIRO envio e era
rem  destrutivo em toda repeticao: reescrevia o .gitignore do
rem  zero, refazia o "git init", trocava o remoto e commitava
rem  tudo sempre com a mesma mensagem, o que apagava o historico
rem  de qualquer commit feito no meio do caminho.
rem
rem  Agora ele so faz o que precisa: manda o que ainda nao foi.
rem  Se houver algo sem commit, cria um commit com a data e a
rem  hora. Se nao houver, apenas envia o que ja estava pronto.
rem ============================================================
cd /d "%~dp0"

rem Trava de indice deixada por um processo anterior.
if exist ".git\index.lock" del /f /q ".git\index.lock" >nul 2>&1

where git >nul 2>&1
if errorlevel 1 (
    echo Instalando Git via winget...
    winget install --id Git.Git -e --silent --accept-source-agreements --accept-package-agreements
    set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
)

echo INICIO %date% %time% > subir_log.txt

rem O remoto so e criado se ainda nao existir. Remover e recriar a
rem cada execucao era o que apagava a configuracao de rastreamento.
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/advfabioscunha-design/fsc-legal-os.git >> subir_log.txt 2>&1
)

git add -A >> subir_log.txt 2>&1

rem Commita apenas se houver diferenca. Sem isto, toda execucao
rem tentava um commit vazio e o log enchia de erro.
git diff --cached --quiet
if errorlevel 1 (
    echo Guardando as alteracoes locais...
    git -c user.name="Fabio Cunha" -c user.email="adv.fabios.cunha@gmail.com" commit -m "Ajustes de %date% %time%" >> subir_log.txt 2>&1
) else (
    echo Nada novo para guardar. Enviando o que ja estava pronto.
)

echo.
echo Enviando... se abrir a janela do GitHub, clique em "Sign in with browser" e depois "Authorize".
git push origin main >> subir_log.txt 2>&1
if errorlevel 1 (
    echo.
    echo O ENVIO FALHOU. Abra o arquivo subir_log.txt nesta pasta para ver o motivo.
    pause
    exit /b 1
)

echo FIM %date% %time% >> subir_log.txt
echo.
echo CONCLUIDO. Confira em: https://github.com/advfabioscunha-design/fsc-legal-os
timeout /t 6 >nul
exit

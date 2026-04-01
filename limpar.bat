@echo off
setlocal enabledelayedexpansion

echo [IdeaForge] Iniciando limpeza profunda do projeto...
echo.

:: 1. Remover pastas de artefatos e logs do sistema
if exist ".forge" (
    echo [CLEAN] Removendo pasta .forge...
    rmdir /s /q ".forge"
)
if exist ".tmp_artifacts" (
    echo [CLEAN] Removendo pasta .tmp_artifacts...
    rmdir /s /q ".tmp_artifacts"
)
if exist ".tmp_planner" (
    echo [CLEAN] Removendo pasta .tmp_planner...
    rmdir /s /q ".tmp_planner"
)

:: 2. Remover pastas de validacao temporarias
if exist "VALIDACAO_FASE_9.5" (
    echo [CLEAN] Removendo pasta VALIDACAO_FASE_9.5...
    rmdir /s /q "VALIDACAO_FASE_9.5"
)

:: 3. Remover caches de Python e Pytest recursivamente
echo [CLEAN] Limpando caches de Python (__pycache__ e .pytest_cache)...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /d /r . %%d in (.pytest_cache) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
for /d /r . %%d in (.tmp_*) do @if exist "%%d" rmdir /s /q "%%d" 2>nul

:: 4. Remover arquivos residuais de execucao e testes
echo [CLEAN] Removendo arquivos residuais (.txt, .log, .pyc, .pyo)...
if exist "test_results.txt" del /f /q "test_results.txt"
del /s /q *.pyc *.pyo *.log >nul 2>&1

:: 5. Verificar se existe .env e avisar (nao removeremos automaticamente por seguranca, mas fica o log)
if exist "idea-forge\.env" (
    echo [INFO] Arquivo idea-forge\.env detectado. Mantido para manter configuracoes de API.
)

echo.
echo [OK] Limpeza concluida! O projeto esta em estado original.
echo.
pause

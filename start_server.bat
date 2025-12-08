@echo off
REM Script para iniciar el servidor Django
REM Carga automáticamente las variables de entorno desde .env

echo ========================================
echo  Portal de Practicas TI - Servidor
echo ========================================
echo.

REM Verificar si el archivo .env existe
if not exist .env (
    echo [ERROR] No se encontro el archivo .env
    echo Por favor copia .env.example a .env y configura tus credenciales
    pause
    exit /b 1
)

echo [OK] Archivo .env encontrado
echo.

REM Opcional: Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    echo Activando entorno virtual...
    call venv\Scripts\activate
    echo.
)

echo Verificando configuracion de Django...
python manage.py check
if errorlevel 1 (
    echo.
    echo [ERROR] Hay problemas con la configuracion
    pause
    exit /b 1
)
echo.

echo Aplicando migraciones pendientes...
python manage.py migrate --noinput
echo.

echo ========================================
echo  Iniciando servidor en http://127.0.0.1:8000
echo  Presiona Ctrl+C para detener el servidor
echo ========================================
echo.

python manage.py runserver

pause

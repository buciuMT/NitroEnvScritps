@echo off

podman machine start

for /f "tokens=*" %%a in ('podman run -d -p "8888:8888" nitro_env') do set notebook=%%a

timeout 10 /nobreak

for /f "tokens=*" %%a in ('podman logs %notebook% 2^>^&1 ^| findstr "http://127.0.0.1:8888"') do set JUPYTER_URL=%%a


start "" "%JUPYTER_URL%"


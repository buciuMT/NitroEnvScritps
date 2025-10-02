import os
import time
import subprocess
import shutil
import platform
import winapps

STOP_SCRIT='''
podman kill -a
'''

START_SCRIPT='''
@echo off

podman machine start

for /f "tokens=*" %%a in ('podman run -d -p "8888:8888" "{}"') do set notebook=%%a

timeout 10 /nobreak

for /f "tokens=*" %%a in ('podman logs %notebook% 2^>^&1 ^| findstr "http://127.0.0.1:8888"') do set JUPYTER_URL=%%a


start "" "%JUPYTER_URL%"

'''

STAGE2_SCRIPT='''
@echo off
color a
echo Initializing podman...
podman machine init
echo Starting Machine...
podman machine start
echo Loading Image...
echo This can take a long time ...
{}
echo Restarting...
shutdown /r /t 5
(goto) 2>nul & del "%~f0"
'''

DEFAULT_CONFIG = {
    "OfflineInstall": False,
    "Vscode": True,
    "PyCharm": True,
    "LocalImage": False,
}

COMPETITION_CONFIG = {
    "OfflineInstall": True,
    "Vscode": True,
    "PyCharm": True,
    "LocalImage": True,
}

def log(msg):
    with open('install.log','a') as w:
        w.write(msg+'\n')
        print(msg)

def fileWrite(path:str,format:str,*args):
    with open(path,'w') as w:
        w.write(format.format(*args))

def config_custom():
    config = {}
    for key in DEFAULT_CONFIG:
        while True:
            val = input(f"{key} (yes/no) [default={'yes' if DEFAULT_CONFIG[key] else 'no'}]: ").strip().lower()
            if val in ["true", "yes", "y"]:
                config[key] = True
                break
            elif val in ["false", "no", "n"]:
                config[key] = False
                break
            elif val == "":
                config[key] = DEFAULT_CONFIG[key]
                break
            else:
                log("Please enter yes, no, y, n, or press Enter for default.")
    return config

def configuration():
    log("Choose configuration mode:")
    log("1. Default")
    log("2. Competition")
    log("3. Custom")
    
    choice = input("Enter choice [1/2/3]: ").strip()

    if choice == "1":
        return DEFAULT_CONFIG
    elif choice == "2":
        return COMPETITION_CONFIG
    elif choice == "3":
        return config_custom()
    else:
        log("Invalid choice, using Default config.")
        return DEFAULT_CONFIG

DESKTOP = os.path.expanduser("~/Desktop")
STARTUP=os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/")

IMAGE={
    "url": "docker.io/lpxt9fz5f/nitro_simple:latest",
    "file": "img/nitro_img.zip",
    "name":"nitro_base",
}

APPS = {
    "winget": {
        "check": "winget",
        "winget": None,
        "installer": None,
        "silent": None,
    },
    "podman": {
        "check": "podman",
        "winget": "RedHat.Podman",
        "installer": "podman-setup.exe",
        "url": "https://github.com/containers/podman/releases/download/v5.6.1/podman-5.6.1-setup.exe",
        "silent": "/S",
    },
    "vscode": {
        "check": "code",
        "winget": "Microsoft.VisualStudioCode",
        "installer": "vscode.exe",
        "url": "https://vscode.download.prss.microsoft.com/dbazure/download/stable/f220831ea2d946c0dcb0f3eaa480eb435a2c1260/VSCodeUserSetup-x64-1.104.0.exe",
        "silent": "/SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART",
    },
    "pycharm": {
        "check": "pycharm",
        "winget": "JetBrains.PyCharm.Community",
        "installer": "pycharm.exe",
        "url": "https://download.jetbrains.com/python/pycharm-community-2025.2.1.1.exe",
        "silent": "/S",
    },
}

def setup_stage2(config):
    log("Setting up stage 2 ...")
    image_name=IMAGE['url'] if not config['LocalImage'] else IMAGE['name']
    if config['LocalImage']:
        log("Extracting the image ...")
        if not run_cmd(f'"{os.path.join(os.getcwd(),"7zip/7za.exe")}" e {IMAGE["file"]} -o"{DESKTOP}"'):
            log("Failed to extract the image")
            return False
    log("Adding the start and stop scripts...")
    if not (fileWrite(os.path.join(DESKTOP,"start_jupyter.bat"),START_SCRIPT,image_name) and fileWrite(os.path.join(DESKTOP,"start_jupyter.bat"),STOP_SCRIT)):
        log("Failed to copy second image")
        return False 
    command=None
    if config['LocalImage']:
        command=f'podman image load --input "{os.path.join(DESKTOP,image_name)}"'
    else:
        command=f'podman pull "{image_name}"'
    log("Writing the Startup stage2")
    fileWrite(os.path.join(STARTUP,'stage2.bat'),STAGE2_SCRIPT,command)
    return True 


def run_cmd(cmd:str):
    try:
        subprocess.run(cmd, check=True, shell=True)
        return True
    except subprocess.CalledProcessError:
        return False


def is_installed(name,shCheck=True):
    if shCheck and shutil.which(name):
        return True
    for app in winapps.list_installed():
        log(f"DEBUG: {app.name}")
        if name.lower() in app.name.lower():
            return True
    return False


def install_offline(filename, silent_flags=None):
    if os.path.exists(filename):
        log(f"Installing from {filename}...")
        cmd = f'"{filename}" {silent_flags}' if silent_flags else f'"{filename}"'
        return run_cmd(cmd)
    return False



def install_winget(winget_id):
    if not winget_id:
        return False
    log(f"Installing {winget_id} via winget...")
    return run_cmd(f"winget install --accept-source-agreements --accept-package-agreements -e --id {winget_id} -h ")


def ensure_winget():
    if shutil.which("winget"):
        return True
    log("Winget not found. Installing...")
    ps_cmd = "irm asheroto.com/winget | iex"
    res=run_cmd(f"powershell -Command \"{ps_cmd}\"")
    if res:
        time.sleep(2)
    return res

def install_app_offline(app,info,retry=True):
    log(f"{app} not found. Trying offline installer...")
    if info.get("installer") and install_offline(info["installer"], info.get("silent")):
        log(f"{app} installed from offline installer.")
        return True
    if retry:
        return install_app_online(app,info,retry=False)
    return False
def install_app_online(app,info,retry=True):
    if not ensure_winget():
        log("Failed to install winget.")
        return False
    log(f"Trying winget for {app}...")
    if info.get("winget") and install_winget(info["winget"]):
        log(f"{app} installed via winget.")
        return True
    else:
        log(f"Failed to install {app}. Please install manually.")
        return False

def intall_app(app,info,online):
    log(f"\nChecking {app}...")
    if is_installed(info["check"]):
        log(f"{app} is already installed.")
        return True
    if online:
        return install_app_online(app,info)
    return install_app_offline(app,info)

def install_wsl():
    return run_cmd("wsl --install --no-distribution") and run_cmd("wsl --set-default-version 2")

# Based on [https://github.com/almogopp/WSL-Offline-Installer], the copyright notice is a comment;
def install_wsl_offline():
    log("WSL not found. Preparing offline installation...")
    distro_path = "distro.appx"
    if not os.path.exists(distro_path):
        log("Invalid path provided. Aborting WSL setup.")
        return False

    try:
        os_caption = subprocess.check_output("wmic os get Caption", shell=True).decode(errors="ignore").strip().split("\n")[-1]
    except Exception:
        os_caption = platform.release()

    log(f"Detected OS: {os_caption}")

    if "Windows Server 2019" in os_caption or "Windows Server 2022" in os_caption:
        run_cmd("powershell -Command \"Install-WindowsFeature -Name Microsoft-Windows-Subsystem-Linux\"")
        run_cmd("powershell -Command \"Install-WindowsFeature -Name VirtualMachinePlatform -IncludeManagementTools\"")
    elif "Windows 10" in os_caption:
        run_cmd("powershell -Command \"Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart\"")
        run_cmd("powershell -Command \"Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart\"")
    elif "Windows 11" in os_caption:
        run_cmd("wsl --install")
    else:
        log("This script supports only Windows Server 2019, 2022, Windows 10 or 11.")
        return False

    # https://github.com/almogopp/WSL-Offline-Installer/blob/main/WSL-Offline-Install.ps1
    temp_file = os.path.join(os.environ["TEMP"], "wsl_install_temp.ps1")
    '''
    MIT License
    
    Copyright (c) 2024 almogopp
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    '''
    script_content = f'''
param ([string]$LinuxDistroPath)

Add-AppxPackage -Path "$LinuxDistroPath"
$distroBaseName = [System.IO.Path]::GetFileNameWithoutExtension($LinuxDistroPath)
$distroName = (Get-AppxPackage | Where-Object {{ $_.Name -match $distroBaseName }}).Name

if ([string]::IsNullOrWhiteSpace($distroName)) {{
    Write-Host "Unable to determine installed distro name. Skipping WSL version setup." -ForegroundColor Yellow
}} else {{
    if ($distroName -match "Ubuntu|Debian|Kali|openSUSE|SLES") {{
        Write-Host "Upgrading $distroName to WSL 2..."
        wsl --set-version $distroName 2
    }}
    wsl --set-default-version 2
}}

Unregister-ScheduledTask -TaskName "WSLInstallTask" -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item "{temp_file}" -Force
Write-Host "Installation complete! WSL setup is done." -ForegroundColor Green
'''

    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(script_content)

    run_cmd(f"powershell -Command \"Register-ScheduledTask -TaskName 'WSLInstallTask' -Action (New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument '-ExecutionPolicy Bypass -File {temp_file} -LinuxDistroPath {distro_path}') -Trigger (New-ScheduledTaskTrigger -AtStartup) -Principal (New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest) -Force\"")

    return True


def vscode_setup()->bool:
    cmds=[
        "code --install-extension ms-toolsai.jupyter --force",
        "code --install-extension ms-python.python --force",
        "code --install-extension ms-python.vscode-pylance --force"
    ]
    for cmd in cmds:
        if not run_cmd(cmd):
            return False
    return True

def main():
    config=configuration()
    log("\nChecking wsl ...") 
    if not is_installed("wsl",shCheck=False):
        log("Installing wsl")
        if not install_wsl():
            log("Failed to install WSL. Please install manually.")
            log("Exiting")
            return

    if not intall_app('Podman',APPS['podman'],online=not config["OfflineInstall"]):
        log("Failed to install WSL. Please install manually.")
        log("Exiting")
        return

    if not intall_app('PyCharm',APPS["pycharm"],online=not config["OfflineInstall"]):
        log("Failed to install PyCharm. Continuing...")
    if intall_app("VsCode",APPS["vscode"],online=not config["OfflineInstall"]):
        log("Installing vscode extensions...")
        time.sleep(3)
        if not vscode_setup():
            log("Failed to install the required vscode extensions")
    else:
        log("Failed to install VsCode. Continuing...")    
    if not setup_stage2(config):
        log("failed setting up stage 2")
        log("Please restart and intervene manually")
    log("The computer is about to restart, if it does not restart in 10 seconds please restart it manually")
    _=run_cmd("shutdown /r /t 5")




        

if __name__ == "__main__":
    main()
    input("Press Enter to exit...")


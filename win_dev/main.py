
import os
import subprocess
import shutil
import winapps
import platform

DESKTOP=desktop = os.path.expanduser("~/Desktop")


IMAGE={
    "url": None,
    "file": "image"
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
        "url": None,
        "silent": "/S",
    },
 #   "docker": {
 #       "check": "DockerDesktop",
 #       "winget": "Docker.DockerDesktop",
 #       "installer": "docker.exe",
 #       "url": "https://desktop.docker.com/win/main/amd64/204649/Docker%20Desktop%20Installer.exe",
 #       "silent": "install --quiet",
 #   },
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
        print(f"DEBUG: {app.name}")
        if name.lower() in app.name.lower():
            return True
    return False


def install_offline(filename, silent_flags=None):
    if os.path.exists(filename):
        print(f"Installing from {filename}...")
        cmd = f'"{filename}" {silent_flags}' if silent_flags else f'"{filename}"'
        return run_cmd(cmd)
    return False



def install_winget(winget_id):
    if not winget_id:
        return False
    print(f"Installing {winget_id} via winget...")
    return run_cmd(f"winget install -e --id {winget_id} -h")


def ensure_winget():
    if shutil.which("winget"):
        return True
    print("Winget not found. Installing...")
    ps_cmd = "irm asheroto.com/winget | iex"
    return run_cmd(f"powershell -Command \"{ps_cmd}\"")

def install_wsl():
    return run_cmd("wsl --install --no-distribution") and run_cmd("wsl --set-default-version 2")

# Based on [https://github.com/almogopp/WSL-Offline-Installer], the copyright notice is a comment;
def install_wsl_offline():
    print("WSL not found. Preparing offline installation...")
    distro_path = "distro.appx"
    if not os.path.exists(distro_path):
        print("Invalid path provided. Aborting WSL setup.")
        return False

    try:
        os_caption = subprocess.check_output("wmic os get Caption", shell=True).decode(errors="ignore").strip().split("\n")[-1]
    except Exception:
        os_caption = platform.release()

    print(f"Detected OS: {os_caption}")

    if "Windows Server 2019" in os_caption or "Windows Server 2022" in os_caption:
        run_cmd("powershell -Command \"Install-WindowsFeature -Name Microsoft-Windows-Subsystem-Linux\"")
        run_cmd("powershell -Command \"Install-WindowsFeature -Name VirtualMachinePlatform -IncludeManagementTools\"")
    elif "Windows 10" in os_caption:
        run_cmd("powershell -Command \"Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart\"")
        run_cmd("powershell -Command \"Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart\"")
    elif "Windows 11" in os_caption:
        run_cmd("wsl --install")
    else:
        print("This script supports only Windows Server 2019, 2022, Windows 10 or 11.")
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
    print("\nChecking wsl ...") 
    if not is_installed("wsl",shCheck=False):
        print("Installing wsl")
        if not install_wsl():
            print("Failed to install WSL. Please install manually.")

    if not ensure_winget():
        print("Failed to install winget. Exiting.")
        return

    for app, info in APPS.items():
        print(f"\nChecking {app}...")
        if is_installed(info["check"]):
            print(f"{app} is already installed.")
            continue

        print(f"{app} not found. Trying offline installer...")
        if info.get("installer") and install_offline(info["installer"], info.get("silent")):
            print(f"{app} installed from offline installer.")
            continue

        print(f"Trying winget for {app}...")
        if info.get("winget") and install_winget(info["winget"]):
            print(f"{app} installed via winget.")
        else:
            print(f"Failed to install {app}. Please install manually.")

        print("Installing vscode extensions...")
        if not vscode_setup():
            print("Failed to install the required vscode extensions")

        print("Extracting the image")


        

if __name__ == "__main__":
    main()
    input("Press Enter to exit...")


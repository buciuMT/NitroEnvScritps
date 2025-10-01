#!/bin/sh

wine pyinstaller main.py -F --hiddenimport elevate --hiddenimport winapps --collect-submodules elevate --collect-submodules winapps --uac-admin

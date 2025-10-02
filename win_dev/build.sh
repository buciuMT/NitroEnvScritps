#!/bin/sh

wine pyinstaller main.py -F --hiddenimport winapps --collect-submodules winapps --uac-admin --noupx

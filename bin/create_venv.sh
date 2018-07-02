#!/bin/bash
#requirements
echo "#sudo apt-get install python3-pip"
echo "#sudo apt-get install python3-venv"

python3 -m venv ~/med2image_venv

#ativar virtual env
. ~/med2image_venv/bin/activate

#instalar as dependências de maneira rápida
echo "#pip install --upgrade pip"
pip3 install med2image


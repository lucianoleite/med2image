#!/bin/bash
#requirements
echo "#sudo apt-get install python3-pip"
echo "#sudo apt-get install python3-venv"
VENV_BASE_FOLDER=/usr/src/app/med2image
rm -rf $VENV_BASE_FOLDER/med2image_venv
python3.7 -m venv $VENV_BASE_FOLDER/med2image_venv

#ativar virtual env
. $VENV_BASE_FOLDER/med2image_venv/bin/activate

#upgrade do pip dentro do venv para poder rodar com py3.7 mesmo sendo py3.10 no container
pip3 install --upgrade pip
pip3 install med2image


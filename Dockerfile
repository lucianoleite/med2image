#Proxy heroku rodar build => sudo docker build --build-arg https_proxy=https://146.164.46.1:3128 --build-arg
# http_proxy=http://146.164.46.1:3128 -t med2image .
# Execucao: sudo docker run med2image /home/petrec07/Documents/dados/plugue1023-projecoes/01_naoseg.nii /home/petrec07/Documents/dados/plugue1023-projecoes/01_naoseg Projecao_Tomografica

FROM python:3
RUN python3 -m venv /root/med2image_venv
RUN /bin/bash -c ". /root/med2image_venv/bin/activate && /root/med2image_venv/bin/pip3 install med2image && deactivate "
ADD bin/ bin/
ADD med2image/ /med2image/
ENTRYPOINT ["/bin/run_seg_med2image"]
CMD []
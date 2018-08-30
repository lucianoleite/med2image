FROM python:3
ADD test.py /
CMD [ "python", "bin/med2image" ]
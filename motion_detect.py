#/usr/bin/python

import RPi.GPIO as GPIO
import time
from subprocess import call
import sys

GPIO.setmode(GPIO.BOARD)
pin = 13
GPIO.setup(pin, GPIO.IN)

 
while 1:
  if GPIO.input(pin) == GPIO.LOW:
    print('no intruders')
    time.sleep(0.2)
  else:
    print('intruder!!!')
    call(["raspistill", "-o", "test.jpg"])
    sys.exit(0)

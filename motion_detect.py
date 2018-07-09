#/usr/bin/python

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
pin = 13
GPIO.setup(pin, GPIO.IN)

 
while 1:
  if GPIO.input(pin) == GPIO.LOW:
    print('no intruders')
    time.sleep(0.2)
  else:
    print('intruder!!!')
    time.sleep(0.2)

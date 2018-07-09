#/usr/bin/python

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
pin = 11
GPIO.setup(pin, GPIO.IN)

 
while 1:
  if GPIO.input(pin) == GPIO.HIGH:
    print('I can hear you')
    time.sleep(0.2)
  else:
    print('Silence')
    time.sleep(0.2)

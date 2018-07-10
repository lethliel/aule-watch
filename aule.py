#/usr/bin/python

import sys
import time
import subprocess
import configparser
import RPi.GPIO as GPIO
from os import environ
from camera import AULE


def setup():
  GPIO.setmode(GPIO.BOARD)
  GPIO.setup(11, GPIO.IN)
  GPIO.setup(13, GPIO.IN)

cfg = configparser.ConfigParser()
cfg.read('/etc/aule/aule.cfg')

def getConfigSections(section):
  cfgdict = {}
  options = cfg.options(section)
  for option in options:
    try:
      cfgdict[option] = cfg.get(section, option)
    except:
      cfgdict[option] = None

  return cfgdict

count = 0
t_end = 0

def callback(pin):
  global t_end
  global count
  global sound_thres
  if GPIO.input(pin):
    if pin == 11:
      we_have_sound = False
      if count == 0:
        t_end = time.time() + 30 * 1
        count = count + 1
      elif count > 0:
        if time.time() < t_end:
          count = count + 1
        else:
          count = 0
          t_end = 0
    if (sound_enabled and count == sound_thres) or (motion_enabled and pin == 13):
      print('Will start camera and start streaming...')
      aule.init_cam()
      print('done streaming...')
      count = 0
      
sound_thres = int(getConfigSections('Sound')['threshold'])
sound_enabled = getConfigSections('Sound')['enabled'].lower()
motion_enabled = getConfigSections('Motion')['enabled'].lower()

setup()

if sound_enabled == 'true':
  print('Will react on sound if sensor hits %s' % sound_thres)
  GPIO.add_event_detect(11, GPIO.RISING, bouncetime=300)
  GPIO.add_event_callback(11, callback)

if motion_enabled == 'true':
  print('Will react on motion')
  GPIO.add_event_detect(13, GPIO.BOTH, bouncetime=300)
  GPIO.add_event_callback(13, callback)

aule = AULE()
aule.start_http()
aule.start_websockets()

print('Entering main loop...')

count = 0

while True:
  time.sleep(1)

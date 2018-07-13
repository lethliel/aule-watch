#!/usr/bin/env python3

import sys
import time
import subprocess
import signal
import configparser
import RPi.GPIO as GPIO
import os
from libaule import AULE
import paho.mqtt.client as mqtt

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

# get settings for the detection
sound_thres = int(getConfigSections('Sound')['threshold'])
sound_enabled = False
motion_enabled = False
sound_stream = False
if getConfigSections('Sound')['enabled'].lower() == 'true':
  sound_enabled = True
if getConfigSections('Motion')['enabled'].lower() == 'true':
  motion_enabled = True
if getConfigSections('Sound')['stream'].lower() == 'true':
  sound_stream = True
# get mqtt settings
mqtt_server = getConfigSections('MQTT')['server'].lower()
mqtt_port = int(getConfigSections('MQTT')['port'])
mqtt_user = getConfigSections('MQTT')['user']
mqtt_pass = getConfigSections('MQTT')['pass']
mqtt_channel = getConfigSections('MQTT')['channel']

#get email notification settings
email_to = getConfigSections('EMAIL')['to']

#get http and stream related settings
server_port = int(getConfigSections('STREAM_SERVER')['port'])
stream_duration = int(getConfigSections('STREAM_SERVER')['duration'])




count = 0
t_end = 0

def notify():
  client=mqtt.Client()
  client.username_pw_set(username=mqtt_user, password=mqtt_pass)
  client.connect(mqtt_server, mqtt_port, 60)
  client.publish(mqtt_channel, 'There is something happening. You should watch')
  client.disconnect()

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
      notify()
      if sound_stream:
        print('We have a sound stream')
        p = subprocess.Popen("sh start_audio_stream.sh", shell=True, preexec_fn=os.setsid)
      time.sleep(5)
      try:
        aule.init_cam(duration=stream_duration)
      except KeyboardInterrupt:
        if sound_stream:
          os.killpg(os.getpgid(p.pid), signal.SIGKILL)
      finally:
        if sound_stream:
          os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        count = 0
        print('done streaming...')
      


setup()

if sound_enabled:
  print('Will react on sound if sensor hits %s' % sound_thres)
  GPIO.add_event_detect(11, GPIO.RISING, bouncetime=300)
  GPIO.add_event_callback(11, callback)

if motion_enabled:
  print('Will react on motion')
  GPIO.add_event_detect(13, GPIO.BOTH, bouncetime=300)
  GPIO.add_event_callback(13, callback)

aule = AULE()
aule.start_http()
aule.start_websockets()

print('Entering main loop...')

count = 0

while True:
  time.sleep(0.1)

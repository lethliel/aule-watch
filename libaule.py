#!/usr/bin/python

import sys
import io
import os
import shutil

from subprocess import Popen, PIPE
from string import Template
from struct import Struct
from threading import Thread

import picamera
from time import sleep, time

from http.server import HTTPServer, BaseHTTPRequestHandler
from wsgiref.simple_server import make_server

from ws4py.websocket import WebSocket
from ws4py.server.wsgirefserver import (
    WSGIServer,
    WebSocketWSGIHandler,
    WebSocketWSGIRequestHandler,
)
from ws4py.server.wsgiutils import WebSocketWSGIApplication


WIDTH = 640
HEIGHT = 480
FRAMERATE = 24
HTTP_PORT = 8082
WS_PORT = 8084
COLOR = u'#444'
BGCOLOR = u'#333'
JSMPEG_MAGIC = b'jsmp'
JSMPEG_HEADER = Struct('>4sHH')
VFLIP = False
HFLIP = False

class StreamingHttpHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
            return
        elif self.path == '/start':
           aule.init_cam(timed=False)
           return
        elif self.path == '/jsmpg.js':
            content_type = 'application/javascript'
            content = self.server.jsmpg_content
        elif self.path == '/index.html':
            content_type = 'text/html; charset=utf-8'
            tpl = Template(self.server.index_template)
            content = tpl.safe_substitute(dict(
                WS_PORT=WS_PORT, WIDTH=WIDTH, HEIGHT=HEIGHT, COLOR=COLOR,
                BGCOLOR=BGCOLOR))
        else:
            self.send_error(404, 'File not found')
            return
        content = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(content))
        self.send_header('Last-Modified', self.date_time_string(time()))
        self.end_headers()
        if self.command == 'GET':
            self.wfile.write(content)

class StreamingHttpServer(HTTPServer):
    def __init__(self):
        super(StreamingHttpServer, self).__init__(
                ('', HTTP_PORT), StreamingHttpHandler)
        with io.open('index.html', 'r') as f:
            self.index_template = f.read()
        with io.open('jsmpg.js', 'r') as f:
            self.jsmpg_content = f.read()


class StreamingWebSocket(WebSocket):
    def opened(self):
        self.send(JSMPEG_HEADER.pack(JSMPEG_MAGIC, WIDTH, HEIGHT), binary=True)

class Converter(object):
  def __init__(self, camera):
    print('Will convert into stream...')
    self.converter = Popen([
      'ffmpeg',
      '-f', 'rawvideo',
      '-pix_fmt', 'yuv420p',
      '-s', '%dx%d' % camera.resolution,
      '-r', str(float(camera.framerate)),
      '-i', '-',
      '-f', 'mpeg1video',
      '-b', '800k',
      '-r', str(float(camera.framerate)),
      '-'],
      stdin=PIPE, stdout=PIPE, stderr=io.open(os.devnull, 'wb'),
      shell=False, close_fds=True)

  def write(self, b):
      self.converter.stdin.write(b)

  def flush(self):
      self.converter.stdin.close()
      self.converter.wait()

class BroadcastThread(Thread):
    def __init__(self, converter, websocket_server):
        super(BroadcastThread, self).__init__()
        self.converter = converter
        self.websocket_server = websocket_server

    def run(self):
        try:
            while True:
                buf = self.converter.stdout.read1(32768)
                if buf:
                    self.websocket_server.manager.broadcast(buf, binary=True)
                elif self.converter.poll() is not None:
                    break
        finally:
            self.converter.stdout.close()

class AULE(object):
    def __init__(self):
      #This is an init object for the AULE Watcher
      self.port = '8082'

    def start_websockets(self):
      print('Initializing websocket...')
      WebSocketWSGIHandler.http_version = '1.1'
      self.websocket_server = make_server(
        '', WS_PORT,
        server_class=WSGIServer,
        handler_class=WebSocketWSGIRequestHandler,
        app=WebSocketWSGIApplication(handler_cls=StreamingWebSocket))
      self.websocket_server.initialize_websockets_manager()
      self.websocket_thread = Thread(target=self.websocket_server.serve_forever)

    def start_http(self):
      print('Initializing HTTP server on port %d' % HTTP_PORT)
      http_server = StreamingHttpServer()
      self.http_thread = Thread(target=http_server.serve_forever)
      self.http_thread.start()

    def init_cam(self, timed=True, duration=120):
      print('Initializing camera...')
      with picamera.PiCamera() as camera:
        camera.resolution = (WIDTH, HEIGHT)
        camera.framerate = FRAMERATE
        camera.vflip = VFLIP # flips image rightside up, as needed
        camera.hflip = HFLIP # flips image left-right, as needed
        print('Warm up #5...')
        sleep(2)
        print('Initializing broadcast thread')
        output = Converter(camera)
        broadcast_thread = BroadcastThread(output.converter, self.websocket_server)
        print('Starting recording')
        camera.start_recording(output, 'yuv')
        try:
          if not self.websocket_thread.isAlive(): 
            print('Starting websockets thread')
            self.websocket_thread.start()
          print('Starting broadcast thread')
          broadcast_thread.start()
          if timed == True:
            t_end = time() + 60 * 5
            while time() < t_end:
              camera.wait_recording(1)
          else:
            while True:
              camera.wait_recording(1)
        except KeyboardInterrupt as e:
          pass
        finally:
          print('Stopping recording')
          camera.stop_recording()
          print('Waiting for broadcast thread to finish')
          broadcast_thread.join()
          #print('Waiting for the websocket thread to finish')
          #self.websocket_thread.join()

#!/usr/bin/python

from __future__ import division
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from demo_topology import DemoTopo
from time import sleep
from mininet.link import TCLink

import subprocess
import traceback
import signal
from bottle import request, Bottle, abort
from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler


__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'


MPSDN_PROJECT_FOLDER = '/home/ambi/mpsdn'
VIDEO_FILE = '/home/ambi/vid.m4v'


class Demo:

    def __init__(self):
        self.wsock = None

    def set_wsock(self, ws):
        self.wsock = ws

    def network_creation(self):
        '''
        Initializes the mininet topology, configures singlepath and pings
        src and dst to test reachability
        '''

        print 'Starting controller'
        self.controllerprocess = subprocess.Popen(
            "./configuration/start_controller.sh",
            stdout=subprocess.PIPE
        )
        sleep(1)
        print 'Creating network'
        self.net = Mininet(topo=DemoTopo(), link=TCLink,
                           switch=OVSKernelSwitch, controller=RemoteController)
        self.net.start()
        sleep(1)
        subprocess.call('./configuration/configure_singlepath.sh', shell=True)

        print 'Testing host reachability'
        self.src = self.net.getNodeByName('src')
        self.dst = self.net.getNodeByName('dst')
        self.h1 = self.net.getNodeByName('h1')
        self.h2 = self.net.getNodeByName('h2')
        self.net.ping([self.src, self.dst])

    def start_streaming(self):
        '''
        Starts streaming the video file between src and dst
        '''

        self.rtp_server = self.src.sendCmd(
            "vlc-wrapper -Idummy -vvv %s --repeat --mtu 1500 --sout "
            "'#rtp{dst=10.0.0.2,port=5050,mux=ts,ttl=64}'" % VIDEO_FILE,
            shell=True
        )
        sleep(1)
        self.rtp_client = self.dst.sendCmd(
            'vlc-wrapper --network-caching=0 rtp://@:5050')

    def start_controller(self):
        '''
        Starts the controller monitoring/path setup
        '''

        subprocess.call(
            './configuration/configure_controller_parameters.sh',
            shell=True
        )
        sleep(5)

    def congest_subpath(self):
        '''
        Congesting path until the end of the demo runtime
        '''

        self.iperf_server = self.h2.popen(
            "iperf -u -s"
        )
        sleep(1)
        self.iperf_client = self.h1.sendCmd(
            "iperf -u -c 10.0.0.4 -t 120 -b 20M"
        )

    def readapt(self):
        '''
        Re-running controller computation to adapt
        '''
        subprocess.call(
            'curl http://localhost:8080/multipath/recompute_multipath',
            shell=True
        )


    def start(self):
        try:
            self.network_creation()
            sleep(13)
            self.wsock.send('step1')
            print 'Step 1 - SinglePath Streaming'
            self.start_streaming()
            sleep(30)
            self.wsock.send('step2')
            print 'Step 2 - Starting Multipath controller'
            self.start_controller()
            sleep(30)
            self.wsock.send('step3')
            print 'Step 3 - Congesting Subpath!'
            self.congest_subpath()
            sleep(20)
            self.wsock.send('step4')
            sleep(5)
            print 'Step 4 - Readapting'
            self.readapt()
            sleep(20)

            # Stop
            self.wsock.send('stop')
            sleep(1)
            self.cleanup()
            self.net.stop()

        except:
            print 'Caught exception!  Cleaning up...'
            traceback.print_exc()
            self.cleanup()
            subprocess.call('mn -c', shell=True)
            subprocess.call('pkill -f python', shell=True)

    def stop(self):
        pass

    def cleanup(self):
        print 'Demo Cleanup'
        if hasattr(self, 'iperf_server'):
            self.iperf_server.send_signal(signal.SIGINT)
        subprocess.call('pkill -f iperf', shell=True)
        subprocess.call('pkill -f ryu', shell=True)
        if hasattr(self, 'rtp_client'):
            try:
                self.rtp_client.send_signal(signal.SIGKILL)
            except:
                pass
        print 'Killing VLC'
        subprocess.call('pkill -f vlc', shell=True)


app = Bottle()
demo = Demo()


@app.route('/websocket')
def handle_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')

    while True:
        try:
            message = wsock.receive()
            if message == 'start':
                print 'Received Start Message'
                wsock.send("start")
                demo.set_wsock(wsock)
                print 'Starting Demo'
                demo.start()
            elif message == 'stop':
                demo.stop()
        except WebSocketError:
            break


server = WSGIServer(("0.0.0.0", 9090), app,
                    handler_class=WebSocketHandler)
server.serve_forever()

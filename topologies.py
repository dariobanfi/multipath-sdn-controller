#!/usr/bin/python


'''
Evaluation topology for the controller
'''


from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI

__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'


class EvaluationTopo(Topo):

    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        bej_host = self.addHost('bej_h')
        haw_host = self.addHost('haw_h')
        hkg_host = self.addHost('hkg_h')
        man_host = self.addHost('man_h')
        sha_host = self.addHost('sha_h')
        sin_host = self.addHost('sin_h')
        syd_host = self.addHost('syd_h')
        tok_host = self.addHost('tok_h')

        bej = self.addSwitch(
            'bej', dpid='0000000000000001', protocols='OpenFlow13')
        haw = self.addSwitch(
            'haw', dpid='0000000000000002', protocols='OpenFlow13')
        hkg = self.addSwitch(
            'hkg', dpid='0000000000000003', protocols='OpenFlow13')
        man = self.addSwitch(
            'man', dpid='0000000000000004', protocols='OpenFlow13')
        sha = self.addSwitch(
            'sha', dpid='0000000000000005', protocols='OpenFlow13')
        sin = self.addSwitch(
            'sin', dpid='0000000000000006', protocols='OpenFlow13')
        syd = self.addSwitch(
            'syd', dpid='0000000000000007', protocols='OpenFlow13')
        tok = self.addSwitch(
            'tok', dpid='0000000000000008', protocols='OpenFlow13')

        self.addLink(syd, haw, port1=1, port2=1, delay='75ms', bw=30, loss=0)
        self.addLink(man, haw, port1=1, port2=2, delay='75ms', bw=30, loss=0)
        self.addLink(tok, haw, port1=1, port2=3, delay='75ms', bw=30, loss=0)

        self.addLink(syd, sin, port1=2, port2=1, delay='50ms', bw=30, loss=0)

        self.addLink(sin, man, port1=2, port2=2, delay='10ms', bw=10, loss=0)
        self.addLink(sin, tok, port1=3, port2=2, delay='10ms', bw=10, loss=0)
        self.addLink(sin, hkg, port1=4, port2=1, delay='10ms', bw=10, loss=0)
        self.addLink(man, hkg, port1=3, port2=2, delay='10ms', bw=10, loss=0)
        self.addLink(hkg, sha, port1=3, port2=1, delay='10ms', bw=10, loss=0)
        self.addLink(hkg, bej, port1=4, port2=1, delay='10ms', bw=10, loss=0)
        self.addLink(sha, bej, port1=2, port2=2, delay='10ms', bw=10, loss=0)
        self.addLink(sha, tok, port1=3, port2=3, delay='10ms', bw=10, loss=0)

        self.addLink(syd, tok, port1=3, port2=4, delay='60ms', bw=20, loss=0)

        self.addLink(bej, bej_host)
        self.addLink(haw, haw_host)
        self.addLink(hkg, hkg_host)
        self.addLink(man, man_host)
        self.addLink(sha, sha_host)
        self.addLink(sin, sin_host)
        self.addLink(syd, syd_host)
        self.addLink(tok, tok_host)


topos = {'evaluation': (lambda: EvaluationTopo())}

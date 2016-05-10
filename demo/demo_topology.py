#!/usr/bin/python

from mininet.topo import Topo

'''
Useful topologies used for testing / simulations
'''

__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'


class DemoTopo(Topo):

    def __init__(self, **opts):
        Topo.__init__(self, **opts)

        src = self.addHost('src', ip='10.0.0.1')
        dst = self.addHost('dst', ip='10.0.0.2')
        h1 = self.addHost('h1', ip='10.0.0.3')
        h2 = self.addHost('h2', ip='10.0.0.4')

        self.switch = {}
        for s in range(1, 7):
            self.switch[s-1] = self.addSwitch(
                's%s' % (s), dpid='000000000000000%s' % s,
                protocols='OpenFlow13'
            )

        self.addLink(
            self.switch[0], self.switch[1], port1=1, port2=1)
        self.addLink(
            self.switch[0], self.switch[3], port1=2, port2=1)

        self.addLink(self.switch[1], self.switch[2],
                     port1=2, port2=1, delay='25ms', bw=7
                     )
        self.addLink(self.switch[2], self.switch[5], port1=2, port2=1)

        self.addLink(self.switch[3], self.switch[4],
                     port1=2, port2=1, delay='25ms', bw=7
                     )
        self.addLink(self.switch[4], self.switch[5], port1=2, port2=2)

        self.addLink(self.switch[0], src)
        self.addLink(self.switch[5], dst)
        self.addLink(self.switch[3], h1)
        self.addLink(self.switch[4], h2)

topos = {'demo': (lambda: DemoTopo())}

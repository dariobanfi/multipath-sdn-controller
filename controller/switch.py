#!/usr/bin/python

from ryu.topology import switches
from ryu.topology.switches import Port as Port_type
from ryu.ofproto.ofproto_v1_0_parser import OFPPhyPort

import netaddr
import logging

__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'

'''
Representation of a Switch and its ports in the MPSDN network
'''

logger = logging.getLogger(__name__)


class Port(switches.Port):

    def __init__(self, port, peer=None, dp=None, is_edge=True):

        # Dpid of peering switch
        self.peer_switch_dpid = None

        # Port_no of peer
        self.peer_port_no = None

        # Delay cost
        self.latency = 0.001

        # Max capacity cost Bytes/s
        # Setting here a default upper limit of 200Mb/s
        self.max_capacity = 25000000

        # Real capacity
        self.capacity = self.max_capacity

        # Used for the algorithm
        self.capacity_maxflow = self.capacity

        # Last time port stats were requested
        self.last_request_time = None

        # Last utilization value computed for the port
        self.last_utilization_value = None

        # Edge ports are ports which are connected to the host networks
        # Every port is initialized as edge_port by default
        # and set to False once a addLink event is seen
        self.is_edge = is_edge

        if isinstance(port, Port_type):
            # init switches.Port variables
            self.dpid = port.dpid
            self._ofproto = port._ofproto
            self._config = port._config
            self._state = port._state

            self.port_no = port.port_no
            self.hw_addr = netaddr.EUI(port.hw_addr)
            self.name = port.name

            # below are our new variables
            if peer:
                self.peer_switch_dpid = peer.dpid
                self.peer_port_no = peer.port_no
        elif isinstance(port, OFPPhyPort):
            self.dpid = dp.id
            self._ofproto = dp.ofproto
            self._config = port.config
            self._state = port.state

            self.port_no = port.port_no
            self.hw_addr = netaddr.EUI(port.hw_addr)
            self.name = port.name
        else:
            logger.error('%s %s %s not match',
                         type(port),
                         switches.Port,
                         Port_type
                         )
            raise AttributeError

    def restore_capacity(self):
        '''
        Resets the capacity which had been decreased by the
        max-flow algorithm
        '''
        self.capacity_maxflow = self.capacity

    def set_max_capacity(self, capacity):
        self.max_capacity = capacity
        self.capacity = capacity
        self.capacity_maxflow = capacity

    def __repr__(self):
        return 'Port<no=%d capacity_maxflow=%f latency=%f>' % (
            self.port_no, self.capacity_maxflow, self.latency
        )

    def __str__(self):
        return 'Port<no=%d capacity_maxflow=%f latency=%f>' % (
            self.port_no, self.capacity_maxflow, self.latency
        )


class Switch(switches.Switch):

    def __init__(self, dp):

        # Init with Datapath object
        super(Switch, self).__init__(dp)

        self.ip_network = None

        self.ip_netmask = None

        self.edge_port = None

        self.peer_to_local_port = {}

        self.ports = {}

        self.delay_to_controller = 0

        self.port_stats_request_time = 0

    def calculate_delay_to_controller(self, timedelta):
        '''
        Smoothes the sample delay to controller with previous
        measurements
        '''
        if self.port_stats_request_time != 0:

            sample_delay = (timedelta - self.port_stats_request_time) / 2

            # Smoothed RTT, like TCP
            if self.delay_to_controller == 0:
                self.delay_to_controller = sample_delay
            else:
                self.delay_to_controller = 0.875 * \
                    self.delay_to_controller + 0.125 * sample_delay

            self.port_stats_request_time = 0
        else:
            logger.error(
                'Trying to calculate switch-controller delay '
                'without initial time value'
                         )

    def calculate_delay_to_peer(self, peer_switch, delay):
        '''
        Smoothes the delay of two peering switches
        '''

        peer_port_no = self.peer_to_local_port[peer_switch]
        delay = delay - self.delay_to_controller - \
            peer_switch.delay_to_controller
        # When delays are very low calculation can be imprecise
        if(delay < 0):
            delay = 0
        if self.ports[peer_port_no].latency != float('inf'):
            # Smoothed RTT
            self.ports[peer_port_no].latency = 0.875 * \
                self.ports[peer_port_no].latency + 0.125 * delay
        else:
            self.ports[peer_port_no].latency = delay

        logger.info('Sample delay from dp %d to %d is %f' %
                    (self.dp.id, peer_switch.dp.id, delay))

    def has_peer_capacity(self):
        ''' Returns true if any of the connected ports to this
        switch sill have capacity_maxflow>0
        '''
        retval = False
        for port_no, port in self.ports.iteritems():
            if not port.is_edge and port.capacity_maxflow > 0:
                retval = True
                break
        return retval

    def __repr__(self):
        msg = 'Switch<dpid=%s, p=' % self.dp.id
        for port in self.ports:
            msg += str(port) + ','

        msg += ' delay=%f>' % self.delay_to_controller
        return msg

    def __str__(self):
        msg = 'Switch<dpid=%s, p=' % self.dp.id
        for port in self.ports:
            msg += str(port) + ','

        msg += ' delay=%f>' % self.delay_to_controller
        return msg

    def __eq__(self, other):
        try:
            if self.dp.id == other.dp.id:
                return True
        except:
            return False
        return False

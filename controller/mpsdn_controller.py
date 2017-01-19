#!/usr/bin/python

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.topology import event
from network_topology import NetworkTopology
from ryu.topology.switches import LLDPPacket
from ryu.lib.packet import (packet, ethernet, arp, icmp, icmpv6, ipv4, ipv6)
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json
import time
import traceback

'''
MPSDN Network Controller for a L2 network
'''

__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'


API_INSTANCE_NAME = 'mp_controller_api_app'


class MultipathController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(MultipathController, self).__init__(*args, **kwargs)

        # Random ethertype to evaluate latency
        self.PROBE_ETHERTYPE = 0x07C7

        # Set to true once there is enoough informatio
        # to start multipath computation
        self.network_is_measured = False

        # Maximum delay imbalance to use a reordering buffer
        # Example 25ms,50ms = |(25/75)-0.5| = 0.16
        self.MDI_REORDERING_THRESHOLD = 0.2

        # Maximum delay imbalance threshold for not using multipath
        self.MDI_DROP_THRESHOLD = 0.25

        # If this value is changed in the configuration, the path setup
        # algorithm is halted if a path has more hops to the destination
        # than this limit.
        # If left -1, MDI_DROP will be used instead!
        # It is suited for L2 Networks where link delays will be
        # very similar
        self.MAX_HOP_DIFFERENCE = -1

        # Minimum available capacity a path needs to be used in B/s
        self.MIN_MULTIPATH_CAPACITY = 100

        # Maximum paths allowed for a multipath flow
        self.MAX_PATHS_PER_MULTIPATH_FLOW = 2

        # Recalculates bucket only on addition or failures in the topology
        self.UPDATE_FORWARDING_ON_TOPOLOGY_CHANGE_ONLY = False

        # Recomputes forwarding continuously reardless of congestion/failures
        self.UPDATE_FORWARDING_CONTINOUSLY = False

        # High priority
        self.PRIORITY_PROBE_PACKETS = 65000

        # Monitoring frequency for port stats.
        self.MONITORING_PORT_STATS_FREQUENCY = 5

        self.MONITORING_PORT_STATS = False

        # Used for REST APIs
        wsgi = kwargs['wsgi']
        wsgi.register(MultipathRestController, {API_INSTANCE_NAME: self})

        # Holds the topology data and structure
        self.topo_shape = NetworkTopology(self)

    ##########################################
    #              UTILITY FUNCTIONS         #
    ##########################################

    def run(self):
        '''
        Called to start the monitoring/computation in the controller
        It can be called with a GET to the API:
        /multipath/start_path_computation
        '''

        # Network monitor module
        self.monitoringhub = hub.spawn(self.network_monitor)

        # Multipath computation module
        hub.spawn_after(5, self.multipath_computation)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ''' Adds a flow to a datapath '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def _send_packet(self, datapath, port, pkt):
        ''' Instructs a datapath to output a packet to one of his ports '''
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.debug('packet-out %s' % (pkt,))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

    def set_edge_ports(self):
        # Setting the edge port [port connected to host networks]
        # of a switch to be the highest in number
        # (In mininet it corresponds to the host port when they are
        # added at the end of the topology creation)
        for dp_id, switch in self.topo_shape.dpid_to_switch.iteritems():
            switch.edge_port = len(switch.ports.keys())

    def multipath_computation(self):
        while True:
            if not self.topo_shape.is_empty() and self.network_is_measured:
                computation_start = time.time()
                self.logger.info('Starting multipath computation sub-routine')
                self.topo_shape.multipath_computation()
                self.logger.info(
                    'Multipath computation finished in %f seconds',
                    time.time() - computation_start
                )

            self.MONITORING_PORT_STATS = True
            if self.UPDATE_FORWARDING_CONTINOUSLY:
                hub.sleep(10)
            else:
                break

    def add_default_flows(self, datapath):
        '''
        Adds default unknown flows to the controller
        '''

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 1, match, actions)

        # Installing the flow rules to send latency probe packets
        match = parser.OFPMatch(eth_type=self.PROBE_ETHERTYPE)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, self.PRIORITY_PROBE_PACKETS, match, actions)

    def add_default_for_all(self):
        for dpid, s in self.topo_shape.dpid_to_switch:
            self.add_default_flows(s.dp)

    def stop_monitoring(self):
        self.keep_monitoring = False



    ##########################################
    #      NETWORK DISCOVERY HANDLERS        #
    ##########################################

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        '''
        Switch features handler callback
        '''
        self.logger.debug('EventOFPSwitchFeatures')
        self.add_default_flows(ev.msg.datapath)


    @set_ev_cls(event.EventSwitchEnter, MAIN_DISPATCHER)
    def switch_enter_handler(self, event):
        self.logger.info('EventSwitchEnter')
        self.topo_shape.add_switch(event.switch)

    @set_ev_cls(event.EventSwitchLeave, MAIN_DISPATCHER)
    def switch_leave_handler(self, event):
        self.logger.debug('EventSwitchLeave')

        # Redundant for Mininet emulated network since
        # you cannot remove switches/link once the topology
        # has started

        # self.topo_shape.remove_switch(event.switch)

    @set_ev_cls(event.EventLinkAdd, MAIN_DISPATCHER)
    def link_add_handler(self, event):
        self.logger.info('EventLinkAdd')
        self.topo_shape.add_link(event)

    @set_ev_cls(event.EventLinkDelete, MAIN_DISPATCHER)
    def link_delete_handler(self, event):
        self.logger.debug('EventLinkDelete %s' % event)
        # Redundant for Mininet emulated network since
        # you cannot remove switches/link once the topology
        # has started

        # self.topo_shape.remove_link(event)

    @set_ev_cls(event.EventPortAdd, MAIN_DISPATCHER)
    def port_add_handler(self, event):
        self.logger.info('EventPortAdd')
        self.topo_shape.add_port(event.port)

    @set_ev_cls(event.EventPortDelete, MAIN_DISPATCHER)
    def port_delete_handler(self, event):
        self.logger.debug('EventPortDelete')

        # Redundant for Mininet emulated network since
        # you cannot remove switches/link once the topology
        # has started

        # self.topo_shape.remove_port(event.port)

    ##########################################
    #              NETWORK MONITORING        #
    ##########################################

    def network_monitor(self):
        ''' Monitors network RTT and Congestion '''

        self.logger.info('Starting monitoring sub-routine')
        # First, we get an estimation of the link benchmark_network_capacity
        # in a state where the network will be idle.
        self.benchmark_network_capacity()

        self.keep_monitoring = True
        # Then we start the periodic measurement of RTT times and port
        # utilization

        counter = 0
        while self.keep_monitoring:
            if not self.topo_shape.is_empty():
                self.logger.debug('Requesting port stats to '
                                  'measure utilization')
                self.logger.info('\n------------------')
                for dpid, s in self.topo_shape.dpid_to_switch.iteritems():

                    s.port_stats_request_time = time.time()

                    # Requesting portstats to calculate controller
                    # to switch delay and congeston
                    # if self.MONITORING_PORT_STATS:
                    self._request_port_stats(s)

                    # Calculating peering switches RTT (once every 10 portstats
                    # so ~10 secs)
                    if counter % 30 == 0:
                        self.send_latency_probe_packet(s)

                counter += 1

            hub.sleep(self.MONITORING_PORT_STATS_FREQUENCY)

        self.logger.info('Stopping monitor')

    def benchmark_network_capacity(self):
        '''
        This mechanism is left for future work.
        It can send a high rate UDP from hosts to destination to and measure
        on the receiving switch the drop rate of the packets, to infer the link
        capacity
        Currently the max capacity is set through REST APIs
        '''

        pass

    def send_latency_probe_packet(self, switch):
        '''
        Injects latency probe packets in the network
        '''
        self.logger.info('Injecting latency probe packets')

        for peer_switch, peer_port in switch.peer_to_local_port.iteritems():

            self.logger.debug('Sending probe packet from %s to %s through '
                              ' port %s',
                              switch, peer_switch, peer_port
                              )

            actions = [switch.dp.ofproto_parser.OFPActionOutput(peer_port)]

            pkt = packet.Packet()
            pkt.add_protocol(ethernet.ethernet(ethertype=self.PROBE_ETHERTYPE,
                                               dst=0x000000000001,
                                               src=0x000000000000)
                             )

            pkt.serialize()
            payload = '%d;%d;%f' % (
                switch.dp.id, peer_switch.dp.id, time.time())
            data = pkt.data + payload

            out = switch.dp.ofproto_parser.OFPPacketOut(
                datapath=switch.dp,
                buffer_id=switch.dp.ofproto.OFP_NO_BUFFER,
                data=data,
                in_port=switch.dp.ofproto.OFPP_CONTROLLER,
                actions=actions
            )

            switch.dp.send_msg(out)

    def probe_packet_handler(self, pkt):
        '''
        Handles a latency probe packets and computes the
        delay between two switches
        '''
        try:
            receive_time = time.time()
            # Ignoring 14 bytes of ethernet header
            data = pkt.data[14:].split(';')
            send_dpid = int(data[0])
            recv_dpid = int(data[1])
            inc_time = float(data[2])
            sample_delay = receive_time - inc_time
            self.topo_shape.dpid_to_switch[send_dpid].calculate_delay_to_peer(
                self.topo_shape.dpid_to_switch[recv_dpid], sample_delay)
            self.network_is_measured = True
        except:
            traceback.print_exc()
            self.logger.error('Unable to parse incoming probe packet')

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        '''
        Handles a PORT STATS response from a switch
        '''

        ports = ev.msg.body
        port_stats_reply_time = time.time()

        # Calculate switch-controller RTT
        switch = self.topo_shape.dpid_to_switch[ev.msg.datapath.id]
        switch.calculate_delay_to_controller(port_stats_reply_time)

        sorted_port_table = sorted(ports, key=lambda l: l.port_no)
        for stat in sorted_port_table:
            if stat.port_no not in switch.ports:
                continue
            port = switch.ports[stat.port_no]
            utilization = stat.tx_bytes + stat.rx_bytes

            if port.last_request_time:
                timedelta = port_stats_reply_time - port.last_request_time
                datadelta = utilization - port.last_utilization_value

                utilization_bps = datadelta / timedelta
                port.capacity = port.max_capacity - utilization_bps

                self.logger.info(
                    's[%s] p[%d] utilization %2.f max_capacity %s',
                    switch.dp.id, stat.port_no,
                    utilization_bps,
                    port.max_capacity
                )
            port.last_request_time = port_stats_reply_time
            port.last_utilization_value = utilization

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        '''
        Handles a FLOW STATS reply
        '''

        self.logger.debug(
            'Receive flow stats response from: %016x at t: %f',
            ev.msg.datapath.id,
            time.time()
        )

        body = ev.msg.body

        self.logger.debug('datapath         '
                          'in-port  eth-dst         '
                          'out-port packets  bytes')

        self.logger.debug('---------------- '
                          '-------- ----------------- '
                          '-------- -------- --------')

        self.logger.debug(ev.msg.body)
        for stat in sorted(
            [flow for flow in body if flow.priority == 1],
            key=lambda flow: (flow.match['in_port'], flow.match['eth_dst'])
        ):
            self.logger.info(
                '%016x %8x %17s %8x %8d %8d',
                ev.msg.datapath.id,
                stat.match['in_port'], stat.match['eth_dst'],
                stat.instructions[0].actions[0].port,
                stat.packet_count, stat.byte_count
            )

    def _request_flow_stats(self, switch):
        '''
        Requests flow stats for a switch
        '''
        self.logger.debug(
            'Request flow stats for: %016x at t: %f',
            switch.dp.id, time.time()
        )
        parser = switch.dp.ofproto_parser
        req = parser.OFPFlowStatsRequest(switch.dp)
        switch.dp.send_msg(req)

    def _request_port_stats(self, switch):
        '''
        Request port statistic to a switch
        '''
        self.logger.debug(
            'Request port stats for dp %s at t: %f',
            switch.dp.id, time.time()
        )
        ofproto = switch.dp.ofproto
        parser = switch.dp.ofproto_parser
        req = parser.OFPPortStatsRequest(switch.dp, 0, ofproto.OFPP_ANY)
        switch.dp.send_msg(req)

    ##########################################
    #             PACKET IN HANDLER          #
    ##########################################

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)

        pkt_ethernet = pkt.get_protocols(ethernet.ethernet)[0]
        datapath = msg.datapath
        port = msg.match['in_port']

        # Checking if it's the probe packet for RTT estimation
        if pkt_ethernet.ethertype == self.PROBE_ETHERTYPE:
            self.probe_packet_handler(pkt)
            return

        # Ignoring LLDP Packets
        try:
            LLDPPacket.lldp_parse(msg.data)
            self.logger.debug('Received LLDP Packet')
            return
        except:
            pass

        self.logger.debug('EventOFPPacketIn %s' % pkt)

        # Handling ARP
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            self._handle_arp(msg, datapath, port, pkt, pkt_arp)
            return

        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
        pkt_icmp = pkt.get_protocol(icmp.icmp)

        # Handling ICMPv4
        if pkt_icmp:
            self._handle_icmpv4(
                msg, datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp)
            return

        # Handing IPv4
        if pkt_ipv4:
            self._handle_ipv4(datapath, port, pkt_ethernet, pkt_ipv4)
            return

        pkt_ipv6 = pkt.get_protocol(ipv6.ipv6)
        pkt_icmp = pkt.get_protocol(icmpv6.icmpv6)

        # Handling ICMPv6
        if pkt_icmp:
            self._handle_icmpv6(
                datapath, port, pkt_ethernet, pkt_ipv6, pkt_icmp)
            return

        # Handing IPv6
        if pkt_ipv4:
            self._handle_ipv6(datapath, port, pkt_ethernet, pkt_ipv4)
            return

        # Unhandled
        self.logger.debug('Unknown packet %s' % str(pkt))

    def _handle_arp(self, msg, datapath, in_port_no, pkt, pkt_arp):

        self.logger.debug('ARP Packet %s' % pkt_arp)

    def _handle_icmpv4(self, msg, datapath, in_port_no, pkt_ethernet, pkt_ipv4,
                       pkt_icmp):

        self.logger.debug('Handling ICMP packet %s', pkt_icmp)

    def _handle_ipv4(self, datapath, port, pkt_ethernet, pkt_ipv4):
        self.logger.debug(
            'Handling ip packet  from port %d - %s' % (port, pkt_ipv4)
        )

    def _handle_ipv6(self, datapath, port, pkt_ethernet, pkt_ipv6):
        self.logger.debug('Handling ipv6 packet')

    def _handle_icmpv6(self, datapath, port, pkt_ethernet, pkt_ipv6, pkt_icmp):
        self.logger.debug('Handling ICMPv6 Packet')


class MultipathRestController(ControllerBase):

    def __init__(self, req, link, data, **config):
        super(MultipathRestController, self).__init__(
            req, link, data, **config)
        self.mp_instance = data[API_INSTANCE_NAME]

    @route('multipath',
           '/multipath/set_port_weight/{dp_id}/{port_no}/{weight}',
           methods=['GET'])
    def set_port_weight(self, req, **kwargs):
        multipath_controller = self.mp_instance

        try:
            dp_id = int(kwargs['dp_id'])
            port_no = int(kwargs['port_no'])
            weight = int(kwargs['weight'])
            multipath_controller.topo_shape.dpid_to_switch[
                dp_id].ports[port_no].set_max_capacity(weight)
        except:
            traceback.print_exc()
            return Response(content_type='text/html', body='Failure!\n')

        return Response(content_type='text/html', body='Success !\n')

    @route('multipath',
           '/multipath/set_edge_port/{dp_id}/{port_no}',
           methods=['GET'])
    def set_edge_port(self, req, **kwargs):
        multipath_controller = self.mp_instance

        try:
            dp_id = int(kwargs['dp_id'])
            port_no = int(kwargs['port_no'])
            multipath_controller.topo_shape.dpid_to_switch[
                dp_id].edge_port = port_no
        except:
            traceback.print_exc()
            return Response(content_type='text/html', body='Failure!\n')

        return Response(content_type='text/html', body='Success !\n')

    @route('multipath', '/multipath/set_ip_network/{dp_id}/{ip}/{netmask}',
           methods=['GET'])
    def set_ip_network(self, req, **kwargs):
        multipath_controller = self.mp_instance
        try:
            dp_id = int(kwargs['dp_id'])
            ip_net = kwargs['ip']
            netmask = kwargs['netmask']
            multipath_controller.topo_shape.dpid_to_switch[
                dp_id].ip_network = ip_net
            multipath_controller.topo_shape.dpid_to_switch[
                dp_id].ip_netmask = netmask
        except:
            traceback.print_exc()
            return Response(content_type='text/html', body='Failure!\n')

        return Response(content_type='text/html', body='Success !\n')

    @route('multipath', '/multipath/start_path_computation', methods=['GET'])
    def start_path_computation(self, req, **kwargs):
        multipath_controller = self.mp_instance

        multipath_controller.run()

        return Response(content_type='text/html',
                        body='Path computation started!\n')

    @route('multipath', '/multipath/recompute_multipath', methods=['GET'])
    def start_path_recomputation(self, req, **kwargs):
        multipath_controller = self.mp_instance

        hub.spawn_after(
            1,
            multipath_controller.multipath_computation
        )


        return Response(content_type='text/html',
                        body='Path recomputatation started!\n')

    @route('multipath', '/multipath/configuration', methods=['POST'])
    def configure_controller_parameters(self, req, **kwargs):
        multipath_controller = self.mp_instance

        config = json.loads(req.body)

        if 'max_hop_difference' in config.keys():
            multipath_controller.MAX_HOP_DIFFERENCE = config['max_hop_difference']
        if 'mdi_reordering' in config.keys():
            multipath_controller.MDI_REORDERING_THRESHOLD = float(
                config['mdi_reordering']
            )
        if 'mdi_drop' in config.keys():
            multipath_controller.MDI_DROP_THRESHOLD = float(
                config['mdi_drop']
            )
        if 'max_paths' in config.keys():
            multipath_controller.MAX_PATHS_PER_MULTIPATH_FLOW = int(
                config['max_paths']
            )
        if 'min_multipath_capacity' in config.keys():
            multipath_controller.MIN_MULTIPATH_CAPACITY = int(
                config['min_multipath_capacity']
            )

        if 'monitoring_frequency_seconds' in config.keys():
            multipath_controller.MONITORING_PORT_STATS_FREQUENCY = int(
                config['monitoring_frequency_seconds']
            )

        return Response(content_type='text/html',
                        body='Configuration accepted\n')

    @route('multipath',
           '/multipath/change_bucket_weight/{dp_id}/{group_id}/{rules}',
           methods=['GET'])
    def change_bucket_weight(self, req, **kwargs):
        '''
        Changes bucket weight for a datapath's GROUP
        Rules are passed in this format port,weight; :
        Example : '1,1;2,1;3,2;4,2'
        '''
        multipath_controller = self.mp_instance

        try:
            dp_id = kwargs['dp_id']
            group_id = kwargs['group_id']
            arg_rules = kwargs['rules']
            rules = {}
            for i in arg_rules.split(';'):
                rules[int(i.split(',')[0])] = int(i.split(',')[1])

            multipath_controller.topo_shape.modify_group(
                multipath_controller.topo_shape.dpid_to_switch[
                    int(dp_id)].dp, int(group_id), rules)
        except:
            traceback.print_exc()

        return Response(content_type='text/html', body='Done!\n')

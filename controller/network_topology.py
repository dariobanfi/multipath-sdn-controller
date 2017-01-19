#!/usr/bin/python

from itertools import tee, islice, chain, izip
from switch import Port, Switch
import logging
import time
import random
import itertools

__author__ = 'Dario Banfi'
__license__ = 'Apache 2.0'
__version__ = '1.0'
__email__ = 'dario.banfi@tum.de'

'''
 Representation of the network topology knowledge mantained
 by the Controller and algorithms necessary to compute and
 set up multipath forwarding flow rules
'''

logger = logging.getLogger(__name__)


class NetworkTopology():

    def __init__(self, controller, *args, **kwargs):

        self.controller = controller

        # Datapath id - Switch dict
        self.dpid_to_switch = {}

        # Dictionary containing the output of the controller
        # path computation algorithm
        self.mp_config = {}

        # Path finding algorithm used inside the max-flow to find
        # forwarding paths
        self.pathfindinding_algo = Dijkstra(
            self.dpid_to_switch,
            controller.MIN_MULTIPATH_CAPACITY,
            controller.UPDATE_FORWARDING_ON_TOPOLOGY_CHANGE_ONLY,
        )

        # Dictionary containg multipath group id for a specific tuple
        # node, src, dst, in_port
        self.multipath_group_ids = {}

        # Group id numbers already in use
        self.group_ids = []

        # Default priority for output rules and splitting groups
        self.PRIORITY_DEFAULT = 32768

        # A bit higher priority for the reordering one so that
        self.PRIORITY_REORDERING = 32800

        # Maximum paths allowed for a multipath flow
        controller.MAX_PATHS_PER_MULTIPATH_FLOW = 2

        # Group number for reordering
        self.OPENFLOW_GROUP_REORDERING = 4

    def is_empty(self):
        return len(self.dpid_to_switch) == 0

    ##########################################
    #            TOPOLOGY CREATION           #
    ##########################################

    def add_switch(self, switch):
        '''
        Adds a switch to the topology
        '''
        if switch.dp.id not in self.dpid_to_switch:
            s = Switch(switch.dp)
            self.dpid_to_switch[switch.dp.id] = s
            for port in switch.ports:
                self.add_port(port)
            self.pathfindinding_algo.topology_last_update = time.time()

    def remove_switch(self, switch):
        '''
        Removes a switch to the topology
        '''
        if switch and switch.dp.id in self.dpid_to_switch:
            del self.dpid_to_switch[switch.dp.id]
            self.pathfindinding_algo.topology_last_update = time.time()

    def add_port(self, port):
        '''
        Adds a port to the topology
        '''
        port = Port(port)
        switch = self.dpid_to_switch[port.dpid]
        switch.ports[port.port_no] = port
        self.pathfindinding_algo.topology_last_update = time.time()

    def remove_port(self, port):
        '''
        Removes a switch to the topology
        '''
        port = Port(port)
        try:
            switch = self.dpid_to_switch[port.dpid]
            del switch.ports[port.port_no]
            self.pathfindinding_algo.topology_last_update = time.time()
        except KeyError:
            return

    def _update_port_link(self, dpid, port):
        '''
        Updates a port
        '''
        switch = self.dpid_to_switch[dpid]
        p = switch.ports.get(port.port_no, None)
        if p:
            p.peer_switch_dpid = port.peer_switch_dpid
            p.peer_port_no = port.peer_port_no
            p.is_edge = False
        else:
            switch.ports[port.port_no] = port

        peer_switch = self.dpid_to_switch[port.peer_switch_dpid]
        switch.peer_to_local_port[peer_switch] = port.port_no

    def add_link(self, event):
        '''
        Adds a link from port to to port
        '''
        src_port = Port(
            port=event.link.src, peer=event.link.dst, is_edge=False)
        dst_port = Port(
            port=event.link.dst, peer=event.link.src, is_edge=False)
        self._update_port_link(src_port.dpid, src_port)
        self._update_port_link(dst_port.dpid, dst_port)
        self.pathfindinding_algo.topology_last_update = time.time()

    def __remove_link(self, port):
        if port.dpid in self.dpid_to_switch:
            switch = self.dpid_to_switch[port.dpid]
            p = switch.ports[port.port_no]
            p.peer_switch_dpid = None
            p.peer_port_no = None

    def remove_link(self, event):
        '''
        Removes a link from a port
        '''
        try:
            switch_1 = self.dpid_to_switch[event.link.src.dpid]
            switch_2 = self.dpid_to_switch[event.link6.dst.dpid]
            del switch_1.peer_to_local_port[switch_2]
            del switch_2.peer_to_local_port[switch_1]

        except KeyError:
            return

        self.__remove_link(event.link.src)
        self.__remove_link(event.link.dst)
        self.pathfindinding_algo.topology_last_update = time.time()

    ##########################################
    #                PATH SETUP              #
    ##########################################

    def multipath_computation(self):
        edges = []
        self.mp_config = {}

        for dpid, switch in self.dpid_to_switch.iteritems():
            #  Updating the capacity_maxflow variable which will be
            # modified by the algorithm with the realtime monitored capacity
            for port_no, port in switch.ports.iteritems():
                port.capacity_maxflow = port.capacity
            # Adding the edge switches to a list
            if switch.edge_port:
                edges.append(switch)

        # Calculate forwarding paths between all edges couples
        logger.info('%s', self.dpid_to_switch)
        for edge_couple in itertools.permutations(edges, 2):
            self.calculate_multipath(edge_couple[0], edge_couple[1])
            self.create_flow_rules(edge_couple[0], edge_couple[1])
            logger.info('-' * 20)

    def restore_capacities(self):
        '''
        Restores max_flow capacities modified by the algorithm
        '''
        for dpid, switch in self.dpid_to_switch.iteritems():
            for port_no, port in switch.ports.iteritems():
                port.restore_capacity()

    def calculate_multipath(self, src, dst):

        paths = []
        previous_path = None

        while True:
            shortest_path = self.pathfindinding_algo.find_route(src, dst)
            if shortest_path and previous_path is None:
                previous_path = shortest_path

            # Limiting the number of paths in a multipath flow
            path_limit_reached = len(paths) + 1 > self.controller.MAX_PATHS_PER_MULTIPATH_FLOW

            path_delays = []

            if shortest_path is None:
                logger.info('Path computation Algorithm terminates '
                            '- NO MORE PATHS')
                break
            else:
                path_delays.append(shortest_path.latency())
                path_delays.append(previous_path.latency())

            # Stopping algorithm on MAX_HOP_DIFFERENCE
            if self.controller.MAX_HOP_DIFFERENCE != -1 and (shortest_path.length() - previous_path.length()) > self.controller.MAX_HOP_DIFFERENCE:
                logger.info('Path computation Algorithm terminates '
                            ' - MAX HOP REACHED')
                break

            # Stopping algorithm on MDI_DROP_THRESHOLD
            if (self.mdi(path_delays) > self.controller.MDI_DROP_THRESHOLD):
                logger.info('Path computation Algorithm '
                            'terminates - MDI_DROP_THRESHOLD REACHED')
                break
            if path_limit_reached is None:
                logger.info('Path computation Algorithm terminates '
                            '- PATH LIMIT REACHED')
                break

            paths.append(shortest_path)

            capacity = shortest_path.capacity()
            latency = shortest_path.latency()
            logger.info('Computed path %s capacity %f latency %f' %
                        (shortest_path, capacity, latency))
            self.save_path(src, dst, shortest_path, capacity, latency)
            shortest_path.decrease_capacity(capacity)

        self.restore_capacities()

    def save_path(self, src, dst, path, capacity, latency):
        for previous_node, node, next_node in path.iter_previous_and_next():
            if node == src:
                input_intf = node.edge_port
            else:
                input_intf = node.peer_to_local_port[previous_node]

            if node == dst:
                output_intf = node.edge_port
            else:
                output_intf = node.peer_to_local_port[next_node]

            if (dst, src, node, input_intf, output_intf) in self.mp_config:
                self.mp_config[
                    dst, src, node, input_intf, output_intf
                    ] += (capacity, latency)
            else:
                self.mp_config[dst, src, node, input_intf, output_intf] = (
                    capacity, latency)

    def generate_openflow_gid(self):
        '''
        Returns a random OpenFlow group id
        '''
        n = random.randint(0, 2**32)
        while n in self.group_ids:
            n = random.randint(0, 2**32)  # lol
        return n

    def mdi(self, rules):
        '''
        The delay imbalance metric checks all the path delays and
        computes the maximum inbalance between them:
        Eg : [50,50,50] 3 paths with the same delay, so the delay
        imbalance will be 0
        Eg : [50,60,300] 3 paths and different delays, the value will be 0.35

        The value ranges from [0 to 0.5] where 0 is no imbalance
        '''
        max_delay_imbalance = 0
        for x, y in itertools.combinations(rules, 2):
            try:
                max_delay_imbalance = max(
                    max_delay_imbalance, abs((x/(x+y))-0.5)
                )
            except ZeroDivisionError:
                max_delay_imbalance = 0

        logger.info(
            'Max delay imbalance for %s is %f',
            rules,
            max_delay_imbalance
        )

        return max_delay_imbalance

    def create_flow_rules(self, src, dst):
        '''
        Creates flow rules from a src to a dst switch
        '''

        # Do the magic
        mp_dict = {}
        for k, v in self.mp_config.iteritems():
            reduce(
                lambda a, b: a.setdefault(b, {}), k[:-1], mp_dict)[k[-1]] = v

        if not mp_dict:
            return

        for node in mp_dict[dst][src]:

            # The switch has multiple paths converging
            max_delay_imbalance = -1
            in_latencies = []
            in_ports = 0

            for in_port in mp_dict[dst][src][node]:
                in_ports += 1
                out_rules = {}
                out_total_capacity = 0
                out_total_latency = 0

                for out_port in mp_dict[dst][src][node][in_port]:
                    capacity = mp_dict[dst][src][node][in_port][out_port][0]
                    latency = mp_dict[dst][src][node][in_port][out_port][1]
                    out_rules[out_port] = (capacity, latency)
                    out_total_capacity += capacity
                    out_total_latency += latency
                    in_latencies.append(latency)

                in_latencies.append(latency)

                group_id = None
                group_new = False

                # The switch is splitting traffic in multipath
                if len(out_rules) > 1:
                    only_delays = [x[1][1] for x in out_rules.items()]
                    max_delay_imbalance = self.mdi(
                        only_delays
                    )

                    if (node, src, dst, in_port) not in self.multipath_group_ids:
                        group_new = True
                        self.multipath_group_ids[
                            node, src, dst, in_port
                        ] = self.generate_openflow_gid()

                    group_id = self.multipath_group_ids[
                        node, src, dst, in_port
                    ]

                # Adding flow out_rules
                ofp = node.dp.ofproto
                ofp_parser = node.dp.ofproto_parser
                match_ip = ofp_parser.OFPMatch(
                    eth_type=0x0800,
                    ipv4_src=(src.ip_network, src.ip_netmask),
                    ipv4_dst=(dst.ip_network, dst.ip_netmask),
                    in_port=in_port
                )
                match_arp = ofp_parser.OFPMatch(
                    eth_type=0x0806,
                    arp_spa=src.ip_network,
                    arp_tpa=dst.ip_network,
                    in_port=in_port
                )

                # Sending SELECT Rules
                if group_id:
                    buckets = []
                    for port, (capacity, latency) in out_rules.iteritems():
                        bucket_weight = self.compute_bucket_weight(
                            out_total_capacity,
                            capacity,
                            out_total_latency,
                            latency,
                            max_delay_imbalance
                        )
                        bucket_action = [
                            ofp_parser.OFPActionOutput(port, 2000)
                        ]
                        if(bucket_weight > 0):
                            buckets.append(
                                ofp_parser.OFPBucket(
                                    weight=bucket_weight,
                                    actions=bucket_action
                                )
                            )
                    # If GROUP Was new, we send a GROUP_ADD
                    if group_new:
                        logger.info(
                            'GROUP_ADD for %s from %s to %s port '
                            '%d GROUP_ID %d out_rules %s',
                            node, src, dst, in_port, group_id, buckets
                        )
                        logger.info('GROUP_ADD_BUCKETS %s', buckets)

                        req = ofp_parser.OFPGroupMod(
                            node.dp, ofp.OFPGC_ADD, ofp.OFPGT_SELECT, group_id,
                            buckets
                        )
                        node.dp.send_msg(req)

                    # If the GROUP already existed, we send a GROUP_MOD to
                    # eventually adjust the buckets with current link
                    # utilization
                    else:
                        req = ofp_parser.OFPGroupMod(
                            node.dp, ofp.OFPGC_MODIFY, ofp.OFPGT_SELECT,
                            group_id, buckets)
                        node.dp.send_msg(req)
                        logger.info('GROUP_MOD for %s from %s to %s port %d '
                                    'GROUP_ID %d out_rules %s',
                                    node, src, dst, in_port, group_id, buckets
                                    )
                        logger.info('GROUP_MOD_BUCKETS %s', buckets)

                    actions = [ofp_parser.OFPActionGroup(group_id)]
                    self.controller.add_flow(node.dp, self.PRIORITY_DEFAULT,
                                             match_ip, actions, buffer_id=None)
                    self.controller.add_flow(node.dp, 1, match_arp,
                                             actions, buffer_id=None)

                # Sending OUTPUT Rules
                else:
                    logger.info('Match for %s from %s to %s port '
                                '%d out_rules %s',
                                node, src, dst, in_port, out_rules)
                    port, rate = out_rules.popitem()
                    actions = [ofp_parser.OFPActionOutput(port)]
                    self.controller.add_flow(node.dp, self.PRIORITY_DEFAULT,
                                             match_ip, actions, buffer_id=None)
                    self.controller.add_flow(
                        node.dp, self.PRIORITY_DEFAULT,
                        match_arp, actions, buffer_id=None
                    )

            # Creating the reordering group if there are multiple paths
            # converging on the node and their delay imbalance is above the
            # threeshold
            if in_ports > 1 and self.mdi(in_latencies) > self.controller.MDI_REORDERING_THRESHOLD:
                self.create_reordering_group(
                    node, src, dst, mp_dict[dst][src][node]
                )

    def create_reordering_group(self, node, src, dst, in_to_out_ports):

        ofp = node.dp.ofproto
        ofp_parser = node.dp.ofproto_parser
        group_id = self.generate_openflow_gid()
        out_port_no = in_to_out_ports.values()[0].keys()[0]
        buckets = []
        bucket_action = [ofp_parser.OFPActionOutput(out_port_no, 2000)]
        buckets.append(ofp_parser.OFPBucket(actions=bucket_action))
        req = ofp_parser.OFPGroupMod(
            node.dp, ofp.OFPGC_ADD, self.OPENFLOW_GROUP_REORDERING,
            group_id, buckets
        )
        node.dp.send_msg(req)

        logger.info(
            'REORDERING at %s to port %d GROUP_ID %d',
            node, out_port_no, group_id
        )

        for in_port in in_to_out_ports.keys():
            match = ofp_parser.OFPMatch(
                eth_type=0x0800, in_port=in_port, ip_proto=6,
                ipv4_src=(src.ip_network,
                          src.ip_netmask),
                ipv4_dst=(dst.ip_network, dst.ip_netmask)
            )
            actions = [ofp_parser.OFPActionGroup(group_id)]
            self.controller.add_flow(node.dp, self.PRIORITY_REORDERING,
                                     match, actions, buffer_id=None)

    def compute_bucket_weight(self, total_capacity, capacity, total_latency,
                              latency, max_delay_imbalance):
        '''
        This function computes the bucket weight, AKA the number of
        packets which are sent over each iteration of the weighted round robin
        Scheduler.
        I saw experimentally that having bursts the size of 50-100 packets
        is the best compromise
        between throughput/reordering with paths that differ a lot in latency.
        If the latency is very close to be the same, I use smaller bursts
        (~10 packets) to fully utilize
        the combined path capacity
        Latency infulences the bucket size but not as much as the capacity,
        the reordering buffer will take care of it
        '''

        c_ratio = float(capacity) / float(total_capacity)
        l_ratio = latency / total_latency

        if max_delay_imbalance < 0.15:
            c_var = 4
            l_var = 0  # Latency is not impactful in such low levels
        elif max_delay_imbalance < 0.25:
            c_var = 10
            l_var = 8
        else:
            c_var = 150
            l_var = 50

        # More capacity more packets, more delay,less packets
        # outval = c_var*c_ratio + (l_var-l_var*l_ratio)

        # Using only bandwidth for bucket weight because there needs to be some
        # better formula otherwise with very low latencies the differences can
        # be huge
        outval = c_var*c_ratio

        logger.info('total_c: %f c_ratio: %f c: %f total_l: %f l_ratio: %f l:'
                    ' %f Bucket weight -> %d',
                    total_capacity, c_ratio, capacity, total_latency,
                    l_ratio, latency, outval
                    )

        return int(outval)

    def modify_group(self, datapath, group_id, rules):

        logger.info('Modify group for %s gid %s rules %s',
                    datapath, group_id, rules)

        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        buckets = []

        for port, rate in rules.iteritems():
            bucket_action = [ofp_parser.OFPActionOutput(port, 2000)]
            buckets.append(ofp_parser.OFPBucket(
                weight=rate, actions=bucket_action)
            )

        req = ofp_parser.OFPGroupMod(
            datapath, ofp.OFPGC_MODIFY, ofp.OFPGT_SELECT,
            group_id, buckets
        )

        datapath.send_msg(req)

    def remove_flow_rules(self, datapath, table_id, match, instructions):
        '''Create OFP flow mod message to remove flows from table'''
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(
            datapath, 0, 0, table_id, ofproto.OFPFC_DELETE, 0, 0, 1,
            ofproto.OFPCML_NO_BUFFER, ofproto.OFPP_ANY,
            ofproto.OFPG_ANY, 0,  match, instructions
        )

        return flow_mod

    def delete_all_flows(self, switch):

        for dpid, node in self.dpid_to_switch.iteritems():
            ofp_parser = switch.dp.ofproto_parser

            empty_match = ofp_parser.OFPMatch()
            instructions = []
            flow_mod = self.remove_flow_rules(
                switch.dp, 0,
                empty_match, instructions
            )
            switch.dp.send_msg(flow_mod)


class Path:

    def __init__(self, node):
        self.nodes = [node]

    def insert(self, index, node):
        self.nodes.insert(index, node)

    def length(self):
        return len(self.nodes)

    def capacity(self):
        capacity = float('inf')
        for previous_node, node, next_node in self.iter_previous_and_next():
            if next_node:
                next_port = node.peer_to_local_port[next_node]
                capacity = min(
                    capacity, node.ports[next_port].capacity_maxflow)
        return capacity

    def latency(self):
        latency = 0
        for previous_node, node, next_node in self.iter_previous_and_next():
            if next_node:
                next_port = node.peer_to_local_port[next_node]
                latency += node.ports[next_port].latency
        return latency

    def decrease_capacity(self, capacity):
        for previous_node, node, next_node in self.iter_previous_and_next():
            if next_node:
                next_port = node.peer_to_local_port[next_node]
                node.ports[next_port].capacity_maxflow -= capacity

    def get_nodes_without(self, node):
        retval = list(self.nodes)
        retval.remove(node)
        return retval

    def iter_previous_and_next(self):
        prevs, items, nexts = tee(self.nodes, 3)
        prevs = chain([None], prevs)
        nexts = chain(islice(nexts, 1, None), [None])
        return izip(prevs, items, nexts)

    def __str__(self):
        s = ''
        for node in self.nodes:
            s = '%s%s   ' % (s, node)
        return s


class Algorithm(object):

    ''' Algorithm base class '''

    def __init__(self, dpid_to_switch, mintravcap, topochangeupdate):
        self.dpid_to_switch = dpid_to_switch
        self.topology_last_update = time.time()
        self.min_trasverse_capacity = mintravcap
        self.update_forwarding_only_on_topology_change = topochangeupdate


    def find_route(self, src, dst):
        '''
            Sub-classes implement this method to calculate
            to calculate the paths
         '''
        logger.error('Algorithm not implemented')
        return None


class Dijkstra(Algorithm):

    class Heap(object):

        '''
            Minimal heap, stores tuple (switch, distance)
        '''

        def __init__(self):
            self.heap = []
            self.switch_to_position = {}

        def insert(self, switch, dist):
            self.heap.append((switch, dist))
            self.switch_to_position[switch] = len(self.heap) - 1
            self._shift_to_root(len(self.heap) - 1)

        def _shift_to_root(self, position):
            while position > 0 and \
                    self.heap[position][1] < self.heap[(position - 1) / 2][1]:
                self._exchange(position, (position - 1) / 2)
                position = (position - 1) / 2

        def pop(self):
            length = len(self.heap)
            if length == 0:
                return None

            ans = self.heap[0]

            self.heap[0] = self.heap[length - 1]
            self.switch_to_position[self.heap[0][0]] = 0
            self.heap.pop()
            del self.switch_to_position[ans[0]]

            self._shift_to_leaf(0)

            return ans

        def _shift_to_leaf(self, position):
            length = len(self.heap)
            while position * 2 + 1 < length:
                if position * 2 + 2 < length:
                    if self.heap[position * 2 + 1][1] < self.heap[position * 2 + 2][1]:
                        if self.heap[position][1] > self.heap[position * 2 + 1][1]:
                            self._exchange(position, position * 2 + 1)
                            position = position * 2 + 1
                        else:
                            break
                    else:
                        if self.heap[position][1] > self.heap[position * 2 + 2][1]:
                            self._exchange(position, position * 2 + 2)
                            position = position * 2 + 2
                        else:
                            break
                else:
                    if self.heap[position][1] > self.heap[position * 2 + 1][1]:
                        self._exchange(position, position * 2 + 1)
                        position = position * 2 + 1
                    else:
                        break

        def _exchange(self, x, y):
            # x and y are positions in self.heap
            self.heap[x], self.heap[y] = self.heap[y], self.heap[x]
            self.switch_to_position[self.heap[x][0]] = x
            self.switch_to_position[self.heap[y][0]] = y

        def update(self, switch, distance):
            position = self.switch_to_position[switch]
            self.heap[position] = (switch, distance)
            self._shift_to_leaf(position)
            self._shift_to_root(position)

        def __repr__(self):
            return str(self.heap)

    def __init__(self, *args, **kwargs):
        super(Dijkstra, self).__init__(*args, **kwargs)
        self.paths = {}
        self.route_last_update = time.time()

    def find_route(self, source, destination):
        logger.info('Searching route from %s to %s' % (source, destination))
        if self.update_forwarding_only_on_topology_change:
            if self.route_last_update < self.topology_last_update:
                self.paths = {}
                self.route_last_update = time.time()
        else:
            self.paths = {}
            self.route_last_update = time.time()

        logger.debug('self.topology_last_update %s' %
                     self.topology_last_update)

        if (source, destination) in self.paths:
            logger.info('Path pre-computed')
            return self.paths[source, destination]

        pq = Dijkstra.Heap()
        distance = {}
        previous = {}

        for dpid, switch in self.dpid_to_switch.iteritems():
            if switch != source:
                distance[switch] = float('inf')
            else:
                distance[switch] = 0

            previous[switch] = None
            logger.debug('Inserting %s in the queue' % switch)
            pq.insert(switch, distance[switch])

        while True:
            x = pq.pop()
            logger.info('Popping %s : %f' % x)
            if x is None:
                break

            logger.info('%s', pq)
            switch, dist = x

            if not switch.has_peer_capacity():
                logger.info('No peer capacity')
                break

            if switch == destination:
                calculated_path = Path(destination)
                while previous[switch]:
                    calculated_path.insert(0, previous[switch])
                    switch = previous[switch]
                self.paths[source, destination] = calculated_path
                if calculated_path.length() == 1:
                    return None
                else:
                    return calculated_path

            for port_no, port in switch.ports.iteritems():
                logger.debug('Analyzing %s %d %s - peer_switch_dpid: %s' %
                             (switch, port_no, port, port.peer_switch_dpid))

                peer_switch = self.dpid_to_switch.get(port.peer_switch_dpid,
                                                      None)

                if peer_switch is None or port.capacity_maxflow <= self.min_trasverse_capacity:
                    logger.info('Port %s cannot be traversed' % port)
                    continue
                logger.info('dist %s port latency %s  distance %s' %
                             (dist, port.latency, distance[peer_switch]))

                if dist + port.latency < distance[peer_switch]:
                    distance[peer_switch] = dist + port.latency
                    pq.update(peer_switch, dist + port.latency)
                    previous[peer_switch] = switch

        return None

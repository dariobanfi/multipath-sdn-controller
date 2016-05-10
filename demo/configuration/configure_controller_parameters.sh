# Configuring controller parameters
curl -X POST -d '{
    "max_hop_difference": 1,
    "mdi_reordering": 0.8,
    "mdi_drop": 0.8,
    "max_paths": 2,
    "min_multipath_capacity": 100,
    "monitoring_frequency_seconds" : 5
 }' http://localhost:8080/multipath/configuration


#  Setting MAXIMUM port speeds ~ 7 Mb/s
curl http://localhost:8080/multipath/set_port_weight/2/2/876000
curl http://localhost:8080/multipath/set_port_weight/3/1/876000
curl http://localhost:8080/multipath/set_port_weight/4/2/876000
curl http://localhost:8080/multipath/set_port_weight/5/1/876000


# Setting the subnet of the switches
curl http://localhost:8080/multipath/set_ip_network/1/10.0.0.1/255.255.255.255
curl http://localhost:8080/multipath/set_ip_network/6/10.0.0.2/255.255.255.255
curl http://localhost:8080/multipath/set_ip_network/4/10.0.0.3/255.255.255.255
curl http://localhost:8080/multipath/set_ip_network/5/10.0.0.4/255.255.255.255

# Setting the edge ports
curl http://localhost:8080/multipath/set_edge_port/1/3
curl http://localhost:8080/multipath/set_edge_port/6/3
curl http://localhost:8080/multipath/set_edge_port/4/3
curl http://localhost:8080/multipath/set_edge_port/5/3

# Starting multipath computation
curl http://localhost:8080/multipath/start_path_computation
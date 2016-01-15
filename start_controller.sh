# Deleting first the flows which were already set on our topology

if [[ $1 = "c" ]]; then 
    ovs-ofctl -O OpenFlow13 del-flows bej
    ovs-ofctl -O OpenFlow13 del-flows haw
    ovs-ofctl -O OpenFlow13 del-flows hkg
    ovs-ofctl -O OpenFlow13 del-flows man
    ovs-ofctl -O OpenFlow13 del-flows sha
    ovs-ofctl -O OpenFlow13 del-flows sin
    ovs-ofctl -O OpenFlow13 del-flows syd
    ovs-ofctl -O OpenFlow13 del-flows tok
fi

# Start controller
ryu-manager --observe-links --enable-debugger controller/mpsdn_controller.py

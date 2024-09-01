from server import dhcp

configuration = dhcp.DHCPServerConfiguration()
configuration.debug = print
#configuration.adjust_if_this_computer_is_a_router()
#configuration.router  # += ['192.168.0.1']
configuration.ip_address_lease_time = 60
configuration.network="192.168.1.2"
server = dhcp.DHCPServer(configuration)

for ip in server.configuration.all_ip_addresses():
    print(ip, server.configuration.network_filter())
    assert ip == server.configuration.network_filter()

server.run()
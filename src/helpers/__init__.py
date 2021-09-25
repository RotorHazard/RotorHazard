
def i2c_url(bus_id, addr):
    return "i2c:{}/{:#04x}".format(bus_id, addr)


def parse_i2c_url(url):
    if not url.startswith('i2c:'):
        raise ValueError('Invalid I2C URL: {}'.format(url))
    bus_addr = url[4:].split('/')
    return (int(bus_addr[0]), int(bus_addr[1], 16))


def socket_url(ip, port):
    return "socket://{}:{}/".format(ip, port)


def parse_socket_url(url):
    if not url.startswith('socket://'):
        raise ValueError('Invalid socket URL: {}'.format(url))
    start = 9
    end = -1 if url[-1] == '/' else len(url)
    ip_port = url[start:end].split(':')
    return (ip_port[0], int(ip_port[1]))

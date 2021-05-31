
def i2c_url(bus_id, addr):
    return "i2c:{}/{:#04x}".format(bus_id, addr)

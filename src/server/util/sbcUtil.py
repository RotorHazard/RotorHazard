
model = None
def get_sbc_model() -> str:
    global model
    if not model:
        with open('/proc/device-tree/model') as f:
            model = f.read()
    return model

def is_raspberry() -> bool:
    return get_sbc_model().find('Raspberry') > -1

def is_libre() -> bool:
    return get_sbc_model().find('Libre') > -1

def is_known_sbc() -> bool:
    return is_raspberry() or is_libre()


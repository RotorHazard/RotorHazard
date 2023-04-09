
def get_sbc_model() -> str:
    with open('/proc/device-tree/model') as f:
        model = f.read()
    return model

def is_raspberry() -> bool:
    model = get_sbc_model()
    return model.find('Raspberry') > -1

def is_libre() -> bool:
    model = get_sbc_model()
    return model.find('Libre') > -1


import logging

logger = logging.getLogger(__name__)
model = None
def get_sbc_model() -> str:
    global model
    if not model:
        try:
            with open('/proc/device-tree/model') as f:
                model = f.read()
        except FileNotFoundError:
            logger.error("Failed to find sbc model")
            model = ""
    return model.strip('\x00')

def is_raspberry() -> bool:
    return "Raspberry" in get_sbc_model()

def is_libre() -> bool:
    return "Libre" in get_sbc_model()

def is_known_sbc() -> bool:
    return is_raspberry() or is_libre()

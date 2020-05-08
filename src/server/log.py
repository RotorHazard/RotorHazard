import sys
import logging.handlers
import platform

import gevent

ROTORHAZARD_FORMAT = "<-RotorHazard: %(name)s-> %(message)s"


class GEventDeferredHandler(logging.Handler):

    def __init__(self, handler):
        super(GEventDeferredHandler, self).__init__()
        self._handler = handler

    def emit(self, record):
        gevent.spawn(self._handler.emit(record))


class SocketForwardHandler(logging.Handler):

    def __init__(self, socket, *a, **kw):
        super(SocketForwardHandler, self).__init__(*a, **kw)
        self._socket = socket

    def emit(self, record):
        self._socket.emit("hardware_log", record.getMessage())


def early_stage_setup():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format=ROTORHAZARD_FORMAT,
    )
    # some 3rd party packages use logging. Good for them. Now be quiet.
    for name in [
            "geventwebsocket.handler",
            "socketio.server",
            "engineio.server",
            "sqlalchemy",
            ]:
        logging.getLogger(name).setLevel(logging.WARN)


def handler_for_config(destination):
    system_logger = logging.handlers.SysLogHandler("/dev/log") \
      if platform.system() == "Linux" else \
      logging.handlers.NTEventLogHandler("RotorHazard")

    choices = {
        "STDERR": logging.StreamHandler(stream=sys.stderr),
        "STDOUT": logging.StreamHandler(stream=sys.stdout),
        "SYSLOG": system_logger
    }
    if destination in choices:
        return choices[destination]
    # we assume if the entry is not amongst them
    # pre-defined choices, it's a filename
    return logging.FileHandler(destination)


def later_stage_setup(config, socket):
    logging_config = dict(
        LEVEL="INFO",
        DESTINATION="STDERR",
    )
    logging_config.update(config)

    root = logging.getLogger()
    # empty out the already configured handler
    # from basicConfig
    root.handlers[:] = []
    handlers = [
        SocketForwardHandler(socket),
        handler_for_config(
            logging_config["DESTINATION"]
        )
    ]
    level = getattr(logging, logging_config["LEVEL"])
    root.setLevel(level)

    for handler in handlers:
        handler.setFormatter(logging.Formatter(ROTORHAZARD_FORMAT))
        root.addHandler(GEventDeferredHandler(handler))

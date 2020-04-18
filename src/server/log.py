import sys
import logging.handlers

ROTORHAZARD_FORMAT = "<-RotorHazard-> %(message)s"


def early_stage_setup():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format=ROTORHAZARD_FORMAT,
    )
    # some 3rd party packages use logging. Good for them. Now be quiet.
    logging.getLogger("socketio.server").setLevel(logging.WARN)
    logging.getLogger("engineio.server").setLevel(logging.WARN)


def handler_for_config(destination):
    choices = {
        "STDERR": logging.StreamHandler(stream=sys.stderr),
        "STDOUT": logging.StreamHandler(stream=sys.stdout),
        "SYSLOG": logging.handlers.SysLogHandler("/dev/log")
    }
    if destination in choices:
        return choices[destination]
    # we assume if the entry is not amongst them
    # pre-defined choices, it's a filename
    return logging.FileHandler(destination)


def later_stage_setup(config):
    logging_config = dict(
        LEVEL="INFO",
        DESTINATION="STDERR",
    )
    logging_config.update(config)

    root = logging.getLogger()
    # empty out the already configured handler
    # from basicConfig
    root.handlers[:] = []
    handler = handler_for_config(
        logging_config["DESTINATION"]
    )
    handler.setFormatter(logging.Formatter(ROTORHAZARD_FORMAT))
    level = getattr(logging, logging_config["LEVEL"])
    root.setLevel(level)
    root.addHandler(handler)

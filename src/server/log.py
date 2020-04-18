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

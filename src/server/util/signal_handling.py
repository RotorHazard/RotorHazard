import logging
from functools import partial

import gevent.event
import gevent.signal as signal

logger = logging.getLogger(__name__)

## This uses linux signals to detect shutdown of computer.
# A few notes:
# This will NOT work if the process is started in an ssh terminal, or even a local terminal.
# for this method to work correctly, the process needs to be started ether by the system as a service.
# Or within a `screen` session.
#
# To install screen: `sudo apt-get install screen`
def register_signal_handlers(*handlers):
    """
    Register handlers run on all relevant signals but SIGHUP.

    Handlers are simple callables without any arguments.
    """
    handler_event = gevent.event.Event()

    def process_handlers():
        handler_event.wait()

        for handler in handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error running signal {handler}")
                logger.exception(e)

    def ignore_sighup(*_args):
        logger.warn(f'Ignoring {signum}, {frame}')


    def signal_forwarder(event, *args):
        event.set()

    for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGQUIT]:
        signal.signal(sig, partial(signal_forwarder, handler_event))

    signal.signal(signal.SIGHUP, ignore_sighup)

    gevent.spawn(process_handlers)

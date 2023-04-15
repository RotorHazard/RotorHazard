import logging
from functools import partial

import gevent.event
import gevent.signal as signal
import signal as _signal

logger = logging.getLogger(__name__)

## This uses linux signals to detect shutdown of computer.
# A few notes:
# This will NOT work if the process is started in an ssh terminal, or even a local terminal.
# for this method to work correctly, the process needs to be started ether by the system as a service.
# Or within a `screen` session.

# The reason for this is because when started in a terminal, the terminal will 'hear' the SIGTERM before
# the service will, and the terminal will send a SIGKILL to all it's children (the service included).
# SIGKILL does not give us a chance to cleanly shutdown.
#
# To install screen: `sudo apt-get install screen`
def register_signal_handlers(*handlers):

    """
    register_signal_handlers is useful for listening
    to linux (and windows) signals to gracefully
    shut down an application.

    To use, write a function or functions that
    handle all the work you would like to do on
    shutdown. Then call this method with those functions
    in order you want them called:
    ```
        def func1():
            pass

        def func2():
            pass

        my_killer = register_signal_handlers(func1, func2)
    ```
    That's it.  func1 and then func2 will be
    called when any of SIGTERM, SIGINT, SIGQUIT is fired.

    This also happens when you Ctrl-C a program,
    so it will gracefully shut down then as well.

    """

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
        logger.warning(f'Ignoring {_args[0]}, {_args[1]}')


    def signal_forwarder(event, *args):
        """When called (by a signal) fire the gevent event created earlier"""
        event.set()

    #different OS's send different signals. the please terminate signal can be any of these three.
    for sig in [_signal.SIGINT, _signal.SIGTERM, _signal.SIGQUIT]:
        signal.signal(sig, partial(signal_forwarder, handler_event))

    # debian also sends a SIGHUP. we need to ignore it or the process quits early.
    signal.signal(_signal.SIGHUP, ignore_sighup)

    gevent.spawn(process_handlers)

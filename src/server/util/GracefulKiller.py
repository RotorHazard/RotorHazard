import signal

## This uses linux signals to detect shutdown of computer.
# A few notes:
# This will NOT work if the process is started in an ssh terminal, or even a local terminal.
# for this method to work correctly, the process needs to be started ether by the system as a service.
# Or within a `screen` session.
#
# To install screen: `sudo apt-get install screen`

class GracefulKiller:
    """
    Class GracefulKiller is useful for listening
    to linux (and windows) signals to gracefully
    shut down an application.

    To use, write a function or functions that
    handle all the work you would like to do on
    shutdown. Then instantiate an instance
    of this class passing in an array to those functions
    in order you want them called:
    ```
        def func1():
            pass

        def func2():
            pass

        my_killer = GracefulKiller([func1, func2])
    ```
    That's it.  func1 and then func2 will be
    called when a SIGTERM is fired.

    This also happens when you Ctrl-C a program,
    so it will gracefully shut down then as well.

    if app uses a `while true` loop for execution
    my_killer.kill_now can be checked to see
    if the loop should exit.

    ```
        killer = GracefulKiller([func1])

        while not killer.kill_now:
            print('do work')
    ```

    """
    kill_now = False

    def __init__(self, handlers, logger=None):
        self.handlers = handlers
        self.logger = logger
        # Listen for ctrl-c
        signal.signal(signal.SIGINT, self.process_handlers)
        # Listen for kill
        signal.signal(signal.SIGTERM, self.process_handlers)
        # debian also sends a SIGHUP. we need to ignore it or the process quits early.
        signal.signal(signal.SIGHUP, self.ignore)
        # Listen for kill but with core dump.
        signal.signal(signal.SIGQUIT, self.process_handlers)


    def ignore(self, signal, frame):
        self.log_or_print(f'Ignoring {signal}, {frame}')

    def process_handlers(self, code, frame):
        self.log_or_print(f"Code: {code}  Frame: {frame}\n")
        for todo in self.handlers:
            todo(code, frame)
        self.actually_die()
    def actually_die(self):
        """
        when gracefulkiller is used
        in an infinite loop, kill_now can be used
        to detect when to exist the loop.
        """
        self.kill_now = True

    def log_or_print(self, message):
        if self.logger:
            self.logger.debug(message)
        else
            print(message)

import signal
import time

## This tests using linux signals to shutdown rotorhazard.
# A few notes:
# This will NOT work if the process is started in an ssh terminal, or even a local terminal.
# for this method to work correctly, the process needs to be started ether by the system as a service.
# Or within a `screen` session.
#
# To install screen: `sudo apt-get install screen`
# I'm writing to a log file instead of print because


out = open('signal_log.txt', 'w')

class GracefulKiller:
    kill_now = False

    def __init__(self, handlers):
        self.handlers = handlers

        # Listen for cntrl-c
        signal.signal(signal.SIGINT, self.process_handlers)
        # Listen for kill
        signal.signal(signal.SIGTERM, self.process_handlers)
        # debian also sends a SIGHUP. we need to ignore it or the process quits early.
        signal.signal(signal.SIGHUP, self.ignore)
        # Listen for kill but with core dump.
        signal.signal(signal.SIGQUIT, self.process_handlers)


    def ignore(self, sig, frame):
        out.write('ignoring signal %d\n' % sig)
        out.flush()


    def killed(self, code, frame):
        out.write(f"Code: {code}  Frame: {frame}\n")
        out.flush()

    def process_handlers(self, code, frame):
        out.write(f"Code: {code}  Frame: {frame}\n")
        out.flush()
        for todo in self.handlers:
            todo(code, frame)
        self.actually_die()
    def actually_die(self):
        out.write('     Signed: Calculon\n')
        out.flush()
        self.kill_now = True


def dramatic_pause(*args):
    out.write("Have been......\n")
    out.flush()
    time.sleep(5)


def exit_gracefully(*args):
    out.write("......\n")
    out.write("killed\n")
    out.flush()


if __name__ == '__main__':
    killer = GracefulKiller([dramatic_pause, exit_gracefully])
    while not killer.kill_now:
        out.write("doing something in a loop ...\n")
        out.flush()
        time.sleep(1)
    out.write("End of the program. I was killed gracefully :)\n")
    out.flush()

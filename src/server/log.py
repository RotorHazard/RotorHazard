import sys
import os
import glob
import logging.handlers
import platform
import gevent
from datetime import datetime

# Sample configuration:
#     "LOGGING": {
#         "CONSOLE_LEVEL": "INFO",
#         "SYSLOG_LEVEL": "NONE",
#         "FILELOG_LEVEL": "INFO",
#         "FILELOG_NUM_KEEP": 30,
#         "CONSOLE_STREAM": "stdout"
#     }
#
# Valid log levels:  DEBUG, INFO, WARNING, WARN, ERROR, FATAL, CRITICAL, NONE
# FILELOG_NUM_KEEP is number of log files to keep, rest will be deleted (oldest first)
# CONSOLE_STREAM may be "stdout" or "stderr"

DEF_CONSOLE_STREAM = sys.stdout  # default console-output stream
DEF_FILELOG_NUM_KEEP = 30        # default number of log files to keep

LOG_FILENAME_STR = "rh.log"
LOG_DIR_NAME = "logs"

CONSOLE_FORMAT_STR = "%(message)s"
SYSLOG_FORMAT_STR = "<-RotorHazard-> %(name)s [%(levelname)s] %(message)s"
FILELOG_FORMAT_STR = "%(asctime)s.%(msecs)03d: %(name)s [%(levelname)s] %(message)s"

CONSOLE_LEVEL_STR = "CONSOLE_LEVEL"
SYSLOG_LEVEL_STR = "SYSLOG_LEVEL"
FILELOG_LEVEL_STR = "FILELOG_LEVEL"
FILELOG_NUM_KEEP_STR = "FILELOG_NUM_KEEP"
CONSOLE_STREAM_STR = "CONSOLE_STREAM"
LEVEL_NONE_STR = "NONE"


class GEventDeferredHandler(logging.Handler):

    def __init__(self, handler):
        super(GEventDeferredHandler, self).__init__()
        self._handler = handler

    def emit(self, record):
        if record.levelno >= self._handler.level:
            gevent.spawn(self._handler.emit(record))


class SocketForwardHandler(logging.Handler):

    def __init__(self, socket, *a, **kw):
        super(SocketForwardHandler, self).__init__(*a, **kw)
        self._socket = socket

    def emit(self, record):
        self._socket.emit("hardware_log", record.getMessage())


def early_stage_setup():
    logging.addLevelName(0, LEVEL_NONE_STR)
    logging.basicConfig(
        stream=DEF_CONSOLE_STREAM,
        level=logging.INFO,
        format=CONSOLE_FORMAT_STR
    )

    # some 3rd party packages use logging. Good for them. Now be quiet.
    for name in [
            "geventwebsocket.handler",
            "socketio.server",
            "engineio.server",
            "sqlalchemy",
            ]:
        logging.getLogger(name).setLevel(logging.WARN)


# Completes the logging setup.
# Returns the path/filename for the current log file in use, or None.
def later_stage_setup(config, socket):
    logging_config = {}
    logging_config[CONSOLE_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[SYSLOG_LEVEL_STR] = LEVEL_NONE_STR
    logging_config[FILELOG_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[FILELOG_NUM_KEEP_STR] = DEF_FILELOG_NUM_KEEP
    logging_config[CONSOLE_STREAM_STR] = DEF_CONSOLE_STREAM.name[1:-1]

    logging_config.update(config)
    
    root = logging.getLogger()
    # empty out the already configured handler
    # from basicConfig
    root.handlers[:] = []

    # TODO: log level and format for socket handler?
    handlers = [ SocketForwardHandler(socket) ]
    
    min_level = logging.CRITICAL  # track minimum specified log level

    # TODO: handle bogus level names
    lvl = logging.getLevelName(logging_config[CONSOLE_LEVEL_STR])
    if lvl > 0:
        stm_obj = sys.stdout if sys.stderr.name.find(logging_config[CONSOLE_STREAM_STR]) != 1 else sys.stderr
        hdlr_obj = logging.StreamHandler(stream=stm_obj)
        hdlr_obj.setLevel(lvl)
        hdlr_obj.setFormatter(logging.Formatter(CONSOLE_FORMAT_STR))
        handlers.append(hdlr_obj)
        if lvl < min_level:
            min_level = lvl

    lvl = logging.getLevelName(logging_config[SYSLOG_LEVEL_STR])
    if lvl > 0:
        system_logger = logging.handlers.SysLogHandler("/dev/log", level=lvl) \
                        if platform.system() != "Windows" else \
                        logging.handlers.NTEventLogHandler("RotorHazard")
        system_logger.setLevel(lvl)
        system_logger.setFormatter(logging.Formatter(SYSLOG_FORMAT_STR))
        handlers.append(system_logger)
        if lvl < min_level:
            min_level = lvl

    lvl = logging.getLevelName(logging_config[FILELOG_LEVEL_STR])
    if lvl > 0:
        # put log files in subdirectory, and with date-timestamp in names
        (lfname, lfext) = os.path.splitext(LOG_FILENAME_STR)
        num_old_del = deleteOldLogfiles(logging_config[FILELOG_NUM_KEEP_STR], lfname, lfext)
        if not os.path.exists(LOG_DIR_NAME):
            os.makedirs(LOG_DIR_NAME)
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path_name = LOG_DIR_NAME + '/' + lfname + '_' + time_str + lfext
        hdlr_obj = logging.FileHandler(log_path_name)
        hdlr_obj.setLevel(lvl)
        # configure log format with milliseconds as ".###" (not ",###")
        hdlr_obj.setFormatter(logging.Formatter(fmt=FILELOG_FORMAT_STR, datefmt='%Y-%m-%d %H:%M:%S'))
        handlers.append(hdlr_obj)
        if lvl < min_level:
            min_level = lvl
    else:
        num_old_del = 0
        log_path_name = None

    root.setLevel(min_level)

    for handler in handlers:
        root.addHandler(GEventDeferredHandler(handler))

    if num_old_del > 0:
        logging.debug("Deleted {0} old log file(s)".format(num_old_del))

    return log_path_name


def deleteOldLogfiles(num_keep_val, lfname, lfext):
    num_del = 0
    try:
        if num_keep_val > 0:
            num_keep_val -= 1  # account for log file that's about to be created
            file_list = list(filter(os.path.isfile, glob.glob(LOG_DIR_NAME + '/' + lfname + '*' + lfext)))
            file_list.sort(key=os.path.getmtime)  # sort by last-modified time
            if len(file_list) > num_keep_val:
                if num_keep_val > 0:
                    file_list = file_list[:(-num_keep_val)]
                for del_path in file_list:
                    os.remove(del_path)
                    num_del += 1
    except Exception as ex:
        print("Error removing old log files: " + str(ex))
    return num_del

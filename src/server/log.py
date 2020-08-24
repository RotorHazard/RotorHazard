import sys
import os
import glob
import logging.handlers
import platform
import time
import zipfile
import gevent
import gevent.queue
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
LOGZIP_DIR_NAME = "logs/zip"

CONSOLE_FORMAT_STR = "%(message)s"
SYSLOG_FORMAT_STR = "<-RotorHazard-> %(name)s [%(levelname)s] %(message)s"
FILELOG_FORMAT_STR = "%(asctime)s.%(msecs)03d: %(name)s [%(levelname)s] %(message)s"

CONSOLE_LEVEL_STR = "CONSOLE_LEVEL"
SYSLOG_LEVEL_STR = "SYSLOG_LEVEL"
FILELOG_LEVEL_STR = "FILELOG_LEVEL"
FILELOG_NUM_KEEP_STR = "FILELOG_NUM_KEEP"
CONSOLE_STREAM_STR = "CONSOLE_STREAM"
LEVEL_NONE_STR = "NONE"

socket_handler_obj = None

# Log handler that distributes log records to one or more destination handlers via a gevent queue.
class QueuedLogEventHandler(logging.Handler):

    # Creates queued-log-event handler, with given destination log handler.
    def __init__(self, dest_hndlr=None):
        super(QueuedLogEventHandler, self).__init__()
        self.queue_handlers_list = []
        self.log_record_queue = gevent.queue.Queue()
        if dest_hndlr:
            self.queue_handlers_list.append(dest_hndlr)
        gevent.spawn(self.queueWorkerFn)

    # Adds given destination log handler.
    def addHandler(self, dest_hndlr):
        self.queue_handlers_list.append(dest_hndlr)

    def queueWorkerFn(self):
        while True:
            try:
                log_rec = self.log_record_queue.get()  # block until log record put into queue
                for dest_hndlr in self.queue_handlers_list:
                    if log_rec.levelno >= dest_hndlr.level:
                        gevent.sleep(0.001)
                        dest_hndlr.emit(log_rec)
            except Exception as ex:
                print("Error processing log-event queue: " + str(ex))

    def emit(self, log_rec):
        try:
            self.log_record_queue.put(log_rec, timeout=1)
        except Exception as ex:
            print("Error adding record to log-event queue: " + str(ex))


class SocketForwardHandler(logging.Handler):

    def __init__(self, socket, *a, **kw):
        super(SocketForwardHandler, self).__init__(*a, **kw)
        self._socket = socket

    def emit(self, record):
        self._socket.emit("hardware_log", self.format(record))


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
            "socketio.client",
            "engineio.client",
            "sqlalchemy",
            "urllib3",
            "PIL"
            ]:
        logging.getLogger(name).setLevel(logging.WARN)


# Determines numeric log level for configuration item, or generates error
#  message if invalid.
def get_logging_level_for_item(logging_config, cfg_item_name, err_str, def_level=logging.INFO):
    lvl_name = logging_config[cfg_item_name]
    try:
        lvl_num = int(logging.getLevelName(lvl_name))
    except Exception:
        lvl_num = def_level
        if err_str:
            err_str += ", "
        else:
            err_str = ""
        err_str += "Invalid log-level name specified for '{0}': {1}".format(cfg_item_name, lvl_name)
    return (lvl_num, err_str)


# Completes the logging setup.
# Returns the path/filename for the current log file in use, or None.
def later_stage_setup(config, socket):
    global socket_handler_obj

    logging_config = {}
    logging_config[CONSOLE_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[SYSLOG_LEVEL_STR] = LEVEL_NONE_STR
    logging_config[FILELOG_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[FILELOG_NUM_KEEP_STR] = DEF_FILELOG_NUM_KEEP
    logging_config[CONSOLE_STREAM_STR] = DEF_CONSOLE_STREAM.name[1:-1]

    logging_config.update(config)

    root = logging.getLogger()
    # empty out the already configured handler from basicConfig
    root.handlers[:] = []

    handlers = []

    min_level = logging.CRITICAL  # track minimum specified log level

    err_str = None
    (lvl, err_str) = get_logging_level_for_item(logging_config, CONSOLE_LEVEL_STR, err_str)
    if lvl > 0:
        stm_obj = sys.stdout if sys.stderr.name.find(logging_config[CONSOLE_STREAM_STR]) != 1 else sys.stderr
        hdlr_obj = logging.StreamHandler(stream=stm_obj)
        hdlr_obj.setLevel(lvl)
        hdlr_obj.setFormatter(logging.Formatter(CONSOLE_FORMAT_STR))
        handlers.append(hdlr_obj)
        if lvl < min_level:
            min_level = lvl

    (lvl, err_str) = get_logging_level_for_item(logging_config, SYSLOG_LEVEL_STR, err_str, logging.NOTSET)
    if lvl > 0:
        system_logger = logging.handlers.SysLogHandler("/dev/log", level=lvl) \
                        if platform.system() != "Windows" else \
                        logging.handlers.NTEventLogHandler("RotorHazard")
        system_logger.setLevel(lvl)
        system_logger.setFormatter(logging.Formatter(SYSLOG_FORMAT_STR))
        handlers.append(system_logger)
        if lvl < min_level:
            min_level = lvl

    (lvl, err_str) = get_logging_level_for_item(logging_config, FILELOG_LEVEL_STR, err_str)
    if lvl > 0:
        # put log files in subdirectory, and with date-timestamp in names
        (lfname, lfext) = os.path.splitext(LOG_FILENAME_STR)
        (num_old_del, err_str) = delete_old_log_files(logging_config[FILELOG_NUM_KEEP_STR], lfname, lfext, err_str)
        if not os.path.exists(LOG_DIR_NAME):
            os.makedirs(LOG_DIR_NAME)
        # if there's already a logfile with the same date/time name then pause and retry
        num_attempts = 0
        while True:
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_path_name = LOG_DIR_NAME + '/' + lfname + '_' + time_str + lfext
            if not os.path.isfile(log_path_name):
                break
            num_attempts += 1
            if num_attempts > 5:
                break
            time.sleep(1.1)
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

    if err_str:
        err_str = "Logging configuration error: " + err_str
        if hdlr_obj:
            hdlr_obj.stream.write(err_str + "\n")  # write error message to log file
            hdlr_obj.flush()
        raise ValueError(err_str)

    socket_handler_obj = SocketForwardHandler(socket)
    # use same configuration as log file
    if lvl > 0:
        socket_handler_obj.setLevel(lvl)
    # configure log format with milliseconds as ".###" (not ",###")
    socket_handler_obj.setFormatter(logging.Formatter(fmt=FILELOG_FORMAT_STR, datefmt='%Y-%m-%d %H:%M:%S'))

    root.setLevel(min_level)

    queued_handler1 = QueuedLogEventHandler()
    for logHndlr in handlers:
        queued_handler1.addHandler(logHndlr)

    root.addHandler(queued_handler1)

    if num_old_del > 0:
        logging.debug("Deleted {0} old log file(s)".format(num_old_del))

    return log_path_name


def start_socket_forward_handler():
    global socket_handler_obj
    if socket_handler_obj:
        # use separate queue for socket forwarder (in case it has trouble because of network issues)
        queued_handler2 = QueuedLogEventHandler(socket_handler_obj)
        logging.getLogger().addHandler(queued_handler2)
        socket_handler_obj = None


def delete_old_log_files(num_keep_val, lfname, lfext, err_str):
    num_del = 0
    try:
        num_keep_val = int(num_keep_val)  # make sure this is numeric
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
        elif num_keep_val < 0:
            raise ValueError("Negative value")
    except ValueError:
        if err_str:
            err_str += ", "
        else:
            err_str = ""
        err_str += "Value for '{0}' in configuration is invalid: {1}".format(FILELOG_NUM_KEEP_STR, num_keep_val)
    except Exception as ex:
        print("Error removing old log files: " + str(ex))
    return num_del, err_str


def create_log_files_zip(logger, config_file, db_file):
    zip_file_obj = None
    try:
        if os.path.exists(LOG_DIR_NAME):
            if not os.path.exists(LOGZIP_DIR_NAME):
                os.makedirs(LOGZIP_DIR_NAME)
            time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_path_name = LOGZIP_DIR_NAME + "/rh_logs_" + time_str + ".zip"
            logger.info("Creating logs .zip file: {0}".format(zip_path_name))
            gevent.sleep(0.1)  # pause to let log message get written
            zip_file_obj = zipfile.ZipFile(zip_path_name, 'w', zipfile.ZIP_DEFLATED)
            for root, dirs, files in os.walk(LOG_DIR_NAME):  # @UnusedVariable
                if root == LOG_DIR_NAME:  # don't include sub-directories
                    for fname in files:
                        zip_file_obj.write(os.path.join(root, fname))
            # also include configuration and database files
            if config_file and os.path.isfile(config_file):
                zip_file_obj.write(config_file)
            if db_file and os.path.isfile(db_file):
                zip_file_obj.write(db_file)
            zip_file_obj.close()
            return zip_path_name
    except Exception:
        logger.exception("Error creating log-files .zip file")
        if zip_file_obj:
            zip_file_obj.close()
        return None

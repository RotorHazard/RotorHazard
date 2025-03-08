import io
import sys
import os
import glob
import logging
import platform
import subprocess
import time
import zipfile
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
LOGZIP_DIR_NAME = "logs/zip"

CONSOLE_FORMAT_STR = "%(message)s"
SYSLOG_FORMAT_STR = "<-RotorHazard-> %(name)s [%(levelname)s] %(message)s"
FILELOG_FORMAT_STR = "%(asctime)s.%(msecs)03d: [%(levelname)s] %(name)s %(message)s"

CONSOLE_LEVEL_STR = "CONSOLE_LEVEL"
SYSLOG_LEVEL_STR = "SYSLOG_LEVEL"
FILELOG_LEVEL_STR = "FILELOG_LEVEL"
FILELOG_NUM_KEEP_STR = "FILELOG_NUM_KEEP"
CONSOLE_STREAM_STR = "CONSOLE_STREAM"
LEVEL_NONE_STR = "NONE"
LEVEL_NONE_VALUE = 9999

socket_handler_obj = None
queued_handler_obj = None   # for log file
queued_handler2_obj = None  # for socket output
socket_min_log_level = logging.NOTSET  # minimum log level for sockout output (NOTSET = show all)
log_error_alerted_flag = False

# Counters to track number of messages logged for each log level
class LogMsgLevelCounters:
    def __init__(self):
        self.level_counters_dict = {}

    def inc_count(self, lvl_name):
        prev_count = self.level_counters_dict.get(lvl_name, 0)
        self.level_counters_dict[lvl_name] = prev_count + 1

    def get_count(self, lvl_name):
        return self.level_counters_dict.get(lvl_name, 0)

    def get_items(self):
        return self.level_counters_dict.items()

msg_level_counters_obj = LogMsgLevelCounters()

# Log handler that distributes log records to one or more destination handlers via a gevent queue.
class QueuedLogEventHandler(logging.Handler):

    # Creates queued-log-event handler, with given destination log handler.
    def __init__(self, dest_hndlr=None):
        super(QueuedLogEventHandler, self).__init__()
        self.queue_handlers_list = []
        self.log_record_queue = gevent.queue.Queue(maxsize=99)
        if dest_hndlr:
            self.queue_handlers_list.append(dest_hndlr)
        self.log_level_callback_lvl_num = logging.NOTSET
        self.log_level_callback_obj = None
        gevent.spawn(self.queueWorkerFn)

    # Adds given destination log handler.
    def addHandler(self, dest_hndlr):
        self.queue_handlers_list.append(dest_hndlr)

    # Sets callback invoked when message with given log level is logged
    def setLogLevelCallback(self, lvl_num, callback_obj):
        self.log_level_callback_lvl_num = lvl_num
        self.log_level_callback_obj = callback_obj

    def queueWorkerFn(self):
        while True:
            try:
                log_rec = self.log_record_queue.get()  # block until log record put into queue
                msg_level_counters_obj.inc_count(log_rec.levelname)
                for dest_hndlr in self.queue_handlers_list:
                    if log_rec.levelno >= dest_hndlr.level:
                        gevent.sleep(0.001)
                        dest_hndlr.emit(log_rec)
                if self.log_level_callback_lvl_num > logging.NOTSET and \
                                    log_rec.levelno >= self.log_level_callback_lvl_num and \
                                    callable(self.log_level_callback_obj):
                    self.log_level_callback_obj(log_rec)
            except KeyboardInterrupt:
                print("Log-event queue worker thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                raise
            except Exception as ex:
                print("Error processing log-event queue: " + str(ex))
                gevent.sleep(5)

    def emit(self, record):
        try:
            self.log_record_queue.put(record, timeout=1)
        except Exception as ex:
            print("Error adding record to log-event queue: " + str(ex))

    def waitForQueueEmpty(self):
        try:
            count = 0
            while not self.log_record_queue.empty():
                count += 1
                if count > 300:
                    print("Timeout waiting for log queue empty")
                    return
                gevent.sleep(0.01)
            gevent.sleep(0.1)
        except Exception as ex:
            print("Error waiting for log queue empty: " + str(ex))

    def close(self):
        try:
            if self.queue_handlers_list:
                self.waitForQueueEmpty()
                for dest_hndlr in self.queue_handlers_list:
                    dest_hndlr.close()
            self.queue_handlers_list = []
            logging.getLogger().removeHandler(self)
            super(QueuedLogEventHandler, self).close()
        except Exception as ex:
            print("Error closing QueuedLogEventHandler: " + str(ex))

class SocketForwardHandler(logging.Handler):

    def __init__(self, socket, *a, **kw):
        super(SocketForwardHandler, self).__init__(*a, **kw)
        self._socket = socket

    def emit(self, record):
        self._socket.emit("hardware_log", self.format(record))

class StreamToLogger:
    """
    File-like stream object that redirects writes to a logger instance.
    From: https://www.iditect.com/program-example/how-to-redirect-stdout-and-stderr-to-logger-in-python.html
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''  # buffer to accumulate partial lines

    def write(self, buf):
        lvl = self.log_level
        if buf.lstrip().startswith("PYDEV DEBUGGER WARNING"):
            lvl = logging.DEBUG  # don't treat expected debugger warning as error
            buf = buf.lstrip()
        for line in buf.rstrip().splitlines():
            self.logger.log(lvl, line.rstrip())

    def flush(self):
        pass  # ensure compatibility with file-like objects


def early_stage_setup():
    logging.addLevelName(LEVEL_NONE_VALUE, LEVEL_NONE_STR)
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
        "requests",
        "PIL",
        "Adafruit_I2C",
        "Adafruit_I2C.Device.Bus"
    ]:
        logging.getLogger(name).setLevel(logging.WARN)

def get_logging_level_value(lvl_name):
    try:
        return int(logging.getLevelName(lvl_name))
    except Exception:
        return -1

# Determines numeric log level for configuration item, or generates error
#  message if invalid.
def get_logging_level_for_item(logging_config, cfg_item_name, err_str, def_level=logging.INFO):
    lvl_name = logging_config[cfg_item_name]
    lvl_num = get_logging_level_value(lvl_name)
    if lvl_num < 0:
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

#    print(logging.Logger.manager.loggerDict)  # uncomment to display all loggers

    logging_config = {}
    logging_config[CONSOLE_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[SYSLOG_LEVEL_STR] = LEVEL_NONE_STR
    logging_config[FILELOG_LEVEL_STR] = logging.getLevelName(logging.INFO)
    logging_config[FILELOG_NUM_KEEP_STR] = DEF_FILELOG_NUM_KEEP
    logging_config[CONSOLE_STREAM_STR] = str(DEF_CONSOLE_STREAM.name)[1:-1]

    logging_config.update(config)

    root = logging.getLogger()
    # empty out the already configured handler from basicConfig
    root.handlers[:] = []

    handlers = []

    min_level = logging.CRITICAL  # track minimum specified log level

    err_str = None
    (lvl, err_str) = get_logging_level_for_item(logging_config, CONSOLE_LEVEL_STR, err_str)
    if lvl > 0 and lvl < LEVEL_NONE_VALUE:
        stm_obj = sys.stdout if str(sys.stderr.name).find(logging_config[CONSOLE_STREAM_STR]) != 1 else sys.stderr
        hdlr_obj = logging.StreamHandler(stream=stm_obj)
        hdlr_obj.setLevel(lvl)
        hdlr_obj.setFormatter(logging.Formatter(CONSOLE_FORMAT_STR))
        handlers.append(hdlr_obj)
        if lvl < min_level:
            min_level = lvl

    (lvl, err_str) = get_logging_level_for_item(logging_config, SYSLOG_LEVEL_STR, err_str, logging.NOTSET)
    if lvl > 0 and lvl < LEVEL_NONE_VALUE:
        system_logger = logging.handlers.SysLogHandler("/dev/log") \
            if platform.system() != "Windows" else \
            logging.handlers.NTEventLogHandler("RotorHazard")
        system_logger.setLevel(lvl)
        system_logger.setFormatter(logging.Formatter(SYSLOG_FORMAT_STR))
        handlers.append(system_logger)
        if lvl < min_level:
            min_level = lvl

    (lvl, err_str) = get_logging_level_for_item(logging_config, FILELOG_LEVEL_STR, err_str)
    if lvl > 0 and lvl < LEVEL_NONE_VALUE:
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
    if lvl > 0 and lvl < LEVEL_NONE_VALUE:
        socket_handler_obj.setLevel(lvl)
    # configure log format with milliseconds as ".###" (not ",###")
    socket_handler_obj.setFormatter(logging.Formatter(fmt=FILELOG_FORMAT_STR, datefmt='%Y-%m-%d %H:%M:%S'))

    root.setLevel(min_level)

    global queued_handler_obj
    queued_handler_obj = QueuedLogEventHandler()
    for logHndlr in handlers:
        queued_handler_obj.addHandler(logHndlr)

    root.addHandler(queued_handler_obj)

    if num_old_del > 0:
        logging.debug("Deleted {0} old log file(s)".format(num_old_del))

    # redirect stdout and stderr to logger
    con_logger = logging.getLogger("_console_")
    stdout_logger = StreamToLogger(con_logger, logging.INFO)
    stderr_logger = StreamToLogger(con_logger, logging.ERROR)
    sys.stdout = stdout_logger
    sys.stderr = stderr_logger

    return log_path_name

# Sets callback invoked when message with given log level is logged
def set_log_level_callback(lvl_num, callback_obj=None):
    if queued_handler_obj:
        queued_handler_obj.setLogLevelCallback(lvl_num, callback_obj)

# Returns True if an alert indicating that error messages have been logged should be shown
def get_log_error_alert_flag():
    global log_error_alerted_flag
    if log_error_alerted_flag or (not queued_handler_obj):
        return False
    if msg_level_counters_obj.get_count(logging.getLevelName(logging.ERROR)) > 0:
        log_error_alerted_flag = True  # set flag so alert is only shown once
        return True
    return False

# Returns a string showing the number of messages for each log level
def get_log_level_counts_str():
    str_list = []
    for name,count in sorted(msg_level_counters_obj.get_items(), key=get_logging_level_value):
        str_list.append("{}={}".format(name, count))
    str_list.reverse()
    return ", ".join(str_list)

def wait_for_queue_empty():
    if queued_handler_obj:
        queued_handler_obj.waitForQueueEmpty()

def close_logging():
    try:
        global queued_handler_obj
        if queued_handler_obj:
            queued_handler_obj.close()
        queued_handler_obj = None
        root = logging.getLogger()
        if root and root.handlers:
            hdlrsList = list(root.handlers)
            for dest_hndlr in hdlrsList:
                root.removeHandler(dest_hndlr)
                dest_hndlr.close()
        root.handlers[:] = []
        logging._handlerList = []  #pylint: disable=protected-access
    except Exception as ex:
        print("Error closing logging: " + str(ex))

def set_socket_min_log_level(lvl_num):
    global socket_min_log_level
    socket_min_log_level = lvl_num
    if queued_handler2_obj:
        queued_handler2_obj.setLevel(socket_min_log_level)

def start_socket_forward_handler():
    global socket_handler_obj
    global queued_handler2_obj
    if socket_handler_obj:
        # use separate queue for socket forwarder (in case it has trouble because of network issues)
        queued_handler2_obj = QueuedLogEventHandler(socket_handler_obj)
        logging.getLogger().addHandler(queued_handler2_obj)
        socket_handler_obj = None
    if queued_handler2_obj:
        queued_handler2_obj.setLevel(socket_min_log_level)

def emit_current_log_file_to_socket(log_path_name, SOCKET_IO):
    if log_path_name:
        try:
            if socket_min_log_level <= logging.NOTSET:
                with io.open(log_path_name, 'r') as f:
                    SOCKET_IO.emit("hardware_log_init", f.read())
                SOCKET_IO.emit("log_level_sel_init", logging.getLevelName(logging.NOTSET))
            else:
                line_list = []  # filter lines so only log levels >= 'socket_min_log_level' are included
                with io.open(log_path_name, 'r') as f:
                    min_lvl_flag = False
                    pos1 = 0
                    for line_str in f:
                        if len(line_str) > 24:
                            pos1 = line_str.find('[', 24)
                        if pos1 > 0:
                            pos2 = line_str.find(']', pos1) if line_str[0:4].isnumeric() else 0
                            if pos2 > pos1:
                                lvl_num = get_logging_level_value(line_str[pos1+1 : pos2])
                                if lvl_num >= socket_min_log_level:
                                    min_lvl_flag = True
                                    line_list.append(line_str)
                                elif lvl_num >= 0:
                                    min_lvl_flag = False
                                elif min_lvl_flag:
                                    line_list.append(line_str)
                            elif min_lvl_flag:
                                line_list.append(line_str)  # if line does not contain "[log-level]" and
                        elif min_lvl_flag:                  #  previous line did then include this one
                            line_list.append(line_str)      #  (because it's probably a stack trace)
                SOCKET_IO.emit("hardware_log_init", ''.join(line_list))
                SOCKET_IO.emit("log_level_sel_init", logging.getLevelName(socket_min_log_level))
        except Exception:
            logging.getLogger(__name__).exception("Error sending current log file to socket")
    start_socket_forward_handler()


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


def create_log_files_zip(logger, config_file, db_file, program_dir_str, outData=None, boot_config_file="/boot/firmware/config.txt", \
                         alt_boot_config_file="/boot/config.txt"):
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
            for root, dirs, files in os.walk(LOG_DIR_NAME):  #pylint: disable=unused-variable
                if root == LOG_DIR_NAME:  # don't include sub-directories
                    for fname in files:
                        zip_file_obj.write(os.path.join(root, fname))
            service_file = '/lib/systemd/system/rotorhazard.service'
            try:
                # include configuration, database, .bashrc, OS boot-config files, etc
                if config_file and os.path.isfile(config_file):
                    zip_file_obj.write(config_file)
                if db_file and os.path.isfile(db_file):
                    zip_file_obj.write(db_file)
                bashrc_file = os.path.expanduser('~/.bashrc')
                if os.path.isfile(bashrc_file):
                    zip_file_obj.write(bashrc_file, 'bashrc.txt')
                if boot_config_file and os.path.isfile(boot_config_file):
                    zip_file_obj.write(boot_config_file, boot_config_file[1:].replace('/','_'))
                elif alt_boot_config_file and os.path.isfile(alt_boot_config_file):
                    zip_file_obj.write(alt_boot_config_file, alt_boot_config_file[1:].replace('/','_'))
                if os.path.isfile(service_file):
                    zip_file_obj.write(service_file, 'rotorhazard.service.txt')
                server_file = os.path.join(program_dir_str,  'server.py')
                if os.path.isfile(server_file):
                    zip_file_obj.write(server_file, 'server.py')
            except Exception:
                logger.exception("Error adding files to log-files .zip file")
            try:
                # include current audio settings
                if outData:
                    audioSettingsData = outData.get('audioSettingsData')
                    audioSettingsFName = outData.get('audioSettingsFName')
                    if audioSettingsData and audioSettingsFName:
                        zip_file_obj.writestr(audioSettingsFName, audioSettingsData)
            except Exception:
                logger.exception("Error adding audio settings info to .zip file")
            try:
                # include current list of Python libraries
                whichPipStr = subprocess.check_output(['which', 'pip']).decode("utf-8").rstrip()
                if whichPipStr:  # include execution path to 'pip'
                    whichPipStr = "$ " + whichPipStr + " list" + os.linesep
                else:
                    whichPipStr = ""
                # fetch output of "pip list" command (send stderr to null because it always contains warning message)
                fetchedStr = subprocess.check_output(['pip', 'list'], stderr=subprocess.DEVNULL).decode("utf-8").rstrip()
                if not fetchedStr:
                    fetchedStr = ""
                fetchedStr = whichPipStr + "Python version: " + sys.version.split()[0] + \
                             os.linesep + os.linesep + fetchedStr
                zip_file_obj.writestr('pip_libs_list.txt', fetchedStr)
            except Exception:
                logger.exception("Error adding pip-list libraries info to .zip file")
            try:
                # fetch output of "systemctl status rotorhazard.service" command
                if os.path.isfile(service_file):
                    fetchedStr =  subprocess.run(['systemctl', 'status', 'rotorhazard.service'], \
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.\
                                  decode("utf-8").rstrip()
                    if fetchedStr:
                        zip_file_obj.writestr('service_status.txt', fetchedStr)
            except Exception:
                logger.exception("Error adding service-status info to .zip file")
            zip_file_obj.close()
            return zip_path_name
    except Exception:
        logger.exception("Error creating log-files .zip file")
        if zip_file_obj:
            zip_file_obj.close()
        return None

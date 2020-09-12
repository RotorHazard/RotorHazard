# ClusterNodeSet:  Manages a set of slave nodes

import logging
import gevent
import json
import socketio
from monotonic import monotonic
import RHUtils
import Database
from util.RunningMedian import RunningMedian

logger = logging.getLogger(__name__)


class SlaveNode:

    TIMER_MODE = 'timer'
    MIRROR_MODE = 'mirror'
    
    LATENCY_AVG_SIZE = 30
    TIMEDIFF_MEDIAN_SIZE = 30
    TIMEDIFF_CORRECTION_THRESH_MS = 1000  # correct split times if slave clock more off than this

    def __init__(self, idVal, info, RACE, DB, getCurrentProfile, \
                 emit_split_pass_info, monotonic_to_epoch_millis):
        self.id = idVal
        self.info = info
        self.RACE = RACE
        self.DB = DB
        self.getCurrentProfile = getCurrentProfile
        self.emit_split_pass_info = emit_split_pass_info
        self.monotonic_to_epoch_millis = monotonic_to_epoch_millis
        addr = info['address']
        if not '://' in addr:
            addr = 'http://' + addr
        self.address = addr
        self.startConnectTime = 0
        self.lastContactTime = -1
        self.firstContactTime = 0
        self.lastCheckQueryTime = 0
        self.freqsSentFlag = False
        self.numDisconnects = 0
        self.numContacts = 0
        self.minLatencyMs = 0
        self.maxLatencyMs = 0
        self.avgLatencyMs = 0
        self.lastLatencyMs = 0
        self.latencyMsList = []
        self.totalUpTimeSecs = 0
        self.totalDownTimeSecs = 0
        self.timeDiffMedianObj = RunningMedian(self.TIMEDIFF_MEDIAN_SIZE)
        self.timeDiffMedianMs = 0
        self.timeCorrectionMs = 0
        self.sio = socketio.Client()
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('pass_record', self.on_pass_record)
        self.sio.on('check_slave_response', self.on_check_slave_response)
        gevent.spawn(self.slave_worker_thread)

    def slave_worker_thread(self):
        self.startConnectTime = monotonic()
        gevent.sleep(0.1)
        while True:
            try:
                gevent.sleep(1)
                if self.lastContactTime <= 0:
                    secs_since_disconn = monotonic() - self.startConnectTime
                    if secs_since_disconn >= 1.0:  # if disconnect just happened then wait a second before reconnect
                        logger.log((logging.INFO if secs_since_disconn <= self.info['timeout'] else logging.DEBUG), \
                                   "Attempting to connect to slave {0} at {1}...".format(self.id+1, self.address))
                        try:
                            self.sio.connect(self.address)
                        except socketio.exceptions.ConnectionError as ex:
                            err_msg = "Unable to connect to slave {0} at {1}: {2}".format(self.id+1, self.address, ex)
                            if monotonic() <= self.startConnectTime + self.info['timeout']:
                                logger.info(err_msg)
                            else:                      # if beyond timeout period then
                                logger.debug(err_msg)  #  log at debug level and
                                gevent.sleep(29)       #  increase delay between attempts
                else:
                    now_time = monotonic()
                    if not self.freqsSentFlag:
                        try:
                            logger.info("Sending node frequencies to slave {0} at {1}".format(self.id+1, self.address))
                            self.freqsSentFlag = True
                            for idx, freq in enumerate(json.loads(self.getCurrentProfile().frequencies)["f"]):
                                data = { 'node':idx, 'frequency':freq }
                                self.emit('set_frequency', data)
                                gevent.sleep(0.001)
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as ex:
                            logger.error("Error sending node frequencies to slave {0} at {1}: {2}".format(self.id+1, self.address, ex))
                    else:
                        try:
                            if self.lastContactTime > 0 and ((now_time > self.lastContactTime + 10 and \
                                            now_time > self.lastCheckQueryTime + 10) or \
                                            (self.lastCheckQueryTime == 0 and \
                                             now_time > self.lastContactTime + 3)):  # if first query do it sooner
                                self.lastCheckQueryTime = now_time
                                # timestamp not actually used by slave, but send to make query and response symmetrical
                                payload = {
                                    'timestamp': self.monotonic_to_epoch_millis(now_time)
                                }
                                # don't update 'lastContactTime' value until response received
                                self.sio.emit('check_slave_query', payload)
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as ex:
                            logger.error("Error sending check-query to slave {0} at {1}: {2}".format(self.id+1, self.address, ex))
            except KeyboardInterrupt:
                logger.info("SlaveNode worker thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                raise
            except Exception:
                logger.exception('Exception in SlaveNode worker thread')
                gevent.sleep(9)

    def emit(self, event, data = None):
        try:
            if self.lastContactTime > 0:
                self.sio.emit(event, data)
                self.lastContactTime = monotonic()
                self.numContacts += 1
            else:
                logger.warn("Unable to emit to disconnected slave {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))
        except Exception:
            logger.exception("Error emitting to slave {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))

    def on_connect(self):
        if self.lastContactTime <= 0:
            self.lastContactTime = monotonic()
            self.firstContactTime = self.lastContactTime
            if self.numDisconnects <= 0:
                logger.info("Connected to slave {0} at {1}".format(self.id+1, self.address))
            else:
                downSecs = int(round(self.lastContactTime - self.startConnectTime)) if self.startConnectTime > 0 else 0
                logger.info("Reconnected to " + self.get_log_str(downSecs, False));
                self.totalDownTimeSecs += downSecs
            self.emit('join_cluster')
        else:
            self.lastContactTime = monotonic()
            logger.debug("Received extra 'on_connect' event for slave {0} at {1}".format(self.id+1, self.address))

    def on_disconnect(self):
        if self.lastContactTime > 0:
            self.startConnectTime = monotonic()
            self.lastContactTime = -1
            self.numDisconnects += 1
            upSecs = int(round(self.startConnectTime - self.firstContactTime)) if self.firstContactTime > 0 else 0
            logger.warn("Disconnected from " + self.get_log_str(upSecs));
            self.totalUpTimeSecs += upSecs
        else:
            logger.debug("Received extra 'on_disconnect' event for slave {0} at {1}".format(self.id+1, self.address))

    def get_log_str(self, timeSecs=None, upTimeFlag=True):
        if timeSecs is None:
            timeSecs = int(round(monotonic() - self.firstContactTime)) if self.lastContactTime > 0 else 0
        totUpSecs = self.totalUpTimeSecs
        totDownSecs = self.totalDownTimeSecs
        if upTimeFlag:
            totUpSecs += timeSecs
            upDownStr = "upTime"
        else:
            totDownSecs += timeSecs
            upDownStr = "downTime"
        upDownTotal = totUpSecs + totDownSecs
        return "slave {0} at {1} (latency: min={2} avg={3} max={4} last={5} ms, disconns={6}, contacts={7}, " \
               "timeDiff={8}ms, {9}={10}, totalUp={11}, totalDown={12}, avail={13:.1%}))".\
                    format(self.id+1, self.address, self.minLatencyMs, self.avgLatencyMs, \
                           self.maxLatencyMs, self.lastLatencyMs, self.numDisconnects, \
                           self.numContacts, self.timeDiffMedianMs, upDownStr, timeSecs, \
                           totUpSecs, totDownSecs, \
                           float(totUpSecs)/upDownTotal if upDownTotal > 0 else 0)

    def on_pass_record(self, data):
        try:
            self.lastContactTime = monotonic()
            self.numContacts += 1
            node_index = data['node']
            pilot_id = Database.HeatNode.query.filter_by( \
                heat_id=self.RACE.current_heat, node_index=node_index).one_or_none().pilot_id
    
            if pilot_id != Database.PILOT_ID_NONE:
    
                # convert split timestamp (epoch ms sine 1970-01-01) to equivalent local 'monotonic' time value
                split_ts = data['timestamp'] - self.RACE.start_time_epoch_ms
    
                act_laps_list = self.RACE.get_active_laps()[node_index]
                lap_count = max(0, len(act_laps_list) - 1)
                split_id = self.id
    
                # get timestamp for last lap pass (including lap 0)
                if len(act_laps_list) > 0:
                    last_lap_ts = act_laps_list[-1]['lap_time_stamp']
                    last_split_id = self.DB.session.query(self.DB.func.max(Database.LapSplit.split_id)).filter_by(node_index=node_index, lap_id=lap_count).scalar()
                    if last_split_id is None: # first split for this lap
                        if split_id > 0:
                            logger.info('Ignoring missing splits before {0} for node {1}'.format(split_id+1, node_index+1))
                        last_split_ts = last_lap_ts
                    else:
                        if split_id > last_split_id:
                            if split_id > last_split_id + 1:
                                logger.info('Ignoring missing splits between {0} and {1} for node {2}'.format(last_split_id+1, split_id+1, node_index+1))
                            last_split_ts = Database.LapSplit.query.filter_by(node_index=node_index, lap_id=lap_count, split_id=last_split_id).one().split_time_stamp
                        else:
                            logger.info('Ignoring out-of-order split {0} for node {1}'.format(split_id+1, node_index+1))
                            last_split_ts = None
                else:
                    logger.info('Ignoring split {0} before zero lap for node {1}'.format(split_id+1, node_index+1))
                    last_split_ts = None
    
                if last_split_ts is not None:
    
                    # if slave-timer clock was detected as not synchronized then apply correction
                    if self.timeCorrectionMs != 0:
                        split_ts -= self.timeCorrectionMs
                        
                    split_time = split_ts - last_split_ts
                    split_speed = float(self.info['distance'])*1000.0/float(split_time) if 'distance' in self.info else None
                    split_time_str = RHUtils.time_format(split_time)
                    logger.debug('Split pass record: Node {0}, lap {1}, split {2}, time={3}, speed={4}' \
                        .format(node_index+1, lap_count+1, split_id+1, split_time_str, \
                        ('{0:.2f}'.format(split_speed) if split_speed is not None else 'None')))
    
                    self.DB.session.add(Database.LapSplit(node_index=node_index, pilot_id=pilot_id, lap_id=lap_count, \
                            split_id=split_id, split_time_stamp=split_ts, split_time=split_time, \
                            split_time_formatted=split_time_str, split_speed=split_speed))
                    self.DB.session.commit()
                    self.emit_split_pass_info(pilot_id, split_id, split_time)
            else:
                logger.info('Split pass record dismissed: Node: {0}, no pilot on node'.format(node_index+1))
        except Exception:
            logger.exception("Error processing pass record from slave {0} at {1}".\
                             format(self.id+1, self.address))

    def on_check_slave_response(self, data):
        try:
            nowTime = monotonic()
            self.lastContactTime = nowTime
            self.numContacts += 1
            transitTime = nowTime - self.lastCheckQueryTime if self.lastCheckQueryTime > 0 else 0
            if transitTime > 0:
                self.lastLatencyMs = int(round(transitTime * 1000))
                self.latencyMsList.append(self.lastLatencyMs)
                listLen = len(self.latencyMsList)
                if listLen > self.LATENCY_AVG_SIZE:
                    self.latencyMsList.pop(0)
                    listLen -= 1
                self.minLatencyMs = min(self.latencyMsList)
                self.maxLatencyMs = max(self.latencyMsList)
                self.avgLatencyMs = int(round(sum(self.latencyMsList) / listLen))
                if data:
                    slaveTimestamp = data.get('timestamp', 0)
                    if slaveTimestamp:
                        # calculate local-time value midway between before and after network query
                        localTimestamp = self.monotonic_to_epoch_millis(self.lastCheckQueryTime + transitTime/2)
                        # calculate clock-time difference in ms and add to running median
                        self.timeDiffMedianObj.insert(int(round(slaveTimestamp - localTimestamp)))
                        self.timeDiffMedianMs = self.timeDiffMedianObj.median()
                        return
                logger.debug("Received check_slave_response with no timestamp from slave {0} at {1}".\
                             format(self.id+1, self.address))
        except Exception:
            logger.exception("Error processing check-response from slave {0} at {1}".\
                             format(self.id+1, self.address))

class ClusterNodeSet:
    def __init__(self):
        self.slaves = []

    def addSlave(self, slave):
        self.slaves.append(slave)

    def hasSlaves(self):
        return (len(self.slaves))

    def emit(self, event, data = None):
        for slave in self.slaves:
            gevent.spawn(slave.emit, event, data)

    def emitToMirrors(self, event, data = None):
        for slave in self.slaves:
            if slave.info['mode'] == SlaveNode.MIRROR_MODE:
                gevent.spawn(slave.emit, event, data)

    def getClusterStatusInfo(self):
        nowTime = monotonic()
        payload = []
        for slave in self.slaves:
            upTimeSecs = int(round(nowTime - slave.firstContactTime)) if slave.lastContactTime > 0 else 0
            downTimeSecs = int(round(nowTime - slave.startConnectTime)) if slave.lastContactTime <= 0 else 0
            totalUpSecs = slave.totalUpTimeSecs + upTimeSecs
            totalDownSecs = slave.totalDownTimeSecs + downTimeSecs
            payload.append(
                {'address': slave.address, \
                 'minLatencyMs':  slave.minLatencyMs, \
                 'avgLatencyMs': slave.avgLatencyMs, \
                 'maxLatencyMs': slave.maxLatencyMs, \
                 'lastLatencyMs': slave.lastLatencyMs, \
                 'numDisconnects': slave.numDisconnects, \
                 'numContacts': slave.numContacts, \
                 'timeDiffMs': slave.timeDiffMedianMs, \
                 'upTimeSecs': upTimeSecs, \
                 'downTimeSecs': downTimeSecs, \
                 'availability': round((100.0*totalUpSecs/(totalUpSecs+totalDownSecs) \
                                       if totalUpSecs+totalDownSecs > 0 else 0), 1), \
                 'last_contact': int(nowTime-slave.lastContactTime) if slave.lastContactTime >= 0 else 'connection lost'})
        return {'slaves': payload}

    def doClusterRaceStart(self):
        for slave in self.slaves:
            if slave.lastContactTime > 0:
                logger.info("Connected at race start to " + slave.get_log_str());
                if abs(slave.timeDiffMedianMs) > SlaveNode.TIMEDIFF_CORRECTION_THRESH_MS:
                    # (log at warning level if this is new information)
                    logger.log((logging.INFO if slave.timeCorrectionMs != 0 else logging.WARN), \
                               "Slave {0} clock not synchronized with master, timeDiff={1}ms".\
                                 format(slave.id+1, slave.timeDiffMedianMs))
                    slave.timeCorrectionMs = slave.timeDiffMedianMs
                else:
                    slave.timeCorrectionMs = 0
                    if slave.lastContactTime > 0:
                        logger.debug("Slave {0} clock synchronized OK with master, timeDiff={1}ms".\
                                     format(slave.id+1, slave.timeDiffMedianMs))
            elif slave.numDisconnects > 0:
                logger.warn("Slave {0} not connected at race start".format(slave.id+1))

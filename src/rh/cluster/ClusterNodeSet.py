# ClusterNodeSet:  Manages a set of secondary nodes

import logging
import gevent
import json
import socketio
from rh.app.RHRace import RaceStatus
from rh.events.eventmanager import Evt
from rh.util.RunningMedian import RunningMedian
from rh.util import Averager, ms_counter, millis_to_secs

logger = logging.getLogger(__name__)


class SecondaryNode:

    SPLIT_MODE = 'split'
    MIRROR_MODE = 'mirror'

    LATENCY_AVG_SIZE = 30
    TIMEDIFF_MEDIAN_SIZE = 30
    TIMEDIFF_CORRECTION_THRESH_MS = 250  # correct split times if secondary clock more off than this

    def __init__(self, idVal, info, RACE, getCurrentProfile, \
                 split_record_callback, join_cluster_callback,
                 PROGRAM_START, \
                 emit_cluster_connect_change, server_release_version):
        self.id = idVal
        self.info = info
        self.RACE = RACE
        self.getCurrentProfile = getCurrentProfile
        self.split_record_callback = split_record_callback
        self.join_cluster_callback = join_cluster_callback
        self.PROGRAM_START = PROGRAM_START
        self.emit_cluster_connect_change = emit_cluster_connect_change
        self.server_release_version = server_release_version
        self.address = info['address']
        self.node_managers = {}
        self.isMirrorMode = (str(info.get('mode', SecondaryNode.SPLIT_MODE)) == SecondaryNode.MIRROR_MODE)
        self.secondaryModeStr = SecondaryNode.MIRROR_MODE if self.isMirrorMode else SecondaryNode.SPLIT_MODE
        self.recEventsFlag = info.get('recEventsFlag', self.isMirrorMode)
        self.queryInterval = 1000*info['queryInterval'] if 'queryInterval' in info else 0
        if self.queryInterval_ms <= 0:
            self.queryInterval_ms = 10000
        self.firstQueryInterval_ms = 3000 if self.queryInterval_ms >= 3000 else 1000
        self.startConnectTime_ms = 0
        self.lastContactTime_ms = -1
        self.firstContactTime_ms = 0
        self.lastCheckQueryTime_ms = 0
        self.msSinceDisconnect = 0
        self.freqsSentFlag = False
        self.numDisconnects = 0
        self.numDisconnsDuringRace = 0
        self.numContacts = 0
        self.latencyAveragerObj = Averager(self.LATENCY_AVG_SIZE)
        self.totalUpTimeSecs = 0
        self.totalDownTimeSecs = 0
        self.timeDiffMedianObj = RunningMedian(self.TIMEDIFF_MEDIAN_SIZE)
        self.timeDiffMedianMs = 0
        self.timeCorrectionMs = 0
        self.progStartEpoch = 0
        self.runningFlag = True
        self.sio = socketio.Client(reconnection=False, request_timeout=1)
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('pass_record', self.on_pass_record)
        self.sio.on('check_secondary_response', self.on_check_secondary_response)
        self.sio.on('join_cluster_response', self.join_cluster_response)
        gevent.spawn(self.secondary_worker_thread)

    def secondary_worker_thread(self):
        self.startConnectTime_ms = ms_counter()
        gevent.sleep(0.1)
        while self.runningFlag:
            try:
                gevent.sleep(1)
                if self.lastContactTime_ms <= 0:  # if current status is not connected
                    oldMsSinceDis = self.msSinceDisconnect
                    self.msSinceDisconnect = ms_counter() - self.startConnectTime_ms
                    if self.msSinceDisconnect >= 1.0:  # if disconnect just happened then wait a second before reconnect
                        # if never connected then only retry if race not in progress
                        if self.numDisconnects > 0 or (self.RACE.race_status != RaceStatus.STAGING and \
                                                        self.RACE.race_status != RaceStatus.RACING):
                            # if first-ever attempt or was previously connected then show log msg
                            if oldMsSinceDis == 0 or self.numDisconnects > 0:
                                logger.log((logging.INFO if self.msSinceDisconnect <= self.info['timeout'] else logging.DEBUG), \
                                           "Attempting to connect to secondary {0} at {1}...".format(self.id+1, self.address))
                            try:
                                self.sio.connect(self.address)
                            except socketio.exceptions.ConnectionError as ex:
                                if self.lastContactTime_ms > 0:  # if current status is connected
                                    logger.info("Error connecting to secondary {0} at {1}: {2}".format(self.id+1, self.address, ex))
                                    if not self.sio.connected:  # if not connected then
                                        self.on_disconnect()    # invoke disconnect function to update status
                                else:
                                    err_msg = "Unable to connect to secondary {0} at {1}: {2}".format(self.id+1, self.address, ex)
                                    if ms_counter() <= self.startConnectTime_ms + self.info['timeout']:
                                        if self.numDisconnects > 0:  # if previously connected then always log failure
                                            logger.info(err_msg)
                                        elif oldMsSinceDis == 0:   # if not previously connected then only log once
                                            err_msg += " (will continue attempts until timeout)"
                                            logger.info(err_msg)
                                    else:  # if beyond timeout period
                                        if self.numDisconnects > 0:  # if was previously connected then keep trying
                                            logger.debug(err_msg)    #  log at debug level and
                                            gevent.sleep(29)         #  increase delay between attempts
                                        else:
                                            logger.warning(err_msg)     # if never connected then give up
                                            logger.warning("Reached timeout; no longer trying to connect to secondary {0} at {1}".\
                                                        format(self.id+1, self.address))
                                            if self.runningFlag and self.emit_cluster_connect_change:
                                                self.emit_cluster_connect_change(False)  # play one disconnect tone
                                            return  # exit worker thread
                else:  # if current status is connected
                    now_ms = ms_counter()
                    if not self.freqsSentFlag:
                        try:
                            self.freqsSentFlag = True
                            if (not self.isMirrorMode) and self.getCurrentProfile:
                                logger.info("Sending node frequencies to secondary {0} at {1}".format(self.id+1, self.address))
                                for idx, freq in enumerate(json.loads(self.getCurrentProfile().frequencies)["f"]):
                                    data = { 'node':idx, 'frequency':freq }
                                    self.emit('set_frequency', data)
                                    gevent.sleep(0.001)
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as ex:
                            logger.error("Error sending node frequencies to secondary {0} at {1}: {2}".format(self.id+1, self.address, ex))
                    else:
                        try:
                            if self.sio.connected:
                                # send heartbeat-query every 'queryInterval' seconds, or that long since last contact
                                if (now_ms > self.lastContactTime_ms + self.queryInterval_ms and \
                                            now_ms > self.lastCheckQueryTime_ms + self.queryInterval_ms) or \
                                            (self.lastCheckQueryTime_ms == 0 and \
                                             now_ms > self.lastContactTime_ms + self.firstQueryInterval_ms):  # if first query do it sooner
                                    self.lastCheckQueryTime_ms = now_ms
                                    # timestamp not actually used by secondary, but send to make query and response symmetrical
                                    payload = {
                                        'timestamp': self.PROGRAM_START.monotonic_to_epoch_millis(now_ms) \
                                                         if self.PROGRAM_START else 0
                                    }
                                    # don't update 'lastContactTime' value until response received
                                    self.sio.emit('check_secondary_query', payload)
                                # if there was no response to last query then disconnect (and reconnect next loop)
                                elif self.lastCheckQueryTime_ms > self.lastContactTime_ms:
                                    if self.lastCheckQueryTime_ms - self.lastContactTime_ms > 3900:
                                        if len(self.timeDiffMedianObj.sorted_) > 0:
                                            logger.warning("Disconnecting after no response for 'check_secondary_query'" \
                                                     " received for secondary {0} at {1}".format(self.id+1, self.address))
                                            # calling 'disconnect()' will usually invoke 'on_disconnect()', but
                                            #  'disconnect()' can be slow to return, so force-update status if needed
                                            gevent.spawn(self.do_sio_disconnect)
                                            if self.wait_for_sio_disconnect(1.0):
                                                logger.info("Forcing 'disconnected' status for stuck connection on" \
                                                            " secondary {0} at {1}".format(self.id+1, self.address))
                                                self.on_disconnect()
                                        else:  # if never any responses then may be old server version on secondary timer
                                            logger.warning("No response for 'check_secondary_query'" \
                                                           " received for secondary {0} at {1} (may need upgrade)".\
                                                           format(self.id+1, self.address))
                                            self.lastCheckQueryTime_ms = self.lastContactTime_ms = now_ms
                                    else:
                                        logger.debug("No response for 'check_secondary_query' received "\
                                                     "after {0:.1f} secs for secondary {1} at {2}".\
                                                     format(self.lastCheckQueryTime_ms - self.lastContactTime_ms, \
                                                            self.id+1, self.address))
                            else:
                                logger.info("Invoking 'on_disconnect()' fn for secondary {0} at {1}".\
                                            format(self.id+1, self.address))
                                self.on_disconnect()
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as ex:
                            logger.error("Error sending check-query to secondary {0} at {1}: {2}".format(self.id+1, self.address, ex))
            except KeyboardInterrupt:
                logger.info("SecondaryNode worker thread terminated by keyboard interrupt")
                raise
            except SystemExit:
                raise
            except Exception as ex:
                if type(ex) is ValueError and "connected" in str(ex):  # if error was because already connected
                    if self.lastContactTime_ms <= 0:  # if current tracked status is not connected
                        logger.debug("Ignoring connect error from sio-already-connected on secondary {0}".\
                                     format(self.id+1))
                    else:
                        logger.info("Forcing 'disconnected' status after sio-already-connected error on" \
                                    " secondary {0}".format(self.id+1))
                        self.on_disconnect()
                else:
                    logger.exception("Exception in SecondaryNode worker thread for secondary {} (sio.conn={})".\
                                     format(self.id+1, self.sio.connected))
                    gevent.sleep(9)

    def emit(self, event, data = None):
        try:
            if self.lastContactTime_ms > 0:
                self.sio.emit(event, data)
                self.lastContactTime_ms = ms_counter()
                self.numContacts += 1
            elif self.numDisconnects > 0:  # only warn if previously connected
                logger.warning("Unable to emit to disconnected secondary {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))
        except Exception:
            logger.exception("Error emitting to secondary {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))
            if self.sio.connected:
                logger.warning("Disconnecting after error emitting to secondary {0} at {1}".\
                            format(self.id+1, self.address))
                self.sio.disconnect()

    def on_connect(self):
        try:
            if self.lastContactTime_ms <= 0:
                self.lastContactTime_ms = ms_counter()
                self.firstContactTime_ms = self.lastContactTime_ms
                if self.numDisconnects <= 0:
                    logger.info("Connected to secondary {0} at {1} (mode: {2})".format(\
                                        self.id+1, self.address, self.secondaryModeStr))
                else:
                    downSecs = round(millis_to_secs(self.lastContactTime_ms - self.startConnectTime_ms)) if self.startConnectTime_ms > 0 else 0
                    logger.info("Reconnected to " + self.get_log_str(downSecs, False))
                    self.totalDownTimeSecs += downSecs
                payload = {
                    'mode': self.secondaryModeStr
                }
                self.emit('join_cluster_ex', payload)
                if (not self.isMirrorMode) and \
                        (self.RACE.race_status == RaceStatus.STAGING or self.RACE.race_status == RaceStatus.RACING):
                    self.emit('stage_race')  # if race in progress then make sure running on secondary
                if self.runningFlag and self.emit_cluster_connect_change:
                    self.emit_cluster_connect_change(True)
            else:
                self.lastContactTime_ms = ms_counter()
                logger.debug("Received extra 'on_connect' event for secondary {0} at {1}".format(self.id+1, self.address))
        except Exception:
            logger.exception("Error handling Cluster 'on_connect' for secondary {0} at {1}".\
                             format(self.id+1, self.address))

    def on_disconnect(self):
        try:
            if self.lastContactTime_ms > 0:
                self.startConnectTime_ms = ms_counter()
                self.lastContactTime_ms = -1
                self.numDisconnects += 1
                self.numDisconnsDuringRace += 1
                upSecs = round(millis_to_secs(self.startConnectTime_ms - self.firstContactTime_ms)) if self.firstContactTime_ms > 0 else 0
                logger.warning("Disconnected from " + self.get_log_str(upSecs))
                self.totalUpTimeSecs += upSecs
                if self.runningFlag and self.emit_cluster_connect_change:
                    self.emit_cluster_connect_change(False)
            else:
                logger.debug("Received extra 'on_disconnect' event for secondary {0} at {1}".format(self.id+1, self.address))
        except Exception:
            logger.exception("Error handling Cluster 'on_disconnect' for secondary {0} at {1}".\
                             format(self.id+1, self.address))

    def do_sio_disconnect(self):
        try:
            if self.sio.connected:
                self.sio.disconnect()
                logger.debug("Returned from 'sio.disconnect()' call for secondary {0} at {1}".\
                             format(self.id+1, self.address))
        except Exception:
            logger.exception("Error calling 'sio.disconnect()' for secondary {0} at {1}".\
                             format(self.id+1, self.address))

    def wait_for_sio_disconnect(self, maxWaitSecs):
        dly = maxWaitSecs / 10
        cnt = 10 if dly > 0 else 0
        while True:
            if not self.sio.connected:
                return False
            if cnt <= 0:
                return True
            cnt -= 1
            gevent.sleep(dly)

    def get_log_str(self, timeSecs=None, upTimeFlag=True, stoppedRaceFlag=False):
        if timeSecs is None:
            timeSecs = round(millis_to_secs(ms_counter() - self.firstContactTime_ms)) if self.lastContactTime_ms > 0 else 0
        totUpSecs = self.totalUpTimeSecs
        totDownSecs = self.totalDownTimeSecs
        if upTimeFlag:
            totUpSecs += timeSecs
            upDownStr = "upTime"
        else:
            totDownSecs += timeSecs
            upDownStr = "downTime"
        upDownTotal = totUpSecs + totDownSecs
        return "secondary {0} at {1} (latency: min={2} avg={3} max={4} last={5} ms, disconns={6}, contacts={7}, " \
               "timeDiff={8}ms, {9}={10}, totalUp={11}, totalDown={12}, avail={13:.1%}{14})".\
                    format(self.id+1, self.address, self.latencyAveragerObj.min, \
                           int(round(self.latencyAveragerObj.mean)), self.latencyAveragerObj.max, \
                           self.latencyAveragerObj.last, self.numDisconnects, self.numContacts, \
                           self.timeDiffMedianMs, upDownStr, timeSecs, totUpSecs, totDownSecs, \
                           (float(totUpSecs)/upDownTotal if upDownTotal > 0 else 0),
                           ((", numDisconnsDuringRace=" + str(self.numDisconnsDuringRace)) if \
                                    (self.numDisconnsDuringRace > 0 and \
                                     (stoppedRaceFlag or self.RACE.race_status == RaceStatus.RACING)) else ""))

    def _lookup_node(self, node_index):
        for nm, ns in self.node_managers.items():
            for n, n_idx in ns.items():
                if n_idx == node_index:
                    return nm, n
        return None

    def on_pass_record(self, data):
        try:
            self.lastContactTime_ms = ms_counter()
            self.numContacts += 1
            # if secondary-timer clock was detected as not synchronized then apply correction
            if self.timeCorrectionMs != 0:
                data['timestamp'] -= self.timeCorrectionMs

            node_index = data['node']
            ts = data['timestamp']
            nm, n = self._lookup_node(node_index)
            # convert split timestamp (epoch ms sine 1970-01-01) to equivalent local 'monotonic' time value
            split_ts = ts - self.RACE.start_time_epoch_ms
            self.split_record_callback(self.address, nm, n, split_ts)
        except Exception:
            logger.exception("Error processing pass record from secondary {0} at {1}".format(self.id+1, self.address))

        try:
            # send message-ack back to secondary (but don't update 'lastContactTime' value)
            payload = {
                'messageType': 'pass_record',
                'messagePayload': data
            }
            self.sio.emit('cluster_message_ack', payload)
        except Exception:
            logger.exception("Error sending pass-record message acknowledgement to secondary {0} at {1}".\
                             format(self.id+1, self.address))

    def on_check_secondary_response(self, data):
        try:
            if self.lastContactTime_ms > 0:
                now_ms = ms_counter()
                self.lastContactTime_ms = now_ms
                self.numContacts += 1
                transitTime = now_ms - self.lastCheckQueryTime_ms if self.lastCheckQueryTime_ms > 0 else 0
                if transitTime > 0:
                    self.latencyAveragerObj.append(transitTime)
                    if data:
                        secondaryTimestamp = data.get('timestamp', 0)
                        if secondaryTimestamp:
                            # calculate local-time value midway between before and after network query
                            localTimestamp = self.PROGRAM_START.monotonic_to_epoch_millis(\
                                             (self.lastCheckQueryTime_ms + transitTime/2)) \
                                             if self.PROGRAM_START else 0
                            # calculate clock-time difference in ms and add to running median
                            self.timeDiffMedianObj.insert(int(round(secondaryTimestamp - localTimestamp)))
                            self.timeDiffMedianMs = self.timeDiffMedianObj.median()
                            return
                    logger.debug("Received check_secondary_response with no timestamp from secondary {0} at {1}".\
                                 format(self.id+1, self.address))
            else:
                logger.debug("Received check_secondary_response while disconnected from secondary {0} at {1}".\
                             format(self.id+1, self.address))
        except Exception:
            logger.exception("Error processing check-response from secondary {0} at {1}".\
                             format(self.id+1, self.address))

    def join_cluster_response(self, data):
        self.node_managers = data['node_managers']
        self.join_cluster_callback(self.address, self.node_managers)
        try:
            infoStr = data.get('server_info')
            logger.debug("Server info from secondary {0} at {1}:  {2}".\
                         format(self.id+1, self.address, infoStr))
            infoDict = json.loads(infoStr)
            prgStrtEpchStr = infoDict.get('prog_start_epoch')
            newPrgStrtEpch = False
            try:
                prgStrtEpch = int(float(prgStrtEpchStr))
                if self.progStartEpoch == 0:
                    self.progStartEpoch = prgStrtEpch
                    newPrgStrtEpch = True
                    logger.debug("Initial 'prog_start_epoch' value for secondary {0}: {1}".\
                                format(self.id+1, prgStrtEpch))
                elif prgStrtEpch != self.progStartEpoch:
                    self.progStartEpoch = prgStrtEpch
                    newPrgStrtEpch = True
                    logger.info("New 'prog_start_epoch' value for secondary {0}: {1}; resetting 'timeDiff' median".\
                                format(self.id+1, prgStrtEpch))
                    self.timeDiffMedianObj = RunningMedian(self.TIMEDIFF_MEDIAN_SIZE)
            except ValueError as ex:
                logger.warning("Error parsing 'prog_start_epoch' value from secondary {0}: {1}".\
                            format(self.id+1, ex))
            # if first time connecting (or possible secondary restart) then check/warn about program version
            if newPrgStrtEpch or self.numDisconnects == 0:
                secondaryVerStr = infoDict.get('release_version')
                if secondaryVerStr:
                    if secondaryVerStr != self.server_release_version:
                        logger.warning("Different program version ('{0}') running on secondary {1} at {2}".\
                                    format(secondaryVerStr, self.id+1, self.address))
                else:
                    logger.warning("Unable to parse 'release_version' from secondary {0} at {1}".\
                                format(self.id+1, self.address))
        except Exception:
            logger.exception("Error processing join-cluster response from secondary {0} at {1}".\
                             format(self.id+1, self.address))
        try:
            # send message-ack back to secondary (but don't update 'lastContactTime' value)
            #  this tells secondary timer to expect future message-acks in response to 'pass_record' emits
            payload = { 'messageType': 'join_cluster_response' }
            self.sio.emit('cluster_message_ack', payload)
        except Exception:
            logger.exception("Error sending join-cluster message acknowledgement to secondary {0} at {1}".\
                             format(self.id+1, self.address))


class ClusterNodeSet:
    def __init__(self, Language, eventmanager):
        self._Language = Language
        self.secondaries = []
        self.splitSecondaries = []
        self.recEventsSecondaries = []
        self.Events = eventmanager

    def init_repeater(self):
        self.Events.on(Evt.ALL, 'cluster', self.event_repeater, priority=75, unique=True)

    def event_repeater(self, args):
        try:
            # if there are cluster timers interested in events then emit it out to them
            if self.hasRecEventsSecondaries():
                payload = { 'evt_name': args['_eventName'] }
                del args['_eventName']
                payload['evt_args'] = json.dumps(args, default=lambda x: '<not serializiable>')
                self.emitEventTrigger(payload)
        except Exception as ex:
            logger.exception("Exception in 'Events.trigger()': " + ex)

    def shutdown(self):
        for secondary in self.secondaries:
            secondary.runningFlag = False

    def addSecondary(self, secondary):
        self.secondaries.append(secondary)
        if not secondary.isMirrorMode:
            self.splitSecondaries.append(secondary)
        if secondary.recEventsFlag:
            self.recEventsSecondaries.append(secondary)

    def hasSecondaries(self):
        return (len(self.secondaries) > 0)

    def hasRecEventsSecondaries(self):
        return (len(self.recEventsSecondaries) > 0)

    # return True if secondary is 'split' mode and is or has been connected
    def isSplitSecondaryAvailable(self, secondary_index):
        return (secondary_index < len(self.secondaries)) and \
               (not self.secondaries[secondary_index].isMirrorMode) and \
                    (self.secondaries[secondary_index].lastContactTime_ms > 0 or \
                     self.secondaries[secondary_index].numDisconnects > 0)

    def emit(self, event, data = None):
        for secondary in self.secondaries:
            gevent.spawn(secondary.emit, event, data)

    def emitToSplits(self, event, data = None):
        for secondary in self.splitSecondaries:
            gevent.spawn(secondary.emit, event, data)

    def emitEventTrigger(self, data = None):
        for secondary in self.recEventsSecondaries:
            gevent.spawn(secondary.emit, 'cluster_event_trigger', data)

    def getClusterStatusInfo(self):
        now_ms = ms_counter()
        payload = []
        for secondary in self.secondaries:
            upTimeSecs = round(millis_to_secs(now_ms - secondary.firstContactTime_ms)) if secondary.lastContactTime_ms > 0 else 0
            downTimeSecs = int(round(secondary.msSinceDisconnect)) if secondary.lastContactTime_ms <= 0 else 0
            totalUpSecs = secondary.totalUpTimeSecs + upTimeSecs
            totalDownSecs = secondary.totalDownTimeSecs + downTimeSecs
            payload.append(
                {'address': secondary.address, \
                 'modeIndicator': ('M' if secondary.isMirrorMode else 'S'), \
                 'minLatencyMs':  secondary.latencyAveragerObj.min, \
                 'avgLatencyMs': int(round(self.latencyAveragerObj.mean)), \
                 'maxLatencyMs': secondary.latencyAveragerObj.max, \
                 'lastLatencyMs': secondary.latencyAveragerObj.last, \
                 'numDisconnects': secondary.numDisconnects, \
                 'numContacts': secondary.numContacts, \
                 'timeDiffMs': secondary.timeDiffMedianMs, \
                 'upTimeSecs': upTimeSecs, \
                 'downTimeSecs': downTimeSecs, \
                 'availability': round((100.0*totalUpSecs/(totalUpSecs+totalDownSecs) \
                                       if totalUpSecs+totalDownSecs > 0 else 0), 1), \
                 'last_contact': int(now_ms-secondary.lastContactTime_ms) if secondary.lastContactTime_ms >= 0 else \
                                 (self.__("connection lost") if secondary.numDisconnects > 0 else self.__("never connected"))
                 })
        return {'secondaries': payload}

    def doClusterRaceStart(self):
        for secondary in self.secondaries:
            secondary.numDisconnsDuringRace = 0
            if secondary.lastContactTime_ms > 0:
                logger.info("Connected at race start to " + secondary.get_log_str())
                if abs(secondary.timeDiffMedianMs) > SecondaryNode.TIMEDIFF_CORRECTION_THRESH_MS:
                    secondary.timeCorrectionMs = secondary.timeDiffMedianMs
                    logger.info("Secondary {0} clock not synchronized with primary, timeDiff={1}ms".\
                                format(secondary.id+1, secondary.timeDiffMedianMs))
                else:
                    secondary.timeCorrectionMs = 0
                    logger.debug("Secondary {0} clock synchronized OK with primary, timeDiff={1}ms".\
                                 format(secondary.id+1, secondary.timeDiffMedianMs))
            elif secondary.numDisconnects > 0:
                logger.warning("Secondary {0} not connected at race start".format(secondary.id+1))

    def doClusterRaceStop(self):
        for secondary in self.secondaries:
            if secondary.lastContactTime_ms > 0:
                logger.info("Connected at race stop to " + secondary.get_log_str(stoppedRaceFlag=True))
            elif secondary.numDisconnects > 0:
                logger.warning("Not connected at race stop to " + secondary.get_log_str(stoppedRaceFlag=True))

    def __(self, *args, **kwargs):
        return self._Language.__(*args, **kwargs)

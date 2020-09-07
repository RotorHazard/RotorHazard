# ClusterNodeSet:  Manages a set of slave nodes

import logging
import gevent
import json
import socketio
from monotonic import monotonic
import RHUtils
import RHRace
import Database

logger = logging.getLogger(__name__)


class SlaveNode:

    TIMER_MODE = 'timer'
    MIRROR_MODE = 'mirror'

    def __init__(self, idVal, info, RACE, DB, getCurrentProfile, emit_split_pass_info):
        self.id = idVal
        self.info = info
        self.RACE = RACE
        self.DB = DB
        self.getCurrentProfile = getCurrentProfile
        self.emit_split_pass_info = emit_split_pass_info
        addr = info['address']
        if not '://' in addr:
            addr = 'http://' + addr
        self.address = addr
        self.startConnectTime = 0
        self.lastContactTime = -1
        self.lastCheckQueryTime = 0
        self.freqsSentFlag = False
        self.raceStartEpoch = 0
        self.clockWarningFlag = False
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
                            if self.lastContactTime > 0 and now_time > self.lastContactTime + 10 and \
                                            now_time > self.lastCheckQueryTime + 10:
                                self.lastCheckQueryTime = now_time
                                self.sio.emit('check_slave_query')  # don't update 'lastContactTime' value until response received
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
            else:
                logger.warn("Unable to emit to disconnected slave {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))
        except Exception:
            logger.exception("Error emitting to slave {0} at {1}, event='{2}'".\
                            format(self.id+1, self.address, event))

    def on_connect(self):
        self.lastContactTime = monotonic()
        logger.info("Connected to slave {0} at {1}".format(self.id+1, self.address))
        self.emit('join_cluster')

    def on_disconnect(self):
        self.lastContactTime = -1
        self.startConnectTime = monotonic()
        logger.warn("Disconnected from slave {0} at {1}".format(self.id+1, self.address))

    def on_pass_record(self, data):
        try:
            self.lastContactTime = monotonic()
            node_index = data['node']
            pilot_id = Database.HeatNode.query.filter_by( \
                heat_id=self.RACE.current_heat, node_index=node_index).one_or_none().pilot_id
    
            if pilot_id != Database.PILOT_ID_NONE:
    
                # convert split timestamp (epoch ms sine 1970-01-01) to equivalent local 'monotonic' time value
                split_ts = data['timestamp'] - self.RACE.start_time_epoch_ms
    
                act_laps_list = self.RACE.get_active_laps()[node_index]
                lap_count = max(0, len(act_laps_list) - 1)
    
                # get timestamp for last lap pass (including lap 0)
                if len(act_laps_list) > 0:
                    last_lap_ts = act_laps_list[-1]['lap_time_stamp']
                    split_id = self.id
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
    
                    # get race-start time value from slave (or previously received and saved value)
                    slv_rs_epoch = data.get('race_start_epoch', 0) or self.raceStartEpoch
                    if slv_rs_epoch > 0:
                        self.raceStartEpoch = slv_rs_epoch  # save race-start time for future laps
                        # compare the local race-start epoch time to the slave's
                        # (account for master-server's prestage race-delay time)
                        rs_epoch_diff = self.RACE.start_time_epoch_ms - slv_rs_epoch - \
                                        int((self.RACE.start_time_delay_secs-RHRace.RACE_START_DELAY_EXTRA_SECS) * 1000)
                        # if slave timer's clock is too far off then correct as best we can
                        #  using estimated difference in race-start epoch times
                        if abs(rs_epoch_diff) > 1000:
                            split_ts += rs_epoch_diff
                            if not self.clockWarningFlag:
                                logger.warn("Slave {0} clock not synchronized with master, offset={1:.1f}ms, split={2}".\
                                            format(self.id+1, (-rs_epoch_diff), split_id+1))
                                self.clockWarningFlag = True
                            logger.debug("Correcting slave-time offset ({0:.1f}ms) on node {1}, new split_ts={2:.1f}, split={3}".\
                                         format((-rs_epoch_diff), node_index+1, split_ts, split_id+1))
                        else:
                            logger.debug("Slave {0} clock synchronized OK with master, offset={1:.1f}ms, split={2}".\
                                         format(self.id+1, (-rs_epoch_diff), split_id+1))
    
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
        self.lastContactTime = monotonic()


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
        now_time = monotonic()
        return {'slaves': [ \
            {'address': slave.address, \
            'last_contact': int(now_time-slave.lastContactTime) if slave.lastContactTime >= 0 else 'connection lost' \
            }] for slave in self.slaves}

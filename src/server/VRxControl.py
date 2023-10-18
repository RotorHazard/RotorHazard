#
# VRx Control
#

import logging
from RHUtils import catchLogExceptionsWrapper
from monotonic import monotonic
from eventmanager import Evt

DEVICE_TIMEOUT = 30 # Consider devices if no response received within X seconds
logger = logging.getLogger(__name__)

class VRxControlManager():
    def __init__(self, Events, RaceContext, rhapi, **_kwargs):
        self._racecontext = RaceContext
        self._rhapi = rhapi
        self.Events = Events

        self.enabled = None
        self.controllers = {} # collection of VRxControllers

        self.Events.trigger(Evt.VRX_INITIALIZE, {
            'register_fn': self.registerController
            })

        if len(self.controllers):
            logger.info('VRx Control enabled')
            self.enabled = True
            self.Events.on(Evt.STARTUP, 'VRx', self.doStartup)
            self.Events.on(Evt.HEAT_SET, 'VRx', self.doHeatSet)
            self.Events.on(Evt.RACE_STAGE, 'VRx', self.doRaceStage, {}, 75)
            self.Events.on(Evt.RACE_START, 'VRx', self.doRaceStart, {}, 75)
            self.Events.on(Evt.RACE_FINISH, 'VRx', self.doRaceFinish)
            self.Events.on(Evt.RACE_STOP, 'VRx', self.doRaceStop)
            self.Events.on(Evt.RACE_LAP_RECORDED, 'VRx', self.doRaceLapRecorded, {}, 200, True)
            self.Events.on(Evt.RACE_PILOT_DONE, 'VRx', self.doRacePilotDone, {}, 200, True)
            self.Events.on(Evt.LAPS_CLEAR, 'VRx', self.doLapsClear)
            self.Events.on(Evt.LAP_DELETE, 'VRx', self.doLapDelete)
            self.Events.on(Evt.FREQUENCY_SET, 'VRx', self.doFrequencySet, {}, 200, True)
            self.Events.on(Evt.MESSAGE_INTERRUPT, 'VRx', self.doSendPriorityMessage)
            self.Events.on(Evt.OPTION_SET, 'VRx', self.doOptionSet)
            self.Events.on(Evt.SHUTDOWN, 'VRx', self.doShutdown)
        else:
            logger.info('VRx Control disabled: no registered controllers')
            self.enabled = False

    def registerController(self, controller):
        if hasattr(controller, 'name'):
            if controller.name in self.controllers:
                logger.warning('Overwriting VRx Controller "{0}"'.format(controller.name))

            controller.manager = self
            controller.racecontext = self._racecontext
            controller.rhapi = self._rhapi
            controller.Events = self.Events

            self.controllers[controller.name] = controller
            logger.info('Importing VRx Controller {}'.format(controller.name))
        else:
            logger.warning('Invalid controller')

    def isEnabled(self):
        if not self.enabled:
            return False 

        for controller in self.controllers.values(): # TODO: should this check be done?
            if controller.ready:
                return True

        return False

    def kill(self, *args):
        if self.enabled:
            logger.info('Killing active VRx Control')
            self.enabled = False
    
            self.Events.off(Evt.STARTUP, 'VRx')
            self.Events.off(Evt.HEAT_SET, 'VRx')
            self.Events.off(Evt.RACE_STAGE, 'VRx')
            self.Events.off(Evt.RACE_START, 'VRx')
            self.Events.off(Evt.RACE_FINISH, 'VRx')
            self.Events.off(Evt.RACE_STOP, 'VRx')
            self.Events.off(Evt.RACE_LAP_RECORDED, 'VRx')
            self.Events.off(Evt.LAPS_CLEAR, 'VRx')
            self.Events.off(Evt.LAP_DELETE, 'VRx')
            self.Events.off(Evt.FREQUENCY_SET, 'VRx')
            self.Events.off(Evt.MESSAGE_INTERRUPT, 'VRx')
            self.Events.off(Evt.OPTION_SET, 'VRx')
            self.Events.off(Evt.SHUTDOWN, 'VRx')
        else:
            logger.info('VRx Control already disabled')

        return True

    def updateStatus(self):
        for controller in self.controllers.values():
            controller.updateStatus()

    def getControllerStatus(self):
        status = {}
        for controller in self.controllers.values():
            status[controller.name] = controller.getStatus()
        return status

    def getAllDeviceStatus(self):
        devices = {}
        for controller in self.controllers.values():
            status = controller.getAllDeviceStatus()
            for device in status:
                manager_device_id = str(controller.name) + ":" + str(device['id'])
                devices[manager_device_id] = device

        return devices

    def getDevices(self):
        devices = {}
        for controller in self.controllers.values():
            for device in controller.devices:
                manager_device_id = str(controller.name) + ":" + str(device.id)
                devices[manager_device_id] = device

        return devices

    def getActiveDevices(self, seat, pilot_id):
        devices = {}
        for controller in self.controllers.values():
            for device in controller.devices:
                manager_device_id = str(controller.name) + ":" + str(device.id)
                if device.method == VRxDeviceMethod.ALL:
                    devices[manager_device_id] = device
                elif device.method == VRxDeviceMethod.PILOT and device.pilot_id == pilot_id:
                    devices[manager_device_id] = device
                elif device.method == VRxDeviceMethod.SEAT and device.pilot_id == seat:
                    devices[manager_device_id] = device

        return devices

    def setDeviceMethod(self, device_id, method):
        for controller in self.controllers.values():
            for device in controller.devices:
                manager_device_id = controller.name + ":" + device
                if manager_device_id == device_id:
                    controller.setDeviceMethod(device, method)
                    return True
        return False

    def setDeviceSeat(self, device_id, seat):
        for controller in self.controllers.values():
            for device in controller.devices:
                manager_device_id = controller.name + ":" + device
                if manager_device_id == device_id:
                    controller.setDeviceSeat(device, seat)
                    return True
        return False

    def setDevicePilot(self, device_id, pilot_id):
        for controller in self.controllers.values():
            for device in controller.devices:
                manager_device_id = controller.name + ":" + device
                if manager_device_id == device_id:
                    controller.setDevicePilot(device, pilot_id)
                    return True
        return False

    def doStartup(self, args):
        for controller in self.controllers.values():
            controller.do_startup(args)

    def doHeatSet(self, args):
        for controller in self.controllers.values():
            controller.do_heat_set(args)

    def doRaceStage(self, args):
        for controller in self.controllers.values():
            controller.do_race_stage(args)

    def doRaceStart(self, args):
        for controller in self.controllers.values():
            controller.do_race_start(args)

    def doRaceFinish(self, args):
        for controller in self.controllers.values():
            controller.do_race_finish(args)

    def doRaceStop(self, args):
        for controller in self.controllers.values():
            controller.do_race_stop(args)

    def doRaceLapRecorded(self, args):
        for controller in self.controllers.values():
            controller.do_race_lap_recorded(args)

    def doRacePilotDone(self, args):
        for controller in self.controllers.values():
            controller.do_race_pilot_done(args)

    def doLapsClear(self, args):
        for controller in self.controllers.values():
            controller.do_laps_clear(args)

    def doLapDelete(self, args):
        for controller in self.controllers.values():
            controller.do_lap_delete(args)

    def doFrequencySet(self, args):
        for controller in self.controllers.values():
            controller.do_frequency_set(args)

    def doSendPriorityMessage(self, args):
        for controller in self.controllers.values():
            controller.do_send_message(args)

    def doOptionSet(self, args):
        for controller in self.controllers.values():
            controller.do_option_set(args)

    def doShutdown(self, args):
        for controller in self.controllers.values():
            controller.do_shutdown(args)

class VRxController():
    def __init__(self, name, label):
        self.name = name
        self.label = label

        self.manager = None
        self.ready = False
        self.devices = {} # collection of VRxDevices

        self.racecontext = None
        self.rhapi = None
        self.Events = None

        self.setup()

    def setup(self):
        self.ready = True

    def updateStatus(self):
        pass

    def getStatus(self):
        return {
            'ready': self.ready,
            'devices': len(self.devices)
        }

    def addDevice(self, device):
        self.devices[device.id] = device

    def removeDevice(self, device):
        self.devices.pop(device.id)

    def getAllDeviceStatus(self):
        status = []
        for device in self.devices.values():
            status.append(self.getDeviceStatus(device))
        return status

    def getDeviceStatus(self, device):
        return device.getStatus()

    def setDeviceMethod(self, device_id, method):
        if device_id in self.devices:
            self.devices[device_id].map.method = method
            return True
        else:
            return False

    def setDeviceSeat(self, device_id, seat):
        if device_id in self.devices:
            self.devices[device_id].map.seat = seat
            return True
        else:
            return False

    def setDevicePilot(self, device_id, pilot_id):
        if device_id in self.devices:
            self.devices[device_id].map.pilot_id = pilot_id
            return True
        else:
            return False

    @catchLogExceptionsWrapper
    def do_startup(self, args):
        self.onStartup(args)

    def onStartup(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_heat_set(self, args):
        self.onHeatSet(args)

    def onHeatSet(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_stage(self, args):
        self.onRaceStage(args)

    def onRaceStage(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_start(self, args):
        self.onRaceStart(args)

    def onRaceStart(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_finish(self, args):
        self.onRaceFinish(args)

    def onRaceFinish(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_stop(self, args):
        self.onRaceStop(args)

    def onRaceStop(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_lap_recorded(self, args):
        self.onRaceLapRecorded(args)

    def onRaceLapRecorded(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_race_pilot_done(self, args):
        self.onRacePilotDone(args)

    def onRacePilotDone(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_laps_clear(self, args):
        self.onLapsClear(args)

    def onLapsClear(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_lap_delete(self, args):
        self.onLapDelete(args)

    def onLapDelete(self, args):
        self.onRaceLapRecorded(args) #override this method

    @catchLogExceptionsWrapper
    def do_frequency_set(self, args):
        self.onFrequencySet(args)

    def onFrequencySet(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_send_message(self, args):
        self.onSendMessage(args)

    def onSendMessage(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_option_set(self, args):
        self.onOptionSet(args)

    def onOptionSet(self, _args):
        pass #override this method

    @catchLogExceptionsWrapper
    def do_shutdown(self, args):
        self.onShutdown(args)

    def onShutdown(self, _args):
        pass #override this method


class VRxDevice():
    def __init__(self):
        self.id = None
        self.ready = False # currently connected and available for commands
        self.connected = False # Communication established
        self.last_request = None # timestamp of last request made
        self.last_response = None # timestamp of last response received
        self.video_lock = False # lock_status
        self.type = None 
        self.name = None
        self.address = None
        self.map = VRxDeviceMap()

        self.extended_properties = {}

    def getStatus(self):
        return VRxDeviceStatus(self)

    def updateStatus(self):
        pass

class VRxDeviceMap():
    def __init__(self):
        self.method = VRxDeviceMethod.ALL
        self.pilot_id = None
        self.seat = None # node_number

class VRxDeviceMethod():
    ALL = 0 # Receive all events
    PILOT = 1 # Receive events for assigned pilot
    SEAT = 2 # Receive events for assigned seat number

class VRxDeviceStatus(dict):
    def __init__(self, device):
        dict.__init__(self,
            id = device.id,
            ready = device.ready,
            connected = device.connected,
            response_time = None,
            video_lock = device.video_lock,
            type = device.type,
            name = device.name,
            address = device.address,
            map = {
                'method': device.map.method,
                'pilot_id': device.map.pilot_id,
                'seat': device.map.seat,
            },
            extended_properties = device.extended_properties,
            last_request = device.last_request,
            last_response = device.last_response,
        )

        if device.last_response is not None and device.last_request is not None:
            self['response_time'] = device.last_response - device.last_request
            if device.last_request > device.last_response and monotonic() > device.last_request + DEVICE_TIMEOUT:
                self['connected'] = False

        if not self['connected']:
            self['ready'] = False


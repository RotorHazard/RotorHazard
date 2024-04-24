from eventmanager import Evt
import json
import requests

class WOPEventStream:
    def __init__(self, rhapi):
        self.rhapi = rhapi

    def init_plugin(self):
        print("WOP Event Stream plugin initialized")

    def start_stream(self):
        print("WOP Event Stream started")

    def stop_stream(self):
        print("WOP Event Stream stopped")

    def restart_stream(self):
        print("WOP Event Stream restarted")

    def on_event(self, event):
        print("WOP Event Stream event received: ", event)

    def forward_event(self, event_data):
        url = "http://localhost:8000/api/event/stream"
        payload = json.dumps(event_data)
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            print("Event sent successfully", response.text)
        else:
            print("Failed to send event:", response.text)


    def race_start(self, event):

        if not event["heat_id"]:
            return
        
        heat = self.rhapi.db.heat_by_id(event["heat_id"])
        slots = self.rhapi.db.slots_by_heat(event["heat_id"])

        pilots = []
        for slot in slots:
            pilot = self.rhapi.db.pilot_by_id(slot["pilot_id"])
            pilots.append(
                {
                    "name": pilot["name"],
                    "callsign": pilot["callsign"],
                    "photo": pilot["photo"]
                })

        event_data = {
            "heat_name": heat["name"],




        self.forward_event(event_data)


        print("WOP Event Stream class added: ", event)


def initialize(rhapi):
    es = WOPEventStream(rhapi)
    rhapi.events.on(Evt.RACE_START, es.race_start)
import re as regex
import requests
import json
from rh.util.RHUtils import FREQS

TIMEOUT = 5


IFPV_BANDS = {
    'rb': 'R',
    'fs': 'F'
}


class Ifpv:
    def is_pilot_url(self, url):
        matches = regex.match('https://league.ifpv.co.uk/pilots/([0-9]+)', url)
        if matches:
            return matches.group(1)
        else:
            return None

    def get_pilot_data(self, url, pilot_id):
        resp = requests.get(url, timeout=TIMEOUT)
        pilot_data = {}
        name_match = regex.search("<div class=\"row vertical-center\">\s+<div class=\"col-md-3\">\s+<h1>(.*)(?=<)</h1>\s+<p>(.*)(?=<)</p>", resp.text)
        if name_match:
            pilot_data['callsign'] = name_match.group(1)
            pilot_data['name'] = name_match.group(2)
        logo_match = regex.search('https://league.ifpv.co.uk/storage/images/pilots/[0-9]+\.(jpg|png|gif)', resp.text)
        if logo_match:
            pilot_data['logo'] = logo_match.group(0)
        return pilot_data

    def is_event_url(self, url):
        matches = regex.match('https://league.ifpv.co.uk/events/([0-9]+)/data', url)
        if matches:
            return matches.group(1)
        else:
            return None

    def get_event_data(self, url, event_id):
        resp = requests.get(url, timeout=TIMEOUT)
        ifpv_data = resp.json()
        event_data = self.convert_ifpv_json(ifpv_data)
        return event_data

    def convert_ifpv_freq(self, ifpv_bc):
        groups = regex.search("([a-z]+)([0-9]+)", ifpv_bc)
        b = IFPV_BANDS[groups.group(1)]
        c = int(groups.group(2))
        f = FREQS[b+str(c)]
        return b, c, f
    
    def convert_ifpv_json(self, ifpv_data):
        event_name = ifpv_data['event']['name']
        event_date = ifpv_data['event']['date']
        num_heats = ifpv_data['event']['heats']
        race_class_name = 'BDRA Open'
        race_format_name = 'BDRA Qualifying'
    
        freqs = json.loads(ifpv_data['event']['frequencies'])
        rhfreqs = [self.convert_ifpv_freq(f) for f in freqs]
        seats = [
            {'frequency': f,
             'bandChannel': b+str(c)
             } for b,c,f in rhfreqs
            ]
    
        pilots = {
            pilot['callsign']: {'name': pilot['name'], 'url': pilot['pilot_url'], 'ifpvId': pilot['id']}
            for pilot in ifpv_data['pilots']
        }
    
        heats = [None] * num_heats
        for pilot in ifpv_data['pilots']:
            heat = pilot['heat']-1
            seat = pilot['car']-1
            if heats[heat] is None:
                heats[heat] = {'name': 'Heat '+str(heat+1),
                               'class': race_class_name,
                               'seats': [None] * len(seats)}
            heats[heat]['seats'][seat] = pilot['callsign']

        event_data = {
            'name': event_name,
            'date': event_date,
            'classes': {race_class_name: {'format': race_format_name}},
            'seats': seats,
            'pilots': pilots,
            'stages': [
                {'name': 'Qualifying',
                 'heats': heats}
            ]
        }

        return event_data


def discover(*args, **kwargs):
    return [Ifpv()]

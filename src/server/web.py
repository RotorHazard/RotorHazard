import gevent.monkey
gevent.monkey.patch_all()
import functools
import requests
import re as regex
import logging
from .socketio import SOCKET_IO
from flask import current_app
import json
from .RHUtils import FREQS
from .race_explorer_core import import_event

logger = logging.getLogger(__name__)

TIMEOUT = 5


@functools.lru_cache(maxsize=128)
def get_pilot_data(url):
    web_data = {}
    try:
        if url.startswith('https://league.ifpv.co.uk/pilots/'):
            resp = requests.get(url, timeout=TIMEOUT)
            name_match = regex.search("<div class=\"row vertical-center\">\s+<div class=\"col-md-3\">\s+<h1>(.*)(?=<)</h1>\s+<p>(.*)(?=<)</p>", resp.text)
            if name_match:
                web_data['callsign'] = name_match.group(1)
                web_data['name'] = name_match.group(2)
            logo_match = regex.search('https://league.ifpv.co.uk/storage/images/pilots/[0-9]+\.(jpg|png|gif)', resp.text)
            if logo_match:
                web_data['logo'] = logo_match.group(0)
        elif url.startswith('https://www.multigp.com/pilots/view/?pilot='):
            # bypass CORS
            mgp_id = regex.search("\?pilot=(.*)", url).group(1)
            web_data['callsign'] = mgp_id
            profile_url = 'https://www.multigp.com/mgp/user/view/'+mgp_id
            headers = {'Referer': url, 'Host': 'www.multigp.com', 'X-Requested-With': 'XMLHttpRequest'}
            resp = requests.get(profile_url, headers=headers, timeout=TIMEOUT)
            logo_match = regex.search("<img id=\"profileImage\"(?:.*)(?=src)src=\"([^\"]*)\"", resp.text)
            if logo_match:
                web_data['logo'] = logo_match.group(1)
        else:
            resp = requests.head(url, timeout=TIMEOUT)
            if resp.headers['Content-Type'].startswith('image/'):
                web_data['logo'] = url
    except BaseException as err:
        logger.debug("Error connecting to '{}': {}".format(url, err))
    return web_data


IFPV_BANDS = {
    'rb': 'R',
    'fs': 'F'
}


def convert_ifpv_freq(ifpv_bc):
    groups = regex.search("([a-z]+)([0-9]+)", ifpv_bc)
    b = IFPV_BANDS[groups.group(1)]
    c = int(groups.group(2))
    f = FREQS[b+str(c)]
    return b, c, f


def convert_ifpv_json(ifpv_data):
    event_name = ifpv_data['event']['name']
    event_date = ifpv_data['event']['date']
    num_heats = ifpv_data['event']['heats']

    freqs = json.loads(ifpv_data['event']['frequencies'])
    rhfreqs = [convert_ifpv_freq(f) for f in freqs]
    seats = [
        {'frequency': f,
         'bandChannel': b+str(c)
         } for b,c,f in rhfreqs
        ]

    pilots = {
        pilot['callsign']: {'name': pilot['name'], 'url': pilot['pilot_url']}
        for pilot in ifpv_data['pilots']
    }

    heats = [None] * num_heats
    for pilot in ifpv_data['pilots']:
        heat = pilot['heat']-1
        seat = pilot['car']-1
        if heats[heat] is None:
            heats[heat] = {'name': 'Heat '+str(heat+1),
                           'seats': [None] * len(seats)}
        heats[heat]['seats'][seat] = pilot['callsign']

    event_data = {
        'name': event_name,
        'date': event_date,
        'seats': seats,
        'pilots': pilots,
        'stages': [
            {'name': 'Qualifying',
             'heats': heats}
        ]
    }

    return event_data


def convert_multigp_json(mgp_data):
    data = mgp_data['data']
    event_name = data['name']
    event_date = data['startDate']
    seats = []
    pilots = {}
    heats = []

    for entry in data['entries']:
        callsign = entry['userName']
        name = entry['firstName'] + ' ' + entry['lastName']
        pilots[callsign] = {'name': name}
        freq = entry['frequency']
        band = entry['band']
        channel = entry['channel']
        heat_idx = int(entry['group']) - 1
        seat_idx = int(entry['groupSlot']) - 1
        if heat_idx == 0:
            while seat_idx >= len(seats):
                seats.append(None)
            seat = {'frequency': freq}
            if band and channel:
                seat['bandChannel'] = band+str(channel)
            seats[seat_idx] = seat

        while heat_idx >= len(heats):
            heats.append(None)
        heat = heats[heat_idx]
        if not heat:
            heat = {'name': 'Heat '+str(heat_idx+1), 'seats': []}
            heats[heat_idx] = heat
        heat_seats = heat['seats']
        while seat_idx >= len(heat_seats):
            heat_seats.append(None)
        heat_seats[seat_idx] = callsign

    event_data = {
        'name': event_name,
        'date': event_date,
        'seats': seats,
        'pilots': pilots,
        'stages': [
            {'name': 'Qualifying',
             'heats': heats}
        ]
    }
    return event_data


@SOCKET_IO.on('sync_event')
def on_sync_event():
    sync_event(current_app.rhserver)


def sync_event(rhserver):
    rhdata = rhserver['RHData']
    event_url = rhdata.get_option('eventURL', '')
    if not event_url:
        return

    logging.info("Syncing event...")
    if '.multigp.com/' in event_url:
        data = {'apiKey': rhserver['rhconfig'].GENERAL['MULTIGP_API_KEY']}
        resp = requests.post(event_url, json=data, timeout=TIMEOUT)
        mgp_data = resp.json()
        event_data = convert_multigp_json(mgp_data)
    else:
        resp = requests.get(event_url, timeout=TIMEOUT)
        ifpv_data = resp.json()
        event_data = convert_ifpv_json(ifpv_data)
    import_event(event_data, rhserver)

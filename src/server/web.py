import functools
import requests
import re as regex
import logging
from .socketio import SOCKET_IO
from flask import current_app
import json
from .RHUtils import FREQS

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


@SOCKET_IO.on('sync_event')
def on_sync_event():
    rhdata = current_app.rhserver['RHData']
    event_url = rhdata.get_option('eventURL', '')
    if not event_url:
        return

    resp = requests.get(event_url, timeout=TIMEOUT)
    event_data = resp.json()
    event_name = event_data['event']['name']
    freqs = json.loads(event_data['event']['frequencies'])
    rhfreqs = [convert_ifpv_freq(f) for f in freqs]

    profile_data = {'profile_name': event_name,
                    'frequencies': {'b': [b for b,_,_ in rhfreqs],
                                    'c': [c for _,c,_ in rhfreqs],
                                    'f': [f for _,_,f in rhfreqs]
                                    }
                    }
    rhprofile = rhdata.upsert_profile(profile_data)

    pilots_by_url = {}
    for rhpilot in rhdata.get_pilots():
        pilots_by_url[rhpilot.url] = rhpilot

    heats = {}
    for pilot in event_data['pilots']:
        url = pilot['pilot_url']
        heat = pilot['heat']-1
        node = pilot['car']-1
        if url in pilots_by_url:
            rhpilot = pilots_by_url[url]
        else:
            # add new pilot
            rhpilot = rhdata.add_pilot({'url': url})

        if heat not in heats:
            heats[heat] = {}
        heats[heat][node] = rhpilot.id
        

    rhheats = rhdata.get_heats()
    for h in range(min(len(heats), len(rhheats))):
        for node, pilot_id in heats[h].items():
            rhdata.alter_heat({'heat': rhheats[h].id, 'node': node, 'pilot': pilot_id})
    for h in range(len(rhheats), len(heats)):
        rhdata.add_heat(initPilots=heats[h])

    current_app.rhserver['on_set_profile']({'profile': rhprofile.id})
    current_app.rhserver['emit_pilot_data']()
    current_app.rhserver['emit_heat_data']()

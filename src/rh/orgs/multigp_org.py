import re as regex
import requests

TIMEOUT = 5


class MultiGP:
    def __init__(self, api_key):
        self.api_key = api_key

    def is_pilot_url(self, url):
        matches = regex.match('https://([a-z]+)\.multigp\.com/pilots/view/\?pilot=(.*)', url)
        if matches:
            return (matches.group(1), matches.group(2))
        else:
            return None

    def get_pilot_data(self, url, pilot_id):
        callsign = pilot_id[1]
        pilot_data = {}
        pilot_data['callsign'] = callsign
        host = pilot_id[0] + '.multigp.com'
        profile_url = 'https://' + host + '/mgp/user/view/' + callsign
        # bypass CORS
        headers = {'Referer': url, 'Host':host, 'X-Requested-With': 'XMLHttpRequest'}
        resp = requests.get(profile_url, headers=headers, timeout=TIMEOUT)
        logo_match = regex.search("<img id=\"profileImage\"(?:.*)(?=src)src=\"([^\"]*)\"", resp.text)
        if logo_match:
            pilot_data['logo'] = logo_match.group(1)
        return pilot_data

    def is_event_url(self, url):
        matches = regex.match('https://([a-z]+)\.multigp\.com/mgp/multigpwebservice/race/view\?id=([0-9]+)', url)
        if matches:
            return (matches.group(1), matches.group(2))
        else:
            matches = regex.match('https://([a-z]+)\.multigp\.com/mgp/multigpwebservice/race/view/id/([0-9]+)', url)
            if matches:
                return (matches.group(1), matches.group(2))
            else:
                return None

    def get_event_data(self, url, event_id):
        if self.api_key:
            data = {'apiKey': self.api_key}
            resp = requests.post(url, json=data, timeout=TIMEOUT)
            mgp_data = resp.json()
            host = event_id[0] + '.multigp.com'
            event_data = self.convert_multigp_json(mgp_data, host)
            return event_data
        else:
            return {}

    def convert_multigp_json(self, mgp_data, host):
        data = mgp_data['data']
        event_name = data['name']
        event_date = data['startDate']
        race_class_name = 'Open'

        seats = []
        pilots = {}
        heats = []

        for entry in data['entries']:
            callsign = entry['userName']
            name = entry['firstName'] + ' ' + entry['lastName']
            pilots[callsign] = {'name': name, 'url': 'https://'+host+'/pilots/view/?pilot='+callsign, 'multigpId': entry['pilotId']}
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
                heat = {'name': 'Heat '+str(heat_idx+1),
                        'class': race_class_name,
                        'seats': []}
                heats[heat_idx] = heat
            heat_seats = heat['seats']
            while seat_idx >= len(heat_seats):
                heat_seats.append(None)
            heat_seats[seat_idx] = callsign

        event_data = {
            'name': event_name,
            'date': event_date,
            'classes': {race_class_name: {}},
            'seats': seats,
            'pilots': pilots,
            'stages': [
                {'name': 'Qualifying',
                 'heats': heats}
            ]
        }
        return event_data

    def upload_results(self, event_id, leaderboards):
        if not self.api_key:
            return
        host = event_id[0] + '.multigp.com'
        results_url = 'https://'+host+'/mgp/multigpwebservice/race/captureOverallRaceResult?id='+event_id[1]
        final_stage_leaderboards = leaderboards['stages'][-1]['leaderboards']
        if not final_stage_leaderboards:
            return
        final_leaderboard = next(iter(final_stage_leaderboards.values()))
        pilots = leaderboards['pilots']
        ranking = []
        pos = 1
        for entry in final_leaderboard['ranking']:
            pilot = pilots[entry['pilot']]
            pilot_id = pilot.get('multigpId')
            if pilot_id is not None:
                ranking.append({
                    'orderNumber': pos,
                    'pilotId': pilot_id
                })
                pos += 1
        data = {
            'apiKey': self.api_key,
            'data': {
                'raceId': event_id[1],
                'bracketResults': ranking
            }
        }
        resp = requests.post(results_url, json=data, timeout=TIMEOUT)
        ok_data = resp.json()
        return ok_data['status']


def discover(config, *args, **kwargs):
    api_key = config.GENERAL.get('MULTIGP_API_KEY') if config else None
    return [MultiGP(api_key)]

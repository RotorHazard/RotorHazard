import functools
import requests
import logging
from rh.app import SOCKET_IO
from flask import current_app
import server.race_explorer_core as racex
from rh.util.Plugins import Plugins
import rh.orgs as org_pkg

logger = logging.getLogger(__name__)

TIMEOUT = 5


ORGS = Plugins(suffix='org')


def init(rhconfig):
    ORGS.discover(org_pkg, config=rhconfig)


@functools.lru_cache(maxsize=128)
def get_pilot_data(url):
    for org in ORGS:
        pilot_id = org.is_pilot_url(url)
        if pilot_id:
            try:
                return org.get_pilot_data(url, pilot_id)
            except BaseException as err:
                logger.warning("Error connecting to '{}'".format(url), exc_info=err)
                return {}
    return {}


def get_event_data(url):
    for org in ORGS:
        event_id = org.is_event_url(url)
        if event_id:
            try:
                return org.get_event_data(url, event_id)
            except BaseException as err:
                logger.warning("Error connecting to '{}'".format(url), exc_info=err)
                return {}

    resp = requests.get(url, timeout=TIMEOUT)
    event_data = resp.json()
    return event_data


@SOCKET_IO.on('sync_event')
def on_sync_event():
    sync_event(current_app.rhserver)


def sync_event(rhserver):
    rhdata = rhserver['RHData']
    event_info = racex.export_event_basic(rhdata)
    url = event_info['url']
    if not url:
        return

    logging.info("Syncing event...")
    event_data = get_event_data(url)
    if event_data:
        racex.import_event(event_data, rhserver)
        logging.info("Syncing completed")
    else:
        logging.info("Nothing to sync")


def upload_results(rhserver):
    rhdata = rhserver['RHData']
    event_info = racex.export_event_basic(rhdata)
    url = event_info['url']
    if not url:
        return

    logging.info("Uploading results...")
    leaderboard = racex.export_leaderboard(rhdata)
    for org in ORGS:
        event_id = org.is_event_url(url)
        if event_id:
            try:
                org.upload_results(event_id, leaderboard)
                logger.info("Upload completed")
            except BaseException as err:
                logger.warning("Error connecting to '{}'".format(url), exc_info=err)
                return {}

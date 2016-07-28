import json
import requests
import re

from config import setup_logging, setup_db

logger = setup_logging()
suc_collection = setup_db().suc

pattern_suc = re.compile(".*(\d+) Supercharger.*", re.DOTALL)
pattern_dc = re.compile(".*(\d+) Tesla Connector.*", re.DOTALL)


def chargers(s):
    m = pattern_suc.match(s)
    if m:
        return int(m.group(1))

    m = pattern_dc.match(s)
    if m:
        return int(m.group(1))

    logger.warn("No chargers found from %s" % s)
    return None


def import_from_url(url, type):
    res = requests.get(url)
    if res.status_code != 200:
        logger.error('Failed to load type=%s, code=%d, url=%s, res=%s' % (type, res.status_code, url, res.text))

    logger.debug('parsing type=%s, code=%d, url=%s' % (type, res.status_code, url))
    results = json.loads(res.text)
    for r in results:
        if 'location_id' not in r:
            logger.warn("No 'location_id' for %s" % str(r))
            continue

        d = {
            'type': type,
            'locationId': r['location_id'],
            'title': r['title'],
            'raw': r,
        }
        if 'chargers' in r:
            d['stalls'] = chargers(r['chargers'])
        else:
            logger.warn("No 'chargers' for %s" % r['location_id'])
            d['stalls'] = None

        if 'latitude' in r and 'longitude' in r:
            lat = float(r['latitude'])
            lng = float(r['longitude'])
            d['loc'] = {'type': "Point", 'coordinates': [lng, lat]}

        suc_collection.insert(d)
    logger.info("Imported, type=%s, count=%d" % (type, len(results)))

logger.info("Importing, suc_collection_count=%d" % suc_collection.count())
suc_collection.remove()
import_from_url('https://www.tesla.com/all-locations?type=supercharger', 'supercharger')
import_from_url('https://www.tesla.com/all-locations?type=destination_charger', 'destination_charger')

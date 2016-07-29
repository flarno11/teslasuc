import json

import pymongo
import requests
import re
import datetime
import pytz
from pymongo.errors import DuplicateKeyError
from pytz import timezone

from config import setup_logging, setup_db

logger = setup_logging()
db = setup_db()
suc_collection = db.suc
charging_collection = db.charging

pattern_suc = re.compile(".*(\d+) Supercharger.*", re.DOTALL)
pattern_dc = re.compile(".*(\d+) Tesla Connector.*", re.DOTALL)

tz_zurich = timezone('Europe/Zurich')

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

        try:
            suc_collection.insert(d)
        except DuplicateKeyError:
            logger.warn("Duplicated key=%s" % d['locationId'])
    logger.info("Imported, type=%s, count=%d" % (type, len(results)))

correction_table = {
    'Hiltpoltstein': 'poltstein',
    'Hamburg SEC': 'Hamburg-Essener Straße',
    'Aix en Provence': 'Aix-en-Provence',
    'Mosjoen': 'Mosjøen',
    'Orange': 'Orange Supercharger',
    'Anif': 'Salzburg',
    'Modena': 'Modena Supercharger',
    'Stjördal': 'stjordalsupercharger',
    'Service Center Schönefeld': 'Berlin-Schönefeld',
    'Berlin Sec': 'Berlin-Schönefeld',
    'Gol': 'golsupercharger',
    'Vystrkov': 'Humpolec',
    'Eselsfürth': 'Kaiserslautern',
    'Carpiano': 'Melegnano',
    'Rivera': 'Monte Ceneri',
    'Stockholm Infracity': 'Sollentuna',
    'Palmanova': 'Palmanova Supercharger 2',
    'Hamburg': 'Hamburg Supercharger',
}

def import_chargings(data):
    post_data = filter(None, data.split("\n"))
    items = [d.split(",") for d in post_data]

    def parse(item):
        error = None

        if len(item) != 7:
            error = 'len=' + str(len(item))

        text = item[2]
        if text in correction_table:
            text = correction_table[text]

        sucs = [s for s in suc_collection.find({
            '$and': [{'type': 'supercharger', 'raw.region': 'europe'}, {
                '$or': [
                    {'title': {'$regex': re.escape(text), '$options': '-i'}},
                    {'locationId': {'$regex': re.escape(text), '$options': '-i'}},
                    {'raw.common_name': {'$regex': re.escape(text), '$options': '-i'}},
                ]
            }]
            })]
        if len(sucs) != 1:
            error = 'Invalid supercharger, len=%d' % len(sucs)
            suc = {'locationId': None, 'title': text}
        else:
            suc = sucs[0]

        try:
            time = datetime.datetime.strptime(item[0] + ' ' + item[1], "%m/%d/%Y %H:%M")
            time = tz_zurich.localize(time)
        except:
            time = None
            error = 'Invalid time: ' + item[0] + ' ' + item[1]

        return {
            'locationId': suc['locationId'],
            'title': suc['title'],
            'time': time,
            'stalls': item[3],
            'charging': item[4],
            'waiting': item[5],
            'blocked': item[6],
            'error': error
        }
    parsed = list(filter(None, [parse(i) for i in items]))
    for item in parsed:
        charging_collection.insert(item)
    return len(parsed)


def run_import():
    logger.info("Importing, suc_collection_count=%d" % suc_collection.count())
    suc_collection.remove()
    import_from_url('https://www.tesla.com/all-locations?type=supercharger', 'supercharger')
    import_from_url('https://www.tesla.com/all-locations?type=destination_charger', 'destination_charger')


if __name__ == "__main__":
    #import_chargings("06/23/2013,13:15,Neuberg,6,3,0,0\n07/09/2014,18:20,Schweitenkirchen,8,2,0,0\n")
    run_import()
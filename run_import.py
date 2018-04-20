import json
import requests
import re
import datetime
from pymongo.errors import DuplicateKeyError
from pytz import timezone

from config import setup_logging, setup_db

logger = setup_logging()

pattern_suc = re.compile("(\d+) Supercharger", flags=re.DOTALL | re.IGNORECASE)
pattern_dc = re.compile("(\d+) Tesla Connector", flags=re.DOTALL | re.IGNORECASE)

tz_zurich = timezone('Europe/Zurich')
tz_utc = timezone('UTC')


def chargers(s, location_id):
    m = pattern_suc.findall(s)
    if len(m) > 0:
        return int(m[0])

    m = pattern_dc.findall(s)
    if len(m):
        return int(m[0])

    logger.warn("No chargers found for %s from '%s'" % (location_id, s))
    return None


def import_from_url(url, type, suc_collection):
    res = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:58.0) Gecko/20100101 Firefox/58.0'
    })
    if res.status_code != 200:
        logger.error('Failed to load type=%s, code=%d, url=%s, res=%s' % (type, res.status_code, url, res.text))

    logger.debug('parsing type=%s, code=%d, url=%s, len=%d, text=%s' % (type, res.status_code, url, len(res.text), res.text[:10]))
    results = json.loads(res.text)
    inserted = 0
    failed = 0
    skipped = 0
    for r in results:
        if 'location_id' not in r:
            logger.warn("No location_id for %s" % str(r))
            skipped += 1
            continue

        if 'open_soon' in r and r['open_soon'] == '1':
            logger.info("Skip open_soon for %s" % r['location_id'])
            skipped += 1
            continue

        d = {
            'type': type,
            'locationId': r['location_id'],
            'title': r['title'],
            'country': r['country'],
            'raw': r,
        }
        if 'chargers' in r and r['chargers']:
            d['stalls'] = chargers(r['chargers'], r['location_id'])
        else:
            logger.warn("No chargers for %s" % r['location_id'])
            d['stalls'] = None

        if 'latitude' in r and 'longitude' in r:
            lat = float(r['latitude'])
            lng = float(r['longitude'])
            d['loc'] = {'type': "Point", 'coordinates': [lng, lat]}

        try:
            suc_collection.insert(d)
            inserted += 1
        except DuplicateKeyError:
            logger.warn("Duplicated key=%s" % d['locationId'])
            failed += 1
    logger.info("Imported, type=%s, count=%d" % (type, len(results)))
    return {'inserted': inserted, 'failed': failed, 'skipped': skipped}


def import_checkins(data, suc_collection, checkin_collection):
    post_data = filter(None, data.split("\n"))
    items = [d.split(",") for d in post_data]

    def parse(item):
        error = None

        if len(item) != 7 and len(item) != 11:
            error = 'len=' + str(len(item))

        text = item[2]
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
            suc = {'locationId': None, 'title': text, 'country': None}
        else:
            suc = sucs[0]

        try:
            time = datetime.datetime.strptime(item[0] + ' ' + item[1], "%m/%d/%Y %H:%M")
            time = tz_zurich.localize(time)
        except:
            time = None
            error = 'Invalid time: ' + item[0] + ' ' + item[1]

        if len(item) == 11:
            notes = item[7]
            tff_user_id = item[8]

            try:
                time_report = datetime.datetime.strptime(item[9] + ' ' + item[10], "%m/%d/%Y %H:%M")
                time_report = tz_zurich.localize(time_report)
            except:
                time_report = None
                error = 'Invalid time2: ' + item[9] + ' ' + item[10]
        else:
            time_report = time
            notes = None
            tff_user_id = None

        return {
            'suc': {
                'locationId': suc['locationId'],
                'title': suc['title'],
                'country': suc['country'],
                'stalls': int(item[3]),
            },
            'checkin': {
                'time': time,
                'charging': int(item[4]),
                'blocked': int(item[5]),
                'waiting': int(item[6]),
                'notes': notes,
            },
            'submitter': {
                'time': time_report,
                'tffUserId': tff_user_id,
                'ip': None,
                'userAgent': None,
            },
            'error': error,
        }
    parsed = list(filter(None, [parse(i) for i in items]))
    for item in parsed:
        checkin_collection.insert(item)
    return len(parsed)


def run_import(suc_collection):
    logger.info("Importing, suc_collection_count=%d" % suc_collection.count())
    suc_collection.remove()
    stats_suc = import_from_url('https://www.tesla.com/all-locations?type=supercharger', 'supercharger', suc_collection)
    stats_dec = import_from_url('https://www.tesla.com/all-locations?type=destination_charger', 'destination_charger', suc_collection)
    return {'statsSuc': stats_suc, 'statsDec': stats_dec}


if __name__ == "__main__":
    #import_chargings("06/23/2013,13:15,Neuberg,6,3,0,0\n07/09/2014,18:20,Schweitenkirchen,8,2,0,0\n")
    #run_import()
    pass
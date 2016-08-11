import re
import json
import datetime
import os
import urllib
from datetime import timedelta

import pymongo
from flask.templating import render_template
from flask import Flask, redirect, url_for, jsonify, request
from bson.objectid import ObjectId
from flask.wrappers import Response
from pytz import timezone

from config import setup_logging, setup_db
from lib import TimeFormat, convert_time_fields, TimePattern, convert_to_csv, TimePatternSimple, TimeFormatSimple
from run_import import run_import, import_checkins

logger = setup_logging()
db = setup_db()
suc_collection = db.suc
checkin_collection = db.checkin

tz_utc = timezone('UTC')
tz_zurich = timezone("Europe/Zurich")

max_distance = 20000
pattern_latlng = re.compile("(\d+\.\d+),(\d+\.\d+)")


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime.datetime):
            return o.strftime(TimeFormat)
        return json.JSONEncoder.default(self, o)


class InvalidAPIUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

app = Flask(__name__)


@app.errorhandler(InvalidAPIUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/')
def index():
    if 'tesla' in request.headers.get('User-Agent').lower()\
            or 'QtCarBrowser' in request.headers.get('User-Agent')\
            or is_legacy():

        country = validate_str(request.args.get('country', ''), max_len=100)

        countries = [s['_id'] for s in suc_collection.aggregate([
            {'$match': {'type': 'supercharger'}},
            {'$group': {'_id': '$country', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 4}}},
            {'$sort': {'_id': 1}}
        ])]

        query = {'type': 'supercharger'}
        if country:
            if country == 'others':
                query['country'] = {'$nin': countries}
            else:
                query['country'] = country

        super_chargers = suc_collection\
            .find(query, {'locationId': True, 'title': True, 'country': True, 'stalls': True})\
            .sort([('country', pymongo.ASCENDING), ('title', pymongo.ASCENDING)])

        return render_template('form.html',
                               countries=countries,
                               time=tz_utc.localize(datetime.datetime.utcnow()).astimezone(tz_zurich).strftime(TimeFormatSimple),
                               superChargers=super_chargers,
                               msg=request.args.get('msg', None),
                               tffUserId=request.args.get('tffUserId', '')
        )
    else:
        return app.send_static_file('index.html')


@app.route('/sucImport', methods=['POST'])
def route_import():
    run_import()
    return jsonify({'error': None})


@app.route('/lookup')
def lookup_query():
    query_param = request.args.get('query', None)
    if query_param and len(query_param) > 2:
        m = pattern_latlng.match(query_param)
        if m:
            lat, lng = float(m.group(1)), float(m.group(2))
            q = get_query_coords(lat, lng)
            q['type'] = 'supercharger'
        else:
            q = {'title': {'$regex': re.escape(query_param), '$options': '-i'}, 'type': 'supercharger'}
        results = [c for c in suc_collection.find(q, {'raw': False, '_id': False, 'loc': False, 'type': False})]
    else:
        results = []

    return Response(JSONEncoder().encode(results), mimetype='application/json')


def get_query_coords(lat, lng):
    return {'loc': {'$near': {'$geometry': {'type': "Point", 'coordinates': [lng, lat]}, '$maxDistance': max_distance,}}}


def is_legacy():
    return request.args.get('legacy', False)


@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if request.method == 'POST':
        if is_legacy():
            client_data = request.form
        else:
            client_data = request.get_json(force=True)

        if not all(k in client_data for k in ('time', 'locationId', 'stalls', 'charging', 'blocked', 'waiting', 'tffUserId', 'notes')):
            raise InvalidAPIUsage("Invalid data received", status_code=400)

        validated_data = {}
        for k in ['stalls', 'charging', 'blocked', 'waiting']:
            validated_data[k] = validate_int(client_data[k])

        validated_data['notes'] = validate_str(client_data['notes'])
        validated_data['tffUserId'] = validate_str(client_data['tffUserId'])

        location = validate_location(client_data['locationId'])

        for k in ['charging', 'blocked']:
            if validated_data[k] > location['stalls']:
                raise InvalidAPIUsage("Charging/blocked cannot be larger than stalls", status_code=400)

        submission = {
            'suc': {
                'locationId': location['locationId'],
                'title': location['title'],
                'country': location['country'],
                'stalls': location['stalls'],
            },
            'submitter': {
                'userAgent': request.headers.get('User-Agent'),
                'ip': request.remote_addr,
                'time': tz_utc.localize(datetime.datetime.utcnow()),
                'tffUserId': validated_data['tffUserId'],
            },
            'checkin': {
                'time': validate_date(client_data['time']),
                'charging': validated_data['charging'],
                'blocked': validated_data['blocked'],
                'waiting': validated_data['waiting'],
                'notes': validated_data['notes'],
            },
        }

        checkin_collection.insert(submission)

        if is_legacy():
            s = "Checkin Nr. %d added, thank you." % checkin_collection.count()
            return redirect('/?legacy=true&msg=' + urllib.parse.quote_plus(s))
        else:
            return jsonify({'error': None})
    else:
        query_param = request.args.get('filter', None)
        format = request.args.get('format', None)
        limit = request.args.get('limit', None)

        if query_param and len(query_param) > 0:
            query = {'suc.title': {'$regex': re.escape(query_param), '$options': '-i'}}
        else:
            query = {}

        res = checkin_collection.find(query, {'_id': False}).sort('checkin.time', -1)
        if limit:
            res = res.limit(validate_int(limit))
        results = [c for c in res]

        if format == 'csv':
            response = Response(convert_to_csv([{'locationId': r['suc']['locationId'], 'stalls': r['suc']['stalls'], 'time': r['checkin']['time'], 'charging': r['checkin']['charging'], 'blocked': r['checkin']['blocked'], 'waiting': r['checkin']['waiting']} for r in results]), mimetype='application/csv')
            response.headers["Content-Disposition"] = "attachment; filename=checkins.csv"
            return response
        else:
            return Response(JSONEncoder().encode(results), mimetype='application/json')


@app.route('/checkinImport', methods=['POST'])
def checkin_import():
    c = import_checkins(request.get_data(as_text=True))
    return jsonify({'imported': c})


@app.route('/stats', methods=['GET'])
def stats():
    checkins = {r['_id']: {'checkins': r['checkins'], 'utilization': r['utilization']}
                for r in checkin_collection.aggregate([
                    {'$group': {'_id': '$suc.country',
                                'checkins': {'$sum': 1},
                                'utilization': {'$avg': {'$divide': ['$checkin.charging', '$suc.stalls' ]}}}}
                ])
                }

    countries = sorted(list(checkins.keys()))

    sucs = {r['_id']: r['sucs']
            for r in suc_collection.aggregate([
                {'$match': {'type': 'supercharger', 'country': {'$in': countries}}},
                {'$group': {'_id': '$country', 'sucs': {'$sum': 1}}}
            ])
            }

    return jsonify([
        {'country': c,
         'sucs': sucs[c],
         'checkins': checkins[c]['checkins'],
         'utilization': checkins[c]['utilization']}
        for c in countries
    ])


@app.route('/stats/country/<country>', methods=['GET'])
def stats_country(country):
    checkins = {r['_id']: {'checkins': r['checkins'], 'utilization': r['utilization']}
                 for r in checkin_collection.aggregate([
                    {'$match': {'suc.country': country}},
                    {'$group': {'_id': '$suc.locationId',
                                'checkins': {'$sum': 1},
                                'utilization': {'$avg': {'$divide': ['$checkin.charging', '$suc.stalls' ]}}}}
                ])
                }

    def create_item(location):
        if location['locationId'] in checkins:
            c = checkins[location['locationId']]
        else:
            c = {'checkins': 0, 'utilization': None}

        return {
            'locationId': location['locationId'],
            'title': location['title'],
            'stalls': location['stalls'],
            'checkins': c['checkins'],
            'utilization': c['utilization'],
        }

    return jsonify([create_item(c) for c in suc_collection.find({'type': 'supercharger', 'country': country}).sort('title')])


@app.route('/stats/superCharger/<location_id>', methods=['GET'])
def stats_super_charger(location_id):
    return jsonify([{
        'time': c['checkin']['time'],
        'stalls': c['suc']['stalls'],
        'charging': c['checkin']['charging'],
        'waiting': c['checkin']['waiting'],
        'blocked': c['checkin']['blocked'],
    } for c in checkin_collection.find({'suc.locationId': location_id}).sort('checkin.time')])


def validate_location(location_id):
    location = suc_collection.find_one({'locationId': location_id})
    if not location:
        raise InvalidAPIUsage("Invalid location", status_code=400)
    return location


def validate_int(s):
    if isinstance(s, str) and not s:  # check for empty string, but s can also be an int when coming from json
        raise InvalidAPIUsage("Invalid number", status_code=400)
    val = int(s)
    if val < 0:
        raise InvalidAPIUsage("Invalid number", status_code=400)
    return val


def validate_str(s, max_len=1000):
    if not isinstance(s, str):
        raise InvalidAPIUsage("Value is not a string", status_code=400)
    if len(s) > max_len:
        raise InvalidAPIUsage("Text too long", status_code=400)
    return s


def validate_date(s):
    if TimePattern.match(s):
        d = datetime.datetime.strptime(s, TimeFormat)
        d = tz_utc.localize(d)
    elif TimePatternSimple.match(s):
        d = datetime.datetime.strptime(s, TimeFormatSimple)
        d = tz_zurich.localize(d)  # TODO use client timezone
    else:
        raise InvalidAPIUsage("Invalid date", status_code=400)

    now_utc = tz_utc.localize(datetime.datetime.utcnow())
    one_hour_from_now = now_utc + timedelta(hours=1)
    one_month_ago = now_utc - timedelta(days=30)
    if d > one_hour_from_now:
        raise InvalidAPIUsage("Time cannot be in the future", status_code=400)
    elif d < one_month_ago:
        raise InvalidAPIUsage("Time cannot be more than one month in the past", status_code=400)

    return d


app.json_encoder = JSONEncoder


if __name__ == "__main__":
    # port = int(os.getenv("VCAP_APP_PORT", "-1"))
    app.run()

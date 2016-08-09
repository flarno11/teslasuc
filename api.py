import re
import json
import datetime
import os
from datetime import timedelta

from flask.templating import render_template
from flask import Flask, redirect, url_for, jsonify, request
from bson.objectid import ObjectId
from flask.wrappers import Response

from config import setup_logging, setup_db
from lib import TimeFormat, convert_time_fields, TimePattern, convert_to_csv
from run_import import run_import, import_checkins

logger = setup_logging()
db = setup_db()
suc_collection = db.suc
checkin_collection = db.checkin

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
def hello_world():
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


@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if request.method == 'POST':
        client_data = request.get_json(force=True)

        if not all(k in client_data for k in ('time', 'locationId', 'stalls', 'charging', 'blocked', 'waiting', 'tffUserId', 'notes')):
            raise InvalidAPIUsage("Invalid data received", status_code=400)

        validated_data = {}
        for k in ['stalls', 'charging', 'blocked', 'waiting']:
            validated_data[k] = validate_int(client_data[k])

        validated_data['notes'] = validate_str(client_data['notes'])
        validated_data['tffUserId'] = validate_str(client_data['tffUserId'])

        for k in ['charging', 'blocked']:
            if validated_data[k] > validated_data['stalls']:
                raise InvalidAPIUsage("Charging/blocked cannot be larger than stalls", status_code=400)

        location = validate_location(client_data['locationId'], validated_data['stalls'])
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
                'time': datetime.datetime.now(),
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
        return jsonify({'error': None})
    else:
        query_param = request.args.get('filter', None)
        format = request.args.get('format', None)
        limit = request.args.get('limit', None)

        if query_param and len(query_param) > 0:
            query = {'title': {'$regex': re.escape(query_param), '$options': '-i'}}
        else:
            query = {}

        res = checkin_collection.find(query, {'_id': False}).sort('checkin.time', -1)
        if limit:
            res = res.limit(validate_int(limit))
        results = [c for c in res]

        if format == 'csv':
            response = Response(convert_to_csv(results), mimetype='application/csv')
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
    checkins = {r['_id']: r['checkins']
                 for r in checkin_collection.aggregate([
                    {'$group': {'_id': '$suc.country', 'checkins': {'$sum': 1}}}
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
        {'country': c, 'sucs': sucs[c], 'checkins': checkins[c]} for c in countries
    ])


def validate_location(location_id, stalls):
    location = suc_collection.find_one({'locationId': location_id})
    if not location or location['stalls'] != stalls:
        raise InvalidAPIUsage("Invalid location", status_code=400)
    return location


def validate_int(s):
    val = int(s)
    if val < 0:
        raise InvalidAPIUsage("Invalid number", status_code=400)
    return val


def validate_str(str, max_len=1000):
    if len(str) > max_len:
        raise InvalidAPIUsage("Text too long", status_code=400)
    return str


def validate_date(s):
    if not TimePattern.match(s):
        raise InvalidAPIUsage("Invalid date", status_code=400)
    d = datetime.datetime.strptime(s, TimeFormat)
    one_hour_from_now = datetime.datetime.now() + timedelta(hours=1)
    if d > one_hour_from_now:
        raise InvalidAPIUsage("Time cannot be in the future", status_code=400)

    return d


app.json_encoder = JSONEncoder


if __name__ == "__main__":
    # port = int(os.getenv("VCAP_APP_PORT", "-1"))
    app.run()

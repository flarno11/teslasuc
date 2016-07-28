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
from lib import TimeFormat, convert_time_fields, TimePattern
from run_import import run_import

logger = setup_logging()
db = setup_db()
suc_collection = db.suc
charging_collection = db.charging

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


@app.route('/import', methods=['POST'])
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
            q = {'title': {'$regex': query_param, '$options': '-i'}, 'type': 'supercharger'}
        results = [c for c in suc_collection.find(q, {'raw': False, '_id': False, 'loc': False, 'type': False})]
    else:
        results = []

    return Response(JSONEncoder().encode(results), mimetype='application/json')


def get_query_coords(lat, lng):
    return {'loc': {'$near': {'$geometry': {'type': "Point", 'coordinates': [lng, lat]}, '$maxDistance': max_distance,}}}


@app.route('/charging', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        client_data = request.get_json(force=True)

        if not all(k in client_data for k in ('time', 'locationId', 'title', 'stalls', 'charging', 'blocked', 'waiting')):
            raise InvalidAPIUsage("Invalid data received", status_code=400)

        submission = {}
        for k in ['stalls', 'charging', 'blocked', 'waiting']:
            submission[k] = validate_int(client_data[k])

        for k in ['charging', 'blocked']:
            if submission[k] > submission['stalls']:
                raise InvalidAPIUsage("Charging/blocked cannot be larger than stalls", status_code=400)

        submission['locationId'] = validate_location(client_data['locationId'], submission['stalls'], client_data['title'])
        submission['title'] = client_data['title']
        submission['time'] = validate_date(client_data['time'])

        charging_collection.insert(submission)
        return jsonify({'error': None})
    else:
        results = [c for c in charging_collection.find({},{'_id': False}).sort('time', -1)]
        return Response(JSONEncoder().encode(results), mimetype='application/json')


def validate_location(location_id, stalls, title):
    location = suc_collection.find_one({'locationId': location_id})
    if not location or location['stalls'] != stalls or location['title'] != title:
        raise InvalidAPIUsage("Invalid location", status_code=400)
    return location_id


def validate_int(s):
    val = int(s)
    if val < 0:
        raise InvalidAPIUsage("Invalid number", status_code=400)
    return val


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

import logging.config
import json
import os
import pymongo
from pymongo import MongoClient


def setup_logging():
    logging.config.fileConfig('logging.conf', defaults={})
    logger = logging.getLogger('suc')
    logger.setLevel(logging.DEBUG)
    return logger


def setup_db():
    mongo_url = os.getenv('MONGODB_URI', None)
    if mongo_url:
        db_name = mongo_url.split('/')[-1]
    else:
        vcap_services = json.loads(os.getenv("VCAP_SERVICES"))
        mongo_url = vcap_services["mongodb"][0]["credentials"]["uri"]
        db_name = vcap_services["mongodb"][0]["credentials"]["database"]

    db = MongoClient(mongo_url)[db_name]

    suc_collection = db.suc
    #suc_collection.ensure_index([('type', pymongo.ASCENDING)])
    suc_collection.create_index("type")
    suc_collection.create_index("title")
    suc_collection.create_index("locationId")
    suc_collection.create_index("country")
    suc_collection.create_index([("loc", pymongo.GEOSPHERE)])
    suc_collection.create_index([("type", pymongo.ASCENDING), ("locationId", pymongo.ASCENDING)], unique=True)

    checkin_colleciton = db.checkin
    checkin_colleciton.create_index("suc.country")
    checkin_colleciton.create_index("checkin.time")
    checkin_colleciton.create_index("submitter.time")
    checkin_colleciton.create_index("suc.locationId")
    return db

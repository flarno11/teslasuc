import logging.config
import json
import os
import pymongo
from pymongo import MongoClient


def setup_logging():
    logging.config.fileConfig('logging.conf', defaults={})
    logger = logging.getLogger('teslaImport')
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

    #db = MongoClient('mongodb://localhost:11003/').suc
    suc_collection = db.suc
    #suc_collection.ensure_index([('type', pymongo.ASCENDING)])
    suc_collection.create_index("type")
    #suc_collection.create_index("text")
    #suc_collection.create_index("city")
    #suc_collection.create_index("common_name")
    suc_collection.create_index("locationId")
    #suc_collection.create_index("sub_region")
    suc_collection.create_index([("loc", pymongo.GEOSPHERE)])
    return db

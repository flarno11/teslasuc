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
    vcap_services = json.loads(os.getenv("VCAP_SERVICES"))
    mongoUrl = vcap_services["mongodb"][0]["credentials"]["uri"]
    dbName = vcap_services["mongodb"][0]["credentials"]["database"]
    db = MongoClient(mongoUrl)[dbName]

    #db = MongoClient('mongodb://localhost:11003/').suc
    suc_collection = db.suc
    #suc_collection.ensure_index([('type', pymongo.ASCENDING)])
    suc_collection.create_index("type")
    suc_collection.create_index("text")
    suc_collection.create_index("city")
    suc_collection.create_index("common_name")
    suc_collection.create_index("location_id")
    suc_collection.create_index("sub_region")
    suc_collection.create_index([("loc", pymongo.GEOSPHERE)])
    return db

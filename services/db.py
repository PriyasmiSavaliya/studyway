from flask import current_app, g
from pymongo import MongoClient

def get_db():
    if 'mongo_client' not in g:
        mongo_uri = current_app.config['MONGO_URI']
        g.mongo_client = MongoClient(mongo_uri)
        g.db = g.mongo_client.get_default_database()
    return g.db

def close_db(e=None):
    client = g.pop('mongo_client', None)
    if client is not None:
        client.close()

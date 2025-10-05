import os
from flask import current_app, g
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/studyway")

def get_db():
    """Get the MongoDB client and database"""
    if 'mongo_client' not in g:
        g.mongo_client = MongoClient(MONGO_URI)
        g.db = g.mongo_client.get_default_database()
    return g.db

def close_db(e=None):
    """Close the MongoDB connection"""
    client = g.pop('mongo_client', None)
    if client is not None:
        client.close()

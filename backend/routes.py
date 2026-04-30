from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

@app.route("/health", methods=["GET"])
def health():
    return {"status": "OK"}, 200

@app.route("/count", methods=["GET"])
def count():
    """return length of data"""
    count = db.songs.count_documents({})
    return {"count": count}, 200

@app.route("/song", methods=["GET"])
def songs():
    """Return a list of all songs"""
    # Fetch all documents from the songs collection
    songs_cursor = db.songs.find({})
    
    # Format the data into a list and return with a 200 OK status
    return {"songs": parse_json(songs_cursor)}, 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Return a song by its id"""
    # Use PyMongo's find_one method to search for a document where "id" matches the requested id
    song = db.songs.find_one({"id": id})
    
    # If the database returns nothing, send a 404 Not Found error
    if not song:
        return {"message": "song with id not found"}, 404
        
    # If the song is found, parse it to JSON and return with a 200 OK status
    return parse_json(song), 200

@app.route("/song", methods=["POST"])
def create_song():
    """Create a new song"""
    # Extract the song data from the request body
    song = request.get_json()

    # Check if a song with the id already exists in the database
    existing_song = db.songs.find_one({"id": song["id"]})
    
    if existing_song:
        # If it exists, return a 302 HTTP status with the required message
        return {"Message": f"song with id {song['id']} already present"}, 302

    # If it does not exist, insert it into the database
    insert_result = db.songs.insert_one(song)

    # Return the inserted id and a 201 Created HTTP status
    return {"inserted id": {"$oid": str(insert_result.inserted_id)}}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update a song in the database"""
    # Extract the song data from the request body
    song_in = request.get_json()

    # Find the song in the database using find_one
    song = db.songs.find_one({"id": id})
    
    # If the song does not exist, send back a status of 404
    if not song:
        return {"message": "song not found"}, 404

    # If the song exists, update it with the incoming request data
    result = db.songs.update_one({"id": id}, {"$set": song_in})

    # If the song was found but the data sent is exactly the same, return a specific message
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}, 200

    # Return the updated song as JSON and a 200 OK status
    updated_song = db.songs.find_one({"id": id})
    return parse_json(updated_song), 200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song from the database"""
    # Attempt to delete the song using PyMongo's delete_one method
    result = db.songs.delete_one({"id": id})
    
    # If no document was deleted, the song doesn't exist
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
        
    # If successful, return an empty body with a 204 No Content status
    return "", 204

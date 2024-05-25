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

######################################################################
# INSERT CODE HERE

@app.route('/health')
def health():
    """Check status API endpoint """
    return jsonify(dict(status="OK")), 200

@app.route('/count')
def count():
    """Count data """
    if not songs_list:
        return jsonify(message="Internal Error!")
    return jsonify(count=len(songs_list)), 200

@app.route('/song')
def songs_list():
    try:
        songs = db.songs.find()
        song_list = []
        for s in songs:
            s['_id'] = {'$oid': str(s['_id'])} 
            song_list.append(s)
        
        # print(song_list)
        return jsonify(songs=song_list), 200
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred while fetching songs"}), 500

@app.route('/song/<int:id>')
def get_song_by_id(id):
    try: 
        song = db.songs.find_one({"id": int(id)})
        if song:
            song['_id'] = {"$oid": str(song['_id'])}
            return jsonify(song), 200
        else:
            return jsonify(message="song with id not found"), 404
    except NameError:
        return jsonify(message="Internal Error"), 500

# def post_song_duplicate(song):
#     # Implement your logic to check for duplicates
#     songs = db.songs.find()
#     for existing_song in songs:
#         if existing_song["id"] == song["id"]: 
#             return {'Message': f"picture with id {song['id']} already present"}, 302
#     return None


@app.route('/song', methods=["POST"])
def create_song():
    try:
        song = request.json
        if not song or 'id' not in song:
            return jsonify(message="Invalid song id"), 422
        
        id_exist = db.songs.find_one({"id": song["id"]})
        if id_exist:
            return jsonify(message=f"Song with id {song['id']} already present"), 302

        new_song = db.songs.insert_one(song)
        if new_song.inserted_id:
            response = {
                "inserted id": {
                    "$oid": str(new_song.inserted_id)
                }
            }
            return jsonify(response), 201
        else:
            return jsonify(message="Failed to insert song into database"), 500
    except NameError:
        return {"message": "An error occurred while processing the request"}, 500


@app.route('/song/<int:id>', methods=["PUT"])
def update_song(id):
    """Update song"""
    song = db.songs.find_one({"id": id})
    input_song = request.json
    if not song:
        return jsonify(message="song not found"), 404
    
    if all(song.get(key) == value for key, value in input_song.items()):
        return jsonify(message="song found, but nothing updated"), 200

    try:
        # Update song
        db.songs.update_one({"id": id}, {"$set": input_song})

        # Retrieve the updated song
        updated_song = db.songs.find_one({"id": id})
        updated_song['_id'] = {"$oid": str(updated_song['_id'])}
        return jsonify(updated_song), 201

    except NameError:
        # Handle server error
        return jsonify(message="Internal error!"), 500

@app.route('/song/<int:id>', methods=["DELETE"])
def delete_song(id):
    """Delete a song by id"""
    try:
        song = db.songs.delete_one({"id": id})
        if song.deleted_count == 1:
            return jsonify(message="song is deleted"), 204
        else:
            return jsonify(message="song not found"), 404
    except NameError:
        return jsonify(message="Internal error"), 500

   
######################################################################

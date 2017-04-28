from flask import Flask, request, jsonify
from google.appengine.ext import ndb
import json
app = Flask(__name__)

class Boat(ndb.Model):
    name = ndb.StringProperty(required=True)
    type = ndb.StringProperty()
    length = ndb.IntegerProperty()
    at_sea = ndb.BooleanProperty()

    def to_dict(self):
        result = super(Boat, self).to_dict()
        result['id'] = self.key.urlsafe()
        return result

@app.route('/boat/<id>', methods=['GET'])
def get_boat(id):
    return jsonify(Boat.query().to_dict())

@app.route('/boat', methods=['POST', 'GET'])
def create_boat():
    if request.method == 'POST':
        json_boat = request.get_json()

        new_boat = Boat()
        new_boat.name = json_boat['name']
        new_boat.type = json_boat['type']
        new_boat.length = json_boat['length']
        new_boat.at_sea = json_boat['at_sea']
        new_boat_key = new_boat.put()

        return jsonify(new_boat_key.get().to_dict())

    if request.method == 'GET':
        boats = Boat.query()

        return jsonify([boat.to_dict() for boat in boats])


if __name__ == '__main__':
    app.run()

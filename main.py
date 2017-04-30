from flask import Flask, request, jsonify
from google.appengine.ext import ndb

app = Flask(__name__)
app.config['DEBUG'] = True

# This is from the Flask guide on Error Handling http://flask.pocoo.org/docs/0.12/patterns/apierrors/
class InvalidUsage(Exception):
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

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response, 400

# Models
class Boat(ndb.Model):
    name = ndb.StringProperty(required=True)
    type = ndb.StringProperty()
    length = ndb.IntegerProperty()
    at_sea = ndb.BooleanProperty()

    def to_dict(self):
        result = super(Boat, self).to_dict()
        result['id'] = self.key.urlsafe()
        return result

class Slip(ndb.Model):
    number = ndb.IntegerProperty(required=True)
    current_boat = ndb.StringProperty(default=None)
    arrival_date = ndb.StringProperty(default=None)
    departure_history = ndb.DateProperty(default=None, repeated=True)


    def to_dict(self):
        result = super(Slip, self).to_dict()
        result['id'] = self.key.urlsafe()
        return result

# Routes
@app.route('/boat/<id>', methods=['GET', 'PATCH', 'DELETE'])
def get_boat(id):
    try:
        boat = ndb.Key(urlsafe=id)
    except TypeError:
        raise InvalidUsage('Invalid data type, only strings allowed for Boat ID\'s', status_code=400)
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise InvalidUsage('Invalid Boat ID', status_code=400)
        else:
            raise

    if boat.kind() != 'Boat':
        raise InvalidUsage('Only Boats can be modified at this endpoint.', status_code=400)

    if boat.get() == None:
        return jsonify({'error': 'not found'}), 404

    if request.method == 'GET':
        return jsonify(boat.get().to_dict())

    if request.method == 'PATCH':
        json_boat = request.get_json()
        boat = boat.get()
        for key, value in json_boat.iteritems():
            if key in boat.to_dict():
                setattr(boat, key, value)

        return jsonify(boat.put().get().to_dict())

    if request.method == 'DELETE':
        boat.delete()
        return "No Content", 204


@app.route('/boat', methods=['POST', 'GET'], strict_slashes=False)
def boat_handler():
    if request.method == 'POST':
        json_boat = request.get_json()

        new_boat = Boat()
        new_boat.name = json_boat.get('name', None)
        new_boat.type = json_boat.get('type', None)
        new_boat.length = json_boat.get('length', None)
        new_boat.at_sea = True
        new_boat.put()

        return jsonify(new_boat.to_dict())

    if request.method == 'GET':
        boats = Boat.query()

        return jsonify([boat.to_dict() for boat in boats])

@app.route('/slip/<id>', methods=['GET', 'PATCH', 'DELETE'])
def get_slip(id):


    pass

@app.route('/slip', methods=['GET', 'POST'], strict_slashes=False)
def slip_handler():

    if request.method == 'GET':
        slips = Slip.query()
        return jsonify([slip.to_dict() for slip in slips])

    if request.method == 'POST':
        json_slip = request.get_json()

        if 'number' not in json_slip or json_slip.get('number') == None:
            raise InvalidUsage('A name is required for creating a slip', status_code=400)

        new_slip = Slip()
        new_slip.number = json_slip.get('number')
        new_slip.current_boat = None
        new_slip.arrival_date = None
        new_slip.departure_history = []

        new_slip.put()
        return jsonify(new_slip.to_dict())

if __name__ == '__main__':
    app.run()

from flask import Flask, request, jsonify
from google.appengine.ext import ndb
from flask_restful import Resource, Api, reqparse
import datetime

errors = {
    'InvalidBoatID': {
        'message': 'Invalid Boat ID provided',
        'status': 400
    },
    'InvalidSlipID': {
        'message': 'Invalid Slip ID provided',
        'status': 400
    }
}

app = Flask(__name__)
api = Api(app, errors=errors)

boat_post_parser = reqparse.RequestParser(bundle_errors=True)
boat_post_parser.add_argument('name', type=str, help='Missing: {error_msg}', required=True)
boat_post_parser.add_argument('type', type=str)
boat_post_parser.add_argument('length', type=int)
boat_post_parser.add_argument('at_sea', type=bool)

boat_patch_parser = boat_post_parser.copy()
boat_patch_parser.replace_argument('name', type=str, required=False)

slip_post_parser = reqparse.RequestParser(bundle_errors=True)
slip_post_parser.add_argument('number', type=int, help="Missing: {error_msg}", required=True)
slip_post_parser.add_argument('current_boat', type=str)
slip_post_parser.add_argument('arrival_date', type=str)
slip_post_parser.add_argument('departure_history', type=list)

slip_patch_parser = slip_post_parser.copy()
slip_patch_parser.replace_argument('number', type=int, required=False)

slip_arrive_parser = reqparse.RequestParser(bundle_errors=True)
slip_arrive_parser.add_argument('boat_id', type=str, help='Missing: {error_msg}', required=True)


# This is from the Flask guide on Error Handling http://flask.pocoo.org/docs/0.12/patterns/apierrors/
class InvalidBoatID(Exception):
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


class InvalidSlipID(Exception):
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


def boat_id_validator(id):
    try:
        boat = ndb.Key(urlsafe=id)
    except TypeError:
        raise InvalidBoatID('Invalid data type, only strings allowed for Boat ID\'s', status_code=400)
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise InvalidBoatID('Invalid Boat ID', status_code=400)
        else:
            raise

    if boat.kind() != 'Boat':
        raise InvalidBoatID('Only Boats can be modified at this endpoint.', status_code=400)
    return boat


def slip_id_validator(id):
    try:
        slip = ndb.Key(urlsafe=id)
    except TypeError:
        raise InvalidSlipID('Invalid data type, only strings allowed for Slip ID\'s', status_code=400)
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise InvalidSlipID('Invalid Boat ID', status_code=400)
        else:
            raise

    if slip.kind() != 'Slip':
        raise InvalidSlipID('Only Slips can be modified at this endpoint.', status_code=400)
    return slip


# Models
class Departures(ndb.Model):
    departure_date = ndb.StringProperty()
    departed_boat = ndb.StringProperty()


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
    departure_history = ndb.StructuredProperty(Departures, default=None, repeated=True)


    def to_dict(self):
        result = super(Slip, self).to_dict()
        result['id'] = self.key.urlsafe()
        return result


# Routes
class BoatListHandler(Resource):
    def get(self):
        boats = Boat.query()
        return jsonify([boat.to_dict() for boat in boats])

    def post(self):
        args = boat_post_parser.parse_args()

        new_boat = Boat()
        new_boat.name = args.get('name', None)
        new_boat.type = args.get('type', None)
        new_boat.length = args.get('length', None)
        new_boat.at_sea = True
        new_boat.put()

        return jsonify(new_boat.to_dict())


class BoatHandler(Resource):
    def get(self, id):
        boat = boat_id_validator(id)
        return jsonify(boat.get().to_dict())

    def patch(self, id):
        boat_patch_parser.parse_args()
        json_args = request.get_json()
        boat = boat_id_validator(id)
        boat = boat.get()

        if boat is None:
            return {'error': 'Boat not found'}, 404

        for key, value in json_args.iteritems():
            if key == "at_sea":
                continue
            if key in boat.to_dict() and value != boat.to_dict().get(key):
                setattr(boat, key, value)

        boat = boat.put()
        return jsonify(boat.get().to_dict())

    def delete(self, id):
        boat = boat_id_validator(id)
        if boat.get() == None:
            return {"error": "Not Found"}, 404
        else:
            boat.delete()
            return {"message": "No Content"}, 204


class SlipListHandler(Resource):
    def get(self):
        slips = Slip.query().order(Slip.number)
        return jsonify([slip.to_dict() for slip in slips])

    def post(self):
        args = slip_post_parser.parse_args()

        if Slip.query(Slip.number == args.number).get() is not None:
            return {'error': 'A slip with that number already exists'}, 403

        new_slip = Slip()
        new_slip.number = args.get('number')
        new_slip.current_boat = None
        new_slip.arrival_date = None
        new_slip.departure_history = []

        new_slip.put()
        return jsonify(new_slip.to_dict())


class SlipHandler(Resource):
    def get(self, id):
        slip_key = slip_id_validator(id)
        slip = Slip.query(Slip.key == slip_key).get()
        if slip is not None:
            return jsonify(slip.to_dict())
        else:
            return {"error": "Not Found"}, 404

    def patch(self, id):
        slip = slip_id_validator(id)
        slip = slip.get()
        slip_patch_parser.parse_args()
        json_args = request.get_json()

        if slip is None:
            return {"error": "Slip not found"}, 404

        if Slip.query(Slip.number == json_args.get('number')).get() is not None:
            return {'error': 'A slip with that number already exists'}, 403

        for key, value in json_args.iteritems():
            if key in slip.to_dict() and value != slip.to_dict().get(key):
                setattr(slip, key, value)

        return jsonify(slip.put().get().to_dict())

    def delete(self, id):
        slip = slip_id_validator(id)
        if slip.get() is None:
            return {"error": "Not Found"}, 404
        else:
            slip.delete()
            return {"message": "No Content"}, 204


class SlipBoatHandler(Resource):
    def post(self, id):
        slip = slip_id_validator(id)
        slip = slip.get()
        slip_arrive_parser.parse_args()

        json_args = request.get_json()

        boat = boat_id_validator(json_args['boat_id'])
        boat = boat.get()

        if boat is None:
            return {'error': 'Boat does not exist'}, 400

        if slip is None:
            return {'error': 'Slip does not exist'}, 404

        if slip.current_boat is not None:
            return {'error': 'Slip currently occupied'}, 403

        boat.at_sea = False

        slip.current_boat = json_args['boat_id']
        slip.arrival_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        boat.put()
        slip.put()
        return jsonify(slip.to_dict())

    def delete(self, id):
        slip = slip_id_validator(id)
        slip = slip.get()

        if slip is None:
            return {'error': 'Slip does not exist'}, 404

        if slip.current_boat is None:
            return {'error': 'Slip does not have a boat'}, 400

        boat = boat_id_validator(slip.current_boat)
        boat = boat.get()
        boat.at_sea = True
        boat.put()

        slip.departure_history.append(
            Departures(departure_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       departed_boat=slip.current_boat)
        )
        slip.current_boat = None
        slip.put()

        return {'message': 'No Content'}, 204

api.add_resource(SlipBoatHandler, '/slip/<string:id>/boat', strict_slashes=False)
api.add_resource(BoatHandler, '/boat/<string:id>', strict_slashes=False)
api.add_resource(SlipHandler, '/slip/<string:id>', strict_slashes=False)
api.add_resource(BoatListHandler, '/boat', strict_slashes=False)
api.add_resource(SlipListHandler, '/slip', strict_slashes=False)

if __name__ == '__main__':
    app.run()

from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from api import db
from psycopg2.extras import RealDictCursor
from api.extensions import issue_token
from api.extensions import requires_auth
from api import maps

search_bp = Blueprint('search_bp', __name__)
search_api = Api(search_bp)

class RidesResource(Resource):
    @requires_auth
    def get(self):
        c = db.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM users WHERE cppemail = %s", (request.email,))
        # check if we got a result
        user = c.fetchone();
        if user is None:
            return 'User does not exist', 404

        # load all other users
        c.execute("SELECT * FROM users WHERE cppemail != %s AND verified = true AND profilecomplete = true AND addressline1 IS NOT NULL and city IS NOT NULL and zip IS NOT NULL", (request.email,))
        rows = c.fetchall()

        if len(rows) == 0:
            return jsonify(results=[])

        for row in rows:
            del row['passhash']
            del row['salt']

        sortedResults = maps.sortByDist(user, rows)
        sortedUsers = []
        for res in sortedResults:
            print res
            # if distance is negative, pass
            if res[1] < 0:
                continue

            res[0]['dist'] = res[1]
            del res[0]['addressline1']
            del res[0]['addressline2']
            sortedUsers.append(res[0])

        for user in sortedUsers:
            # fetch reviews
            c.execute("SELECT * FROM reviews WHERE reviewee_userid = %s", (user['id'],))
            reviews = c.fetchall()
            reviewCount = len(reviews)
            stars = 0

            if reviewCount > 0:
                # compute average num of stars
                starsList = list(map(lambda r: r['stars'], reviews))
                stars = reduce(lambda sum, s: sum + s, starsList) / reviewCount

            # add on review count and avg stars
            user['reviewCount'] = reviewCount
            user['stars'] = stars

            # fetch schedule
            c.execute("SELECT * FROM schedule WHERE userid = %s ORDER BY dayofweek ASC", (user['id'],))
            scheduled_days = c.fetchall()

            user['schedule'] = [{'arrive': d['arrive'], 'depart': d['depart']} for d in scheduled_days]

        return jsonify(results=sortedUsers)

search_api.add_resource(RidesResource, '/')

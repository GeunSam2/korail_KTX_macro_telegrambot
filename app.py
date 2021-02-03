from flask import Flask
from flask_restful import Api
from flask_cors import CORS, cross_origin
from telegramBot import Index

app = Flask(__name__)
CORS(app)
api = Api(app)

api.add_resource(Index, '/<target_host>/')

if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0', port=8080, threaded=True)
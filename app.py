from flask import Flask
from flask_restful import Api
from flask_cors import CORS, cross_origin
from telegramBot import Index
from multiprocessing import Pool

application = Flask(__name__)
CORS(application)
api = Api(application)

api.add_resource(Index, '/telebot')

if __name__ == '__main__':
    
    context = ('./certs/fullchain.pem', './certs/privkey.pem')
    application.run(debug = True, host='0.0.0.0', port=8080, threaded=True, ssl_context=context)
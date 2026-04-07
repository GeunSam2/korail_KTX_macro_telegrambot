from flask import Flask
from flask_restful import Api
from flask_cors import CORS, cross_origin
from telegramBot import Index, CheckPayment
from multiprocessing import Pool

application = Flask(__name__)
CORS(application)
api = Api(application)

api.add_resource(Index, '/telebot')
api.add_resource(CheckPayment, '/check_payment')

if __name__ == '__main__':
    
    application.run(debug = True, host='0.0.0.0', port=8080, threaded=True)
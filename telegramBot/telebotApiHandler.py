from flask import Flask, request, jsonify, make_response
from flask_restful import marshal_with, Resource, reqparse, fields
import requests
import time
import base64
import json
import os

class Index(Resource):
    def get(self, target_host):
        print (request.data)
        
        return_json = {
            "status": "green"
        }
        return make_response(jsonify(return_json))
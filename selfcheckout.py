import sys

from flask import Flask, Response, request
import requests 
import json

from settings import *


LOAN_XML = """<?xml version='1.0' encoding='UTF-8'?>
  <item_loan>
    <circ_desk>{}</circ_desk>
    <library>{}</library>
  </item_loan>
""".format(CIRC_DESK, LIB_NAME)


app = Flask(__name__)


@app.route('/')
def root():
    return app.send_static_file('self-check.html')


@app.route('/login/<userid>/<lastname>')
def login(userid, lastname):
    url = "{}/users/{}".format(API_URL, userid)
    params = {}
    params['apiKey'] = API_KEY
    params['expand'] = "loans,requests,fees"
    params['format'] = "json"
    response = requests.get(url, params=params)
    if response.json().get("last_name").lower() == lastname.lower():
        if response.status_code == 200:
            return Response(response, mimetype="application/json")
        else:
            return Response('Incorrect Login<br> Try Again', 500)
    else:
        return Response('Incorrect Login<br>Try Again', 401)


@app.route('/checkout/<userid>/<barcode>')
def loan(userid, barcode):
    # test to see if book is already checked out
    barcodeurl = "{}/items".format(API_URL)
    params = {'apiKey': API_KEY,
              'item_barcode': barcode,
              'format': 'json'}
    redirect = requests.get(barcodeurl, params=params, allow_redirects=True)
    url = redirect.url
    url, _ = url.split('?')
    url = '{}/loans'.format(url)

    # del params['item_barcode']
    loans_response = requests.get(url, params=params)
    already_checked_out = loans_response.json().get('item_loan', False)

    # error handling
    if already_checked_out:
        return Response('This item is already checked out', 409)
    if loans_response.status_code == 404:
        return Response('Error: Invalid Barcode', 404)

    # Checkout the item
    url = "{}/users/{}/loans".format(API_URL, userid)
    headers = {'Content-Type': 'application/xml', 'dataType': "xml"}
    response = requests.post(url, params=params, headers=headers, data=LOAN_XML)
    if response.status_code == 400 and "reference" in redirect.text.lower():
        return Response('Cannot Checkout: Reference Materials', 403)
    if response.status_code == 400 and "non-circulating" in redirect.text.lower():
        return Response('Cannot Checkout: Reserve Materials', 403)
    if response.status_code == 400 and "loan limit" in response.text.lower():
        return Response('Item cannot be loaned due to loan limit being reached', 411)
    return Response(response, mimetype="application/json")


if __name__ == "__main__":
    app.run()

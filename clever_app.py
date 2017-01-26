import os
import json
import base64
import requests

from urllib import urlencode

from flask import Flask, session, render_template, request, redirect, url_for

app = Flask(__name__)

CLEVER_API_BASE = 'https://api.clever.com'
CLIENT_ID = os.environ['CLEVER_CLIENT_ID']
CLIENT_SECRET = os.environ['CLEVER_CLIENT_SECRET']
TEST_DISTRICT_ID = '588910be5e56c4000146fc87'

# Production conditional logic
if os.environ.get('PRODUCTION') == "TRUE":
    REDIRECT_URI = 'https://cleverinstantlogin.herokuapp.com/redirect'
else:
    REDIRECT_URI = 'http://localhost:8000/redirect'

@app.route('/')
def index():
    # If the user is in the session we consider them authenticated
    if session.get('user'):
        redirect(url_for('home'))

    encoded = urlencode({
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'district_id': TEST_DISTRICT_ID,
        'client_id': CLIENT_ID,
        'scope': 'read:user_id read:sis'
    })

    redirect_url = 'https://clever.com/oauth/authorize?{}'.format(encoded)

    return render_template(
        'index.html',
        redirect_url=redirect_url
    )

@app.route('/redirect')
def oauth_redirect():
    code = request.args.get('code')

    payload = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI
    }

    headers = {
        'Authorization': 'Basic {b64string}'.format(b64string=base64.b64encode(CLIENT_ID + ':' + CLIENT_SECRET)),
        'Content-Type': 'application/json',
    }

    response = requests.post('https://clever.com/oauth/tokens', data=json.dumps(payload), headers=headers)
    if response.status_code != 200:
        return "An error occurred with your login. Please try again."
    else:
        response_obj = response.json()
    token = response_obj['access_token']

    bearer_headers = {
        'Authorization': 'Bearer {token}'.format(token=token)
    }

    api_response = requests.get(CLEVER_API_BASE + '/me', headers=bearer_headers)
    if api_response.status_code != 200:
        return "An error occurred trying to retrieve your information. Please try again."

    else:
        api_response_obj = api_response.json()
        session['user'] = api_response_obj['data'].get('id', None)
        session['data'] = json.dumps(api_response_obj['data'])

        return redirect(url_for('home'))


@app.route('/home')
def home():
    # If the user is in the session we display the app
    if session.get('user'):
        data = json.loads(session.get('data'))
        return render_template(
            'home.html',
            data=data
        )
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()

app.secret_key = os.environ['CLEVER_APP_SECRET_KEY']
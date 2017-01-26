# Building your first application with Clever Instant Login

Clever’s Instant Login is the simplest and fastest way to integrate your application with thousands of school districts across the country. Instant Login leverages a district’s existing identity systems to provide seamless access to your application, easing the burden on students and teachers so that more classroom time can be spent learning. In this post, you’ll be guided through building a simple web application that allows students and teachers to login and view their own information through the Clever API. 

## Getting Started

Before we get started here are a few useful references as you build your application.
- [Clever API Reference](https://clever.com/developers/docs/explorer#api_identity)
- [Getting Started with OAuth](https://oauth.net/getting-started/)
- [Flask Web framework](flask.pocoo.org)
- [Sample Application Framework zip file](https://www.dropbox.com/s/jnd70u9szr15mu7/clever_app.zip?dl=0)
- [Completed Sample Application](https://github.com/grantt/clever_app)

Also, if you haven’t already, please register as a Clever developer in order to get your application credentials. You can do this by following these simple steps:

1. Navigate to https://apps.clever.com/signup
2. Fill out your personal and application information and agree to our terms of service
3. Click the ‘Sign up’ button

Once you have signed in as a developer, you’ll be redirect to your dashboard where you can access your application settings as well as a sandbox district set up for you to test against. This sandbox district is prepopulated with users for your application, making it easy to test your development work against simulated data. If you have sample data from a particular school district that you would prefer to work with, you can do so by following this [tutorial](https://dev.clever.com/guides/creating-district-sandboxes).

## Understanding the Application

Our application will focus on simply accepting login requests from students and teachers and displaying the response from the  `/me` endpoint. Instant Login authentication is negotiated via the OAuth 2.0 standard which allows for a user to authorize your application to use an access token in order to make requests to Clever’s API on the user’s behalf. Your application is registered with clever via an ID and secret key that uniquely identity it to Clever. The basic OAuth handshake looks like this:

1. A user launches your application from a student or teacher dashboard or from your website (for this example we will assume your app is launched via a web link) and the application makes a request to authorize with Clever and provides its client ID, the scope of services it wishes to access, and a redirect URI.
2. Clever redirects the user (prompting them to log in if they are not) to your redirect URI and provides an exchange token code in the request query string.
3. Your application submits a `POST` request to Clever with the provided code and [basic auth](https://en.wikipedia.org/wiki/Basic_access_authentication) encoded client id and client secret.
4. Clever validates your request and responds with an access token that may be included in the authorization headers for all further requests to the Clever API.

The application you’ll build today demonstrates all aspects of the OAuth handshake, a user will click a link to log in, be prompted for their credentials, redirected to a new URL in your app, authenticated with Clever, and finally redirected to the home page of your app where an API request to the `/me` endpoint will be made on their behalf.

## Building the Application

We’ll be using Python 2.7 and the Flask micro-framework for this example but all the lessons are applicable to whichever language or tools you choose for your web application. Flask just provides a lightweight set of tools that allow for simple processing of web requests and easy templating.

To get started, unpack the zip file of the Sample App Framework into a directory of your choice. Next, open your terminal, navigate to the app directory, and install the Python package requirements with `pip install -r requirements.txt`.

The main contents of the application are stored in `clever_app.py` so let’s start there. You’ll see some imported packages, several constants referencing environment variables, and three routed views, the login page `/`, the redirect URI `/redirect`, and the home page of the app `/home`. 

To set up your application to be specific to your own developer account, you’ll set the following environment variables:

- CLEVER_CLIENT_ID
- CLEVER_CLIENT_SECRET
- CLEVER_APP_SECRET_KEY

The first two variables are accessible in the [Applications section](https://apps.clever.com/applications) of your developer dashboard by selecting your app from the list. Please note that the client secret is sensitive information and should never be publicly posted or checked into your version control software. The final variable is simply a string utilized for Flask’s session object, use a secret key of your choice.

Next, you can add in the ID of your test district, found in your sandbox district’s Info section on the developer dashboard. The addition of this ID bypasses Clever’s district picker when a user is prompted for login and streamlines this tutorial. In production you’ll want to omit this if your app is accessed by multiple districts.

With these variables set, you may now run the application locally, using the command `gunicorn clever_app:app` which will launch the app at `localhost:8000`.

Next we will build out the first steps of our OAuth handshake in the `index` view, submitting a request to authorize with Clever. This request is sent to `https://clever.com/oauth/authorize` with a set of parameters that identify your application, the scope of access your app requires, and the redirect URI for Clever to send a request back to. In this case, we’ve chosen the path `/redirect` for our redirect URI. Add this URI to your application’s Settings page in the *Redirect URLs* section (you’ll want to add the full path, `http://localhost:8000/redirect` or your own production URL if not testing locally). The scope of our application is simply `read:user_id read:sis` since  we are only working with the `/me` endpoint, your production application may have a broader scope. The information is url encoded and included in the request to Clever as a query string. Note the full code for this view below:

```python
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

    url = 'https://clever.com/oauth/authorize?{}'.format(encoded)

    return render_template(
        'index.html',
        url=url
    )
```

With our log in button working we can proceed to the next step, receiving the response from Clever and posting a request for an access token. First let’s handle the request from Clever by retrieving the exchange token from the code query parameter using 

```python
code = request.args.get('code')
``` 

Then we can build our authorization request with a payload containing the `code`, `grant_type`, and `redirect_uri`:

```python
payload = {
    'code': code,
    'grant_type': 'authorization_code',
    'redirect_uri': REDIRECT_URI
}
```

As well as basic auth request headers using the application’s client ID and secret. Be aware that we specify the `Content-Type` header as `application/json`, but the `auth/tokens` endpoint also accepts `application/x-www-form-urlencoded` for traditional `POST` bodies. Here are our headers:

```python
headers = {
    'Authorization': 'Basic {b64string}'.format(b64string=base64.b64encode(CLIENT_ID + ':' + CLIENT_SECRET)),
    'Content-Type': 'application/json',
}
```

Now we can make a `POST` request to `https://clever.com/oauth/tokens` to receive an access token in a successful response. Note that we check for the proper HTTP status code in the response to properly handle errors. For your application, you will want to make sure to handle invalid responses to ensure a quality user experience. 

```python
response = requests.post('https://clever.com/oauth/tokens', data=json.dumps(payload), headers=headers)
if response.status_code != 200:
    return "An error occurred with your login. Please try again."
else:
    response_obj = response.json()
token = response_obj['access_token']
``` 

With an access token received, we can use it in the request header to authenticate all future requests to Clever’s API.

```python
bearer_headers = {
    'Authorization': 'Bearer {token}'.format(token=token)
}
```

Let’s make a `GET` request to the `/me` endpoint, load the user data into the session if successful, and redirect to the app’s main page:

```python
api_response = requests.get(CLEVER_API_BASE + '/me', headers=bearer_headers)
if api_response.status_code != 200:
    return "An error occurred trying to retrieve your information. Please try again."

else:
    api_response_obj = api_response.json()
    session['user'] = api_response_obj['data'].get('id', None)
    session['data'] = json.dumps(api_response_obj['data'])

    return redirect(url_for('home'))
``` 

This completes our `/redirect` view, which should now look like this:

```python
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
```

That’s it! Now the application has an OAuth access token and can directly access the API on a user’s behalf. Your application even knows the details of your signed in user. Before you continue building your application, let’s test it and make sure it works smoothly and repeatably.

## Testing the Application
Clever provides two useful ways of testing your application, manually moving through the login flow using a generated user, or the automated testing provided on your developer dashboard. We recommend using both methods in order to test not only a wide variety of users, but to get a feel for how an individual would navigate your app.

To test using the full sandbox district user set, simply go to our [Instant Login Testing tool](https://apps.clever.com/dev-tools/instant-login-testing), select your sandbox district, and click the `Run Test` button. This will execute logins for each student and teacher in your sandbox district and show you the rate of success as well as allowing you to view status codes for individual failed attempts. 

To test using an individual user, you can navigate your application in a browser. Click the `Log in with Clever` link from your app’s main page, `http://localhost:8000/` and you’ll be prompted to log in as a Clever user. For our sandbox district, students and teachers are populated from the CSV in the Day 1 directory of [this zip file](https://dev.clever.com/archives/sandbox/cleverusd.zip). To log in as one of these users simply enter the student or teacher number listed in the CSV as a user’s username and password. After a valid login, you should be redirected to your application and you can confirm that the login flow works as expected.

## Conclusion

Congratulations! You’ve successfully integrated with Clever Instant Login. Now that you’ve got a sense for how OAuth and Clever’s Identity API work, you can explore the rest of our API and fully develop your application. Don’t forget to check out all the [resources](https://dev.clever.com/) Clever provides for our developers, and feel free to contact our [developer support](https://dev.clever.com/support/) for any specific questions not addressed by our documentation. Good luck and happy coding!
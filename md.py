from flask import Flask, escape, url_for
app =  Flask(__name__)

@app.route('/MD')
def homepage():
	return 'Welcome to Mobidetails!'

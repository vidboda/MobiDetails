from flask import Flask, escape, url_for, render_template
app =  Flask(__name__)

@app.route('/MD')
def homepage():
	#return 'Welcome to Mobidetails!'
	return render_template('homepage.html')

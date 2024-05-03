from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)




@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/teste')
def teste():
    return 'teste deu'

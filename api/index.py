from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'cristovao.portugalinteractivo.com'
app.config['MYSQL_USER'] = 'cristovao_bd'
app.config['MYSQL_PASSWORD'] = 'B6teCbBcemmw'
app.config['MYSQL_DB'] = 'cristovao_bd'

mysql = MySQL(app)


@app.route('/')
def home():
      # Exemplo de consulta ao banco de dados
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cliente")
    data = cur.fetchall()
    cur.close()
    return str(data)


@app.route('/about')
def about():
    return 'About'

@app.route('/teste')
def teste():
    return 'teste deu'

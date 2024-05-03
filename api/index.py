from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://p4:p4@localhost:15432/p4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização do SQLAlchemy
db = SQLAlchemy(app)


@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/teste')
def teste():
    try:
        # Esta operação é apenas uma verificação de conexão
        db.session.execute("SELECT 1")
        connection_message = "Conexão com o banco de dados estabelecida com sucesso!"
    except Exception as e:
        connection_message = f"Falha ao conectar ao banco de dados: {str(e)}"

    return connection_message

from flask import Flask, request, jsonify
import pymysql
import hashlib

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'cristovao.portugalinteractivo.com'
app.config['MYSQL_USER'] = 'cristovao_bd'
app.config['MYSQL_PASSWORD'] = 'B6teCbBcemmw'
app.config['MYSQL_DB'] = 'cristovao_bd'

# Inicialização da conexão com o banco de dados
conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB']
)


@app.route('/')
def home():
    # Exemplo de consulta ao banco de dados
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cliente")
    data = cursor.fetchall()
    cursor.close()
    return str(data)


@app.route('/about')
def about():
    return 'About'

@app.route('/teste')
def teste():
    return 'teste deu'


@app.route('/newuser', methods=['POST'])
def newuser():
    # Recebe o JSON com os dados do novo usuário
    user_data = request.json
    nome = user_data.get('nome')
    email = user_data.get('email')
    password = user_data.get('password')

    # Criptografa a senha em MD5
    encrypted_password = hashlib.md5(password.encode()).hexdigest()

    # Insere os dados do novo usuário na tabela Users
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Users (nome, email, password) VALUES (%s, %s, %s)", (nome, email, encrypted_password))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Usuário inserido com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir usuário: " + str(e)}), 500

    
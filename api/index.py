from flask import Flask, request, jsonify
from datetime import datetime
import pymysql
import hashlib
import random
import string




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

    # Gerar um token aleatório de 12 caracteres
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    # Criptografa a senha em MD5
    encrypted_password = hashlib.md5(password.encode()).hexdigest()

    # Criptografa o token em MD5
    encrypted_token = hashlib.md5(token.encode()).hexdigest()

    # Insere os dados do novo usuário na tabela Users
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Users (nome, email, password, token) VALUES (%s, %s, %s, %s)", (nome, email, encrypted_password, encrypted_token))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Usuário inserido com sucesso!", "token": token}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir usuário: " + str(e)}), 500


@app.route('/loginft', methods=['POST'])
def loginft():
    # Recebe o JSON com os dados de login
    login_data = request.json
    email = login_data.get('email')
    password = login_data.get('password')

    # Criptografa a senha em MD5
    encrypted_password = hashlib.md5(password.encode()).hexdigest()

    # Consulta o banco de dados para verificar as credenciais
    cursor = conn.cursor()
    cursor.execute("SELECT token, data_token FROM Users WHERE email = %s AND password = %s", (email, encrypted_password))
    user = cursor.fetchone()
    cursor.close()

    if user is None:
        return jsonify({"message": "Credenciais inválidas"}), 401

    token, data_token = user

    # Se o data_token estiver vazio, atualiza-o com a data atual
    if not data_token:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Users SET data_token = %s WHERE email = %s", (datetime.now(), email))
            conn.commit()
            cursor.close()
        except Exception as e:
            conn.rollback()
            cursor.close()
            return jsonify({"message": "Erro ao atualizar data_token: " + str(e)}), 500

    return jsonify({"token": token}), 200
    
    
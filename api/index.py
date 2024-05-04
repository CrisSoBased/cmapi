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
    """
    # Exemplo de consulta ao banco de dados
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cliente")
    data = cursor.fetchall()
    cursor.close()
    return str(data)
    """
    return 'tá ok'


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
        return jsonify({"message": "User inserido com sucesso!", "token": encrypted_token}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir user: " + str(e)}), 500


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


@app.route('/newproject', methods=['POST'])
def newproject():
    # Recebe o JSON com o nome do projeto
    project_data = request.json
    nome_projeto = project_data.get('nome')

    # Insere o novo projeto na tabela Projects
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Projects (nome) VALUES (%s)", (nome_projeto,))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Projeto inserido com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir projeto: " + str(e)}), 500
    

@app.route('/removeproject', methods=['POST'])
def removeproject():
    # Recebe o JSON com o ID único do projeto
    project_data = request.json
    unique_id = project_data.get('UniqueID')

    # Remove o projeto da tabela Projects
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Projects WHERE UniqueID = %s", (unique_id,))
        conn.commit()
        if cursor.rowcount > 0:
            cursor.close()
            return jsonify({"message": "Projeto removido com sucesso!"}), 200
        else:
            cursor.close()
            return jsonify({"message": "Nenhum projeto encontrado com o ID fornecido"}), 404
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao remover projeto: " + str(e)}), 500


@app.route('/editarproject', methods=['POST'])
def editarproject():
    # Recebe o JSON com os dados do projeto a ser editado
    project_data = request.json
    unique_id = project_data.get('UniqueID')
    novo_nome = project_data.get('nome')
    nova_data_ini = datetime.strptime(project_data.get('data_ini'), '%Y-%m-%d').date()
    nova_descricao = project_data.get('descricao')

    # Atualiza os dados do projeto na tabela Projects
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Projects SET nome = %s, data_ini = %s, descricao = %s WHERE UniqueID = %s", 
                       (novo_nome, nova_data_ini, nova_descricao, unique_id))
        conn.commit()
        if cursor.rowcount > 0:
            cursor.close()
            return jsonify({"message": "Projeto atualizado com sucesso!"}), 200
        else:
            cursor.close()
            return jsonify({"message": "Nenhum projeto encontrado com o ID fornecido"}), 404
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao atualizar projeto: " + str(e)}), 500
    

@app.route('/removeruser', methods=['POST'])
def removeruser():
    # Recebe o JSON com o ID único do usuário a ser removido
    data = request.json
    unique_id = data.get('UniqueID')

    # Remove o usuário com o ID único especificado
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Users WHERE UniqueID = %s", (unique_id,))
        conn.commit()
        cursor.close()
        return jsonify({"message": "User removido com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao remover user: " + str(e)}), 500


@app.route('/alteraruser', methods=['POST'])
def alteraruser():
    # Recebe o JSON com os dados do user a serem atualizados
    data = request.json
    unique_id = data.get('UniqueID')
    nome = data.get('nome')
    email = data.get('email')
    password = data.get('password')

    # Criptografa a senha em MD5
    encrypted_password = hashlib.md5(password.encode()).hexdigest()

    # Verifica se o novo email já existe com um ID diferente
    cursor = conn.cursor()
    cursor.execute("SELECT UniqueID FROM Users WHERE email = %s AND UniqueID != %s", (email, unique_id))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        return jsonify({"message": "Erro ao atualizar user: email já está em uso por outro user"}), 400

    # Atualiza os dados do usuário na tabela Users
    try:
        cursor.execute("UPDATE Users SET nome = %s, email = %s, password = %s WHERE UniqueID = %s", (nome, email, encrypted_password, unique_id))
        conn.commit()
        cursor.close()
        return jsonify({"message": "User atualizado com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao atualizar user: " + str(e)}), 500
    
    
@app.route('/associargestorprojeto', methods=['POST'])
def associargestorprojeto():
    # Recebe o JSON com os dados do projeto e do novo gestor
    data = request.json
    unique_id = data.get('UniqueID')
    id_gestor = data.get('id_gestor')

    # Verifica se o projeto com o UniqueID especificado existe
    cursor = conn.cursor()
    cursor.execute("SELECT UniqueID FROM Projects WHERE UniqueID = %s", (unique_id,))
    project_exists = cursor.fetchone()

    if not project_exists:
        cursor.close()
        return jsonify({"message": "Erro ao associar gestor ao projeto: projeto não encontrado"}), 404

    # Atualiza o id_gestor para o projeto com o UniqueID especificado
    try:
        cursor.execute("UPDATE Projects SET id_gestor = %s WHERE UniqueID = %s", (id_gestor, unique_id))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Gestor associado ao projeto com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao associar gestor ao projeto: " + str(e)}), 500
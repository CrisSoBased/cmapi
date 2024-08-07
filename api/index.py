from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pymysql
import hashlib
import random
import string
import jwt




app = Flask(__name__)

app.config['MYSQL_HOST'] = 'cristovao.portugalinteractivo.com'
app.config['MYSQL_USER'] = 'cristovao_bd'
app.config['MYSQL_PASSWORD'] = 'B6teCbBcemmw'
app.config['MYSQL_DB'] = 'cristovao_bd'
app.config['SECRET_KEY'] = 'your_secret_key'


# Inicialização da conexão com o banco de dados
conn = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB']
)

#commit
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
        return jsonify({"message": "User inserido com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir user: " + str(e) + "nome : " + nome + "email : " + email + "pass: " + password}), 500


@app.route('/loginft', methods=['POST'])
def loginft():
    login_data = request.json
    email = login_data.get('email')
    password = login_data.get('password')

    print("Received login data:", login_data)
    print("Email:", email)
    print("Password:", password)

    # Encrypt the password
    encrypted_password = hashlib.md5(password.encode()).hexdigest()
    print("Encrypted password:", encrypted_password)

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID, email FROM Users WHERE email = %s AND password = %s", (email, encrypted_password))
        user = cursor.fetchone()
        print("User fetched from DB:", user)
    except Exception as e:
        print("Database error:", str(e))
        return jsonify({"message": "Internal server error"}), 500
    finally:
        cursor.close()

    if user is None:
        print("Invalid credentials")
        return jsonify({"message": "Credenciais inválidas"}), 401

    unique_id, email = user

    try:
        secret_key = app.config['SECRET_KEY']
        print("Secret key type:", type(secret_key))  # Ensure it's a string
        token = jwt.encode(
            {
                'user_id': unique_id,
                'exp': datetime.utcnow() + timedelta(hours=24)  # Token válido por 24 horas
            },
            secret_key,
            algorithm='HS256'
        )
        print("Generated token:", token)
    except Exception as e:
        print("JWT encoding error:", str(e))
        return jsonify({"message": "Token generation error"}), 500

    return jsonify({"token": token}), 200

def token_required(f):
    def decorator(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({"message": "Token é necessário!"}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE UniqueID = %s", (data['user_id'],))
            current_user = cursor.fetchone()
            cursor.close()
        except Exception as e:
            return jsonify({"message": "Token é inválido!"}), 401

        return f(current_user, *args, **kwargs)

    decorator.__name__ = f.__name__
    return decorator

@app.route('/newproject', methods=['POST'])
@token_required
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
@token_required
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
@token_required
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
@token_required
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
@token_required
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
@token_required
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
    
    
@app.route('/newtarefa', methods=['POST'])
@token_required
def newtarefa():
    # Recebe o JSON com os dados da nova tarefa
    data = request.json
    nome = data.get('nome')
    id_projeto = data.get('id_projeto')

    # Insere a nova tarefa na tabela Tasks
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Tasks (nome, id_projeto) VALUES (%s, %s)", (nome, id_projeto))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Nova tarefa inserida com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir nova tarefa: " + str(e)}), 500


@app.route('/associarutilizadortarefa', methods=['POST'])
@token_required
def associarutilizadortarefa():
    # Recebe o JSON com os IDs do utilizador e da tarefa
    data = request.json
    id_utilizador = data.get('id_utilizador')
    id_task = data.get('id_task')

    # Insere a associação na tabela usertask
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usertask (id_utilizador, id_task) VALUES (%s, %s)", (id_utilizador, id_task))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Associação de utilizador e tarefa inserida com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir associação de utilizador e tarefa: " + str(e)}), 500


@app.route('/gettarefasprojeto', methods=['POST'])
@token_required
def gettarefasprojeto():
    # Recebe o JSON com o ID do projeto
    data = request.json
    id_projeto = data.get('id_projeto')

    # Seleciona as tarefas do projeto especificado
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID, nome, concluir FROM Tasks WHERE id_projeto = %s", (id_projeto,))
        tarefas = cursor.fetchall()
        cursor.close()

        # Prepara os resultados para retorno
        tarefas_info = []
        for tarefa in tarefas:
            tarefa_info = {
                "UniqueID": tarefa[0],
                "nome": tarefa[1],
                "concluir": tarefa[2]
            }
            tarefas_info.append(tarefa_info)

        return jsonify({"tarefas": tarefas_info}), 200
    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao obter tarefas do projeto: " + str(e)}), 500
    

@app.route('/updutlizadoresprojeto', methods=['POST'])
@token_required
def updutlizadoresprojeto():
    # Recebe o JSON com o ID do projeto
    data = request.json
    id_projeto = data.get('id_projeto')

    # Busca os UniqueID das tarefas associadas ao projeto
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID FROM Tasks WHERE id_projeto = %s", (id_projeto,))
        tarefas = cursor.fetchall()
        task_ids = [str(tarefa[0]) for tarefa in tarefas]  # Lista de UniqueIDs das tarefas
        cursor.close()

        # Busca os id_utilizador correspondentes às tarefas encontradas
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT id_utilizador FROM usertask WHERE id_task IN %s", (task_ids,))
        users = cursor.fetchall()
        user_ids = [str(user[0]) for user in users]  # Lista de id_utilizador sem repetição
        cursor.close()

        # Formata os id_utilizador como string separada por vírgulas
        id_utilizadores_str = ','.join(user_ids)

        # Atualiza o atributo id_utilizadores na tabela Projects
        cursor = conn.cursor()
        cursor.execute("UPDATE Projects SET id_utilizadores = %s WHERE UniqueID = %s", (id_utilizadores_str, id_projeto))
        conn.commit()
        cursor.close()

        return jsonify({"message": "ID dos utilizadores atualizado com sucesso para o projeto"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao atualizar ID dos utilizadores para o projeto: " + str(e)}), 500


@app.route('/concluirprojeto', methods=['POST'])
@token_required
def concluirprojeto():
    # Recebe o JSON com o ID do projeto
    data = request.json
    id_projeto = data.get('id_projeto')

    # Busca os id_utilizadores associados ao projeto
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_utilizadores FROM Projects WHERE UniqueID = %s", (id_projeto,))
        id_utilizadores_str = cursor.fetchone()[0]  # Obtem a string de id_utilizadores
        cursor.close()

        # Transforma a string de id_utilizadores em uma lista de inteiros
        id_utilizadores = [int(id_user) for id_user in id_utilizadores_str.split(',')]

        # Insere na tabela avaliacao para cada id_utilizador do projeto
        cursor = conn.cursor()
        for id_user in id_utilizadores:
            cursor.execute("INSERT INTO avaliacao (id_utilizador, id_projeto) VALUES (%s, %s)", (id_user, id_projeto))
        conn.commit()
        cursor.close()

        # Atualiza o projeto para concluir
        cursor = conn.cursor()
        cursor.execute("UPDATE Projects SET concluir = 1 WHERE UniqueID = %s", (id_projeto,))
        conn.commit()
        cursor.close()

        return jsonify({"message": "Projeto concluído e avaliações inseridas com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao concluir projeto e inserir avaliações: " + str(e)}), 500


@app.route('/updtavaliacao', methods=['POST'])
@token_required
def updtavaliacao():
    # Recebe o JSON com os dados da avaliação
    data = request.json
    id_projeto = data.get('id_projeto')
    id_utilizador = data.get('id_utilizador')
    rate = data.get('rate')
    comentario = data.get('comentario')

    # Atualiza a avaliação na tabela avaliacao
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE avaliacao SET rate = %s, comentario = %s WHERE id_projeto = %s AND id_utilizador = %s", (rate, comentario, id_projeto, id_utilizador))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Avaliação atualizada com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao atualizar avaliação: " + str(e)}), 500
    
    

@app.route('/updtusertask', methods=['POST'])
@token_required
def updtusertask():
    # Recebe o JSON com os dados da tarefa do utilizador
    data = request.json
    id_task = data.get('id_task')
    id_utilizador = data.get('id_utilizador')
    data_ini = data.get('data_ini')
    local = data.get('local')
    temp_disp = data.get('temp_disp')
    observacoes = data.get('observacoes')
    concluido = data.get('concluido')

    # Atualiza a entrada na tabela usertask
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE usertask SET data_ini = %s, local = %s, temp_disp = %s, observacoes = %s, concluido = %s WHERE id_task = %s AND id_utilizador = %s", (data_ini, local, temp_disp, observacoes, concluido, id_task, id_utilizador))
        conn.commit()
        cursor.close()
        return jsonify({"message": "Tarefa do utilizador atualizada com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao atualizar tarefa do utilizador: " + str(e)}), 500
    
    
@app.route('/getusertarefas', methods=['POST'])
@token_required
def getusertarefas():
    # Recebe o JSON com o ID do utilizador
    data = request.json
    id_utilizador = data.get('id_utilizador')

    # Busca todas as tarefas associadas ao utilizador na tabela usertask
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM usertask WHERE id_utilizador = %s", (id_utilizador,))
        tarefas = cursor.fetchall()
        cursor.close()

        # Preparaa os resultados para retorno
        tarefas_info = []
        for tarefa in tarefas:
            tarefa_info = {
                "id_task": tarefa[0],
                "id_utilizador": tarefa[1],
                "data_ini": str(tarefa[2]),
                "local": tarefa[3],
                "temp_disp": str(tarefa[4]),
                "observacoes": tarefa[5],
                "concluido": tarefa[6]
            }
            tarefas_info.append(tarefa_info)

        return jsonify({"tarefas": tarefas_info}), 200
    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao obter tarefas do utilizador: " + str(e)}), 500
    
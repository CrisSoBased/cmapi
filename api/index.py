from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import pymysql
import hashlib
import random
import string
import jwt
import traceback




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
    user_data = request.json
    nome = user_data.get('nome')
    email = user_data.get('email')
    password = user_data.get('password')

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    encrypted_password = hashlib.md5(password.encode()).hexdigest()
    encrypted_token = hashlib.md5(token.encode()).hexdigest()

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (nome, email, password, token)
            VALUES (%s, %s, %s, %s)
        """, (nome, email, encrypted_password, encrypted_token))
        conn.commit()

        cursor.execute("SELECT LAST_INSERT_ID()")
        row = cursor.fetchone()
        if not row or row[0] is None:
            raise Exception("Falha ao obter o ID do usuário recém-criado.")

        user_id = row[0]
        print("DEBUG - Novo usuário criado com UniqueID:", user_id)
        cursor.close()

        return jsonify({
            "message": "User inserido com sucesso!",
            "user_id": user_id,
            "token": encrypted_token
        }), 200

    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({
            "message": "Erro ao inserir user: " + str(e),
            "nome": nome,
            "email": email
        }), 500



@app.route('/loginft', methods=['POST'])
def loginft():
    login_data = request.json
    email = login_data.get('email')
    password = login_data.get('password')

    print("Received login data:", login_data)

    encrypted_password = hashlib.md5(password.encode()).hexdigest()
    cursor = conn.cursor()

    try:
        # Fetch full user details
        cursor.execute("""
            SELECT UniqueID, email, nome, tipo 
            FROM Users 
            WHERE email = %s AND password = %s
        """, (email, encrypted_password))
        user = cursor.fetchone()
    except Exception as e:
        print("DB error:", str(e))
        return jsonify({"message": "Internal server error"}), 500
    finally:
        cursor.close()

    if user is None:
        return jsonify({"message": "Credenciais inválidas"}), 401

    unique_id, email, nome, tipo = user

    try:
        secret_key = app.config['SECRET_KEY']
        token = jwt.encode(
            {'user_id': unique_id, 'exp': datetime.utcnow() + timedelta(hours=24)},
            secret_key,
            algorithm='HS256'
        )
    except Exception as e:
        print("JWT error:", str(e))
        return jsonify({"message": "Token generation error"}), 500

    # ✅ Include user details in response
    return jsonify({
        "token": token,
        "user_id": unique_id,
        "nome": nome,
        "email": email,
        "role": tipo
    }), 200


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

        return f(current_user[0], *args, **kwargs)

    decorator.__name__ = f.__name__
    return decorator



@app.route('/newproject', methods=['POST'])
@token_required
def newproject(current_user_id):
    project_data = request.json
    nome_projeto = project_data.get('nome')

    if not nome_projeto:
        return jsonify({"message": "O nome do projeto é obrigatório"}), 400

    cursor = conn.cursor()
    try:
        # Insert the new project
        cursor.execute("INSERT INTO Projects (nome) VALUES (%s)", (nome_projeto,))
        conn.commit()

        # Get inserted project ID
        cursor.execute("SELECT LAST_INSERT_ID()")
        row = cursor.fetchone()
        if not row or row[0] is None:
            raise Exception("Falha ao obter o ID do projeto recém-criado.")
        
        project_id = row[0]

        # Prepare debug info
        debug_info = {
            "user_id": current_user_id,
            "project_id": project_id,
            "role": 'owner',
            "param_types": {
                "user_id": str(type(current_user_id)),
                "project_id": str(type(project_id)),
                "role": str(type('owner'))
            }
        }

        try:
            cursor.execute("""
                INSERT INTO UserProjects (user_id, project_id, role)
                VALUES (%s, %s, %s)
            """, (current_user_id, project_id, 'owner'))
        except Exception as insert_error:
            conn.rollback()
            return jsonify({
                "message": "Erro ao inserir em UserProjects",
                "error": str(insert_error),
                "debug": debug_info
            }), 500

        conn.commit()

        return jsonify({
            "message": "Projeto criado com sucesso!",
            "project_id": project_id,
            "debug": debug_info
        }), 200

    except Exception as e:
        conn.rollback()
        return jsonify({
            "message": "Erro ao criar projeto: " + str(e)
        }), 500

    finally:
        cursor.close()


@app.route('/userprojects', methods=['GET'])
@token_required
def get_user_projects(current_user_id):  # already an int!
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.UniqueID, p.nome
            FROM Projects p
            JOIN UserProjects up ON p.UniqueID = up.project_id
            WHERE up.user_id = %s
        """, (current_user_id,))
        results = cursor.fetchall()
        projects = [{"id": row[0], "name": row[1]} for row in results]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()


@app.route('/getproject', methods=['GET'])
@token_required
def get_project(current_user_id):
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"message": "Parâmetro 'project_id' é obrigatório"}), 400

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT UniqueID, nome, descricao, data_ini
            FROM Projects
            WHERE UniqueID = %s
        """, (project_id,))
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return jsonify({"message": "Projeto não encontrado"}), 404

        return jsonify({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "start_date": row[3].isoformat() if row[3] else None
        }), 200

    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao obter projeto: " + str(e)}), 500



@app.route('/invite_user_to_project', methods=['POST'])
@token_required
def invite_user_to_project(current_user_id):
    data = request.json
    email = data.get('email')
    project_id = data.get('project_id')

    if not email or not project_id:
        return jsonify({"message": "Email e project_id são obrigatórios"}), 400

    cursor = conn.cursor()
    try:
        # Verify user exists
        cursor.execute("SELECT UniqueID FROM Users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"message": "Usuário com este email não encontrado"}), 404
        user_id = user[0]

        # Insert into UserProjects
        cursor.execute("""
            INSERT IGNORE INTO UserProjects (user_id, project_id, role)
            VALUES (%s, %s, %s)
        """, (user_id, project_id, 'collaborator'))
        conn.commit()
        return jsonify({"message": "Usuário adicionado ao projeto com sucesso!"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Erro ao adicionar usuário: " + str(e)}), 500
    finally:
        cursor.close()



@app.route('/get_project_collaborators', methods=['GET'])
@token_required
def get_project_collaborators(current_user_id):
    project_id = request.args.get('project_id')

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.UniqueID, u.nome, u.email, up.role
            FROM UserProjects up
            JOIN Users u ON up.user_id = u.UniqueID
            WHERE up.project_id = %s
        """, (project_id,))
        collaborators = cursor.fetchall()
        cursor.close()

        return jsonify([
            {
                "user_id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3]
            } for row in collaborators
        ]), 200
    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao buscar colaboradores: " + str(e)}), 500


@app.route('/ownedprojects', methods=['GET'])
@token_required
def get_owned_projects(current_user_id):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.UniqueID, p.nome
            FROM Projects p
            JOIN UserProjects up ON p.UniqueID = up.project_id
            WHERE up.user_id = %s AND up.role = 'owner'
        """, (current_user_id,))
        results = cursor.fetchall()
        projects = [{"id": row[0], "name": row[1]} for row in results]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()





    

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
def editarproject(current_user_id):
    project_data = request.json

    # Safely get fields
    unique_id = project_data.get('UniqueID')
    novo_nome = project_data.get('nome')
    nova_descricao = project_data.get('descricao')
    data_ini_str = project_data.get('data_ini')

    # Validate required fields
    if not all([unique_id, novo_nome, nova_descricao, data_ini_str]):
        return jsonify({"message": "Todos os campos (UniqueID, nome, descricao, data_ini) são obrigatórios."}), 400

    # Validate and parse date
    try:
        nova_data_ini = datetime.strptime(data_ini_str, '%Y-%m-%d').date()
    except Exception as e:
        return jsonify({"message": f"Formato de data inválido: {str(e)}"}), 400

    # Execute update
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Projects 
            SET nome = %s, data_ini = %s, descricao = %s 
            WHERE UniqueID = %s
        """, (novo_nome, nova_data_ini, nova_descricao, unique_id))
        conn.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": "Projeto atualizado com sucesso!"}), 200
        else:
            return jsonify({"message": "Nenhum projeto encontrado com o ID fornecido"}), 404

    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Erro ao atualizar projeto: {str(e)}"}), 500
    finally:
        cursor.close()

    

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
def newtarefa(current_user_id):
    data = request.json
    nome = data.get('nome')
    id_projeto = data.get('id_projeto')

    if not nome or not id_projeto:
        return jsonify({"message": "Campos 'nome' e 'id_projeto' são obrigatórios."}), 400

    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO Tasks (nome, id_projeto) VALUES (%s, %s)",
            (nome, id_projeto)
        )
        conn.commit()
        cursor.close()
        return jsonify({"message": "Nova tarefa inserida com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"message": "Erro ao inserir nova tarefa: " + str(e)}), 500
    


@app.route('/editartarefa', methods=['POST'])
@token_required
def editartarefa(current_user_id):
    data = request.json
    task_id = data.get('UniqueID')
    nome = data.get('nome')
    concluir = data.get('concluir')
    data_ini = data.get('data_ini')
    local = data.get('local')
    tempo = data.get('tempo')
    observacoes = data.get('observacoes')

    if not task_id or nome is None:
        return jsonify({"message": "Campos 'UniqueID' e 'nome' são obrigatórios."}), 400

    cursor = conn.cursor()
    try:
        query = """
            UPDATE Tasks SET 
                nome = %s,
                concluir = %s,
                data_ini = %s,
                local = %s,
                tempo = %s,
                observacoes = %s
            WHERE UniqueID = %s
        """
        values = (nome, concluir, data_ini, local, tempo, observacoes, task_id)

        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Tarefa atualizada com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Erro ao editar tarefa: {str(e)}"}), 500
    finally:
        cursor.close()




@app.route('/removertarefa', methods=['POST'])
@token_required
def removertarefa(current_user_id):
    data = request.json
    task_id = data.get('UniqueID')

    if not task_id:
        return jsonify({"message": "Campo 'UniqueID' é obrigatório."}), 400

    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Tasks WHERE UniqueID = %s", (task_id,))
        conn.commit()
        return jsonify({"message": "Tarefa removida com sucesso!"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"message": "Erro ao remover tarefa: " + str(e)}), 500
    finally:
        cursor.close()





@app.route('/associarutilizadortarefa', methods=['POST'])
@token_required
def associarutilizadortarefa(current_user_id):
    data = request.json
    id_utilizador = data.get('id_utilizador')
    id_task = data.get('id_task')

    if not id_utilizador or not id_task:
        return jsonify({"message": "id_utilizador e id_task são obrigatórios"}), 400

    cursor = conn.cursor()
    try:
        # Optional: prevent duplicate association
        cursor.execute("""
            SELECT 1 FROM TaskAssignments WHERE user_id = %s AND task_id = %s
        """, (id_utilizador, id_task))
        if cursor.fetchone():
            return jsonify({"message": "Esta associação já existe."}), 400

        cursor.execute("""
            INSERT INTO TaskAssignments (user_id, task_id)
            VALUES (%s, %s)
        """, (id_utilizador, id_task))
        conn.commit()
        return jsonify({"message": "Utilizador atribuído à tarefa com sucesso!"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"message": f"Erro ao associar utilizador à tarefa: {str(e)}"}), 500
    finally:
        cursor.close()



@app.route('/gettarefasprojeto', methods=['POST'])
@token_required
def gettarefasprojeto(current_user_id):
    try:
        data = request.json
        id_projeto = data.get('id_projeto')
        if id_projeto is None:
            return jsonify({"error": "Missing id_projeto in request"}), 400

        cursor = conn.cursor()

        # Check if current user is the owner
        cursor.execute("""
            SELECT role FROM UserProjects 
            WHERE user_id = %s AND project_id = %s
        """, (current_user_id, id_projeto))
        role_row = cursor.fetchone()

        if role_row and role_row[0] == 'owner':
            # Owner sees all tasks
            cursor.execute("""
                SELECT UniqueID, nome, concluir, data_ini, local, tempo, observacoes 
                FROM Tasks WHERE id_projeto = %s
            """, (id_projeto,))
        else:
            # Collaborators only see their assigned tasks
            cursor.execute("""
                SELECT t.UniqueID, t.nome, t.concluir, t.data_ini, t.local, t.tempo, t.observacoes
                FROM Tasks t
                JOIN TaskAssignments ta ON ta.task_id = t.UniqueID
                WHERE t.id_projeto = %s AND ta.user_id = %s
            """, (id_projeto, current_user_id))

        tarefas = cursor.fetchall()
        cursor.close()

        tarefas_info = [{
            "UniqueID": row[0],
            "nome": row[1],
            "concluir": row[2],
            "data_ini": row[3],
            "local": row[4],
            "tempo": row[5],
            "observacoes": row[6]
        } for row in tarefas]

        return jsonify(tarefas_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500





@app.route('/allprojects', methods=['GET'])
@token_required
def get_all_user_projects(current_user_id):
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.UniqueID, p.nome
            FROM Projects p
            JOIN UserProjects up ON p.UniqueID = up.project_id
            WHERE up.user_id = %s
        """, (current_user_id,))
        results = cursor.fetchall()
        projects = [{"id": row[0], "name": row[1]} for row in results]
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()








    

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
    
    
    
@app.route('/getuser', methods=['GET'])
@token_required
def getuser():
    unique_id = request.args.get('UniqueID')

    if not unique_id:
        return jsonify({"message": "Parâmetro 'UniqueID' é obrigatório"}), 400

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT UniqueID, nome, email, foto, desc_perfil, tipo, ativo, data_token
            FROM Users
            WHERE UniqueID = %s
        """, (unique_id,))
        user = cursor.fetchone()
        cursor.close()

        if not user:
            return jsonify({"message": "Usuário não encontrado"}), 404

        # Mapeia os resultados para um dicionário
        user_data = {
            "UniqueID": user[0],
            "nome": user[1],
            "email": user[2],
            "foto": user[3],
            "desc_perfil": user[4],
            "tipo": user[5],
            "ativo": user[6],
            "data_token": user[7].isoformat() if user[7] else None
        }

        return jsonify(user_data), 200

    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao obter dados do usuário: " + str(e)}), 500
    
    
    
@app.route('/getprojectbymanager', methods=['POST'])
@token_required
def getprojectbymanager():
    # Recebe o JSON com o ID do gestor
    data = request.json
    id_gestor = data.get('id_gestor')

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Projects WHERE id_gestor = %s", (id_gestor,))
        projetos = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()

        if projetos:
            result = [dict(zip(columns, row)) for row in projetos]
            return jsonify(result), 200
        else:
            return jsonify({"message": "Nenhum projeto encontrado para o gestor fornecido"}), 404
    except Exception as e:
        cursor.close()
        return jsonify({"message": "Erro ao buscar projetos: " + str(e)}), 500
    


@app.route('/hasproject', methods=['GET'])
@token_required
def hasproject(current_user_id):  # rename to reflect it's just an ID
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM UserProjects WHERE user_id = %s", (current_user_id,))
        result = cursor.fetchone()
        has_project = result[0] > 0
        return jsonify({"hasProject": has_project}), 200
    except Exception as e:
        return jsonify({"message": "Erro ao verificar projetos: " + str(e)}), 500
    finally:
        cursor.close()



@app.route('/debug/check-projects-table')
def check_projects_table():
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'Projects'")
        result = cursor.fetchone()
        if result:
            return "✅ Projects table exists", 200
        else:
            return "❌ Projects table does NOT exist", 404
    except Exception as e:
        return f"❌ Error checking table: {str(e)}", 500
    finally:
        cursor.close()


@app.route('/debug/projects-schema')
def check_projects_schema():
    cursor = conn.cursor()
    try:
        cursor.execute("DESCRIBE Projects")
        columns = cursor.fetchall()
        result = []
        for col in columns:
            result.append({
                "Field": col[0],
                "Type": col[1],
                "Null": col[2],
                "Key": col[3],
                "Default": col[4],
                "Extra": col[5]
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()


@app.route('/debug/userprojects-schema')
def check_userprojects_schema():
    cursor = conn.cursor()
    try:
        cursor.execute("DESCRIBE UserProjects")
        columns = cursor.fetchall()
        result = []
        for col in columns:
            result.append({
                "Field": col[0],
                "Type": col[1],
                "Null": col[2],
                "Key": col[3],
                "Default": col[4],
                "Extra": col[5]
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@app.route('/debug/test-insert')
def test_insert():
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO UserProjects (user_id, project_id, role)
            VALUES (%s, %s, %s)
        """, (999, 888, 'test'))
        conn.commit()
        return "✅ Insert successful", 200
    except Exception as e:
        return f"❌ Insert failed: {str(e)}", 500
    finally:
        cursor.close()



@app.route('/debug/users')
def debug_users():
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID, nome, email FROM Users")
        users = cursor.fetchall()
        return jsonify(users), 200
    finally:
        cursor.close()


@app.route('/debug/projects')
def debug_projects():
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID, nome FROM Projects")
        projects = cursor.fetchall()
        return jsonify(projects), 200
    finally:
        cursor.close()


@app.route('/debug/userprojects')
def debug_userprojects():
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, project_id, role FROM UserProjects")
        links = cursor.fetchall()
        return jsonify(links), 200
    finally:
        cursor.close()

@app.route('/debug/tasks-for-project/<int:project_id>')
def debug_tasks_for_project(project_id):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT UniqueID, nome, concluir FROM Tasks WHERE id_projeto = %s", (project_id,))
        tarefas = cursor.fetchall()
        result = []
        for tarefa in tarefas:
            result.append({
                "UniqueID": tarefa[0],
                "nome": tarefa[1],
                "concluir": tarefa[2]
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()


@app.route('/debug/tables')
def list_tables():
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        return jsonify([t[0] for t in tables])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()


@app.route('/debug/describe')
def describe_table():
    table = request.args.get("table")
    if not table:
        return jsonify({"error": "Missing 'table' query parameter"}), 400

    cursor = conn.cursor()
    try:
        cursor.execute(f"DESCRIBE `{table}`")  # safe only if table name is trusted
        columns = cursor.fetchall()
        return jsonify([
            {
                "Field": col[0],
                "Type": col[1],
                "Null": col[2],
                "Key": col[3],
                "Default": col[4],
                "Extra": col[5]
            }
            for col in columns
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
import random
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração do banco de dados MySQL
def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",  # Substitua pelo seu usuário do MySQL
        password="vitor3255",  # Substitua pela sua senha do MySQL
        database="idolrpg"  # Nome do banco de dados
    )
    return conn

# Função para inicializar o banco de dados
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        with open('schema.sql', 'r') as f:
            sql_commands = f.read().split(';')
            for command in sql_commands:
                if command.strip():
                    cursor.execute(command)
        db.commit()

# Rota para a página de lançar músicas
@app.route('/lancar_musica', methods=['GET', 'POST'])
def lancar_musica():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        genero_principal = request.form['genero_principal']
        genero_secundario = request.form.get('genero_secundario', '')
        genero_terciario = request.form.get('genero_terciario', '')
        data_lancamento = datetime.now().strftime('%Y-%m-%d')  # Data atual

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO musicas (usuario_id, nome, genero_principal, genero_secundario, genero_terciario, data_lancamento) '
            'VALUES (%s, %s, %s, %s, %s, %s)',
            (session['user_id'], nome, genero_principal, genero_secundario, genero_terciario, data_lancamento)
        )
        db.commit()
        flash('Música lançada com sucesso!')
        return redirect(url_for('home'))

    return render_template('lancar_musica.html')

# Rota para aplicar buzz a uma música
@app.route('/aplicar_buzz/<int:musica_id>', methods=['POST'])
def aplicar_buzz(musica_id):
    if 'user_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Usuário não autenticado."})

    tipo_buzz = request.json.get("tipo_buzz")

    if tipo_buzz == "barato":
        custo = 50000
        uls = random.randint(1000, 5000)
        streams = random.randint(15000, 20000)
    elif tipo_buzz == "mediano":
        custo = 150000
        uls = random.randint(10000, 15000)
        streams = random.randint(25000, 40000)
    elif tipo_buzz == "caro":
        custo = 300000
        uls = random.randint(20000, 25000)
        streams = random.randint(45000, 60000)
    else:
        return jsonify({"sucesso": False, "mensagem": "Tipo de buzz inválido."})

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT SUM(custo) as total FROM compras WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)', (session['user_id'],))
    gasto_semanal = cursor.fetchone()['total'] or 0

    if gasto_semanal + custo > 600000:
        return jsonify({"sucesso": False, "mensagem": "Compra excede o limite semanal de gasto com buzz."})

    cursor.execute('INSERT INTO compras (usuario_id, musica_id, tipo_buzz, custo, uls, streams, data) VALUES (%s, %s, %s, %s, %s, %s, CURDATE())', (session['user_id'], musica_id, tipo_buzz, custo, uls, streams))
    cursor.execute('UPDATE musicas SET buzz = buzz + %s WHERE id = %s', (streams, musica_id))
    db.commit()

    return jsonify({"sucesso": True, "mensagem": f"Buzz aplicado com sucesso! ULS: +{uls}, Streams: +{streams}"})

# Função para calcular pontos e unique listeners
def calcular_pontos_e_uls(streams, downloads, buzz):
    pontos_downloads = (downloads // 1000) * 10
    pontos_streams = ((streams + buzz) // 1000) * 50
    pontos_totais = pontos_downloads + pontos_streams

    percentual_uls = random.uniform(0.4, 0.6)  # Entre 40% e 60%
    uls = int((streams + buzz) * percentual_uls)

    return pontos_totais, uls

# Função para atualizar os charts
def atualizar_charts():
    with app.app_context():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM musicas')
        musicas = cursor.fetchall()
        for musica in musicas:
            streams = musica['streams']
            downloads = musica['downloads']
            data_lancamento = datetime.strptime(musica['data_lancamento'], "%Y-%m-%d")
            buzz = musica['buzz']

            pontos, uls = calcular_pontos_e_uls(streams, downloads, buzz)

            # Diminuir 10% a cada hora
            pontos *= 0.9
            uls *= 0.9

            # Verificar se a música completou uma semana
            if datetime.now() >= data_lancamento + timedelta(days=7):
                pontos *= 0.5  # Queda de 50%
                uls *= 0.5

            # Atualizar os dados da música
            cursor.execute('UPDATE musicas SET pontos = %s, uls = %s WHERE id = %s', (pontos, uls, musica['id']))
        db.commit()

# Agendamento da atualização dos charts
scheduler = BackgroundScheduler()
scheduler.add_job(atualizar_charts, 'interval', hours=1)  # Atualizar a cada hora
scheduler.start()

# Rotas
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT * FROM musicas WHERE usuario_id = %s', (session['user_id'],))
    musicas = cursor.fetchall()
    cursor.execute('SELECT SUM(custo) as total FROM compras WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)', (session['user_id'],))
    gasto_semanal = cursor.fetchone()['total'] or 0
    return render_template('index.html', musicas=musicas, gasto_semanal=gasto_semanal, limite_gasto_semanal=600000)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuarios WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO usuarios (username, email, password) VALUES (%s, %s, %s)', (username, email, password))
            db.commit()
            flash('Cadastro realizado com sucesso! Faça login.')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Usuário ou e-mail já cadastrado.')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/comprar_buzz', methods=['POST'])
def comprar_buzz():
    if 'user_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Usuário não autenticado."})

    tipo_buzz = request.json.get("tipo_buzz")
    musica_id = request.json.get("musica_id")

    if tipo_buzz == "barato":
        custo = 50000
        uls = random.randint(1000, 5000)
        streams = random.randint(15000, 20000)
    elif tipo_buzz == "mediano":
        custo = 150000
        uls = random.randint(10000, 15000)
        streams = random.randint(25000, 40000)
    elif tipo_buzz == "caro":
        custo = 300000
        uls = random.randint(20000, 25000)
        streams = random.randint(45000, 60000)
    else:
        return jsonify({"sucesso": False, "mensagem": "Tipo de buzz inválido."})

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute('SELECT SUM(custo) as total FROM compras WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)', (session['user_id'],))
    gasto_semanal = cursor.fetchone()['total'] or 0

    if gasto_semanal + custo > 600000:
        return jsonify({"sucesso": False, "mensagem": "Compra excede o limite semanal de gasto com buzz."})

    cursor.execute('INSERT INTO compras (usuario_id, musica_id, tipo_buzz, custo, uls, streams, data) VALUES (%s, %s, %s, %s, %s, %s, CURDATE())', (session['user_id'], musica_id, tipo_buzz, custo, uls, streams))
    cursor.execute('UPDATE musicas SET buzz = buzz + %s WHERE id = %s', (streams, musica_id))
    db.commit()

    # Redirecionar para a página inicial após a compra
    return jsonify({"sucesso": True, "mensagem": f"Buzz aplicado com sucesso! ULS: +{uls}, Streams: +{streams}", "redirect": url_for('home')})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
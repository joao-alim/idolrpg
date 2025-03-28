from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
import random
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Mantenha essa chave

# ========== FILTROS TEMPLATE ==========
@app.template_filter('format_currency')
def format_currency(value):
    try:
        return f"${float(value or 0):,.0f}".replace(",", ".")
    except:
        return "$0"

@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    if not value:
        return "N/A"
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').strftime(format)
    except:
        return str(value)

@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except:
        return str(value)

# ========== BANCO DE DADOS ==========
def get_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="vitor3255",
            database="idolrpg"
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        raise

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS musicas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    nome VARCHAR(100) NOT NULL,
                    genero_principal VARCHAR(50) NOT NULL,
                    genero_secundario VARCHAR(50),
                    genero_terciario VARCHAR(50),
                    streams INT DEFAULT 0,
                    uls INT DEFAULT 0,
                    buzz INT DEFAULT 0,
                    pontos FLOAT DEFAULT 0,
                    data_lancamento DATE NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compras (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    musica_id INT NOT NULL,
                    tipo_buzz VARCHAR(20) NOT NULL,
                    custo INT NOT NULL,
                    uls INT NOT NULL,
                    streams INT NOT NULL,
                    data DATE NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                    FOREIGN KEY (musica_id) REFERENCES musicas(id)
                )
            """)
            db.commit()
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            db.rollback()

# ========== ROTAS PRINCIPAIS ==========
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Recupera músicas do usuário
        cursor.execute('SELECT * FROM musicas WHERE usuario_id = %s', (session['user_id'],))
        musicas = cursor.fetchall()
        
        # Calcula gasto semanal
        cursor.execute('''
            SELECT SUM(custo) as total 
            FROM compras 
            WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ''', (session['user_id'],))
        gasto_semanal = cursor.fetchone()['total'] or 0
        
        return render_template(
            'index.html',
            musicas=musicas,
            gasto_semanal=gasto_semanal,
            limite_gasto_semanal=600000
        )
        
    except Exception as e:
        print(f"Erro na rota home: {e}")
        flash("Erro ao carregar dados")
        return render_template('index.html', musicas=[], gasto_semanal=0, limite_gasto_semanal=600000)

@app.route('/lancarmusica', methods=['GET', 'POST'])
def lancarmusica():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute('''
                INSERT INTO musicas (
                    usuario_id, nome, genero_principal, genero_secundario, 
                    genero_terciario, data_lancamento
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                session['user_id'],
                request.form['nome'],
                request.form['genero_principal'],
                request.form.get('genero_secundario', ''),
                request.form.get('genero_terciario', ''),
                datetime.now().strftime('%Y-%m-%d')
            ))
            db.commit()
            flash('Música lançada com sucesso!')
            return redirect(url_for('home'))
            
        except Exception as e:
            db.rollback()
            print(f"Erro ao lançar música: {e}")
            flash('Erro ao lançar música')

    return render_template('lancarmusica.html')

# ... (cabeçalho e imports anteriores permanecem iguais)

# ========== ROTAS DE AUTENTICAÇÃO ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute(
                'SELECT * FROM usuarios WHERE username = %s AND password = %s',
                (username, password)
            )
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['id']
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Usuário ou senha incorretos', 'danger')
        except Exception as e:
            print(f"Erro no login: {e}")
            flash('Erro durante o login', 'danger')
    
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
            cursor.execute(
                'INSERT INTO usuarios (username, email, password) VALUES (%s, %s, %s)',
                (username, email, password)
            )
            db.commit()
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Usuário ou e-mail já cadastrado', 'danger')
        except Exception as e:
            print(f"Erro no registro: {e}")
            flash('Erro durante o cadastro', 'danger')
            db.rollback()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Você foi desconectado', 'info')
    return redirect(url_for('login'))

# ========== ROTAS DE MÚSICAS ==========
@app.route('/editar_musica/<int:musica_id>', methods=['GET', 'POST'])
def editar_musica(musica_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    if request.method == 'POST':
        try:
            cursor.execute('''
                UPDATE musicas SET
                    nome = %s,
                    genero_principal = %s,
                    genero_secundario = %s,
                    genero_terciario = %s
                WHERE id = %s AND usuario_id = %s
            ''', (
                request.form['nome'],
                request.form['genero_principal'],
                request.form.get('genero_secundario', ''),
                request.form.get('genero_terciario', ''),
                musica_id,
                session['user_id']
            ))
            db.commit()
            flash('Música atualizada com sucesso!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            print(f"Erro ao editar música: {e}")
            flash('Erro ao atualizar música', 'danger')
            db.rollback()
    
    # Carrega dados da música para edição
    cursor.execute(
        'SELECT * FROM musicas WHERE id = %s AND usuario_id = %s',
        (musica_id, session['user_id'])
    )
    musica = cursor.fetchone()
    
    if not musica:
        flash('Música não encontrada', 'danger')
        return redirect(url_for('home'))
    
    return render_template('editar_musica.html', musica=musica)

@app.route('/excluir_musica/<int:musica_id>', methods=['POST'])
def excluir_musica(musica_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            'DELETE FROM musicas WHERE id = %s AND usuario_id = %s',
            (musica_id, session['user_id'])
        )
        db.commit()
        flash('Música excluída com sucesso', 'success')
    except Exception as e:
        print(f"Erro ao excluir música: {e}")
        flash('Erro ao excluir música', 'danger')
        db.rollback()
    
    return redirect(url_for('home'))

# ========== ROTAS DE RELATÓRIOS ==========
@app.route('/relatorios')
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Músicas mais populares
        cursor.execute('''
            SELECT nome, pontos 
            FROM musicas 
            WHERE usuario_id = %s 
            ORDER BY pontos DESC 
            LIMIT 5
        ''', (session['user_id'],))
        top_musicas = cursor.fetchall()
        
        # Histórico de buzz
        cursor.execute('''
            SELECT m.nome, c.tipo_buzz, c.data, c.streams 
            FROM compras c
            JOIN musicas m ON c.musica_id = m.id
            WHERE c.usuario_id = %s
            ORDER BY c.data DESC
            LIMIT 10
        ''', (session['user_id'],))
        historico_buzz = cursor.fetchall()
        
        return render_template(
            'relatorios.html',
            top_musicas=top_musicas,
            historico_buzz=historico_buzz
        )
        
    except Exception as e:
        print(f"Erro ao gerar relatórios: {e}")
        flash('Erro ao carregar relatórios', 'danger')
        return redirect(url_for('home'))

# ========== INICIALIZAÇÃO ==========
if __name__ == '__main__':
    init_db()  # Garante que as tabelas existam
    try:
        app.run(debug=True, port=5000, host='0.0.0.0')
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")
        raise

@app.route('/comprar_buzz', methods=['POST'])
def comprar_buzz():
    if 'user_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Não autenticado"})

    try:
        data = request.get_json()
        tipo_buzz = data.get("tipo_buzz")
        musica_id = data.get("musica_id")

        if not tipo_buzz or not musica_id:
            return jsonify({"sucesso": False, "mensagem": "Dados incompletos"})

        # Valores originais do seu sistema
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
            return jsonify({"sucesso": False, "mensagem": "Tipo de buzz inválido"})

        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Verificação de limite semanal
        cursor.execute('''
            SELECT SUM(custo) as total 
            FROM compras 
            WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ''', (session['user_id'],))
        gasto_semanal = cursor.fetchone()['total'] or 0

        if gasto_semanal + custo > 600000:
            return jsonify({"sucesso": False, "mensagem": "Limite semanal excedido"})

        # Atualiza a música
        cursor.execute('''
            UPDATE musicas 
            SET buzz = buzz + %s 
            WHERE id = %s AND usuario_id = %s
        ''', (streams, musica_id, session['user_id']))
        
        # Registra a compra
        cursor.execute('''
            INSERT INTO compras (
                usuario_id, musica_id, tipo_buzz, custo, uls, streams, data
            ) VALUES (%s, %s, %s, %s, %s, %s, CURDATE())
        ''', (
            session['user_id'], musica_id, tipo_buzz, custo, uls, streams
        ))
        
        db.commit()
        return jsonify({
            "sucesso": True,
            "mensagem": f"Buzz aplicado! +{streams} streams e +{uls} ULS",
            "dados": {"streams": streams, "uls": uls}
        })

    except Exception as e:
        print(f"Erro em comprar_buzz: {e}")
        return jsonify({"sucesso": False, "mensagem": "Erro interno"})

# ========== AGENDADOR ==========
def atualizar_charts():
    with app.app_context():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute('SELECT * FROM musicas')
            for musica in cursor.fetchall():
                # Sua lógica original de cálculo de pontos
                pontos = ((musica['streams'] + musica['buzz']) // 1000) * 50
                uls = int((musica['streams'] + musica['buzz']) * 0.5)
                
                cursor.execute('''
                    UPDATE musicas 
                    SET pontos = %s, uls = %s 
                    WHERE id = %s
                ''', (pontos, uls, musica['id']))
            db.commit()
        except Exception as e:
            print(f"Erro no agendador: {e}")
            db.rollback()

scheduler = BackgroundScheduler()
scheduler.add_job(atualizar_charts, 'interval', hours=1)
scheduler.start()

# ========== INICIALIZAÇÃO ==========
if __name__ == '__main__':
    init_db()  # Garante que as tabelas existam
    try:
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")
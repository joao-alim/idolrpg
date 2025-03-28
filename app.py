from flask import Flask, jsonify, request, render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta
import random
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

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

@app.route('/debug_routes')
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'path': str(rule),
            'methods': sorted(rule.methods)
        })
    return jsonify({'routes': routes})

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT * FROM musicas WHERE usuario_id = %s', (session['user_id'],))
        musicas = cursor.fetchall()
        
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

@app.route('/relatorios')
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute('''
            SELECT nome, pontos 
            FROM musicas 
            WHERE usuario_id = %s 
            ORDER BY pontos DESC 
            LIMIT 5
        ''', (session['user_id'],))
        top_musicas = cursor.fetchall()
        
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

@app.route('/buzz', endpoint='buzz_page') 
def buzz_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute('SELECT * FROM musicas WHERE usuario_id = %s', (session['user_id'],))
        musicas = cursor.fetchall()
        
        cursor.execute('''
            SELECT SUM(custo) as total FROM compras 
            WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ''', (session['user_id'],))
        gasto_semanal = cursor.fetchone()['total'] or 0
        
        return render_template(
            'buzz.html',
            musicas=musicas,
            gasto_semanal=gasto_semanal,
            limite_gasto_semanal=600000
        )
        
    except Exception as e:
        print(f"Erro na página de buzz: {e}")
        flash("Erro ao carregar dados")
        return render_template('buzz.html', musicas=[], gasto_semanal=0, limite_gasto_semanal=600000)

@app.route('/comprar_buzz', methods=['POST'])
def comprar_buzz():
    if 'user_id' not in session:
        return jsonify({"sucesso": False, "mensagem": "Não autenticado"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"sucesso": False, "mensagem": "Dados inválidos"}), 400

        tipo_buzz = data.get("tipo_buzz")
        musica_id = data.get("musica_id")

        if not tipo_buzz or not musica_id:
            return jsonify({"sucesso": False, "mensagem": "Dados incompletos"}), 400

        valores = {
            "barato": {
                "custo": 50000,
                "uls": (1000, 5000),
                "streams": (15000, 20000),
                "downloads": (500, 1000)
            },
            "mediano": {
                "custo": 150000,
                "uls": (10000, 15000),
                "streams": (25000, 40000),
                "downloads": (2000, 3000)
            },
            "caro": {
                "custo": 300000,
                "uls": (20000, 25000),
                "streams": (45000, 60000),
                "downloads": (5000, 7000)
            }
        }

        if tipo_buzz not in valores:
            return jsonify({"sucesso": False, "mensagem": "Tipo de buzz inválido"}), 400

        config = valores[tipo_buzz]
        uls = random.randint(*config["uls"])
        streams = random.randint(*config["streams"])
        downloads = random.randint(*config["downloads"])

        db = get_db()
        cursor = db.cursor()

        cursor.execute('''
            SELECT SUM(custo) as total FROM compras 
            WHERE usuario_id = %s AND data >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        ''', (session['user_id'],))
        gasto_semanal = cursor.fetchone()[0] or 0

        if gasto_semanal + config["custo"] > 600000:
            return jsonify({"sucesso": False, "mensagem": "Limite semanal excedido"}), 400

        cursor.execute('''
            SELECT id FROM musicas WHERE id = %s AND usuario_id = %s
        ''', (musica_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({"sucesso": False, "mensagem": "Música não encontrada"}), 404

        cursor.execute('''
            UPDATE musicas 
            SET 
                buzz = buzz + %s,
                streams = streams + %s,
                uls = uls + %s,
                downloads = downloads + %s
            WHERE id = %s
        ''', (streams, streams, uls, downloads, musica_id))


        cursor.execute('''
            INSERT INTO compras (
                usuario_id, musica_id, tipo_buzz, custo, 
                uls, streams, downloads, data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURDATE())
        ''', (
            session['user_id'], musica_id, tipo_buzz, config["custo"],
            uls, streams, downloads
        ))

        db.commit()
        
        return jsonify({
            "sucesso": True,
            "mensagem": f"Buzz aplicado! +{streams} streams, +{uls} ULS e +{downloads} downloads",
            "dados": {
                "streams": streams,
                "uls": uls,
                "downloads": downloads,
                "tipo": tipo_buzz,
                "limite_restante": 600000 - (gasto_semanal + config["custo"])
            }
        })

    except mysql.connector.Error as err:
        print(f"Erro MySQL em comprar_buzz: {err}")
        db.rollback()
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro no banco de dados",
            "detalhes": str(err)
        }), 500
        
    except Exception as e:
        print(f"Erro geral em comprar_buzz: {str(e)}")
        db.rollback()
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro interno no servidor",
            "detalhes": str(e)
        }), 500
    
@app.route('/charts')
def charts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute('''
            SELECT m.nome, m.genero_principal, m.streams, m.buzz, m.uls, m.downloads,
                   m.pontos, u.username as artista
            FROM musicas m
            JOIN usuarios u ON m.usuario_id = u.id
            ORDER BY pontos DESC
            LIMIT 10
        ''')
        top_global = cursor.fetchall()
        
        cursor.execute('''
            SELECT nome, genero_principal, streams, buzz, uls, downloads, pontos
            FROM musicas
            WHERE usuario_id = %s
            ORDER BY pontos DESC
            LIMIT 5
        ''', (session['user_id'],))
        top_usuario = cursor.fetchall()
        
        cursor.execute('''
            SELECT genero_principal, COUNT(*) as quantas, 
                   SUM(pontos) as total_pontos
            FROM musicas
            GROUP BY genero_principal
            ORDER BY total_pontos DESC
            LIMIT 5
        ''')
        top_generos = cursor.fetchall()
        
        cursor.execute('''
            SELECT m.nome, m.downloads, u.username as artista
            FROM musicas m
            JOIN usuarios u ON m.usuario_id = u.id
            ORDER BY downloads DESC
            LIMIT 5
        ''')
        top_downloads = cursor.fetchall()
        
        cursor.execute('''
            SELECT m.nome, m.uls, u.username as artista
            FROM musicas m
            JOIN usuarios u ON m.usuario_id = u.id
            ORDER BY uls DESC
            LIMIT 5
        ''')
        top_uls = cursor.fetchall()
        
        return render_template(
            'charts.html',
            top_global=top_global,
            top_usuario=top_usuario,
            top_generos=top_generos,
            top_downloads=top_downloads,
            top_uls=top_uls,
            ultima_atualizacao=datetime.now().strftime('%d/%m/%Y %H:%M'))
            
    except Exception as e:
        print(f"Erro na página de charts: {e}")
        flash("Erro ao carregar charts")
        return render_template('charts.html', 
                            top_global=[], 
                            top_usuario=[], 
                            top_generos=[],
                            top_downloads=[],
                            top_uls=[],
                            ultima_atualizacao="N/A")

def atualizar_charts():
    with app.app_context():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            print(f"Iniciando atualização de charts em {datetime.now()}")
            
            cursor.execute('SELECT id, streams, buzz, uls, downloads FROM musicas')
            for musica in cursor.fetchall():
                streams_totais = musica['streams'] + musica['buzz']

                pontos_streams = streams_totais // 1000
                
                pontos_downloads = musica['downloads'] * 15
                
                pontos_uls = musica['uls'] // 2
                
                pontos_totais = pontos_streams + pontos_downloads + pontos_uls
                
                if musica['downloads'] >= 10000:
                    bonus_viral = 1 + (musica['downloads'] // 10000 * 0.05)
                    pontos_totais = int(pontos_totais * bonus_viral)
                
                if musica['uls'] > 5000:
                    bonus_consistencia = 1 + ((musica['uls'] - 5000) // 1000 * 0.02)
                    pontos_totais = int(pontos_totais * bonus_consistencia)
                
                pontos_minimos = streams_totais // 2000
                pontos_totais = max(pontos_totais, pontos_minimos)
                
                cursor.execute('''
                    UPDATE musicas 
                    SET pontos = %s 
                    WHERE id = %s
                ''', (pontos_totais, musica['id']))
                
                if musica['id'] == 1:
                    print(f"\nDebug cálculo de pontos - Música ID {musica['id']}:")
                    print(f"Streams: {streams_totais} = {pontos_streams} pontos")
                    print(f"Downloads: {musica['downloads']} = {pontos_downloads} pontos")
                    print(f"ULS: {musica['uls']} = {pontos_uls} pontos")
                    print(f"Bônus viral: {bonus_viral if musica['downloads'] >= 10000 else 'N/A'}")
                    print(f"Bônus consistência: {bonus_consistencia if musica['uls'] > 5000 else 'N/A'}")
                    print(f"Pontos finais: {pontos_totais}")
            
            db.commit()
            print("Charts atualizados com sucesso!")
            
            atualizar_ranking_generos()
            
        except Exception as e:
            print(f"Erro ao atualizar charts: {e}")
            db.rollback()
            raise

def atualizar_ranking_generos():
    """Função auxiliar para atualizar o ranking de gêneros musicais"""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ranking_generos (
                    genero VARCHAR(50) PRIMARY KEY,
                    total_pontos BIGINT DEFAULT 0,
                    total_musicas INT DEFAULT 0,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO ranking_generos (genero, total_pontos, total_musicas)
                SELECT 
                    genero_principal as genero,
                    SUM(pontos) as total_pontos,
                    COUNT(*) as total_musicas
                FROM musicas
                GROUP BY genero_principal
                ON DUPLICATE KEY UPDATE
                    total_pontos = VALUES(total_pontos),
                    total_musicas = VALUES(total_musicas),
                    data_atualizacao = CURRENT_TIMESTAMP
            ''')
            
            db.commit()
            print("Ranking de gêneros atualizado!")
            
        except Exception as e:
            print(f"Erro ao atualizar ranking de gêneros: {e}")
            db.rollback()

scheduler = BackgroundScheduler()
scheduler.add_job(atualizar_charts, 'interval', hours=1)
scheduler.start()

if __name__ == '__main__':
    init_db()
    try:
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Erro ao iniciar servidor: {e}")
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3, os, bcrypt, smtplib
from datetime import date
from reportlab.pdfgen import canvas
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

app = Flask(__name__)
app.secret_key = "chave_super_segura"

# ---------------------
# Inicialização do Banco
# ---------------------
def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS monitores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        usuario TEXT UNIQUE,
        senha TEXT,
        email TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS faltas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        monitor TEXT,
        aluno TEXT,
        turma TEXT,
        tipo TEXT,
        data TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS desempenho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        monitor TEXT,
        aluno TEXT,
        observacao TEXT,
        data TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------------
# Funções auxiliares
# ---------------------
def enviar_email(destinatario, assunto, mensagem, anexo=None):
    remetente = "seuemail@gmail.com"
    senha = "senha_app_google"  # gere uma senha de app no Gmail
    msg = MIMEMultipart()
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto

    msg.attach(MIMEText(mensagem, 'html'))
    if anexo:
        with open(anexo, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(anexo))
        part['Content-Disposition'] = f'attachment; filename=\"{os.path.basename(anexo)}\"'
        msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remetente, senha)
        smtp.send_message(msg)

# ---------------------
# Rotas
# ---------------------

@app.route('/')
def home():
    if 'usuario' not in session:
        return redirect('/login')
    return render_template('index.html', usuario=session['usuario'])

# Cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        senha = request.form['senha']
        email = request.form['email']
        hash_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO monitores (nome, usuario, senha, email) VALUES (?, ?, ?, ?)',
                        (nome, usuario, hash_senha, email))
            conn.commit()
            return redirect('/login')
        except:
            return "Usuário já existe!"
        finally:
            conn.close()
    return render_template('cadastro.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute('SELECT senha FROM monitores WHERE usuario=?', (usuario,))
        row = cur.fetchone()
        conn.close()

        if row and bcrypt.checkpw(senha.encode('utf-8'), row[0]):
            session['usuario'] = usuario
            return redirect('/')
        else:
            return "Usuário ou senha incorretos!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect('/login')

# Registrar faltas
@app.route('/registrar_falta', methods=['POST'])
def registrar_falta():
    aluno = request.form['aluno']
    turma = request.form['turma']
    tipo = request.form['tipo']
    data_hoje = str(date.today())
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO faltas (monitor, aluno, turma, tipo, data) VALUES (?, ?, ?, ?, ?)',
                (session['usuario'], aluno, turma, tipo, data_hoje))
    conn.commit()
    conn.close()
    return redirect('/historico')

# Registrar desempenho
@app.route('/registrar_desempenho', methods=['POST'])
def registrar_desempenho():
    aluno = request.form['aluno']
    obs = request.form['observacao']
    data_hoje = str(date.today())
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO desempenho (monitor, aluno, observacao, data) VALUES (?, ?, ?, ?)',
                (session['usuario'], aluno, obs, data_hoje))
    conn.commit()
    conn.close()
    return redirect('/historico')

# Histórico com filtro
@app.route('/historico', methods=['GET', 'POST'])
def historico():
    turma = request.form.get('turma') if request.method == 'POST' else None
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    if turma:
        cur.execute('SELECT * FROM faltas WHERE turma=? ORDER BY data DESC', (turma,))
    else:
        cur.execute('SELECT * FROM faltas ORDER BY data DESC')
    faltas = cur.fetchall()
    cur.execute('SELECT * FROM desempenho ORDER BY data DESC')
    desempenho = cur.fetchall()
    conn.close()
    return render_template('historico.html', faltas=faltas, desempenho=desempenho)

# Gerar PDF e enviar por e-mail
@app.route('/gerar_pdf')
def gerar_pdf():
    filename = f"relatorio_{session['usuario']}.pdf"
    path = os.path.join('static', filename)
    c = canvas.Canvas(path)
    c.drawString(100, 800, f"Relatório de {session['usuario']}")
    c.drawString(100, 780, "Gerado automaticamente pelo sistema de monitoria.")
    c.save()

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()
    cur.execute('SELECT email FROM monitores WHERE usuario=?', (session['usuario'],))
    email_dest = cur.fetchone()[0]
    conn.close()

    enviar_email(email_dest, "Relatório de Monitoria", "<p>Segue o relatório em anexo.</p>", path)
    return redirect(f"/static/{filename}")

if __name__ == '__main__':
    app.run(debug=True)

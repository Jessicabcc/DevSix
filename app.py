import os
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'chave_secreta_agendamento'

ESTRUTURA_SALAS = {
    "predio_central": {
        "nome": "Prédio Central",
        "emoji": "🏛️",
        "salas": ["New York", "Washington", "Sala 101", "Sala 102"]
    },
    "anexo_1": {
        "nome": "Anexo 1",
        "emoji": "🏢",
        "salas": [f"Sala {i}" for i in range(1, 21)] + ["Laboratório 1", "Laboratório 2", "Sala Maker"]
    },
    "anexo_2": {
        "nome": "Anexo 2 (Anfiteatro)",
        "emoji": "🎤",
        "salas": ["Anfiteatro 1", "Anfiteatro 2"] + [f"Sala {i}" for i in range(30, 37)]
    }
}

def iniciar_planilhas():
    if not os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['nome', 'email', 'senha', 'tipo'])

    if not os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['predio', 'sala', 'data', 'turno', 'professor', 'email'])

iniciar_planilhas()

def obter_todas_reservas():
    reservas = []
    if os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for linha in reader:
                id_predio = linha.get('predio', 'predio_central')
                linha['predio_nome'] = ESTRUTURA_SALAS.get(id_predio, {}).get('nome', id_predio)
                linha['sala'] = linha.get('sala', 'Não informada')
                linha['data'] = linha.get('data', '--/--/----')
                linha['turno'] = linha.get('turno', 'Indefinido')
                linha['professor'] = linha.get('professor', 'Anônimo')
                reservas.append(linha)
    return reservas

@app.route('/')
def index():
    return render_template('index.html', 
                           usuario_logado=session.get('usuario'), 
                           tipo_usuario=session.get('tipo'), 
                           predios=ESTRUTURA_SALAS,
                           reservas=obter_todas_reservas())

@app.route('/predio/<id_predio>')
def ver_predio(id_predio):
    if id_predio not in ESTRUTURA_SALAS:
        return redirect(url_for('index'))
    return render_template('predio.html', 
                           predio=ESTRUTURA_SALAS[id_predio], 
                           id_predio=id_predio, 
                           usuario_logado=session.get('usuario'), 
                           tipo_usuario=session.get('tipo'))

@app.route('/salvar_agendamento', methods=['POST'])
def salvar_agendamento():
    if 'usuario' not in session or session.get('tipo') != 'Professor':
        flash("Apenas professores podem realizar agendamentos.", "error")
        return redirect(url_for('index'))
    
    id_predio = request.form['id_predio']
    nome_sala = request.form['nome_sala']
    data = request.form['data']
    turno = request.form['turno']
    professor = session['usuario']
    
    email_professor = ""
    with open('usuarios.csv', 'r', encoding='utf-8') as f:
        for linha in csv.DictReader(f):
            if linha.get('nome') == professor:
                email_professor = linha.get('email', '')
                break

    ocupado = False
    with open('agendamentos.csv', 'r', encoding='utf-8') as f:
        for linha in csv.DictReader(f):
            if linha.get('sala') == nome_sala and linha.get('data') == data and linha.get('turno') == turno:
                ocupado = True
                break
    
    if ocupado:
        flash(f"A {nome_sala} já está reservada para o dia {data} no turno da {turno}.", "error")
        return redirect(url_for('ver_predio', id_predio=id_predio))

    with open('agendamentos.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([id_predio, nome_sala, data, turno, professor, email_professor])
    
    flash("Agendamento realizado com sucesso!", "success")
    return redirect(url_for('minhas_reservas'))

@app.route('/minhas-reservas')
def minhas_reservas():
    if 'usuario' not in session or session.get('tipo') != 'Professor':
        flash("Acesso restrito para professores logados.", "error")
        return redirect(url_for('index'))
    
    reservas = [r for r in obter_todas_reservas() if r.get('professor') == session['usuario']]
    return render_template('minhas_reservas.html', 
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           reservas=reservas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        with open('usuarios.csv', 'r', encoding='utf-8') as f:
            for linha in csv.DictReader(f):
                if (linha.get('nome') == usuario or linha.get('email') == usuario) and linha.get('senha') == senha:
                    session['usuario'] = linha.get('nome')
                    session['tipo'] = linha.get('tipo')
                    flash("Bem-vindo(a) de volta!", "success")
                    return redirect(url_for('index'))
        flash("Usuário/E-mail ou senha incorretos.", "error")
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        with open('usuarios.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([request.form['nome'], request.form['email'], request.form['senha'], request.form['tipo']])
        flash("Conta criada com sucesso! Faça seu login.", "success")
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
import os
import csv
import uuid
import socket
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'chave_secreta_agendamento'

# Prédios base do sistema
PREDIOS = {
    "predio_central": {"nome": "Prédio Central", "emoji": "🏛️"},
    "anexo_1": {"nome": "Anexo 1", "emoji": "🏢"},
    "anexo_2": {"nome": "Anexo 2 (Anfiteatro)", "emoji": "🎤"}
}

def iniciar_planilhas():
    if not os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['nome', 'email', 'senha', 'tipo'])
            senha_admin = generate_password_hash('joao123')
            writer.writerow(['João Vieira', 'vieirabotelhojoaovictor@gmail.com', senha_admin, 'Administrador'])

    if not os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status'])
            
    if not os.path.exists('convites.csv'):
        with open('convites.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['token', 'usado', 'expiracao', 'tipo_conta'])
            
    if not os.path.exists('trocas_salas.csv'):
        with open('trocas_salas.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_troca', 'id_reserva_alvo', 'id_reserva_origem', 'status_troca'])

    if not os.path.exists('salas.csv'):
        with open('salas.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_sala', 'predio', 'nome_sala', 'observacoes'])

iniciar_planilhas()

def obter_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def obter_salas():
    salas = []
    if os.path.exists('salas.csv'):
        with open('salas.csv', 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                salas.append(row)
    return salas

def obter_todas_reservas():
    reservas = []
    if os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for linha in reader:
                id_predio = linha.get('predio', 'predio_central')
                linha['predio_nome'] = PREDIOS.get(id_predio, {}).get('nome', id_predio)
                linha['sala'] = linha.get('sala', 'Não informada')
                linha['data'] = linha.get('data', '--/--/----')
                linha['turno'] = linha.get('turno', 'Indefinido')
                linha['professor'] = linha.get('professor', 'Anônimo')
                linha['status'] = linha.get('status', 'Aprovado')
                reservas.append(linha)
    return reservas

@app.route('/')
def index():
    todas_reservas = obter_todas_reservas()
    todas_salas = obter_salas()
    
    predios_dinamicos = {}
    for key, p in PREDIOS.items():
        predios_dinamicos[key] = p.copy()
        predios_dinamicos[key]['salas'] = [s for s in todas_salas if s['predio'] == key]
    
    minhas_aprovadas = []
    if session.get('usuario') and session.get('tipo') == 'Professor':
        minhas_aprovadas = [r for r in todas_reservas if r['professor'] == session['usuario'] and r['status'] == 'Aprovado']

    return render_template('index.html', 
                           usuario_logado=session.get('usuario'), 
                           tipo_usuario=session.get('tipo'), 
                           predios=predios_dinamicos,
                           reservas=todas_reservas,
                           minhas_aprovadas=minhas_aprovadas)

@app.route('/predio/<id_predio>')
def ver_predio(id_predio):
    if id_predio not in PREDIOS:
        return redirect(url_for('index'))
        
    salas_do_predio = [s for s in obter_salas() if s['predio'] == id_predio]
        
    return render_template('predio.html', 
                           predio=PREDIOS[id_predio], 
                           id_predio=id_predio,
                           salas=salas_do_predio,
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
    for r in obter_todas_reservas():
        if r['sala'] == nome_sala and r['data'] == data and r['turno'] == turno and r['status'] in ['Pendente', 'Aprovado']:
            ocupado = True
            break
    
    if ocupado:
        flash(f"A {nome_sala} já está reservada ou em análise para o dia {data} no turno da {turno}.", "error")
        return redirect(url_for('ver_predio', id_predio=id_predio))

    id_reserva = str(uuid.uuid4())
    status = 'Pendente'
    
    with open('agendamentos.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([id_reserva, id_predio, nome_sala, data, turno, professor, email_professor, status])
    
    flash("Reserva enviada! Aguardando aprovação do administrador.", "success")
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

@app.route('/notificacoes')
def notificacoes():
    if session.get('tipo') != 'Professor':
        return redirect(url_for('index'))
        
    todas_reservas = obter_todas_reservas()
    reservas_dict = {r['id_reserva']: r for r in todas_reservas}
    
    minhas_notificacoes = []
    if os.path.exists('trocas_salas.csv'):
        with open('trocas_salas.csv', 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                if row['status_troca'] == 'Pendente':
                    alvo = reservas_dict.get(row['id_reserva_alvo'])
                    origem = reservas_dict.get(row['id_reserva_origem'])
                    
                    if alvo and origem and alvo['professor'] == session['usuario']:
                        minhas_notificacoes.append({
                            'id_troca': row['id_troca'],
                            'prof_origem': origem['professor'],
                            'sala_origem': origem['sala'],
                            'data_origem': origem['data'],
                            'turno_origem': origem['turno'],
                            'minha_sala': alvo['sala'],
                            'minha_data': alvo['data'],
                            'meu_turno': alvo['turno']
                        })
                        
    return render_template('notificacoes.html', 
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           notificacoes=minhas_notificacoes)

@app.route('/responder_troca/<id_troca>/<resposta>')
def responder_troca(id_troca, resposta):
    if session.get('tipo') != 'Professor':
        return redirect(url_for('index'))
        
    linhas_trocas = []
    troca_encontrada = None
    with open('trocas_salas.csv', 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['id_troca'] == id_troca and row['status_troca'] == 'Pendente':
                row['status_troca'] = 'Aceito' if resposta == 'aceitar' else 'Rejeitado'
                troca_encontrada = row
            linhas_trocas.append(row)
            
    if troca_encontrada:
        with open('trocas_salas.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_troca', 'id_reserva_alvo', 'id_reserva_origem', 'status_troca'])
            for r in linhas_trocas:
                writer.writerow([r['id_troca'], r['id_reserva_alvo'], r['id_reserva_origem'], r['status_troca']])
                
        if resposta == 'aceitar':
            todas_reservas = obter_todas_reservas()
            prof_alvo, email_alvo = "", ""
            prof_origem, email_origem = "", ""
            
            for r in todas_reservas:
                if r['id_reserva'] == troca_encontrada['id_reserva_alvo']:
                    prof_alvo, email_alvo = r['professor'], r['email']
                if r['id_reserva'] == troca_encontrada['id_reserva_origem']:
                    prof_origem, email_origem = r['professor'], r['email']
                    
            with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status'])
                for r in todas_reservas:
                    if r['id_reserva'] == troca_encontrada['id_reserva_alvo']:
                        r['professor'], r['email'] = prof_origem, email_origem
                    elif r['id_reserva'] == troca_encontrada['id_reserva_origem']:
                        r['professor'], r['email'] = prof_alvo, email_alvo
                    writer.writerow([r['id_reserva'], r['predio'], r['sala'], r['data'], r['turno'], r['professor'], r['email'], r['status']])
                    
            flash("Troca de sala realizada com sucesso!", "success")
        else:
            flash("Proposta de troca rejeitada.", "success")
            
    return redirect(url_for('notificacoes'))

@app.route('/solicitar_troca', methods=['POST'])
def solicitar_troca():
    if session.get('tipo') != 'Professor':
        return redirect(url_for('index'))
        
    id_alvo = request.form['id_reserva_alvo']
    minha_reserva = request.form['minha_reserva_id']
    
    with open('trocas_salas.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([str(uuid.uuid4()), id_alvo, minha_reserva, 'Pendente'])
        
    flash("Sua proposta de troca foi enviada ao professor responsável!", "success")
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form['usuario'].strip().lower()
        senha_input = request.form['senha']
        
        with open('usuarios.csv', 'r', encoding='utf-8') as f:
            for linha in csv.DictReader(f):
                nome_db = linha.get('nome', '').strip().lower()
                email_db = linha.get('email', '').strip().lower()
                
                if (nome_db == usuario_input or email_db == usuario_input):
                    if check_password_hash(linha.get('senha', ''), senha_input):
                        session['usuario'] = linha.get('nome')
                        session['tipo'] = linha.get('tipo')
                        flash("Bem-vindo(a) de volta!", "success")
                        return redirect(url_for('index'))
                    
        flash("Usuário/E-mail ou senha incorretos.", "error")
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def painel_admin():
    if session.get('tipo') != 'Administrador':
        flash("Acesso restrito ao Administrador.", "error")
        return redirect(url_for('index'))
    
    link_convite = None
    tipo_convite_gerado = None
    
    if request.method == 'POST' and 'tipo_conta' in request.form:
        tipo_conta = request.form.get('tipo_conta', 'Professor')
        novo_token = str(uuid.uuid4())
        expiracao = (datetime.now() + timedelta(minutes=15)).isoformat()
        
        with open('convites.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([novo_token, 'False', expiracao, tipo_conta])
            
        ip_maquina = obter_ip_local()
        caminho_registro = url_for('registro', token=novo_token)
        link_convite = f"http://{ip_maquina}:5000{caminho_registro}"
        tipo_convite_gerado = tipo_conta
        
        flash(f"Convite para {tipo_conta} gerado! Válido por 15 minutos.", "success")
        
    reservas_pendentes = [r for r in obter_todas_reservas() if r['status'] == 'Pendente']
        
    return render_template('admin.html', 
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           link_convite=link_convite,
                           tipo_convite_gerado=tipo_convite_gerado,
                           reservas_pendentes=reservas_pendentes,
                           predios=PREDIOS)

@app.route('/admin/nova_sala', methods=['POST'])
def nova_sala():
    if session.get('tipo') != 'Administrador':
        return redirect(url_for('index'))
    
    predio = request.form['predio']
    nome_sala = request.form['nome_sala'].strip()
    observacoes = request.form['observacoes'].strip()
    id_sala = str(uuid.uuid4())
    
    with open('salas.csv', 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([id_sala, predio, nome_sala, observacoes])
    
    flash(f"Sala '{nome_sala}' adicionada com sucesso ao prédio selecionado!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/admin/acao_reserva/<id_reserva>/<acao>')
def acao_reserva(id_reserva, acao):
    if session.get('tipo') != 'Administrador':
        return redirect(url_for('index'))
        
    todas_reservas = obter_todas_reservas()
    
    with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status'])
        for r in todas_reservas:
            if r['id_reserva'] == id_reserva:
                r['status'] = 'Aprovado' if acao == 'aprovar' else 'Rejeitado'
            writer.writerow([r['id_reserva'], r['predio'], r['sala'], r['data'], r['turno'], r['professor'], r['email'], r['status']])
            
    flash("Status da reserva atualizado!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    token = request.args.get('token') or request.form.get('token')
    token_valido, token_expirado, linhas_convites = False, False, []
    tipo_conta_token = 'Professor'
    
    if os.path.exists('convites.csv'):
        # utf-8-sig ignora caracteres invisíveis (BOM) colocados pelo Excel/Windows
        with open('convites.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                # .get() previne KeyError se a estrutura do arquivo estiver corrompida
                row_token = row.get('token')
                if row_token and row_token == token and row.get('usado') == 'False':
                    try:
                        if datetime.now() > datetime.fromisoformat(row.get('expiracao', '')):
                            token_expirado = True
                        else:
                            token_valido = True
                            tipo_conta_token = row.get('tipo_conta', 'Professor')
                    except ValueError:
                        pass
                linhas_convites.append(row)
                
    if token_expirado:
        flash("Este link de convite expirou.", "error")
        return redirect(url_for('login'))
    if not token_valido:
        flash("Link de convite inválido ou já utilizado.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        email = request.form['email'].strip().lower()
        senha_hash = generate_password_hash(request.form['senha'])
        
        with open('usuarios.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([nome, email, senha_hash, tipo_conta_token])
            
        with open('convites.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['token', 'usado', 'expiracao', 'tipo_conta'])
            for r in linhas_convites:
                if r.get('token') == token:
                    r['usado'] = 'True'
                writer.writerow([r.get('token'), r.get('usado'), r.get('expiracao', ''), r.get('tipo_conta', 'Professor')])

        flash(f"Conta de {tipo_conta_token} criada! Faça seu login.", "success")
        return redirect(url_for('login'))
        
    return render_template('registro.html', token=token, tipo_conta=tipo_conta_token)

@app.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada com sucesso.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
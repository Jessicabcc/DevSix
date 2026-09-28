import os
import csv
import re
import uuid
import socket
import unicodedata
from io import BytesIO
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = 'chave_secreta_agendamento'

PREDIOS_PADRAO = [
    {"id_predio": "predio_central", "nome": "Prédio Central", "emoji": "🏛️"},
    {"id_predio": "anexo_1", "nome": "Anexo 1", "emoji": "🏢"},
    {"id_predio": "anexo_2", "nome": "Anexo 2 (Anfiteatro)", "emoji": "🎤"}
]

CATEGORIAS_SALA = {
    "Laboratorio": {"label": "Laboratório", "cor": "vermelho", "emoji": "🔬"},
    "Normal": {"label": "Sala Normal", "cor": "verde", "emoji": "📗"},
    "Metodologia": {"label": "Metodologia Ativa", "cor": "azul", "emoji": "💡"},
    "Quadra": {"label": "Quadra/Piscina", "cor": "laranja", "emoji": "🏀"}
}

def iniciar_planilhas():
    if not os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['nome', 'email', 'senha', 'tipo', 'foto'])
            senha_admin = generate_password_hash('joao123')
            writer.writerow(['João Vieira', 'vieirabotelhojoaovictor@gmail.com', senha_admin, 'Administrador', ''])

    if not os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status', 'solicitado_em', 'responsavel', 'decidido_em'])

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
            writer.writerow(['id_sala', 'predio', 'nome_sala', 'observacoes', 'categoria', 'status'])

    if not os.path.exists('predios.csv'):
        with open('predios.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_predio', 'nome', 'emoji'])
            for p in PREDIOS_PADRAO:
                writer.writerow([p['id_predio'], p['nome'], p['emoji']])

    if not os.path.exists('favoritos.csv'):
        with open('favoritos.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['professor', 'id_sala'])

    if not os.path.exists('historico_alteracoes.csv'):
        with open('historico_alteracoes.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['data_hora', 'usuario', 'tipo_usuario', 'acao', 'detalhes'])

iniciar_planilhas()

def eh_admin():
    return session.get('tipo') == 'Administrador'

def eh_gestor():
    return session.get('tipo') in ['Administrador', 'Coordenador']

def gerar_slug(texto):
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', sem_acento).strip('_').lower()
    return slug or str(uuid.uuid4())[:8]

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

def registrar_historico(acao, detalhes):
    with open('historico_alteracoes.csv', 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            session.get('usuario', 'Sistema'),
            session.get('tipo', ''),
            acao,
            detalhes
        ])

def obter_historico_alteracoes():
    historico = []
    if os.path.exists('historico_alteracoes.csv'):
        with open('historico_alteracoes.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                historico.append(row)
    historico.reverse()
    return historico

def obter_predios():
    predios = {}
    if os.path.exists('predios.csv'):
        with open('predios.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row.get('id_predio'):
                    predios[row['id_predio']] = {
                        'nome': row.get('nome', ''),
                        'emoji': row.get('emoji') or '🏢'
                    }
    return predios

def obter_salas():
    salas = []
    if os.path.exists('salas.csv'):
        with open('salas.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                row['categoria'] = row.get('categoria') or 'Normal'
                row['status'] = row.get('status') or 'Ativa'
                salas.append(row)
    return salas

def obter_todas_reservas():
    reservas = []
    predios_cadastrados = obter_predios()
    if os.path.exists('agendamentos.csv'):
        with open('agendamentos.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for linha in reader:
                id_predio = linha.get('predio', 'predio_central')
                linha['predio_nome'] = predios_cadastrados.get(id_predio, {}).get('nome', id_predio)
                linha['sala'] = linha.get('sala', 'Não informada')
                linha['data'] = linha.get('data', '--/--/----')
                linha['turno'] = linha.get('turno', 'Indefinido')
                linha['professor'] = linha.get('professor', 'Anônimo')
                linha['status'] = linha.get('status', 'Aprovado')
                linha['solicitado_em'] = linha.get('solicitado_em', '')
                linha['responsavel'] = linha.get('responsavel', '')
                linha['decidido_em'] = linha.get('decidido_em', '')
                reservas.append(linha)
    return reservas

def obter_favoritos():
    favoritos = []
    if os.path.exists('favoritos.csv'):
        with open('favoritos.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                favoritos.append(row)
    return favoritos

def calcular_metricas(todas_reservas):
    hoje = datetime.now().date()
    total = len(todas_reservas)
    aprovadas = len([r for r in todas_reservas if r.get('status') == 'Aprovado'])
    pendentes = len([r for r in todas_reservas if r.get('status') == 'Pendente'])
    rejeitadas = len([r for r in todas_reservas if r.get('status') == 'Rejeitado'])

    semana, mes = 0, 0
    for r in todas_reservas:
        try:
            data_reserva = datetime.strptime(r.get('data', ''), '%Y-%m-%d').date()
            diff = (hoje - data_reserva).days
            if 0 <= diff <= 7:
                semana += 1
            if 0 <= diff <= 30:
                mes += 1
        except ValueError:
            continue

    return {
        'total': total,
        'aprovadas': aprovadas,
        'pendentes': pendentes,
        'rejeitadas': rejeitadas,
        'semana': semana,
        'mes': mes
    }

def calcular_ranking_ocupacao(todas_reservas, todas_salas):
    contagem = {}
    for r in todas_reservas:
        if r.get('status') == 'Aprovado':
            sala = r.get('sala')
            contagem[sala] = contagem.get(sala, 0) + 1

    valores = list(contagem.values())
    media = sum(valores) / len(valores) if valores else 0

    ranking = []
    for sala in todas_salas:
        nome_sala = sala.get('nome_sala')
        total_reservas = contagem.get(nome_sala, 0)
        status_cor = 'vermelho' if (total_reservas > media and total_reservas > 0) else 'verde'
        ranking.append({
            'nome_sala': nome_sala,
            'predio': sala.get('predio'),
            'categoria': sala.get('categoria'),
            'status_sala': sala.get('status'),
            'total_reservas': total_reservas,
            'status_cor': status_cor
        })
    ranking.sort(key=lambda x: x['total_reservas'], reverse=True)
    return ranking

@app.route('/')
def index():
    todas_reservas = obter_todas_reservas()
    todas_salas = obter_salas()
    predios_cadastrados = obter_predios()

    predios_dinamicos = {}
    for key, p in predios_cadastrados.items():
        predios_dinamicos[key] = p.copy()
        predios_dinamicos[key]['salas'] = [s for s in todas_salas if s.get('predio') == key]

    minhas_aprovadas = []
    if session.get('usuario') and session.get('tipo') == 'Professor':
        minhas_aprovadas = [r for r in todas_reservas if r.get('professor') == session['usuario'] and r.get('status') == 'Aprovado']

    return render_template('index.html',
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           predios=predios_dinamicos,
                           reservas=todas_reservas,
                           minhas_aprovadas=minhas_aprovadas)

@app.route('/predio/<id_predio>')
def ver_predio(id_predio):
    predios = obter_predios()
    if id_predio not in predios:
        return redirect(url_for('index'))

    salas_do_predio = [s for s in obter_salas() if s.get('predio') == id_predio]

    favoritos_ids = []
    if session.get('tipo') == 'Professor':
        favoritos_ids = [f.get('id_sala') for f in obter_favoritos() if f.get('professor') == session.get('usuario')]

    return render_template('predio.html',
                           predio=predios[id_predio],
                           id_predio=id_predio,
                           salas=salas_do_predio,
                           favoritos_ids=favoritos_ids,
                           categorias=CATEGORIAS_SALA,
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'))

@app.route('/favoritar/<id_sala>')
def favoritar_sala(id_sala):
    if session.get('tipo') != 'Professor':
        return redirect(url_for('index'))

    professor = session['usuario']
    favoritos = obter_favoritos()
    ja_favoritada = any(f.get('professor') == professor and f.get('id_sala') == id_sala for f in favoritos)

    if ja_favoritada:
        favoritos = [f for f in favoritos if not (f.get('professor') == professor and f.get('id_sala') == id_sala)]
        with open('favoritos.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['professor', 'id_sala'])
            for fav in favoritos:
                writer.writerow([fav.get('professor'), fav.get('id_sala')])
        flash("Sala removida dos favoritos.", "success")
    else:
        with open('favoritos.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([professor, id_sala])
        flash("Sala adicionada aos favoritos!", "success")

    return redirect(request.referrer or url_for('index'))

@app.route('/perfil')
def perfil():
    if 'usuario' not in session:
        flash("Você precisa estar logado para acessar seu perfil.", "error")
        return redirect(url_for('login'))

    contexto = {
        'usuario_logado': session.get('usuario'),
        'tipo_usuario': session.get('tipo'),
    }

    if session.get('tipo') == 'Professor':
        professor = session['usuario']
        todas_reservas = obter_todas_reservas()
        minhas_reservas_todas = [r for r in todas_reservas if r.get('professor') == professor]
        aprovadas = [r for r in minhas_reservas_todas if r.get('status') == 'Aprovado']

        todas_salas = obter_salas()
        predios_cadastrados = obter_predios()
        favoritos = [f for f in obter_favoritos() if f.get('professor') == professor]
        salas_favoritas = []
        for fav in favoritos:
            sala_info = next((s for s in todas_salas if s.get('id_sala') == fav.get('id_sala')), None)
            if sala_info:
                sala_copia = sala_info.copy()
                sala_copia['predio_nome'] = predios_cadastrados.get(sala_info.get('predio'), {}).get('nome', sala_info.get('predio'))
                salas_favoritas.append(sala_copia)

        contexto['reservas_aprovadas'] = aprovadas
        contexto['salas_favoritas'] = salas_favoritas
        contexto['categorias'] = CATEGORIAS_SALA

    return render_template('perfil.html', **contexto)

@app.route('/dashboard_admin')
def dashboard_admin():
    if not eh_gestor():
        flash("Acesso restrito ao Administrador/Coordenador.", "error")
        return redirect(url_for('index'))

    todas_reservas = obter_todas_reservas()
    todas_salas = obter_salas()
    predios_cadastrados = obter_predios()

    metricas = calcular_metricas(todas_reservas)
    ranking = calcular_ranking_ocupacao(todas_reservas, todas_salas)

    for item in ranking:
        item['predio_nome'] = predios_cadastrados.get(item['predio'], {}).get('nome', item['predio'])

    historico_recente = obter_historico_alteracoes()[:8]

    return render_template('dashboard_admin.html',
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           metricas=metricas,
                           ranking=ranking,
                           total_salas=len(todas_salas),
                           total_predios=len(predios_cadastrados),
                           historico_recente=historico_recente)

@app.route('/admin/relatorio_pdf')
def relatorio_pdf():
    if not eh_gestor():
        flash("Acesso restrito ao Administrador/Coordenador.", "error")
        return redirect(url_for('index'))

    todas_reservas = obter_todas_reservas()
    historico = obter_historico_alteracoes()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    estilos = getSampleStyleSheet()

    titulo_estilo = ParagraphStyle('TituloCustom', parent=estilos['Title'],
                                    textColor=colors.HexColor('#1e3a8a'), fontSize=18)
    subtitulo_estilo = ParagraphStyle('SubtituloCustom', parent=estilos['Heading2'],
                                       textColor=colors.HexColor('#1d4ed8'), spaceBefore=20, spaceAfter=10)
    normal_estilo = estilos['Normal']

    elementos = []
    elementos.append(Paragraph("Relatório de Agendamento de Salas - UniSapiens", titulo_estilo))
    elementos.append(Paragraph("Campus Jd. das Mangueiras - Porto Velho/RO", normal_estilo))
    elementos.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} por {session.get('usuario')} ({session.get('tipo')})",
        normal_estilo))
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("Histórico de Reservas", subtitulo_estilo))
    dados_reservas = [['Data / Turno', 'Sala', 'Professor', 'Status', 'Responsável', 'Decidido em']]
    for r in todas_reservas:
        dados_reservas.append([
            f"{r.get('data', '')} - {r.get('turno', '')}",
            r.get('sala', ''),
            r.get('professor', ''),
            r.get('status', ''),
            r.get('responsavel', '') or '-',
            r.get('decidido_em', '') or '-'
        ])

    if len(dados_reservas) == 1:
        elementos.append(Paragraph("Nenhuma reserva registrada até o momento.", normal_estilo))
    else:
        tabela_reservas = Table(dados_reservas, repeatRows=1,
                                 colWidths=[3.3 * cm, 3.2 * cm, 3.5 * cm, 2.2 * cm, 3 * cm, 2.8 * cm])
        tabela_reservas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eff6ff')]),
        ]))
        elementos.append(tabela_reservas)

    elementos.append(Spacer(1, 25))
    elementos.append(Paragraph("Registro de Alterações e Atualizações de Estrutura", subtitulo_estilo))
    dados_historico = [['Data/Hora', 'Usuário', 'Ação', 'Detalhes']]
    for h in historico:
        dados_historico.append([
            h.get('data_hora', ''),
            f"{h.get('usuario', '')} ({h.get('tipo_usuario', '')})",
            h.get('acao', ''),
            h.get('detalhes', '')
        ])

    if len(dados_historico) == 1:
        elementos.append(Paragraph("Nenhuma alteração estrutural registrada até o momento.", normal_estilo))
    else:
        tabela_historico = Table(dados_historico, repeatRows=1,
                                  colWidths=[3 * cm, 3.7 * cm, 3 * cm, 7.3 * cm])
        tabela_historico.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eff6ff')]),
        ]))
        elementos.append(tabela_historico)

    doc.build(elementos)
    buffer.seek(0)

    nome_arquivo = f"relatorio_unisapiens_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype='application/pdf')

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

    sala_info = next((s for s in obter_salas() if s.get('nome_sala') == nome_sala and s.get('predio') == id_predio), None)
    if sala_info and sala_info.get('status') == 'Bloqueada':
        flash(f"A {nome_sala} está bloqueada para manutenção e não pode ser reservada no momento.", "error")
        return redirect(url_for('ver_predio', id_predio=id_predio))

    email_professor = ""
    with open('usuarios.csv', 'r', encoding='utf-8-sig') as f:
        for linha in csv.DictReader(f):
            if linha.get('nome') == professor:
                email_professor = linha.get('email', '')
                break

    ocupado = False
    for r in obter_todas_reservas():
        if r.get('sala') == nome_sala and r.get('data') == data and r.get('turno') == turno and r.get('status') in ['Pendente', 'Aprovado']:
            ocupado = True
            break

    if ocupado:
        flash(f"A {nome_sala} já está reservada ou em análise para o dia {data} no turno da {turno}.", "error")
        return redirect(url_for('ver_predio', id_predio=id_predio))

    id_reserva = str(uuid.uuid4())
    status = 'Pendente'
    solicitado_em = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open('agendamentos.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([id_reserva, id_predio, nome_sala, data, turno, professor, email_professor, status, solicitado_em, '', ''])

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
        with open('trocas_salas.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row.get('status_troca') == 'Pendente':
                    alvo = reservas_dict.get(row.get('id_reserva_alvo'))
                    origem = reservas_dict.get(row.get('id_reserva_origem'))

                    if alvo and origem and alvo.get('professor') == session['usuario']:
                        minhas_notificacoes.append({
                            'id_troca': row.get('id_troca'),
                            'prof_origem': origem.get('professor'),
                            'sala_origem': origem.get('sala'),
                            'data_origem': origem.get('data'),
                            'turno_origem': origem.get('turno'),
                            'minha_sala': alvo.get('sala'),
                            'minha_data': alvo.get('data'),
                            'meu_turno': alvo.get('turno')
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
    with open('trocas_salas.csv', 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('id_troca') == id_troca and row.get('status_troca') == 'Pendente':
                row['status_troca'] = 'Aceito' if resposta == 'aceitar' else 'Rejeitado'
                troca_encontrada = row
            linhas_trocas.append(row)

    if troca_encontrada:
        with open('trocas_salas.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_troca', 'id_reserva_alvo', 'id_reserva_origem', 'status_troca'])
            for r in linhas_trocas:
                writer.writerow([r.get('id_troca'), r.get('id_reserva_alvo'), r.get('id_reserva_origem'), r.get('status_troca')])

        if resposta == 'aceitar':
            todas_reservas = obter_todas_reservas()
            prof_alvo, email_alvo = "", ""
            prof_origem, email_origem = "", ""

            for r in todas_reservas:
                if r.get('id_reserva') == troca_encontrada.get('id_reserva_alvo'):
                    prof_alvo, email_alvo = r.get('professor'), r.get('email')
                if r.get('id_reserva') == troca_encontrada.get('id_reserva_origem'):
                    prof_origem, email_origem = r.get('professor'), r.get('email')

            with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status', 'solicitado_em', 'responsavel', 'decidido_em'])
                for r in todas_reservas:
                    if r.get('id_reserva') == troca_encontrada.get('id_reserva_alvo'):
                        r['professor'], r['email'] = prof_origem, email_origem
                    elif r.get('id_reserva') == troca_encontrada.get('id_reserva_origem'):
                        r['professor'], r['email'] = prof_alvo, email_alvo
                    writer.writerow([r.get('id_reserva'), r.get('predio'), r.get('sala'), r.get('data'), r.get('turno'), r.get('professor'), r.get('email'), r.get('status'), r.get('solicitado_em', ''), r.get('responsavel', ''), r.get('decidido_em', '')])

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

        with open('usuarios.csv', 'r', encoding='utf-8-sig') as f:
            for linha in csv.DictReader(f):
                nome_db = linha.get('nome', '').strip().lower()
                email_db = linha.get('email', '').strip().lower()

                if (nome_db == usuario_input or email_db == usuario_input):
                    if check_password_hash(linha.get('senha', ''), senha_input):
                        session['usuario'] = linha.get('nome')
                        session['email'] = linha.get('email')
                        session['tipo'] = linha.get('tipo')
                        session['foto'] = linha.get('foto', '')
                        flash("Bem-vindo(a) de volta!", "success")
                        return redirect(url_for('index'))

        flash("Usuário/E-mail ou senha incorretos.", "error")
    return render_template('login.html')

@app.route('/atualizar_perfil', methods=['POST'])
def atualizar_perfil():
    if 'usuario' not in session:
        flash("Sessão expirada. Faça login novamente.", "error")
        return redirect(url_for('login'))

    novo_nome = request.form.get('nome', '').strip()
    foto_arquivo = request.files.get('foto')

    usuario_atual = session['usuario']
    email_atual = session.get('email')
    nome_salvo = usuario_atual
    filename_foto = session.get('foto', '')

    if foto_arquivo and foto_arquivo.filename != '':
        ext = os.path.splitext(foto_arquivo.filename)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            filename_foto = f"{uuid.uuid4()}{ext}"
            upload_dir = os.path.join(app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            foto_arquivo.save(os.path.join(upload_dir, filename_foto))
        else:
            flash("Formato de imagem inválido. Use PNG, JPG, JPEG, GIF ou WEBP.", "error")
            return redirect(request.referrer or url_for('perfil'))

    if novo_nome:
        nome_salvo = novo_nome

    usuarios = []
    if os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or ['nome', 'email', 'senha', 'tipo', 'foto']
            if 'foto' not in fieldnames:
                fieldnames.append('foto')

            for u in reader:
                if u.get('nome') == usuario_atual or (email_atual and u.get('email') == email_atual):
                    u['nome'] = nome_salvo
                    u['foto'] = filename_foto
                elif 'foto' not in u:
                    u['foto'] = ''
                usuarios.append(u)

        with open('usuarios.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(usuarios)

    if novo_nome and novo_nome != usuario_atual:
        reservas = []
        if os.path.exists('agendamentos.csv'):
            with open('agendamentos.csv', 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames_ag = reader.fieldnames or ['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status', 'solicitado_em', 'responsavel', 'decidido_em']
                for r in reader:
                    if r.get('professor') == usuario_atual:
                        r['professor'] = nome_salvo
                    reservas.append(r)
            with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames_ag)
                writer.writeheader()
                writer.writerows(reservas)

    session['usuario'] = nome_salvo
    session['foto'] = filename_foto

    flash("Perfil atualizado com sucesso!", "success")
    return redirect(request.referrer or url_for('perfil'))

@app.route('/admin', methods=['GET', 'POST'])
def painel_admin():
    if not eh_gestor():
        flash("Acesso restrito ao Administrador/Coordenador.", "error")
        return redirect(url_for('index'))

    link_convite = None
    tipo_convite_gerado = None

    if request.method == 'POST' and 'tipo_conta' in request.form:
        tipo_conta = request.form.get('tipo_conta', 'Professor')

        if tipo_conta in ['Coordenador', 'Administrador'] and not eh_admin():
            flash("Apenas o Administrador pode gerar convites para Coordenador ou Administrador.", "error")
            return redirect(url_for('painel_admin'))

        novo_token = str(uuid.uuid4())
        expiracao = (datetime.now() + timedelta(minutes=15)).isoformat()

        with open('convites.csv', 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([novo_token, 'False', expiracao, tipo_conta])

        ip_maquina = obter_ip_local()
        caminho_registro = url_for('registro', token=novo_token)
        link_convite = f"http://{ip_maquina}:5000{caminho_registro}"
        tipo_convite_gerado = tipo_conta

        flash(f"Convite para {tipo_conta} gerado! Válido por 15 minutos.", "success")

    reservas_pendentes = [r for r in obter_todas_reservas() if r.get('status') == 'Pendente']
    todas_salas = obter_salas()
    predios_cadastrados = obter_predios()

    return render_template('admin.html',
                           usuario_logado=session.get('usuario'),
                           tipo_usuario=session.get('tipo'),
                           eh_admin=eh_admin(),
                           link_convite=link_convite,
                           tipo_convite_gerado=tipo_convite_gerado,
                           reservas_pendentes=reservas_pendentes,
                           predios=predios_cadastrados,
                           salas=todas_salas,
                           categorias=CATEGORIAS_SALA)

@app.route('/admin/nova_sala', methods=['POST'])
def nova_sala():
    if not eh_gestor():
        return redirect(url_for('index'))

    predio = request.form['predio']
    nome_sala = request.form['nome_sala'].strip()
    observacoes = request.form['observacoes'].strip()
    categoria = request.form.get('categoria', 'Normal')
    if categoria not in CATEGORIAS_SALA:
        categoria = 'Normal'
    id_sala = str(uuid.uuid4())

    with open('salas.csv', 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([id_sala, predio, nome_sala, observacoes, categoria, 'Ativa'])

    predios_cadastrados = obter_predios()
    nome_predio = predios_cadastrados.get(predio, {}).get('nome', predio)
    registrar_historico("Nova Sala", f"Sala '{nome_sala}' cadastrada em {nome_predio} (categoria: {CATEGORIAS_SALA.get(categoria, {}).get('label', categoria)})")

    flash(f"Sala '{nome_sala}' adicionada com sucesso ao prédio selecionado!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/admin/sala/<id_sala>/<acao>')
def alterar_status_sala(id_sala, acao):
    if not eh_admin():
        flash("Apenas o Administrador pode bloquear ou desbloquear salas.", "error")
        return redirect(url_for('index'))

    if acao not in ['bloquear', 'desbloquear']:
        return redirect(url_for('painel_admin'))

    salas = obter_salas()
    nome_sala_alterada = None
    with open('salas.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id_sala', 'predio', 'nome_sala', 'observacoes', 'categoria', 'status'])
        for s in salas:
            if s.get('id_sala') == id_sala:
                s['status'] = 'Bloqueada' if acao == 'bloquear' else 'Ativa'
                nome_sala_alterada = s.get('nome_sala')
            writer.writerow([s.get('id_sala'), s.get('predio'), s.get('nome_sala'), s.get('observacoes'), s.get('categoria'), s.get('status')])

    if nome_sala_alterada:
        acao_label = "bloqueada para manutenção" if acao == 'bloquear' else "desbloqueada"
        registrar_historico("Bloqueio de Sala" if acao == 'bloquear' else "Desbloqueio de Sala",
                             f"Sala '{nome_sala_alterada}' foi {acao_label}")

    flash("Status da sala atualizado!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/admin/novo_predio', methods=['POST'])
def novo_predio():
    if not eh_gestor():
        return redirect(url_for('index'))

    nome = request.form.get('nome_predio', '').strip()
    emoji = request.form.get('emoji_predio', '🏢').strip() or '🏢'

    if not nome:
        flash("Informe o nome do novo prédio.", "error")
        return redirect(url_for('painel_admin'))

    predios_existentes = obter_predios()
    id_predio = gerar_slug(nome)
    if id_predio in predios_existentes:
        id_predio = f"{id_predio}_{str(uuid.uuid4())[:4]}"

    with open('predios.csv', 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([id_predio, nome, emoji])

    registrar_historico("Novo Prédio", f"Prédio '{nome}' cadastrado no sistema")

    flash(f"Prédio '{nome}' cadastrado com sucesso!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/admin/acao_reserva/<id_reserva>/<acao>')
def acao_reserva(id_reserva, acao):
    if not eh_gestor():
        return redirect(url_for('index'))

    todas_reservas = obter_todas_reservas()
    responsavel = session.get('usuario', '')
    decidido_em = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open('agendamentos.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id_reserva', 'predio', 'sala', 'data', 'turno', 'professor', 'email', 'status', 'solicitado_em', 'responsavel', 'decidido_em'])
        for r in todas_reservas:
            if r.get('id_reserva') == id_reserva:
                r['status'] = 'Aprovado' if acao == 'aprovar' else 'Rejeitado'
                r['responsavel'] = responsavel
                r['decidido_em'] = decidido_em
            writer.writerow([r.get('id_reserva'), r.get('predio'), r.get('sala'), r.get('data'), r.get('turno'), r.get('professor'), r.get('email'), r.get('status'), r.get('solicitado_em', ''), r.get('responsavel', ''), r.get('decidido_em', '')])

    flash("Status da reserva atualizado!", "success")
    return redirect(url_for('painel_admin'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    token = request.args.get('token') or request.form.get('token')
    token_valido, token_expirado, linhas_convites = False, False, []
    tipo_conta_token = 'Professor'

    if os.path.exists('convites.csv'):
        with open('convites.csv', 'r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
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
            csv.writer(f).writerow([nome, email, senha_hash, tipo_conta_token, ''])

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
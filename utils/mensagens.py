"""Mensagens da interface centralizadas para facilitar alterações futuras."""

# ---------- Mensagens usadas em mais de uma tela ----------
MSG_NENHUMA_SOLICITACAO_PENDENTE = "Nenhuma solicitação pendente."
MSG_NENHUMA_TROCA_PENDENTE = "Nenhuma solicitação de troca de sala pendente."
MSG_NENHUMA_SALA = "Nenhuma sala cadastrada."
MSG_SEM_RESERVAS_APROVADAS = "Você ainda não possui reservas aprovadas."
MSG_DEFINIR_URL_PUBLICA = (
    "Defina STREAMLIT_PUBLIC_URL para gerar um QR acessível por outros dispositivos."
)
MSG_PREDIO_INVALIDO = "Informe um nome de prédio válido."
MSG_PREDIO_CADASTRADO = "Prédio {nome} cadastrado."

# ---------- Login / acesso (app.py) ----------
MSG_QR_EXPIRADO = (
    "Este QR Code expirou ou já foi utilizado. "
    "Gere outro no perfil do dispositivo conectado."
)
MSG_CREDENCIAIS_INVALIDAS = "Credenciais inválidas."

# ---------- Registro por convite (registro_view.py) ----------
MSG_CONVITE_AUSENTE = "Use um convite válido para criar sua conta."
MSG_REGISTRO_DADOS_INVALIDOS = "Informe nome, e-mail válido e senha."
MSG_CONVITE_EXPIRADO = "Este convite expirou."
MSG_CONVITE_INVALIDO = "O convite é inválido ou já foi utilizado."
MSG_REGISTRO_NEGADO = (
    "O nome ou e-mail já está cadastrado, "
    "ou o convite não tem permissão para este papel."
)

# ---------- Administração (admin_view.py) ----------
MSG_CADASTRAR_PREDIO_ANTES = "Cadastre um prédio antes de adicionar salas."
MSG_SALA_CADASTRADA = "Sala {nome} cadastrada."
MSG_SALA_INVALIDA = "Informe um nome único e selecione um prédio válido."
MSG_TITULARIDADE_ATUALIZADA = "Titularidade das reservas atualizada."
MSG_TROCA_NAO_APLICADA = "Não foi possível aplicar a troca."
MSG_CONVITE_CRIADO = "Convite criado. Ele expira em 15 minutos e só pode ser usado uma vez."
MSG_CONVITE_SEM_PERMISSAO = "Seu perfil não pode gerar esse tipo de convite."
MSG_CONTA_EXCLUIDA = "{nome} excluído."
MSG_NENHUMA_ALTERACAO = "Nenhuma alteração registrada."

# ---------- Secretário (secretario_view.py) ----------
MSG_NENHUMA_RESERVA_PROCESSADA = "Nenhuma reserva processada ainda."
MSG_USUARIO_SENHA_OBRIGATORIOS = "Informe um usuário e uma senha."
MSG_PROFESSOR_CADASTRADO = "Professor cadastrado com sucesso."
MSG_PROFESSOR_NAO_CADASTRADO = "Usuário já existe ou você não tem permissão para esta ação."
MSG_PROFESSOR_EXCLUIDO = "Professor excluído com sucesso."

# ---------- Páginas gerais (streamlit_pages.py) ----------
MSG_NENHUMA_AREA = "Nenhuma área disponível."
MSG_NENHUMA_RESERVA_REGISTRADA = "Nenhuma reserva registrada."
MSG_TROCA_SEM_RESERVA_APROVADA = "Você precisa ter uma reserva aprovada para propor uma troca."
MSG_NENHUMA_SALA_NOS_FILTROS = "Nenhuma sala corresponde aos filtros."
MSG_SALA_BLOQUEADA = "Esta sala está bloqueada para agendamentos."
MSG_SEM_SOLICITACOES_RESERVA = "Você ainda não possui solicitações de reserva."
MSG_NENHUMA_PROPOSTA_TROCA = "Nenhuma proposta de troca no momento."
MSG_PERFIL_ATUALIZADO = "Perfil atualizado."
MSG_SEM_FAVORITOS = "Você ainda não favoritou nenhuma sala."
MSG_ADICIONE_FAVORITOS = "Adicione salas aos favoritos para encontrá-las rapidamente."
MSG_NENHUMA_SALA_NO_MOMENTO = "Nenhuma sala cadastrada até o momento."
MSG_NENHUMA_ALTERACAO_ESTRUTURAL = "Nenhuma alteração estrutural registrada."
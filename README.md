# UniSapiens - Sistema de Agendamento de Salas

Sistema desenvolvido em Python com Streamlit para gerenciar reservas de salas universitárias, aprovações, trocas e usuários.

## Funcionalidades

- Login por usuário e senha e acesso rápido por QR Code
- Tipos de usuário:
  - Administrador
  - Coordenador
  - Secretário
  - Professor
- Cadastro por link de convite e gerenciamento de usuários
- Reservas de salas por data e turno
- Aprovação ou rejeição de reservas
- Solicitação de trocas entre reservas aprovadas
- Validação de trocas inválidas
- Histórico de aprovações e trocas
- Controle de status Online/Offline

## Estrutura do projeto

- `app.py` — ponto de entrada da aplicação.
  
- `style/style.css` — estilos visuais da interface.
  
- `views/` — telas por perfil de usuário.
  
- `assets/` - imagens e os dados armazenados.
  
- `controllers/` - separa a lógica de negócio e o processamento dos dados das telas ou rotas da interface.
  
- `utils/` - armazena funções auxiliares, genéricas e reutilizáveis que dão suporte a várias partes da aplicação.
  
- `models/` - cuida de tudo o que está relacionado à estrutura, persistência e regras de armazenamento das informações.

## Requisitos

- Python 3.10+
- Streamlit
- Pandas

## Instalação

1. Acesse a pasta do projeto:

```bash
cd DevSix
```

2. Crie um ambiente virtual, se desejar:

```bash
python -m venv .venv
```

3. Ative o ambiente virtual:

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

4. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Execução

No diretório do projeto, execute:

```bash
streamlit run app.py
```

## Usuários iniciais

## Usuário inicial

Na primeira execução, caso não exista nenhum usuário cadastrado, o sistema cria automaticamente uma conta de administrador padrão:

- Usuário: `Suporte.ti`
- Senha inicial: `admin123`
- Tipo: `Administrador`

A conta inicial só é criada quando o arquivo de usuários está vazio. Após o primeiro acesso, recomenda-se alterar a senha padrão.

## Regras de negócio importantes

- O professor só pode reservar salas a partir do dia atual
- Não é permitido agendar salas em datas passadas
- Não é possível trocar salas quando:
  - a mesma sala aparece nos dois lados
  - a data é a mesma
  - o turno é o mesmo
- Troca duplicada não pode ser enviada novamente
- O histórico de trocas mostra professor, sala, data e turno

## Observações

Os arquivos CSV utilizados pelo sistema são lidos e gravados em UTF-8. Na leitura, o sistema aceita UTF-8 com BOM (`utf-8-sig`) para compatibilidade com arquivos existentes. Os dados CSV são armazenados na pasta `assets/data/`, então o sistema é simples e estático, ideal para fins acadêmicos e de demonstração.
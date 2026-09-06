# UniSapiens - Sistema de Agendamento de Salas

Sistema desenvolvido em Python com Streamlit para gerenciar reservas de salas universitárias, aprovações, trocas e usuários.

## Funcionalidades

- Login por usuário e senha
- Tipos de usuário:
  - Administrador
  - Secretário
  - Professor
- Cadastro e gerenciamento de usuários
- Reservas de salas por data e turno
- Aprovação ou rejeição de reservas
- Solicitação de trocas entre reservas aprovadas
- Validação de trocas inválidas
- Histórico de aprovações e trocas
- Controle de status Online/Offline

## Estrutura do projeto

- `app.py` — ponto de entrada da aplicação
- `style.css` — estilos visuais da interface
- `database/` — arquivos CSV do sistema
- `views/` — telas por perfil de usuário

## Requisitos

- Python 3.10+
- Streamlit
- Pandas

## Instalação

1. Acesse a pasta do projeto:

```bash
cd pasta-projeto-2
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
pip install streamlit pandas
```

## Execução

No diretório do projeto, execute:

```bash
streamlit run app.py
```

## Usuários iniciais

O sistema cria automaticamente um usuário administrador padrão:

- Usuário: `Suporte.ti`
- Senha: `admin123`

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

Os dados são armazenados em CSV na pasta `database/`, então o sistema é simples e estático, ideal para fins acadêmicos e de demonstração.

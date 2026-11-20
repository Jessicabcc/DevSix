# UniSapiens — Sistema de Agendamento de Salas

Aplicação em Python e Streamlit para consultar salas de um campus, solicitar reservas e trocas, aprovar solicitações e administrar usuários.

## Funcionalidades

- Login e perfis de administrador, coordenador, secretário e professor.
- Autenticação por senha, acesso por QR Code e cadastro por convite.
- Consulta de prédios e salas.
- Solicitação, aprovação e rejeição de reservas.
- Solicitação e gerenciamento de trocas entre reservas, com validação.
- Salas favoritas, histórico e relatórios.
- Controle de status Online/Offline.
- Persistência em Cloud Firestore.

## Requisitos

- Windows 10 ou superior (os comandos deste guia são para PowerShell).
- Python 3.11 ou superior.
- Google Cloud CLI (`gcloud`).
- Uma conta Google com acesso ao projeto Firebase que será usado.
- Acesso à internet para instalar dependências e comunicar com o Firestore.

## 1. Abrir o projeto e instalar as dependências

Abra o PowerShell na pasta do projeto, onde estão `app.py` e `requirements.txt`. Se ainda não clonou o repositório, clone-o e entre na pasta que contém esses arquivos.

Crie e ative um ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, permita scripts somente nesta janela e tente novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Instale as dependências fixadas pelo projeto:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirme que o Streamlit está instalado:

```powershell
python -m streamlit --version
```

Mantenha esse terminal aberto para continuar os próximos passos.

## 2. Criar ou selecionar um projeto Firebase

1. Abra o [Firebase Console](https://console.firebase.google.com/) e entre com a conta Google que usará o aplicativo.
2. Crie um projeto Firebase ou selecione um projeto ao qual você já tenha acesso.
3. Anote o **ID do projeto** (Project ID), disponível nas configurações do projeto. Ele não é necessariamente igual ao nome exibido.
4. No menu do Firebase, abra **Build → Firestore Database**.
5. Se o Firestore ainda não existir, escolha **Create database**, modo **Native**, e crie o banco padrão **`(default)`**. Escolha uma região próxima dos usuários; a localização não poderá ser alterada depois.
6. O app e o importador criam as coleções automaticamente. Não é preciso usar **Iniciar coleção**.

### Projeto usado por padrão neste repositório

O código está configurado para usar o projeto `reservasalas-6622c` quando nenhuma variável de projeto está definida. Para apontar para outro projeto, configure `GOOGLE_CLOUD_PROJECT` conforme a próxima seção.

## 3. Instalar e autenticar o Google Cloud CLI

Se ainda não tiver o `gcloud`, instale o [Google Cloud CLI para Windows](https://cloud.google.com/sdk/docs/install-sdk#windows). Depois, abra um novo PowerShell. Se o comando `gcloud` não for reconhecido, feche e reabra o terminal após a instalação.

No PowerShell, substitua o valor abaixo pelo ID correto do seu projeto:

```powershell
$projectId = "SEU_ID_DO_PROJETO"
gcloud config set project $projectId
gcloud auth application-default login
gcloud auth application-default set-quota-project $projectId
$env:GOOGLE_CLOUD_PROJECT = $projectId
```

O comando de login abre o navegador. Entre com a conta Google que tem permissão para acessar o Firestore e autorize o acesso. Use **`gcloud auth application-default login`**; `gcloud auth login` sozinho não configura as credenciais ADC que a aplicação utiliza.

A última linha define o projeto apenas para o terminal atual. Execute os comandos de configuração novamente em cada novo terminal, ou grave a variável para terminais futuros:

```powershell
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_PROJECT", $projectId, "User")
```

Depois de gravá-la, abra um novo terminal para que a variável seja carregada. Se usar um projeto diferente do padrão, também atualize `FIREBASE_PROJECT_ID` em `utils/firebase_utils.py` ou mantenha `GOOGLE_CLOUD_PROJECT` definido ao iniciar o app.

Confira a conexão de leitura antes de continuar:

```powershell
python -c "from utils.firebase_utils import get_firestore_client; c = get_firestore_client(); print('Projeto:', c.project); print('Coleções:', len(list(c.collections())))"
```

O comando mostra o projeto e a quantidade de coleções, sem imprimir os documentos. Se falhar, confira se o ID está correto, se a conta tem acesso ao projeto e se o Firestore foi criado.

## 4. Migrar os CSVs (somente para um Firestore novo)

Os CSVs existentes ficam em `assets/data/`. Se estiver configurando **um projeto Firestore novo e vazio** e quiser importar esses dados, execute uma única vez:

```powershell
python -m models.firestore_migration
```

O importador lê os CSVs atuais e os arquivos compatíveis em `assets/data/legacy/`, cria as coleções e verifica os documentos gravados. As coleções são:

`usuarios`, `salas`, `agendamentos`, `trocas`, `convites`, `predios`, `favoritos` e `historico_alteracoes`.

**Importante:** execute a migração somente no banco de destino vazio. Não apague coleções nem repita a migração sobre dados já utilizados. O importador interrompe a execução se encontrar conteúdo incompatível e registra quando uma migração foi concluída. Os CSVs locais não são apagados nem alterados.

Se estiver usando o Firestore deste projeto já configurado e migrado, **não execute a migração novamente**; siga para a execução do app.

## 5. Executar o Streamlit

No mesmo PowerShell em que o ambiente virtual está ativo, as credenciais ADC estão configuradas e `GOOGLE_CLOUD_PROJECT` está definido, execute:

```powershell
python -m streamlit run app.py
```

O Streamlit abrirá o endereço local no navegador (normalmente `http://localhost:8501`). Para encerrar, volte ao terminal e pressione `Ctrl+C`.

## 6. Publicar no Streamlit Community Cloud

1. Envie o projeto ao GitHub sem incluir arquivos de chave, `.env` ou `.streamlit/secrets.toml`.
2. No Streamlit Community Cloud, crie um app apontando para o repositório, a branch desejada e `app.py`.
3. Crie no Supabase Storage um bucket privado chamado `profile-photos`. Não habilite acesso público: o app faz upload e download no servidor.
4. Em **App settings → Secrets**, configure a conta de serviço Firebase para o Firestore e o URL/chave secreta do Supabase para as fotos:

```toml
[firebase]
project_id = "ID_DO_PROJETO_FIREBASE"
client_email = "EMAIL_DA_CONTA_DE_SERVICO"
private_key = """-----BEGIN PRIVATE KEY-----
COLE AQUI O CONTEUDO DA CHAVE PRIVADA
-----END PRIVATE KEY-----
"""

[supabase]
url = "https://ID_DO_PROJETO.supabase.co"
secret_key = "sb_secret_..."
bucket = "profile-photos"
```

Obtenha `client_email` e `private_key` do JSON da conta de serviço Firebase, e `url` e `secret_key` na área de API Keys do projeto Supabase. A chave `sb_secret_...` tem privilégios elevados: mantenha-a apenas nos Secrets do Streamlit, nunca no navegador, GitHub, `.env` versionado ou nesta conversa. O app usa essa chave somente no servidor para acessar o bucket privado.

No Firebase, conceda à conta de serviço acesso ao Firestore, por exemplo, a função IAM **Cloud Datastore User**. O Firebase continua sendo usado para o Firestore; as fotos novas ficam no Supabase Storage.

Antes de publicar, confirme que o Firestore configurado em `project_id` já contém os dados e o documento de conclusão da migração CSV. Se ainda não migrou, faça isso uma única vez em um ambiente local autenticado com acesso ao mesmo projeto, seguindo o passo 4. Não rode a migração de um banco já utilizado.

O `requirements.txt` do repositório deve estar em UTF-8 para que o Cloud instale as dependências corretamente. Depois do deploy, confira os logs do app se a inicialização indicar credenciais, bucket ou migração ausentes.

Uploads de fotos feitos no Streamlit Cloud são armazenados no bucket privado do Supabase. Fotos locais antigas em `assets/uploads/` continuam sendo lidas enquanto estiverem incluídas no repositório. Em execução local sem Secrets do Firebase e do Supabase, uploads continuam usando a pasta local. Se os Secrets do Firebase estiverem configurados sem os do Supabase, novos uploads são recusados para evitar gravações no Firebase Storage.

## 7. Primeiro acesso

Use uma conta já existente nos dados importados. O app só cria o usuário inicial abaixo se a coleção `usuarios` estiver vazia:

- Usuário: `Suporte.ti`
- Senha inicial: `admin123`

Se essa conta for criada, troque a senha inicial antes de usar o sistema com dados reais.

## Segurança e operação

- Não compartilhe nem versione arquivos de credenciais, tokens ou o arquivo ADC do Google Cloud.
- Este app usa o Firebase Admin SDK no servidor. As operações são autorizadas pela identidade Google/ADC e pelas permissões IAM da conta; as regras de acesso do SDK cliente Firebase não substituem o controle de acesso IAM para essa conexão.
- A chave secreta do Supabase também é usada somente no servidor e pode ignorar as políticas RLS; nunca a exponha no cliente. Mantenha o bucket privado e conceda somente os acessos necessários.
- Dê à conta somente as permissões necessárias no projeto. Para acesso ao Firestore, peça ao administrador do projeto uma função IAM apropriada e, se necessário, permissão para usar o projeto como quota project.
- Mantenha uma cópia de segurança dos CSVs. Depois que os dados estiverem no Firestore, o app lê e grava no Firestore; os CSVs servem apenas como origem da migração.
- As leituras são armazenadas em cache por até 5 segundos. Gravações realizadas pelo app invalidam o cache imediatamente.

## Solução de problemas

### `ValueError: Project ID is required to access Firestore`

Defina o ID no terminal antes de iniciar o app e reinicie o Streamlit:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "SEU_ID_DO_PROJETO"
python -m streamlit run app.py
```

### Credenciais ADC não encontradas

Execute o login ADC e conclua a autorização no navegador:

```powershell
gcloud auth application-default login
```

### Aviso sobre quota project ou erro de quota

Defina o projeto padrão e o quota project:

```powershell
gcloud config set project SEU_ID_DO_PROJETO
gcloud auth application-default set-quota-project SEU_ID_DO_PROJETO
```

Se o comando negar permissão, solicite ao administrador do Google Cloud acesso ao projeto e permissão para usá-lo como quota project.

### O app informa que a migração não foi concluída

Confirme se está apontando para o projeto Firestore correto. Para um banco novo e vazio com os CSVs disponíveis, siga o passo 4. Não rode o importador em um banco que já contém dados de produção.

### `pip` ou `streamlit` não é reconhecido

Ative o ambiente virtual e use os comandos pelo módulo Python:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Estrutura principal

Os dados são armazenados em CSV na pasta `database/`, então o sistema é simples e estático, ideal para fins acadêmicos e de demonstração.
---
## Versão e ambiente

A versão da aplicação fica em `utils/versao.py` (`APP_VERSAO`) e aparece no rodapé.
O ambiente é definido pela variável `APP_ENV` (padrão: `desenvolvimento`).
Ao lançar uma nova versão, altere apenas `APP_VERSAO`.
=======
- `app.py` — entrada do aplicativo.
- `models/` — persistência e migração de dados.
- `controllers/` — regras de negócio.
- `views/` — páginas e componentes de interface.
- `utils/` — integração Firebase e utilitários.
- `assets/data/` — CSVs de origem e cópias locais.
- `assets/uploads/` — imagens enviadas ao sistema.


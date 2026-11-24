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

## Usuário inicial

Na primeira execução, caso não exista nenhum usuário cadastrado, o sistema cria automaticamente uma conta de administrador padrão:

- Usuário: `Suporte.ti`
- Senha inicial: `admin123`
- Tipo: `Administrador`

A conta inicial só é criada quando o arquivo de usuários está vazio. Após o primeiro acesso, recomenda-se alterar a senha padrão.

- `app.py` — entrada do aplicativo.
- `models/` — persistência e migração de dados.
- `controllers/` — regras de negócio.
- `views/` — páginas e componentes de interface.
- `utils/` — integração Firebase e utilitários.
- `assets/data/` — CSVs de origem e cópias locais.
- `assets/uploads/` — imagens enviadas ao sistema.

## Versão e ambiente

A versão da aplicação fica em `utils/versao.py` (`APP_VERSAO`) e aparece no rodapé.
O ambiente é definido pela variável `APP_ENV` (padrão: `desenvolvimento`).
Ao lançar uma nova versão, altere apenas `APP_VERSAO`.

Os arquivos CSV utilizados pelo sistema são lidos e gravados em UTF-8. Na leitura, o sistema aceita UTF-8 com BOM (`utf-8-sig`) para compatibilidade com arquivos existentes. Os dados CSV são armazenados na pasta `assets/data/`, então o sistema é simples e estático, ideal para fins acadêmicos e de demonstração.

### Status Online/Offline

Ao realizar o login, o sistema registra o usuário como `Online`. Ao utilizar o botão **Sair**, o sistema registra o usuário como `Offline`.

O encerramento inesperado da aplicação, como fechar o navegador diretamente, perder a conexão ou ocorrer uma falha durante a sessão, pode impedir que o logout seja registrado. Nesses casos, a conta pode permanecer temporariamente marcada como `Online`.

Por isso, o status representa o estado conhecido pelo sistema e não uma indicação de conexão em tempo real.

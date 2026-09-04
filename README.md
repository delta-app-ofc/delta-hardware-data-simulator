# Delta Hardware Data Simulator

## Objetivo

Este repositório gera dados sintéticos para as coleções MongoDB do Projeto
Delta. Ele atende a dois cenários de desenvolvimento:

- simular os pacotes de pulsos enviados por um ESP32 ao hidrômetro;
- popular as demais coleções de telemetria e do aplicativo sem escrever
  comandos `insertMany` manualmente.

O projeto é somente um gerador de dados. Ele não implementa firmware, envio
HTTP, processamento de telemetria ou regras do backend.

## O que está implementado

A CLI gera de 1 a 100 documentos por execução para sete coleções:

| Banco                | Coleção               | Finalidade                       |
|----------------------|-----------------------|----------------------------------|
| `db_delta_telemetry` | `pulses_raw`          | Pacotes de pulsos do ESP32       |
| `db_delta_telemetry` | `consumption_summary` | Resumos de consumo por janela    |
| `db_delta_telemetry` | `device_status`       | Estado atual dos dispositivos    |
| `db_delta_app`       | `user_preferences`    | Preferências dos usuários        |
| `db_delta_app`       | `alerts_history`      | Histórico de alertas             |
| `db_delta_app`       | `chat_sessions`       | Sessões e mensagens do chatbot   |
| `db_delta_app`       | `chat_feedback`       | Avaliações vinculadas às sessões |

Os documentos seguem os validators implementados nos scripts
[`delta-telemetry/script-collections.js`](../delta-nosql-database/scripts/delta-telemetry/script-collections.js)
e
[`delta-app/script-collections.js`](../delta-nosql-database/scripts/delta-app/script-collections.js).

## Pré-requisitos

- Python 3.10 ou superior;
- MongoDB com as coleções e os validators do Projeto Delta já criados;
- `make` apenas se quiser usar o atalho opcional do Makefile.

Instale as dependências na raiz deste repositório:

```powershell
python -m pip install -r requirements.txt
```

## Configuração

Crie o arquivo local `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

O valor padrão do exemplo aponta para um MongoDB local:

```env
MONGO_URI=mongodb://localhost:27017
```

Altere somente o `.env` local quando precisar de outra instância. O arquivo é
ignorado pelo Git e não deve conter credenciais destinadas ao repositório.

## Uso da CLI

A interface suportada em qualquer sistema com Python é:

```text
python -m dataload.cli <coleção> <quantidade> [--dry-run]
```

Exemplo que gera e insere vinte pacotes do ESP32:

```powershell
python -m dataload.cli pulses_raw 20
```

Para conferir três documentos sem inserir no banco:

```powershell
python -m dataload.cli consumption_summary 3 --dry-run
```

Para simular o envio do ESP32 em tempo real, usando uma janela de cinco
minutos entre os pacotes:

```powershell
python -m dataload.cli pulses_raw 3 --continuo
```

Nesse modo, o primeiro pacote é gerado imediatamente e os demais aguardam o
intervalo configurado. O número informado continua limitando a quantidade de
pacotes. Para testar com um intervalo menor:

```powershell
python -m dataload.cli pulses_raw 3 --continuo --intervalo-segundos 10
```

O modo contínuo também pode ser encerrado por tempo. Neste exemplo, ele roda
por no máximo um minuto e pode gerar até três pacotes:

```powershell
python -m dataload.cli pulses_raw 3 --continuo --intervalo-segundos 10 --tempo-maximo 60
```

O valor de `quantidade` continua sendo um limite de segurança entre 1 e 100;
o gerador também encerra quando atingir `tempo-maximo`.

O `--dry-run` imprime MongoDB Extended JSON válido. Datas aparecem com
`$date` e IDs BSON podem aparecer com `$oid`; isso preserva os tipos que serão
usados no insert.

Outros exemplos:

```powershell
python -m dataload.cli device_status 5
python -m dataload.cli user_preferences 5
python -m dataload.cli alerts_history 10
python -m dataload.cli chat_sessions 4
python -m dataload.cli chat_feedback 4
```

Nomes de coleção inválidos, quantidades que não sejam inteiras e valores fora
do intervalo de 1 a 100 terminam com código de saída `1` antes da geração.

### Dependência de `chat_feedback`

Cada `chat_feedback.session_id` deve apontar para o `_id` real de uma sessão
existente no banco alvo. Se a coleção `chat_sessions` estiver vazia, a CLI
informa o comando necessário e não cria sessões escondidas.

Execute nesta ordem:

```powershell
python -m dataload.cli chat_sessions 5
python -m dataload.cli chat_feedback 5
```

Essa dependência também existe no `--dry-run` de `chat_feedback`, pois um ID
inventado não representaria um documento válido para o projeto.

### Erros do MongoDB

Erros de validator, índice único ou conexão não são ignorados. Se o MongoDB
rejeitar um documento, o erro é exibido para que uma divergência entre o
gerador e o schema seja corrigida.

## Makefile opcional

Se `make` estiver instalado, o mesmo comando pode ser executado por variáveis:

```text
make dataload COLLECTION=pulses_raw N=20
make dataload COLLECTION=alerts_history N=3 DRY_RUN=--dry-run
make dataload COLLECTION=pulses_raw N=3 OPTIONS="--continuo --intervalo-segundos 10"
make dataload COLLECTION=pulses_raw N=3 OPTIONS="--continuo --intervalo-segundos 10 --tempo-maximo 60"
```

O Makefile é apenas uma conveniência. Em instalações do Windows sem `make`,
use diretamente `python -m dataload.cli ...`, que é a interface oficialmente
suportada pelo projeto.

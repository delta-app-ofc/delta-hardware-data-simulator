# Delta Hardware Data Simulator

## Objetivo

Gerar dados sintéticos consistentes para os 13 KPIs BI do Delta, respeitando os
validators do `delta-mongo-database` e os vínculos cadastrais do PostgreSQL.
A implementação usa Python, pymongo e funções pequenas por coleção; não implementa
firmware, backend, API, Gold ou dashboard.

## Instalação e configuração

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure as duas conexões no `.env` local, que é ignorado pelo Git:

```env
MONGO_URI_TELEMETRY=mongodb://localhost:27017
MONGO_URI_APP=mongodb://localhost:27017
```

As conexões podem apontar para instâncias diferentes. `MONGO_URI` continua como
alternativa quando a configuração específica estiver vazia. Uma falha na conexão
específica não redireciona a carga. Os bancos usados são `db_delta_telemetry` e
`db_delta_app`; utilize instâncias de desenvolvimento, pois os valores são simulados.
Não existe confirmação interativa: o comando sem `--dry-run` escreve nos destinos
configurados. As coleções, validators e índices precisam existir previamente.

Dependências: `pymongo`, `python-dotenv` e `tzdata` (calendário de São Paulo no Windows).
Python 3.10 ou superior. Não há ORM nem dependência de driver PostgreSQL.

## 1. Exportar os vínculos do SQL

Execute [sql/exportar-contexto-bi.sql](sql/exportar-contexto-bi.sql) no PostgreSQL.
É apenas um SELECT: salve o conteúdo da célula `contexto_json` em um arquivo local
`contexto-sql.json`. Não acrescente aspas externas ou escapes do cliente SQL.

O catálogo contém dispositivo, usuário responsável, imóvel, região, cidade, classe,
coordenadas, instalação e associação. O exportador seleciona deterministicamente o
menor `user_id` vinculado ao imóvel como responsável; não inventa usuários nem faz
rateio entre coproprietários. Confira essa escolha para imóveis compartilhados.
Inclui os dispositivos cadastrados, pois um flag atual de inatividade não informa
quando o dispositivo foi desativado no passado. Não exporta senhas, e-mails ou nomes.

Coordenadas do imóvel vêm exclusivamente do SQL. IDs ausentes/repetidos e regiões
contraditórias interrompem a leitura do catálogo. Cidades são padronizadas em maiúsculas,
sem acentos e sem espaços repetidos: `São Paulo`, `SÃO PAULO` e `SAO PAULO` convergem
para `SAO PAULO`. Essa normalização do catálogo não altera os cadastros PostgreSQL.
`device_id` é preservado exatamente para os cruzamentos.

Por padrão, coordenadas ausentes/invalidas interrompem a leitura. Se os dois campos
estiverem ausentes, `--permitir-coordenadas-ausentes` permite gerar as coleções Mongo
mantendo `latitude`/`longitude` desconhecidas no catálogo, sem inventar pontos.
Uma coordenada preenchida inválida ou um par incompleto continua sendo rejeitado.
O clima sintético usa então um perfil por cidade; consumo/chat/alertas não recebem
campos geográficos extras. Essa opção **não resolve o mapa** nem a validação estrita
de coordenadas da Gold: é necessário corrigir os endereços SQL para esses usos.

**Não use o catálogo de exemplo para uma carga real.** Seus IDs e pontos são fictícios;
a CLI permite esse arquivo apenas em `--dry-run`. Para o mapa ter várias cidades e
pontos reais do cadastro, eles precisam existir no SQL. O simulador não cria imóveis,
não altera endereços e não espalha coordenadas artificialmente. Tarifas continuam no SQL.

Não corte dispositivos de um mesmo imóvel ao selecionar o contexto: as horas completas
da Gold dependem de todos os medidores esperados. Para usuários com vários imóveis,
exporte também seus demais dispositivos para não deixar a meta sem cobertura.

## 2. Conferir o cenário sem acessar MongoDB

Exemplo independente dos bancos:

```powershell
python -m dataload.cli bi --contexto dataload/fixtures/contexto-exemplo.json --inicio 2026-09-01 --fim 2026-09-03 --janela-minutos 60 --dry-run
```

Ou confira seu catálogo exportado:

```powershell
python -m dataload.cli bi --contexto contexto-sql.json --inicio 2026-09-01 --fim 2026-09-03 --seed 42 --max-documentos 2000 --janela-minutos 60 --dry-run
```

Quando houver endereços SQL sem coordenadas, a opção deve ser explícita:

```powershell
python -m dataload.cli bi --contexto contexto-sql.json --inicio 2026-10-03 --fim 2026-10-17 --permitir-coordenadas-ausentes --janela-minutos 60 --max-documentos 2000 --dry-run
```

O resultado é Extended JSON, com contagens e uma amostra por coleção. O dry-run não
lê `.env`, não abre conexão e não insere dados. As datas e ObjectIds preservam seus
tipos BSON. Escapes Unicode no JSON evitam diferenças de encoding no Windows.

`--inicio` é inclusivo; `--fim` é exclusivo e assume hoje em São Paulo quando omitido.
O dia em andamento e dias futuros não são gerados. O cenário aceita 1 a 366 dias
completos, desde 2020, e até 1000 dispositivos. Só há medições depois da instalação
**e** do vínculo cadastral; data de instalação recente não autoriza inventar histórico
anterior. Há 288 janelas por dispositivo/dia no modo padrão de cinco minutos e 24 no modo `--janela-minutos 60`. Antes de abrir qualquer conexão,
o comando prepara e conta as sete saídas, com limite total padrão de 2 mil documentos.
Se exceder, falha sem escrever e sem truncar dias ou relações entre coleções.
Use `--max-documentos` para definir um limite explícito; ampliar esse valor deve ser
uma decisão deliberada, conferida na prévia. O limite vale para o cenário solicitado,
incluindo os documentos que serão atualizados, e não é uma cota acumulada do banco.
Selecione poucos imóveis completos no catálogo SQL e um período curto para começar;
não use todos os dispositivos por várias semanas em uma demonstração pequena.

## 3. Carregar e ampliar gradualmente

Após conferir a prévia e a configuração dos destinos de desenvolvimento:

```powershell
python -m dataload.cli bi --contexto contexto-sql.json --inicio 2026-09-01 --fim 2026-09-03 --seed 42 --max-documentos 2000 --janela-minutos 60
```

Para acrescentar o próximo dia, preserve contexto, início e seed e aumente o fim:

```powershell
python -m dataload.cli bi --contexto contexto-sql.json --inicio 2026-09-01 --fim 2026-09-04 --seed 42 --max-documentos 2000 --janela-minutos 60
```

Também é possível omitir `--fim` e repetir o comando nos dias seguintes. Isso gera até
o último dia encerrado. Nenhuma automação ou agendamento é criado.

As observações usam chaves estáveis por dispositivo/data, localização/dia ou sessão.
O carregador faz upsert em lotes de no máximo 100 documentos: repetir o mesmo intervalo
não acrescenta cópias; ampliar o fim acrescenta dias e atualiza o status reconciliado.
O histórico já conhecido de disponibilidade não pode ser encurtado. Trocar o seed
altera os valores simulados das mesmas observações; mantenha-o fixo durante a demonstração.

Antes de escrever, o carregador confere as sete coleções, os validators de chat/status,
o índice único de clima por localização e `weather_date`, e conflitos legados no período. Grades de cinco minutos e uma hora não podem ser misturadas no mesmo período/dispositivo.
Se encontrar clima com grafia/calendário antigo ou consumo duplicado/fora da grade,
pede correção explícita. Não executa `drop`, `delete`, `collMod` ou criação de índices.
Essas verificações não substituem uma auditoria completa de dados fora do período.

O carregador não limpa dados antigos automaticamente. Em uma base já inconsistente,
normalize os documentos existentes ou use uma instância de desenvolvimento limpa com os
scripts atuais do Mongo. O povoamento novo não garante que registros legados fora do
recorte estejam corretos. Erros de validator/conexão continuam visíveis.

As coleções/bancos não participam de uma transação conjunta. Uma falha de execução pode
deixar parte da carga concluída; corrija a causa e repita o mesmo comando. Execute uma
carga de cada vez. Não execute Glue/transfer/Gold durante a carga; aguarde a conclusão,
recapture o lote e atualize a Gold antes de avaliar o dashboard.

## Coleções e coerência dos dados

| Coleção | Dados gerados |
| --- | --- |
| `weather_daily` | 24 observações por cidade/dia, temperatura e sensação distintas, variação diária/horária, umidade, chuva, vento e condição. `samples` coincide com `hours`. |
| `consumption_summary` | Janelas contíguas de cinco minutos (padrão) ou uma hora (`--janela-minutos 60`), sem sobreposição, mesmos dispositivos/usuários do catálogo. Perfis residencial/comercial, horários de pico, fim de semana e influência da temperatura pareada. |
| `device_status` | Um status por device, contador online e intervalos offline reconciliados; firmware identifica o simulador. O snapshot ao fim do período fica online, com quedas no histórico. |
| `user_preferences` | Uma preferência por usuário, meta diária relacionada aos seus medidores e dias dentro/fora da meta. Não promete preservar a vigência histórica das metas. |
| `alerts_history` | Os quatro tipos reais, ligados ao mesmo device/usuário e período. Quedas coincidem com os intervalos offline; vazamento/fluxo atípico coincidem com anomalias no consumo. |
| `chat_sessions` | Uma sessão por usuário/dia, especialistas `consumption`, `forecast`, `leak`, duração individual, variação e outliers. HTTP 429/500/503 simulados; sem chamadas de juiz/roteador. |
| `chat_feedback` | Feedback referencia o ObjectId da sessão do próprio cenário, inserida antes. |

As coordenadas ficam no catálogo SQL e orientam a localização do cenário; não se
acrescentam campos de endereço ao consumo, ao chat ou aos alertas. O contrato Mongo
consultado não declara coordenadas em `weather_daily`; o gerador publica apenas os
campos declarados. O mapa da Gold continua usando as coordenadas dos imóveis SQL.

Queda de conexão representa indisponibilidade de comunicação; as leituras do período
são simuladas como armazenadas no dispositivo e enviadas posteriormente. Por isso a
série de consumo continua completa durante as quedas. `leitura_impossivel` representa
uma leitura rejeitada: o gerador não insere volume negativo/inválido para criar o alerta.

Todos os dados desta ferramenta são sintéticos. A relação temperatura/consumo é uma
regra de simulação, não evidência de causalidade. Não há campo `is_mock` inventado nas
coleções: preserve o aviso de demonstração nos consumidores. O comando não muda o tipo
ou a configuração dos gráficos; use os datasets/prompt BI corretos depois da carga.

### Dispersão entre temperatura e consumo

Para visualizar a dispersão, cada ponto do scatter deve representar **um imóvel em
uma hora**: temperatura observada naquela cidade/hora no eixo X e consumo total
do imóvel naquela hora, em litros, no eixo Y. Some as janelas de cinco minutos e
todos os medidores do imóvel antes de parear o clima. Preserve imóvel/data/hora como
identidade do ponto na consulta e na visualização, para que o gráfico não volte a
agregar as observações. As faixas de temperatura podem orientar cores ou filtros.

Uma média única por faixa de 5 °C responde outra pergunta e produz poucos pontos,
escondendo a variação. Com a granularidade imóvel/hora, o título adequado é
**Consumo horário por imóvel versus temperatura**. Centenas de documentos de consumo
já produzem centenas de pontos pareados no modo horário; volume alto não é requisito para esse gráfico.

## Prévias individuais e código legado

```powershell
python -m dataload.cli weather_daily 3 --dry-run
python -m dataload.cli consumption_summary 3 --dry-run
python -m dataload.cli chat_sessions 4 --dry-run
```

São prévias de até 100 documentos, com o catálogo fictício comum. Coleções únicas podem
retornar menos documentos que o máximo pedido. Inserções individuais foram retiradas
para impedir IDs sorteados sem vínculo com o SQL; use `bi` para a carga coordenada.
`chat_feedback` individual mantém a dependência de sessões existentes no banco, inclusive
no dry-run; prefira `bi --dry-run` para uma prévia totalmente sem conexão.

`pulses_raw` foi removida das opções da CLI porque não existe no modelo atual. O módulo
antigo foi preservado como código legado, sem integrar o povoamento. O modo contínuo
antigo de pulsos também não integra a CLI atual; o crescimento acontece ampliando o
período do cenário. O hardware atual envia `consumption_summary` diretamente.

O Makefile é opcional e seu padrão é uma prévia de `consumption_summary`:

```text
make dataload COLLECTION=consumption_summary N=3
```

No Windows sem `make`, use a CLI Python. A infraestrutura Docker existente permanece
como conveniência de dry-run; consulte [DOCKER-HELP.md](DOCKER-HELP.md).

## Testes e limites de validação

```powershell
python -m unittest discover -s tests -v
```

A suíte usa dados fictícios e um snapshot versionado dos validators executáveis em
`tests/fixtures/mongo-schemas.json`, com hashes das fontes. Confere BSON, campos declarados,
referências, calendário, cobertura, contadores, perfis, agentes, idempotência e preflight.
Os testes do carregador usam um destino em memória e não comprovam execução no Mongo.

Nesta revisão, 27 testes locais passaram, incluindo o limite total antes de qualquer
conexão, o caso de coordenadas ausentes
com autorização explícita de uso sem GPS e normalização de cidades. Esses testes não
comprovam execução remota. No sandbox Windows, precisaram de `TEMP`/`TMP` apontando
para uma pasta gravável do workspace.

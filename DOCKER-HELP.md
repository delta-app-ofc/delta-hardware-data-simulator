# Docker — delta-hardware-data-simulator

## Objetivo

Gerar um documento de consumption_summary em dry-run, sem gravar no MongoDB.

## Pré-requisitos

Docker Engine em execução e Docker Compose v2. Execute os comandos na raiz deste repositório. Os exemplos usam uma identificação de projeto própria para isolar containers e volumes.

## Executar

```bash
docker compose -p delta-hardware-data-simulator-test -f docker-compose.test.yml config --quiet
docker compose -p delta-hardware-data-simulator-test -f docker-compose.test.yml run --build --rm dry-run
# Para gerar outra quantidade sem inserir:
docker compose -p delta-hardware-data-simulator-test -f docker-compose.test.yml run --rm dry-run consumption_summary 5 --dry-run
docker compose -p delta-hardware-data-simulator-test -f docker-compose.test.yml down
```

## Conferir o resultado e encerrar

Confira o JSON gerado e o código de saída da CLI. O serviço não recebe `.env`, não publica portas e não usa volumes. O resultado não comprova que o MongoDB aceita os documentos. Uma inserção real exige um MongoDB local isolado com os scripts do `delta-mongo-database` aplicados; isso não faz parte deste dry-run.

Para diagnosticar falhas de um serviço Compose, use `docker compose -p <projeto> -f <arquivo> ps -a` e `docker compose -p <projeto> -f <arquivo> logs <serviço>`, com o mesmo projeto e arquivo da execução.

`down` preserva volumes nomeados. Só use `down -v` depois de conferir o nome do projeto e confirmar que seus dados são descartáveis. Não remova volumes de outros ambientes.

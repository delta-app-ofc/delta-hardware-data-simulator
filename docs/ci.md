# CI técnico

O workflow executa em pull requests e por acionamento manual. Ele verifica a
compilação dos módulos Python e usa o Compose existente para executar a CLI
em `dry-run`, gerando um documento de `consumption_summary` sem inserir dados.

Para repetir localmente, com Python e Docker Compose instalados:

```bash
python -m compileall -q dataload
docker compose -f docker-compose.test.yml run --build --rm dry-run
```

Essa verificação não testa inserções, validators MongoDB nem todos os
geradores. Em particular, `chat_feedback` consulta o MongoDB mesmo no modo
`--dry-run`, portanto não é executado pelo smoke test isolado.

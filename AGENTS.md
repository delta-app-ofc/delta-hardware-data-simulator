# AGENTS.md — Contexto do Delta Hardware Data Simulator

Este arquivo orienta agentes de IA e pessoas desenvolvedoras que atuam neste repositório. Leia as instruções antes de alterar qualquer arquivo e valide sempre o estado real da branch em uso.

## 1. Visão geral do Projeto Delta

O Delta é um projeto acadêmico do Ensino Médio Técnico em Análise e Desenvolvimento de Sistemas. O produto é uma plataforma IoT de monitoramento inteligente do consumo residencial de água: dispositivos instalados em hidrômetros coletam pulsos, e os demais componentes do sistema consolidam o consumo, apoiam a detecção de vazamentos e a estimativa de gastos e disponibilizam informações para aplicações e para um chatbot.

A arquitetura de dados documentada distribui responsabilidades entre PostgreSQL, para dados cadastrais e transacionais, e MongoDB, para telemetria IoT e dados adequados ao modelo documental. Redis e Neo4j aparecem na documentação como componentes planejados, mas não possuem implementação neste workspace.

Os repositórios do Projeto Delta são independentes. Crie branches e commits dentro deste repositório e não presuma a estrutura de aplicações, bancos, firmware ou serviços mantidos fora dele.

## 2. Contexto deste repositório

O `delta-hardware-data-simulator` foi criado para armazenar códigos que simulem os dados que, na versão final do projeto, serão capturados por hardware. Essa finalidade está registrada no `README.md`.

No estado atual, a `main` ainda não contém implementação executável do simulador. Não há linguagem de programação, dependências, formato de payload, protocolo de comunicação, destino de envio, frequência de geração, modelo de dispositivo ou estratégia de testes definidos nos arquivos rastreados. Não invente essas decisões nem apresente a finalidade planejada como funcionalidade pronta.

### Estrutura atual do repositório

```text
delta-hardware-data-simulator/
├── .github/
│   └── workflows/
│       └── trigger_actions.yml
├── .gitignore
├── LICENSE
└── README.md
```

Responsabilidades confirmadas:

- `README.md`: registra a finalidade geral do repositório;
- `.github/workflows/trigger_actions.yml`: chama o workflow reutilizável da organização para validar Pull Requests;
- `.gitignore`: exclui configurações locais de IDE, `.env` e artefatos `__pycache__/`;
- `LICENSE`: contém a licença do repositório.

O workflow atual é acionado em Pull Requests abertos ou editados e usa `delta-app-ofc/.github/.github/workflows/main.yml@main`. Ele executa as verificações compartilhadas da organização; não há neste repositório um workflow que execute o simulador ou uma suíte de testes automatizados.

## 3. Leitura obrigatória do `TASK.md`

Antes de executar qualquer tarefa:

1. leia integralmente o `TASK.md` localizado na raiz deste repositório;
2. confirme seus requisitos, limitações e critérios de aceite;
3. inspecione os arquivos e o estado Git atuais;
4. restrinja a alteração ao escopo solicitado.

Se o `TASK.md` não existir, não crie, copie ou improvise esse arquivo. Trabalhe somente com o escopo fornecido explicitamente pela pessoa solicitante e peça esclarecimento quando faltar uma decisão indispensável.

## 4. Padrão de branches e commits

Siga as convenções registradas em `delta-handbook/DEVOPS/convencoes-desenvolvimento.md`. Cada mudança deve ser feita em uma branch própria, criada neste repositório a partir da `main` atualizada:

```bash
git checkout main
git pull origin main
git checkout -b <tipo>/<descricao-da-alteracao>
```

O formato de branch é `<tipo>/<descricao-da-alteracao>`, com descrição curta, em minúsculas e separada por hífens.

| Tipo | Uso |
| --- | --- |
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Refatoração sem mudança de comportamento |
| `docs` | Criação ou atualização de documentação |
| `test` | Criação ou manutenção de testes |
| `style` | Alteração de estilização |

Exemplos:

```text
docs/agents-md
feat/simulador-telemetria
test/validacao-dados-simulados
```

Os exemplos indicam apenas nomenclatura de branches e não confirmam funcionalidades existentes.

Os commits seguem Conventional Commits no formato `<tipo>: descrição`, usando os mesmos tipos permitidos. Mantenha cada commit coeso e não misture mudanças sem relação.

## 5. Padrão de documentação

Siga o padrão definido no `README.md` do `delta-handbook` ao criar ou atualizar documentos:

- use Markdown com extensão `.md`;
- comece com um título e um objetivo claros;
- apresente contexto e justificativas antes dos detalhes operacionais;
- organize o conteúdo em seções e subseções com hierarquia coerente;
- use listas para regras e responsabilidades, tabelas para comparações e blocos de código para exemplos técnicos;
- use diagramas somente quando forem necessários para explicar relações ou fluxos;
- nomeie novos arquivos em minúsculas, com palavras separadas por hífens;
- prefira links relativos e confira se os caminhos referenciados existem;
- verifique se já existe conteúdo equivalente antes de criar outro documento;
- registre atualizações relevantes quando o histórico for necessário;
- diferencie explicitamente o que está implementado, o que está planejado, o que é exemplo e o que ainda depende de decisão.

Ao documentar futuramente o simulador, mantenha exemplos de payload, protocolos, comandos e dependências alinhados à implementação real. Não declare compatibilidade ou comportamento validado sem evidência nos arquivos ou em execução.

## 6. Limites de atuação

- Não crie `TASK.md`.
- Não escolha linguagem, framework, protocolo ou formato de dados sem que a tarefa defina essa decisão ou que ela já esteja registrada oficialmente.
- Não inclua credenciais, tokens, URLs privadas ou valores reais de `.env` em código, exemplos ou logs.
- Não implemente firmware de hardware, backend, banco de dados ou aplicações clientes neste repositório sem uma mudança formal de escopo.
- Não altere as automações compartilhadas da organização por meio deste repositório.
- Não descreva testes ou integrações como existentes enquanto eles não estiverem presentes e validados.
- Preserve alterações locais não relacionadas e limite cada entrega aos arquivos solicitados.

## 7. Limite de complexidade e nível técnico

As soluções devem ser compatíveis com o conhecimento de estudantes do Ensino Médio Técnico em Análise e Desenvolvimento de Sistemas.

- Priorize código simples, legível e dividido em pequenas responsabilidades.
- Utilize primeiro os recursos já presentes no repositório e conhecidos pela equipe.
- Não adicione frameworks, bibliotecas, padrões arquiteturais ou infraestrutura sem necessidade comprovada.
- Evite abstrações prematuras, metaprogramação, arquiteturas distribuídas e padrões avançados quando uma solução direta atender ao requisito.
- Não reestruture grandes partes do projeto para resolver uma tarefa localizada.
- Explique decisões técnicas e trechos não óbvios com linguagem didática.
- Quando a solução exigir conhecimento acima do limite registrado abaixo, apresente primeiro uma alternativa mais simples e solicite aprovação antes de prosseguir.
- Não implemente automaticamente uma solução avançada sem justificativa e autorização explícita.

### Stack e nível de aprofundamento da equipe

| Tecnologia ou assunto | Nível atual | Limite esperado |
| --- | --- | --- |
| Lógica de programação | Intermediário | Avançado |
| Git e GitHub | Intermediário | Avançado |
| HTML e CSS | Básico | Intermediário |
| JavaScript | Básico | Intermediário |
| Java | Intermediário | Avançado |
| Spring Boot | Básico | Avançado |
| Python | Intermediário | Avançado |
| FastAPI | Básico | Intermediário |
| SQL e PostgreSQL | Avançado | Avançado |
| MongoDB | Básico | Intermediário |
| APIs REST | Intermediário | Intermediário |
| Testes automatizados | Básico | Intermediário |
| Docker e CI/CD | Básico | Intermediário |
| Arquitetura e padrões de projeto | Básico | Intermediário |
| IoT e comunicação com hardware | Básico | Básico |

O **nível atual** representa o conhecimento que a equipe já possui e consegue aplicar com alguma autonomia. O **limite esperado** representa o nível máximo de complexidade que a IA pode utilizar.

Quando o limite esperado for superior ao nível atual, a IA deve explicar os novos conceitos de forma simples e didática, relacionando-os ao código produzido. Qualquer solução que ultrapasse o limite esperado exige aprovação explícita antes da implementação.

## 8. Aviso de manutenção

A seção **Estrutura atual do repositório** deve ser revisada periodicamente nesta conversa e atualizada depois
de commits oficiais que adicionem, removam ou reorganizem arquivos. Antes de cada atualização, compare esta
descrição com a árvore real da `main`; o conteúdo deste arquivo não substitui a inspeção do estado atual.

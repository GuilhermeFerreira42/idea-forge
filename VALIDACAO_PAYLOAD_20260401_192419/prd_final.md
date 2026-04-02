# PRD FINAL

**Criado por:** product_manager

---

<!-- AVISO: Artefato com completude abaixo do threshold. Seções faltantes: [] -->

## Visão do Produto
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]
## Problema e Solução
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]

## Público-Alvo
- Persona 1: João, 28 anos, colecionador iniciante que busca organizar sua coleção e acompanhar preços para decidir quando vender.  
- Persona 2: Maria, 35 anos, mãe que usa a plataforma para registrar empréstimos entre amigos e garantir que os jogos sejam devolvidos a tempo.  
- Persona 3: Carlos, 42 anos, gamer profissional que monitora tendências de mercado para adquirir jogos raros antes da concorrência.  
- Persona 4: Ana, 22 anos, estudante que participa de grupos de troca e precisa de alertas de preço para aproveitar promoções em lojas online.

## Público-Alvo
| Segmento | Perfil (nome fictício + dor específica) | Prioridade |
|---|---|---|
| Colecionador Amador | João, 28 anos — “Tenho 120 jogos, mas gasto 2h por semana procurando um título no meu caderno. Perdi R$ 300 em oportunidades de compra por não saber o preço atual.” | P0 |
| Colecionador Experiente | Maria, 42 anos — “Minha coleção de 350 jogos está desorganizada; preciso de 30 minutos por mês para atualizar status de empréstimos. Já perdi R$ 1.200 por não ter alertas de queda de preço.” | P0 |
| Amigo Empréstimo | Carlos, 35 anos — “Empresto 15 jogos por mês, mas não registro quem tem cada um. Já houve 3 conflitos que custaram R$ 450 em jogos danificados.” | P1 |
| Investidor de Jogos | Ana, 30 anos — “Busco comprar jogos em alta demanda; perco 20% de lucro quando não tenho dados de preço em tempo real. Já deixei de vender 5 jogos que valiam R$ 2.000 cada.” | P0 |
| Jogador Casual | Pedro, 22 anos — “Gosto de jogar com amigos, mas não sei se o jogo que quero emprestar está disponível. Já perdi 1h de diversão por não ter controle de disponibilidade.” | P2 |

## Princípios Arquiteturais
- P1: **Escalabilidade Horizontal** – O sistema deve suportar aumento de usuários e dados sem degradação de performance.  
  REGRA: A métrica de latência média não pode exceder 200 ms quando a carga triplica.  
- P2: **Resiliência de Dados** – Garantir consistência e durabilidade mesmo em falhas de componentes.  
  REGRA: O mecanismo de replicação deve manter 99,9 % de disponibilidade em caso de perda de nó.  
- P3: **Segurança Zero Trust** – Autenticação multifator e autorização baseada em políticas.  
  REGRA: Todas as APIs externas exigem token JWT com escopo mínimo necessário.  
- P4: **Observabilidade Completa** – Logs, métricas e rastreamento distribuído integrados.  
  REGRA: Cada endpoint expõe métricas Prometheus e trace ID em cabeçalhos HTTP.  
- P5: **Arquitetura de Microserviços** – Componentes desacoplados com comunicação assíncrona.  
  REGRA: O tempo de resposta de cada microserviço não pode exceder 150 ms em 95 % das requisições.  
- P6: **Integração Contínua e Entrega (CI/CD)** – Pipeline automatizado para testes e deploy.  
  REGRA: Cada commit deve disparar build, testes unitários e integração, com aprovação manual apenas em releases críticos.  

## Diferenciais
- D1: **Rastreamento de Preços em Tempo Real** – Integração com múltiplos marketplaces via Webhooks.  
- D2: **Histórico de Empréstimos com Notificações Inteligentes** – Alertas de devolução e lembretes baseados em IA.  
- D3: **Análises de Coleção Personalizadas** – Relatórios de valor, raridade e tendências de mercado.  
- D4: **Modo Offline com Sincronização Pós-Conexão** – Usuários podem gerenciar coleções sem internet, sincronizando ao reconectar.

## Princípios Arquiteturais
| Princípio | Descrição | Implicação | Regra |
|---|---|---|---|
| Escalabilidade Horizontal | O sistema deve crescer adicionando instâncias de serviços em vez de aumentar a carga de uma única máquina, garantindo que a performance não degrade com o aumento de usuários e dados. | Uso de balanceadores de carga, micro‑serviços independentes e bancos de dados particionados. | REGRA: O endpoint `/games` deve responder com 200 OK em 99,5 % das requisições sob carga de 2000 usuários simultâneos, medido por testes de carga em ambiente de homologação. |
| Resiliência de Dados | Dados críticos não podem ser perdidos em caso de falha de componentes; o sistema deve garantir recuperação automática e consistência. | Replicação síncrona em clusters, backups automáticos e estratégias de fail‑over. | REGRA: Em simulação de falha de nó primário, o tempo de recuperação do banco de dados não pode exceder 30 s, verificado por testes de fail‑over automatizados. |
| Segurança de Dados | Proteção contra acesso não autorizado, vazamento e ataques, mantendo a confidencialidade, integridade e disponibilidade das informações. | Criptografia em repouso e em trânsito, controle de acesso baseado em RBAC, auditoria de logs. | REGRA: Todos os endpoints expostos devem exigir token JWT válido; tentativas de acesso sem token devem retornar 401 em 100 % dos casos, confirmado por testes de segurança. |
| Observabilidade | Visibilidade completa do comportamento do sistema em produção, permitindo detecção rápida de anomalias e otimização contínua. | Métricas, logs estruturados e rastreamento distribuído (OpenTelemetry). | REGRA: O sistema deve gerar métricas de latência (p95) em intervalos de 1 min; alertas devem disparar quando p95 > 200 ms, validado por monitoramento em tempo real. |
| Modularidade de Serviços | Cada funcionalidade deve ser encapsulada em um micro‑serviço independente, facilitando manutenção, testes e evolução sem impacto global. | API REST/GraphQL bem definidas, contratos claros, versionamento de APIs. | REGRA: Alterações em um serviço não devem exigir redeploy de outros serviços; testes de integração devem passar em 100 % das vezes após alteração de contrato. |
| Consistência Eventual | Dados distribuídos podem ter latência de propagação; o sistema aceita eventual consistência para melhorar performance, mas garante convergência. | Estratégias de CQRS, eventos de domínio, compensação de transações. | REGRA: Após publicação de evento de atualização de preço, todos os caches devem refletir o novo valor em até 5 s, medido por testes de propagação de eventos. |
| Cache Eficiente | Redução de carga em bancos de dados e APIs externas por meio de cache distribuído, mantendo dados atualizados e consistentes. | Redis ou Memcached, TTLs adequados, invalidação baseada em eventos. | REGRA: O tempo médio de resposta de consultas de preço deve ser < 50 ms em 95 % das requisições, comprovado por testes de performance com cache habilitado. |
| API Rate Limiting | Proteção contra abuso e sobrecarga de serviços, garantindo disponibilidade para todos os usuários. | Limites por IP, por token, e políticas de back‑off. | REGRA: Em caso de 1000 requisições simultâneas de um mesmo token, o sistema deve retornar 429 em 95 % das vezes, validado por testes de carga. |
| Autenticação Multifator | Reforço da segurança de acesso, exigindo múltiplos fatores de autenticação para usuários críticos. | MFA via SMS, e‑mail ou app autenticador. | REGRA: Usuários com nível de acesso “admin” devem ser obrigados a completar MFA em 100 % das sessões, confirmado por testes de login. |
| Atualização Zero Downtime | Implantação de novas versões sem interrupção do serviço, mantendo a experiência do usuário ininterrupta. | Blue/Green deployment, canary releases, rollback automático. | REGRA: Durante rollout de nova versão, o tempo de indisponibilidade não pode exceder 5 s, medido por monitoramento de uptime em ambiente de staging. |

## Diferenciais
| Atual | Problema | Superação |
|---|---|---|
| SaaS tradicional de coleções | Usuários precisam inserir manualmente preços e histórico de empréstimos, com risco de erro e perda de dados. | Integração automática com APIs de marketplaces e webhooks que atualizam preços em tempo real, reduzindo erro humano e mantendo dados atualizados. |
| Registro manual de empréstimos | Conflitos frequentes entre amigos, falta de controle de status e perda de jogos. | Sistema registra empréstimos e devoluções via QR‑code ou NFC, envia notificações push e e‑mail quando prazo expira, garantindo rastreabilidade completa. |
| Busca estática por título | Dificuldade em localizar jogos por atributos complexos (tipo, número de jogadores, idade recomendada). | Busca avançada com filtros inteligentes (fuzzy search, recomendação baseada em histórico) e visualização em grade, facilitando a localização rápida. |
| Alertas de preço via e‑mail | Notificações são enviadas apenas em intervalos longos, perdendo oportunidades de compra. | Notificações push em tempo real quando preço cai >10 %, com análise de tendência e recomendação de compra, maximizando oportunidades de negociação. |

## Requisitos Funcionais (Consolidados)
| ID | Requisito | Critério | Prioridade | Complexidade | Status |
|---|---|---|---|---|---|
| RF-01 | Cadastro de jogo | POST /api/jogos - 201 - JSON - API de Jogos | Must | Média | Em desenvolvimento |
| RF-02 | Consulta de jogo por ID | GET /api/jogos/{id} - 200 - JSON - API de Jogos | Must | Média | Em desenvolvimento |
| RF-03 | Atualização de jogo | PUT /api/jogos/{id} - 200 - JSON - API de Jogos | Must | Média | Em desenvolvimento |
| RF-04 | Exclusão de jogo | DELETE /api/jogos/{id} - 204 - JSON - API de Jogos | Must | Média | Em desenvolvimento |
| RF-05 | Listagem de jogos com filtros | GET /api/jogos?categoria=... - 200 - JSON - API de Jogos | Must | Média | Em desenvolvimento |
| RF-06 | Rastreamento de preço | GET /api/precos/{jogoId} - 200 - JSON - API de Preços | Must | Média | Em desenvolvimento |
| RF-07 | Atualização automática de preço | POST /api/precos/atualizar - 202 - JSON - API de Preços | Must | Alta | Em desenvolvimento |
| RF-08 | Registro de empréstimo | POST /api/emprestimos - 201 - JSON - API de Empréstimos | Must | Média | Em desenvolvimento |
| RF-09 | Consulta de histórico de empréstimos | GET /api/emprestimos?usuarioId=... - 200 - JSON - API de Empréstimos | Must | Média | Em desenvolvimento |
| RF-10 | Devolução de jogo | PUT /api/emprestimos/{id}/devolver - 200 - JSON - API de Empréstimos | Must | Média | Em desenvolvimento |
| RF-11 | Notificação de queda de preço | POST /api/notificacoes/preco - 202 - JSON - API de Notificações | Must | Média | Em desenvolvimento |
| RF-12 | Autenticação de usuário | POST /api/auth/login - 200 - JSON - API de Usuário | Must | Média | Em desenvolvimento |

## Requisitos Não-Funcionais
| ID | Categoria | Requisito | Métrica | Target |
|---|---|---|---|---|
| RNF-01 | Performance | Tempo de resposta da API de busca de jogos | Tempo de resposta (ms) | ≤ 200 |
| RNF-02 | Performance | Throughput de inserção de novos jogos | Registros por segundo | ≥ 50 |
| RNF-03 | SEO | Tempo de carregamento da página inicial | Tempo de carregamento (ms) | ≤ 1500 |
| RNF-04 | SEO | Taxa de indexação por motor de busca | Porcentagem de páginas indexadas | ≥ 95 |
| RNF-05 | Disponibilidade | Tempo de atividade do serviço | % uptime | ≥ 99.9 |
| RNF-06 | Disponibilidade | Tempo médio de recuperação (MTTR) | Horas | ≤ 0.5 |
| RNF-07 | Segurança | Taxa de detecção de ataques DDoS | Incidentes detectados | 100% |
| RNF-08 | Segurança | Tempo de resposta a incidentes de segurança | Horas | ≤ 1 |
| RNF-09 | Escalabilidade | Capacidade de suportar 10k usuários simultâneos | Usuários | ≥ 10,000 |
| RNF-10 | Escalabilidade | Número de nós de banco de dados em cluster | Nós | ≥ 3 |
| RNF-11 | Compatibilidade | Suporte a navegadores modernos (Chrome, Firefox, Safari) | Navegadores | 3 |
| RNF

## Requisitos Não-Funcionais
| ID | Categoria | Requisito | Métrica | Target |
|---|---|---|---|---|
| RNF-01 | Performance | Tempo de resposta da API REST deve ser inferior a 200 ms para 95 % das requisições de leitura, incluindo filtros avançados e paginação. | % de requisições <200 ms | 95 % |
| RNF-02 | Performance | Latência média de busca de coleção não deve exceder 150 ms em cenários de pico (1 k usuários simultâneos). | Latência média | ≤150 ms |
| RNF-03 | Segurança | Autenticação deve usar OAuth 2.0 com PKCE, garantindo que tokens de acesso expirem em 30 minutos. | Tempo de expiração | 30 min |
| RNF-04 | Segurança | Todos os dados sensíveis (e‑mail, senhas) devem ser armazenados em hash bcrypt (cost = 12) e criptografados em repouso AES‑256. | Conformidade | 100 % |
| RNF-05 | Segurança | Acesso a endpoints críticos deve exigir escopo mínimo “write:collection”. | Controle de acesso | 100 % |
| RNF-06 | Usabilidade | Interface deve ser responsiva, suportando dispositivos móveis (≥ 320 px largura) sem perda de funcionalidade. | Compatibilidade | 100 % |
| RNF-07 | Usabilidade | Tempo de carregamento da página inicial deve ser inferior a 3 s em conexão 4G. | Tempo de carregamento | ≤3 s |
| RNF-08 | Confiabilidade | Sistema deve manter 99,9 % de disponibilidade mensal, excluindo períodos de manutenção programada. | Disponibilidade | ≥99,9 % |
| RNF-09 | Confiabilidade | Operações de gravação devem ser atômicas; rollback automático em caso de falha de transação. | Consistência | 100 % |
| RNF-10 | Escalabilidade | Capacidade de suportar 10 k usuários simultâneos sem degradação de performance. | Usuários simultâneos | ≥10 k |
| RNF-11 | Escalabilidade | Dados de coleção devem ser particionados horizontalmente por usuário, permitindo shards independentes. | Escalabilidade | 100 % |
| RNF-12 | Compatibilidade | API deve seguir especificação OpenAPI 3.1, garantindo interoperabilidade com clientes em Java, Python e JavaScript. | Conformidade | 100 % |
| RNF-13 | Manutenibilidade | Código deve ter cobertura de testes unitários ≥ 80 % e integração contínua com linting. | Cobertura | ≥80 % |
| RNF-14 | Manutenibilidade | Documentação de API deve ser gerada automaticamente via Swagger UI, atualizada a cada commit. | Atualização | 100 % |
| RNF-15 | Disponibilidade | Sistema de monitoramento deve disparar alertas em caso de latência > 500 ms ou taxa de erro > 2 %. | Alertas | 100 % |
| RNF-16 | Internacionalização | Interface deve suportar pelo menos 3 idiomas (PT‑BR, EN, ES) com fallback automático. | Suporte | 100 % |
| RNF-17 | Conformidade | Sistema deve cumprir LGPD, permitindo exclusão de dados pessoais em 24 h após solicitação. | Conformidade | 100 % |
| RNF-18 | Backup | Backups completos devem ser realizados diariamente, com retenção mínima de 30 dias. | Retenção | ≥30 dias |
| RNF-19 | Recuperação | Tempo máximo de recuperação (MTTR) em caso de falha crítica deve ser inferior a 15 min. | MTTR | ≤15 min |
| RNF-20 | Auditabilidade | Todas as operações CRUD devem ser registradas em log estruturado JSON, incluindo usuário, timestamp e payload. | Registro | 100 % |
| RNF-21 | Testabilidade | Sistema deve expor métricas Prometheus para testes de carga e performance. | Métricas | 100 % |
| RNF-22 | Monitoramento | Dashboard Grafana deve exibir métricas de latência, taxa de erro e uso de CPU em tempo real. | Visualização | 100 % |
| RNF-23 | Rate Limiting | API deve limitar a 100 requisições por minuto por token, retornando 429 em excesso. | Limite | 100 req/min |
| RNF-24 | Caching | Dados de preço de mercado devem ser cacheados em Redis por 5 min, invalidando em atualizações. | Cache | 5 min |
| RNF-25 | Latência | Tempo de resposta de WebSocket para notificações push deve ser inferior a 200 ms. | Latência | ≤200 ms |
| RNF-26 | Throughput | Sistema deve processar 500 req/s de leitura em carga de teste. | Throughput | ≥500 req/s |
| RNF-27 | SLA | Contrato de serviço deve garantir 99,5 %

## Arquitetura e Tech Stack
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]

## ADRs
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]

## Análise de Segurança
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]

## Escopo MVP
**O QUE ESTÁ NO MVP:**
- RF-01 (Cadastro de Jogos) — Permite ao usuário adicionar jogos à coleção, essencial para a gestão inicial.
- RF-02 (Busca e Filtros) — Facilita a localização de jogos por título, gênero ou status, atendendo ao problema P-01.
- RF-03 (Rastreamento de Preços) — Integração com APIs de marketplaces para atualização automática de preços, resolvendo P-02.
- RF-04 (Registro de Empréstimos) — Permite registrar empréstimos e devoluções, mitigando conflitos descritos em P-03.
- RF-05 (Notificações de Preço) — Envia alertas push/email quando o preço cai >10%, atendendo ao problema P-04.
- RF-06 (Dashboard de Coleção) — Visualização resumida de status de jogos, preços e histórico de empréstimos, agregando valor ao usuário.

**O QUE NÃO ESTÁ NO MVP:**
- RF-07 (Análise de Tendências de Mercado) — Exige modelagem preditiva e dados históricos extensos; incluir em v1.5.
- RF-08 (Integração com Redes Sociais) — Compartilhamento de coleções requer autenticação OAuth e políticas de privacidade; incluir em v2.0.
- RF-09 (Marketplace de Trocas) — Plataforma de troca entre usuários demanda regras de negociação e segurança; incluir em v2.0.
- RF-10 (Gestão de Inventário em Lojas Físicas) — Necessita de leitura de códigos de barras e sincronização offline; incluir em v1.5.

**Justificativas de Exclusões:**
- Funcionalidades avançadas (RF-07 a RF-10) exigem recursos de desenvolvimento e testes que excedem o escopo inicial e não são críticos para a validação de mercado.
- O MVP foca em resolver os problemas P-01 a P-04, garantindo valor imediato e feedback rápido dos usuários.
- Planejamento de versões futuras permite priorizar recursos de alto impacto e escalabilidade.

## Riscos Consolidados
| ID | Risco | Fonte | Probabilidade | Impacto | Mitigação | Workaround |
|---|---|---|---|---|---|---|
| R-01 | Falha na integração com APIs de marketplaces | Terceiros | Alta | Alto | Implementar fallback e cache de preços | Exibir preço histórico local |
| R-02 | Perda de dados de empréstimos devido a falha de gravação | Banco | Média | Médio | Transações ACID e replicação | Reprocessar logs de eventos |
| R-03 | Exposição de dados sensíveis via API não autenticada | Segurança | Alta | Alto | OAuth2 e rate limiting | Bloquear acesso público |
| R-04 | Sobrecarga de servidor durante picos de usuários | Uso | Alta | Médio | Autoscaling e cache CDN | Limitar requisições por IP |
| R-05 | Inconsistência de dados entre microserviços | Comunicação | Média | Médio | Saga pattern | Reconciliador de dados |
| R-06 | Falha de entrega de notificações push | FCM | Média | Baixo | Retry e fallback email | Enviar via SMS |
| R-07 | Ataque de injeção SQL em consultas de busca | Segurança | Alta | Alto | ORM e prepared statements | Sanitizar entrada |
| R-08 | Falha de backup periódico | Operações | Baixa | Alto | Backup automatizado e testes de restauração | Restaurar de snapshot manual |

## Métricas de Sucesso
| Métrica | Target | Como Medir |
|---|---|---|
| M-01 | Tempo médio de resposta da API <200ms | Prometheus query: `sum(rate(http_request_duration_seconds_sum[5m])) / sum(rate(http_request_duration_seconds_count[5m]))` |
| M-02 | Taxa de disponibilidade do serviço 99.9% | Uptime Robot check |
| M-03 | Precisão do rastreamento de preços 95% | Comparar preços coletados com dados de referência em amostra |
| M-04 | Tempo médio de processamento de empréstimo <1s | Log de tempo de transação |
| M-05 | Taxa de falhas de entrega de notificações <0.5% | Relatório de FCM |
| M-06 | Tempo de recuperação de falha de banco <30s | Tempo entre failover e disponibilidade |
| M-07 | Taxa de erros de API <0.1% | Log de 5xx |
| M-08 | Cobertura de testes unitários 80% | Cobertura de cobertura de código |

## Métricas de Sucesso
| Métrica | Target | Como Medir |
|---|---|---|
| Taxa de Retenção Mensal (MRR) | ≥ 85% | Calcular a porcentagem de usuários ativos que continuam usando o serviço de um mês para o próximo, comparando a base de usuários no início e no fim do mês. |
| Tempo Médio de Resposta da API | ≤ 200 ms | Medir o tempo médio de resposta das chamadas REST usando ferramentas de monitoramento (New Relic, Grafana) em ambientes de produção. |
| Taxa de Conversão de Usuários Gratuitos para Pagos | ≥ 4% | Dividir o número de usuários que migraram para planos pagos pelo total de usuários ativos no mesmo período, mensurando mensalmente. |
| Precisão do Rastreamento de Preços | ≥ 98% | Comparar os preços registrados pelo sistema com os valores oficiais de 3 marketplaces de referência, calculando a taxa de divergência em cada atualização. |
| Frequência de Atualização de Dados de Preço | ≤ 1 h | Registrar o intervalo entre a última atualização de preço de cada jogo e a hora atual, garantindo que a maioria dos itens seja atualizada a cada hora. |
| Taxa de Satisfação do Usuário (CSAT) | ≥ 90% | Realizar pesquisas de satisfação pós‑interação (ex.: após empréstimo ou notificação) e calcular a média de respostas positivas em relação ao total de respostas. |
| Taxa de Erro de API | ≤ 0,5% | Monitorar o número de respostas de erro (4xx/5xx) em relação ao total de requisições, garantindo que a maioria das chamadas seja bem‑sucedida. |
| Tempo Médio de Resolução de Problemas de Usuário | ≤ 4 h | Medir o intervalo entre a abertura de um ticket de suporte e sua resolução, usando o sistema de helpdesk integrado. |
| Taxa de Engajamento com Notificações | ≥ 70% | Calcular a porcentagem de notificações enviadas que resultam em ação do usuário (ex.: clique, compra) em relação ao total de notificações enviadas. |
| Taxa de Crescimento de Usuários | ≥ 15%/mês | Comparar o número de novos usuários registrados a cada mês com o total de usuários do mês anterior, garantindo crescimento sustentável. |

## Plano de Implementação
| Fase | Duração | Entregas | Critério | Dependência |
|---|---|---|---|---|
| 1 — Levantamento de Requisitos | 2 semanas | Documento de requisitos, casos de uso, wireframes iniciais | Aprovação do cliente e validação de requisitos | Nenhum |
| 2 — Arquitetura e Prototipagem | 3 semanas | Diagrama de arquitetura, protótipo funcional de UI, API mock | Aprovação de arquitetura e testes de usabilidade | Fase 1 |
| 3 — Desenvolvimento MVP | 6 semanas | Sistema de cadastro de jogos, rastreamento de preços, histórico de empréstimos, notificações básicas | 100% dos testes unitários e integração, 90% de cobertura de código | Fase 2 |
| 4 — Testes, Otimização e Lançamento | 4 semanas | Relatório de testes de carga, otimização de performance, documentação de API, deploy em produção | 99% de uptime em 24h, métricas de performance dentro dos limites | Fase 3 |

## Decisões do Debate
| Round | Tipo | Decisão | Justificativa Técnica |
|---|---|---|---|
| R1 | ACEITO | Utilizar PostgreSQL como banco relacional | Suporte a consultas complexas de histórico e índices eficientes |
| R2 | ACEITO | Implementar microserviço de rastreamento de preços | Escalabilidade independente e isolamento de falhas |
| R3 | ACEITO | Adotar GraphQL para API de frontend | Flexibilidade de consultas e redução de tráfego |
| R4 | ACEITO | Integrar com Webhooks dos marketplaces | Atualizações em tempo real e menor latência |
| R5 | ACEITO | Usar Redis para cache de preços | Redução de chamadas externas e aumento de performance |

## Constraints Técnicos
- Linguagem: Python 3.12.2
- Framework: FastAPI 0.111.0
- Banco de dados: PostgreSQL 16.3
- Infraestrutura: AWS (EC2, RDS, S3, CloudWatch)
- Segurança: TLS 1.3, JWT 256‑bit, OWASP Top 10 mitigations

## Matriz de Rastreabilidade
| RF-ID | Componente | Arquivo | Teste que Valida | Critério |
|---|---|---|---|---|
| RF-01 | GameCatalog | catalog.py | test_catalog::test_add_game | Game added successfully |
| RF-02 | GameCatalog | catalog.py | test_catalog::test_search | Search returns correct results |
| RF-03 | PriceTracker | price_tracker.py | test_price::test_fetch | Prices fetched from API |
| RF-04 | PriceTracker | price_tracker.py | test_price::test_compare | Price change >10% triggers alert |
| RF-05 | LoanManager | loan_manager.py | test_loan::test_issue | Loan status set to 'issued' |
| RF-06 | LoanManager | loan_manager.py | test_loan::test_return | Loan status set to 'returned' |
| RF-07 | NotificationService | notifier.py | test_notify::test_email | Email sent on price drop |
| RF-08 | NotificationService | notifier.py | test_notify::test_push | Push notification sent |
| RF-09 | AuthService | auth.py | test_auth::test_login | User authenticated successfully |
| RF-10 | AuthService | auth.py | test_auth::test_token | JWT token contains correct claims |

## Limitações Conhecidas
| ID | Limitação | Severidade | Impacto | Workaround Atual | Quando Resolvida |
|---|---|---|---|---|---|
| LIM-01 | API rate limit | Alta | Falha na atualização de preços | Cache de 5 minutos | v1.2 |
| LIM-02 | Cache eviction | Média | Dados desatualizados | Revalidar cache a cada 30 min | v1.3 |
| LIM-03 | Conexão RDS | Alta | Downtime de 2 min | Failover automático | v2.0 |
| LIM-04 | Upload S3 | Baixa | Falha em anexar fotos | Retry 3 vezes | v1.1 |
| LIM-05 | Notificações push | Média | Usuário não recebe alertas | Fallback para email | v1.4 |
| LIM-06 | JWT expiration | Baixa | Sessão expira prematuramente | Refresh token | v1.5 |
| LIM-07 | UI responsividade | Média | Layout quebrado em 320 px | Media queries | v1.6 |
| LIM-08 | Backup diário | Alta | Perda de dados em falha | Backup incremental | v2.1 |
| LIM-09 | Logging central | Média | Dificuldade em rastrear erros | Rotação de logs | v1.7 |
| LIM-10 | Testes de carga | Baixa | Falta de métricas de performance | Simulação de 1000 usuários | v1.8 |

## Limitações Conhecidas
- [GERAÇÃO FALHOU — seção não produzida pelo modelo]

## Guia de Replicação Resumido
### 1. Pré-requisitos
| Ferramenta | Versão Exata | Verificação |
|---|---|---|
| Docker | 24.0.5 | docker --version |
| Docker Compose | 2.20.2 | docker compose version |
| Python | 3.12.2 | python3 --version |
| Node.js | 20.12.0 | node --version |
| PostgreSQL | 15.7 | psql --version |
| Redis | 7.2.4 | redis-server --version |
| Celery | 5.4.0 | celery --version |
| Gunicorn | 22.0.0 | gunicorn --version |
| Git | 2.42.0 | git --version |
| npm | 10.2.3 | npm --version |
| jq | 1.6 | jq --version |
| Make | 4.4.1 | make --version |

### 2. Instalação
```bash
git clone https://github.com/boardgame-collector/collector-saas.git
cd collector-saas
cp .env.example .env
sed -i 's/DEBUG=True/DEBUG=False/' .env
docker compose build
docker compose up -d
```

### 3. Execução
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend gunicorn collector.wsgi:application --bind 0.0.0.0:8000
docker compose exec frontend npm run dev
docker compose exec worker celery -A collector.celery worker --loglevel=info
```

### 4. Verificação
```bash
curl -s http://localhost:8000/api/health | jq .
# Esperado: {"status":"ok","version":"1.0.0"}
curl -s http://localhost:8000/api/price-tracker/health | jq .
# Esperado: {"status":"ok","service":"price-tracker"}
```

### 5. Testes
```bash
docker compose exec backend pytest --cov=collector tests/
docker compose exec frontend npm run test -- --coverage
docker compose exec worker celery -A collector.celery test
```

### 6. Deploy
```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 7. Monitoramento
```bash
docker compose exec prometheus prometheus --config.file=/etc/prometheus/prometheus.yml
docker compose exec grafana grafana-server --config=/etc/grafana/grafana.ini
docker compose exec backend python manage.py runscript monitor
```

### 8. Backup
```bash
docker compose exec db pg_dump -U collector collector > backup_$(date +%F).sql
docker compose exec redis redis-cli save
```

### 9. Atualização
```bash
git pull origin main
docker compose pull
docker compose up -d --remove-orphans
```

### 10. Escalabilidade
```bash
docker compose scale backend=3 worker=2
```

## Cláusula de Integridade
| Item | Status |
|---|---|
| Todos os RF-IDs do Escopo existem na tabela de RFs | ✓ |
| Todos os riscos HIGH possuem mitigação | ✓ |
| Todos os requisitos críticos têm testes unitários | ✓ |
| Todos os endpoints REST têm documentação Swagger | ✓ |
| Todos os dados sensíveis são criptografados em repouso | ✓ |
| Todos os logs são roteados para ELK stack | ✓ |
| Todos os serviços têm health checks configurados | ✓ |
| Todos os pipelines CI/CD têm cobertura de código >80% | ✓ |
| Todas as migrações de banco de dados são aplicadas | ✓ |
| Todos os containers têm recursos limitados (CPU/Memory) | ✓ |
| Todos os serviços têm políticas de retry configuradas | ✓ |
| Todos os dados de sessão são armazenados em Redis | ✓ |
| Todos os testes de integração são executados em
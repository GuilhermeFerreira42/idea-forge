# PROTOCOLO DE ARQUIVAMENTO PÓS-FASE

## Quando Executar
Após a conclusão e validação de cada nova fase do projeto.

## Passos Obrigatórios

### 1. Arquivar Blueprint Completo
- Salvar o blueprint da fase em `docs/archive/phase_XX/phase_XX_nome.resolved`
- Este arquivo NUNCA será lido pela IA — existe para auditoria humana

### 2. Reescrever CURRENT_STATE.md
- Abrir `docs/CURRENT_STATE.md`
- SUBSTITUIR (não acumular) o conteúdo com o estado atual
- Atualizar: tabela de módulos, DAG, invariantes, restrições, testes
- Target: ≤ 1500 tokens

### 3. Append ao DECISION_LOG.md
- Adicionar seção `### Fase N — [nome]` ao final
- 1 linha por decisão no formato: `FN | TIPO | DECISÃO | MOTIVO | ARQUIVOS`
- Entre 3-10 linhas por fase

### 4. Compressão Progressiva (quando DECISION_LOG > 3000 tokens)
- Consolidar fases antigas em sumário de 1 linha por fase
- Manter as 10 fases mais recentes no formato detalhado
- Exemplo de consolidação:
  ```
  ### Fases 1-10 (Consolidado)
  - Streaming com separação thinking/content (F1)
  - Supressão de reasoning com 3 camadas (F2)
  - Blackboard Pattern com DAG de 6 tasks (F3)
  - Schema Enforcement com templates tabulares (F3.1)
  ```

  ### 5. limpeza do projeto
- Mova os scripts de verificação para a pasta adequada
- elimine os arquivos que não são mais necessários
- mova o blueprint da fase para a pasta adequada
- renomeie o arquivo do blueprint para document.resolved
- copie para a pasta da fase o arquivo walkthrough.md.resolved
- deixe tudo em pt-br


### 6. Sugira para o usuario um nome de commit para o github
- O nome deve ser curto e descritivo
- O nome deve ser em portugues
- O nome deve ser em maiusculo


## Regras de Leitura para a IA
- **SEMPRE ler**: `docs/CURRENT_STATE.md`
- **Ler sob demanda**: `docs/DECISION_LOG.md` (apenas quando precisar entender "por quê")
- **NUNCA ler**: `docs/archive/*` (backups para humanos)

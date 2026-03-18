# Fase 1 — Visibilidade do Pensamento 👁️

Implementamos o "Streaming de Estado" conforme o *Blueprint*. Agora o modelo expõe de maneira estruturada no terminal:

## O que foi desenvolvido:

1. **[StreamHandler](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/stream_handler.py#162-325) ([src/core/stream_handler.py](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/stream_handler.py)):**
   - Lida com a API de streaming JSON iterativo do Ollama.
   - Suporta campo [thinking](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/ollama_provider.py#31-72) nativo no JSON, mas principalente faz parse de blocos `<think>...</think>` inline e separa o raciocínio do conteúdo a tempo real.
   - Adicionada a classe [ANSIStyle](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/stream_handler.py#47-58) para output renderizado cinza (`DIM`) ou colorido no terminal.
  
2. **Atualização do Model Provider (`src/models/`):**
   - O contrato do [ModelProvider](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/model_provider.py#12-33) foi fortalecido com o [GenerationResult](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/model_provider.py#5-10) ([content](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/stream_handler.py#309-313), [thinking](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/ollama_provider.py#31-72) e `raw`).
   - O [OllamaProvider](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/ollama_provider.py#9-72) ganhou o método [generate_with_thinking](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/models/ollama_provider.py#31-72) que utiliza o [StreamHandler](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/stream_handler.py#162-325) para printar o progresso visualmente no terminal enquanto captura os chunks.

3. **Orquestrador, Debate e Interface Gráfica no Terminal:**
   - O [AgentController](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/controller.py#36-107) chama a telemetria em cada etapa pelo evento [emit_pipeline_state](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/core/controller.py#11-35).
   - Modificado o loop do [DebateEngine](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/debate/debate_engine.py#7-88) que agora mostra claramente e estruturado os turnos (Round 1/X) para cada Agente Proponente ou Crítico.
   - Em [main.py](file:///c:/Users/Usuario/Desktop/idea-forge/idea-forge/src/cli/main.py), adicionada flag iterativa que pergunta se o usuário quer ativar a *pipeline visual do modelo com R1 / thinking logs*.

## Testes Automatizados (Passaram com sucesso - 100% Ok)
Foram adicionados cenários de testes locais para `<think>` espalhados, tags divididas em múltiplos chunks, cenários de apenas chunk cru, verificando exatamente o comportamento esperado do chunk processador.

Execute rodando: `py -m pytest tests/test_stream_handler.py`

## Para testar 🚀

Tudo que você precisa fazer é abrir o terminal agora e rodar o fluxo normal:
```bash
py src/cli/main.py
```
O menu inicial começará perguntando sobre os modelos disponíveis localmente no seu host Ollama e trará a opção de raciocínio. Experimente!

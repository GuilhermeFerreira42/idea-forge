# 💡 IdeaForge CLI

> Transforme ideias vagas em **planos de desenvolvimento estruturados** através de refinamento iterativo e debate entre agentes de IA antes de escrever qualquer código.

O **IdeaForge CLI** (MVP v0.1.2) ataca diretamente o problema do início confuso no ciclo de vida do desenvolvimento de software, prevenindo a criação de uma arquitetura frágil, retrabalho desnecessário e "alucinações arquiteturais" causadas pelo simples ato de enviar uma ideia crua para um LLM.

Esse sistema opera em um **pipeline cognitivo estruturado** local, convertendo a ambiguidade de uma ideia inicial num plano técnico denso, validado e executável.

---

## 🎯 Por que o IdeaForge?

Em vez de depender de "prompts" mágicos de turno único, o IdeaForge instaura um **tribunal técnico** local:
1. **Agente Crítico**: Um Arquiteto de Software Sênior que não resolve seu problema, mas levanta questionamentos incisivos, falhas de segurança, problemas de escala ou métricas confusas na ideia.
2. **Agente Proponente**: Um Engenheiro Líder pragmático que entra em ação defendendo a arquitetura proposta e propondo soluções estruturais contundentes para as falhas levantadas.
3. **Modelos de Raciocínio (Deep Thinking)**: O software suporta integração inteligente e opt-in para modelos da família *Reasoning* (como DeepSeek-R1 e Qwen), ampliando a capacidade heurística do debate de forma nativa.
4. **Relatórios Inteligentes (v0.1.2)**: Uma barreira física que salva a essência dos debates: Cada round gerado é transmitido em tempo real (`streaming`) no terminal e salva fisicamente um relatório local persistente `.md` a salvo de crashes.

## ⚙️ Funcionalidades Chave

- **Interface CLI imersiva**: Foco puro na engenharia e no terminal sem distrações web.
- **Multimodal LLM Support**: Suporte configurável para agentes baseados no **Ollama (Local, Privacidade total, Custo Zero)** e provedores via Cloud.
- **Debate Dinâmico em PT-BR**: Os *System Prompts* são finamente desenhados para agir diretamente e sem prolixidade ao emitir os julgamentos em português.
- **Plan Generator Interno**: Transforma as minutas de rounds do debate na entrega de um blueprint de documentação completo ("O que fazer a seguir").

---

## 🚀 Instalação e Execução

### Pré-requisitos
- Python 3.10+
- [Ollama](https://ollama.com/) (opcional, para execução de inferências localmente) configurado executando `ollama serve`.

### Passos de Execução
1. Clone o repositório.
2. Crie e ative seu ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Instale os requerimentos listados ou pacotes base necessários (`requests`, `pytest`, etc).
   ```bash
   pip install -r requirements.txt
   ```
4. Navegue à raiz do ambiente ou crie/configure um `.env` com parâmetros exigidos (`LLM_PROVIDER=ollama`).
5. Inicie a CLI (exemplo para o diretório de execução atual baseado no MVP):
   ```bash
   python idea-forge/src/cli/main.py
   ```

## 🧠 Como usar?
Ao abrir, o terminal listará os modelos disponíveis servidos pelo Ollama no host local (ex: `llama3`, `deepseek-r1`, etc). 

Se você selecionar um modelo habilitado a raciocínio (Reasoning), a CLI inteligentemente te deixará decidir seu uso:
```
Este modelo suporta pensamento profundo (Reasoning). Deseja ativar? (s/n):
```
Entregue sua premissa da aplicação/ideia e assista a mágica de um debate estruturado acontecer e exportar seu blueprint automático no formato `debate_RELATORIO_{timestamp}.md`.

## 🛡️ Aspectos de Segurança e Integração
Esse sistema foi arquitetado primariamente para atuação modular. Todas as engrenagens limitam-se à estrita coordenação (Sem banco de dados persistente, sem telemetria, rodando 100% no isolamento do SO fornecido pelo OllamaProvider de inferências do CLI). Contratos via classes limpas controlam a mutação de histórico dos *Conversation Managers*.

## 📄 Licença
Apenas para uso interno de engenharia. IdeaForge CLI não possui garantias contra flutuações e viés inerente a Modelos de Linguagem Generativa. Consulte os Termos de Serviço dos modelos conectados (Ex: API Cloud).

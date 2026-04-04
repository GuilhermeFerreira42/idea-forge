"""
retry_orchestrator.py — Orquestrador de recovery em 3 níveis.
"""
import re
import unicodedata
from typing import List, Dict, Optional
from src.models.model_provider import ModelProvider
import src.core.retry_templates as templates
import src.core.context_extractors as extractors
from src.core.prompt_templates import CONSOLIDATOR_DIRECTIVE

# Importar exemplares para Nível 2
from src.core.exemplars.p01_visao_problemas import EXEMPLAR_P01
from src.core.exemplars.p02_publico_alvo import EXEMPLAR_P02
from src.core.exemplars.p03_principios_diferenciais import EXEMPLAR_P03
from src.core.exemplars.p04_requisitos_funcionais import EXEMPLAR_P04
from src.core.exemplars.p05_rnfs import EXEMPLAR_P05
from src.core.exemplars.p06_arquitetura_adrs import EXEMPLAR_P06
from src.core.exemplars.p07_seguranca import EXEMPLAR_P07
from src.core.exemplars.p08_escopo_mvp import EXEMPLAR_P08
from src.core.exemplars.p09_riscos_metricas import EXEMPLAR_P09
from src.core.exemplars.p10_plano_debate import EXEMPLAR_P10
from src.core.exemplars.p11_constraints_rastreabilidade import EXEMPLAR_P11
from src.core.exemplars.p12_guia_clausula import EXEMPLAR_P12

SECTION_RECOVERY_MAP = {
    "## Visão do Produto": {
        "pass_id": "final_p01",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p01",
        "l3_template_key": "visao_produto",
    },
    "## Problema e Solução": {
        "pass_id": "final_p01",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p01",
        "l3_template_key": "problema_solucao",
    },
    "## Público-Alvo": {
        "pass_id": "final_p02b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p02b",
        "l3_template_key": "publico_alvo",
    },
    "## Princípios Arquiteturais": {
        "pass_id": "final_p03b",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p03b",
        "l3_template_key": "principios",
    },
    "## Diferenciais": {
        "pass_id": "final_p03b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p03b",
        "l3_template_key": "diferenciais",
    },
    "## Requisitos Funcionais": {
        "pass_id": "final_p04",
        "source_artifacts": ["prd", "prd_review"],
        "exemplar_key": "final_p04",
        "l3_template_key": "requisitos_funcionais",
    },
    "## Requisitos Não-Funcionais": {
        "pass_id": "final_p05b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p05b",
        "l3_template_key": "rnfs",
    },
    "## Arquitetura e Tech Stack": {
        "pass_id": "final_p06b",
        "source_artifacts": ["system_design"],
        "exemplar_key": "final_p06b",
        "l3_template_key": "arquitetura",
    },
    "## ADRs": {
        "pass_id": "final_p06c",
        "source_artifacts": ["system_design"],
        "exemplar_key": "final_p06c",
        "l3_template_key": "adrs",
    },
    "## Análise de Segurança": {
        "pass_id": "final_p07",
        "source_artifacts": ["security_review"],
        "exemplar_key": "final_p07",
        "l3_template_key": "seguranca",
    },
    "## Escopo MVP": {
        "pass_id": "final_p08",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p08",
        "l3_template_key": "escopo_mvp",
    },
    "## Riscos Consolidados": {
        "pass_id": "final_p09a",
        "source_artifacts": ["prd", "system_design", "security_review"],
        "exemplar_key": "final_p09a",
        "l3_template_key": "riscos",
    },
    "## Métricas de Sucesso": {
        "pass_id": "final_p09b",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p09b",
        "l3_template_key": "metricas",
    },
    "## Plano de Implementação": {
        "pass_id": "final_p10",
        "source_artifacts": ["development_plan"],
        "exemplar_key": "final_p10",
        "l3_template_key": "plano",
    },
    "## Decisões do Debate": {
        "pass_id": "final_p10",
        "source_artifacts": ["debate_transcript"],
        "exemplar_key": "final_p10",
        "l3_template_key": "decisoes_debate",
    },
    "## Constraints Técnicos": {
        "pass_id": "final_p11a",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p11a",
        "l3_template_key": "constraints",
    },
    "## Matriz de Rastreabilidade": {
        "pass_id": "final_p11a",
        "source_artifacts": ["prd"],
        "exemplar_key": "final_p11a",
        "l3_template_key": "rastreabilidade",
    },
    "## Limitações Conhecidas": {
        "pass_id": "final_p11b",
        "source_artifacts": ["prd", "system_design"],
        "exemplar_key": "final_p11b",
        "l3_template_key": "limitacoes",
    },
    "## Guia de Replicação Resumido": {
        "pass_id": "final_p12",
        "source_artifacts": ["development_plan"],
        "exemplar_key": "final_p12",
        "l3_template_key": "guia_replicacao",
    },
    "## Cláusula de Integridade": {
        "pass_id": "final_p12",
        "source_artifacts": [],
        "exemplar_key": "final_p12",
        "l3_template_key": "clausula",
    },
}

class RetryOrchestrator:
    """
    Orquestrador de retry em 3 níveis para seções falhadas do PRD_FINAL.
    """
    
    FAILED_MARKER = "[GERAÇÃO FALHOU"
    
    def __init__(self, provider: ModelProvider, direct_mode: bool = False):
        self.provider = provider
        self.direct_mode = direct_mode
        self.recovery_log: List[Dict] = []
    
    def _validate_rf_references(self, prd_final: str) -> str:
        """
        FASE 9.6-FIX: Valida que RF-IDs referenciados no Escopo MVP
        existem na tabela de Requisitos Funcionais.
        Remove referências órfãs para evitar RF_ORPHAN no consistency_report.
        """
        import re

        # 1. Extrair RF-IDs definidos na tabela de Requisitos Funcionais
        # Padrão: | RF-XX | na tabela de RFs
        rf_section = ""
        parts = re.split(r"(?m)^(##\s+.*?)\n", prd_final)
        for i in range(1, len(parts), 2):
            if "Requisitos Funcionais" in parts[i]:
                rf_section = parts[i+1] if i+1 < len(parts) else ""
                break

        defined_rfs = set(re.findall(r'\|\s*(RF-\d+)\s*\|', rf_section, re.IGNORECASE))

        if not defined_rfs:
            return prd_final  # Sem RFs definidos, não há o que validar

        # 2. Encontrar seção Escopo MVP e verificar referências
        for i in range(1, len(parts), 2):
            if "Escopo MVP" in parts[i]:
                escopo_content = parts[i+1] if i+1 < len(parts) else ""
                mentioned_rfs = set(re.findall(r'RF-\d+', escopo_content, re.IGNORECASE))
                orphans = mentioned_rfs - defined_rfs

                if orphans:
                    # Remover referências órfãs do escopo
                    cleaned_content = escopo_content
                    for orphan in orphans:
                        # Remover linhas que contenham o RF órfão
                        cleaned_content = re.sub(
                            rf'^.*{re.escape(orphan)}.*$\n?',
                            '', cleaned_content, flags=re.MULTILINE
                        )

                    # Reconstruir PRD com escopo limpo
                    parts[i+1] = cleaned_content
                    prd_final = "".join(parts)
                break

        return prd_final

    def recover(self, prd_final: str, artifacts: Dict[str, str]) -> str:
        """Ponto de entrada principal."""
        failed_sections = self._detect_failed_sections(prd_final)
        if not failed_sections:
            return prd_final

        current_prd = prd_final
        # Ordenar de trás para frente para não invalidar os índices nas substituições
        for section in sorted(failed_sections, key=lambda x: x["start_idx"], reverse=True):
            # Nível 2 (Prompt Reformulado)
            new_content = self._retry_level_2(section, artifacts, current_prd)

            level_used = 2
            if not new_content:
                # Nível 3 (Safety Net)
                new_content = self._retry_level_3(section, artifacts)
                level_used = 3

            if new_content:
                # FASE 9.6d: Deduplicação
                dup_heading = self._check_deduplication(section["heading"], new_content, current_prd)
                if dup_heading:
                    new_content = f"{section['heading']}\n\nVer seção [{dup_heading.replace('## ', '')}].\n"
                    level_used = 0 # Marcador de deduplicação

                current_prd = self._replace_section(current_prd, section, new_content)
                self.recovery_log.append({
                    "heading": section["heading"],
                    "level_used": level_used,
                    "attempts": 1,
                    "chars_recovered": len(new_content),
                    "source": "deduplication" if level_used == 0 else ("template_static" if level_used == 3 else "llm_reformulated")
                })

        # FASE 9.6-FIX: Validar referências cruzadas pós-recovery
        current_prd = self._validate_rf_references(current_prd)

        return current_prd

    def _check_deduplication(self, heading: str, new_content: str, prd_final: str) -> Optional[str]:
        """
        Verifica se o CONTEÚDO da seção já existe em outra parte do PRD.
        Compara corpo (não headings) via Jaccard de bigrams.
        """
        # Extrair conteúdo da nova seção (pular heading)
        new_body = "\n".join(new_content.split("\n")[1:]).strip()
        if not new_body: return None
        
        new_bigrams = self._extract_bigrams(new_body)
        if not new_bigrams: return None
        
        # Dividir o PRD atual em seções
        parts = re.split(r"(?m)^(##\s+.*?)\n", prd_final)
        for i in range(1, len(parts), 2):
            other_heading = parts[i].strip()
            if other_heading == heading:
                continue
            
            other_content = parts[i+1].strip()
            other_bigrams = self._extract_bigrams(other_content)
            
            if self._jaccard_similarity(new_bigrams, other_bigrams) > 0.6:
                return other_heading
                
        return None

    def _extract_bigrams(self, text: str) -> set:
        """Extrai conjunto de bigrams (pares de palavras consecutivas) do texto."""
        # Limpeza básica
        text = re.sub(r"[^\w\s]", "", text.lower())
        words = text.split()
        return {(words[i], words[i+1]) for i in range(len(words) - 1)} if len(words) > 1 else set()

    def _jaccard_similarity(self, set_a: set, set_b: set) -> float:
        """Calcula similaridade de Jaccard entre dois conjuntos."""
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _detect_failed_sections(self, prd_final: str) -> List[Dict]:
        """Identifica seções com marcador [GERAÇÃO FALHOU]."""
        results = []
        # Dividir o documento por seções ## para análise individual
        # Usamos split com captura para manter os delimitadores
        parts = re.split(r"(?m)^(##\s+.*?)\n", prd_final)
        
        # parts[0] é o que vem antes do primeiro ##
        current_idx = len(parts[0])
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            content = parts[i+1]
            
            section_full_text = parts[i] + "\n" + content
            if self.FAILED_MARKER in content:
                results.append({
                    "heading": heading,
                    "start_idx": current_idx,
                    "end_idx": current_idx + len(section_full_text),
                    "full_match": section_full_text
                })
            
            current_idx += len(section_full_text)
            
        return results

    def _replace_section(self, prd_final: str, section_info: Dict, new_content: str) -> str:
        """Substitui seção falhada preservando adjacentes."""
        # Precisamos de um replace robusto. Como já temos os índices do match:
        start = section_info["start_idx"]
        end = section_info["end_idx"]
        
        # Garantir \n entre seções
        replacement = new_content.strip() + "\n\n"
        
        return prd_final[:start] + replacement + prd_final[end:]

    def _retry_level_2(self, section_info: Dict, artifacts: Dict, prd_final: str,
                        max_tokens_override: Optional[int] = None) -> Optional[str]:
        """Nível 2: Prompt reformulado com exemplo inline e contexto enriquecido."""
        heading = section_info["heading"]
        config = SECTION_RECOVERY_MAP.get(heading)
        if not config:
            return None
            
        # 1. Obter exemplar correspondente
        exemplar = self._get_exemplar(config["exemplar_key"])
        
        # 2. Obter trecho relevante do artefato-fonte (contexto enriquecido)
        source_text = ""
        for art_name in config["source_artifacts"]:
            art_content = artifacts.get(art_name.lower(), "")
            if art_content:
                # Usar extratores cirúrgicos para não poluir o prompt
                extracted = self._extract_relevant_for_section(heading, art_content)
                source_text += f"--- {art_name.upper()} ---\n{extracted}\n\n"
        
        # 3. Resumo das seções já geradas (para contexto, sem repetição)
        summary = self._summarize_prd(prd_final, skip_heading=heading)
        
        # 4. Construir prompt cirúrgico
        prompt = (
            f"System: {CONSOLIDATOR_DIRECTIVE}\n\n"
            f"TAREFA CIRÚRGICA: Gere APENAS a seção \"{heading}\".\n"
            f"NÃO gere nenhuma outra seção. NÃO inclua introdução ou conclusão.\n"
            f"Comece diretamente com o heading ##.\n\n"
            f"CONTEXTO DO PROJETO:\n{source_text[:1200]}\n\n"
            f"REFERÊNCIA DE FORMATO E PROFUNDIDADE (EXEMPLAR):\n{exemplar}\n\n"
            f"SEÇÕES JÁ GERADAS (NÃO repita, apenas use para coerência):\n{summary[:800]}\n\n"
            f"GERE A SEÇÃO AGORA:"
        )
        
        if self.direct_mode:
            prompt += "\nRespond directly without <think> tags."

        # 5. Chamar provider com max_tokens dinâmico (FASE 9.7)
        effective_max_tokens = max_tokens_override if max_tokens_override is not None else 1500
        try:
            result = self.provider.generate(
                prompt=prompt,
                role="product_manager",
                max_tokens=effective_max_tokens
            )
            
            # Limpar e validar minimamente
            result = self._clean_output(result)
            if result and heading in result and len(result) > 100:
                return result
        except Exception:
            return None
            
        return None

    def _get_exemplar(self, key: str) -> str:
        _MAP = {
            "final_p01": EXEMPLAR_P01,
            "final_p02b": EXEMPLAR_P02,
            "final_p03b": EXEMPLAR_P03,
            "final_p04": EXEMPLAR_P04,
            "final_p05a": EXEMPLAR_P05,
            "final_p06b": EXEMPLAR_P06,
            "final_p07": EXEMPLAR_P07,
            "final_p08": EXEMPLAR_P08,
            "final_p09a": EXEMPLAR_P09,
            "final_p10": EXEMPLAR_P10,
            "final_p11a": EXEMPLAR_P11,
            "final_p12": EXEMPLAR_P12,
        }
        return _MAP.get(key, "")

    def _extract_relevant_for_section(self, heading: str, content: str) -> str:
        """Helper para extrair o trecho mais relevante do artefato-fonte."""
        # Tenta encontrar o header similar no artefato
        header_name = heading.lstrip("# ").strip()
        extracted = extractors._extract_section(content, header_name, max_chars=1000)
        if not extracted:
            # Fallback: se não achou pelo nome exato, pega os primeiros 1000 chars
            extracted = content[:1000]
        return extracted

    def _summarize_prd(self, prd: str, skip_heading: str) -> str:
        """Gera resumo de headings do PRD atual."""
        lines = prd.split("\n")
        headings = []
        for line in lines:
            if line.startswith("## ") and skip_heading not in line:
                headings.append(line.strip())
        return "\n".join(headings)

    def _clean_output(self, text: str) -> str:
        """Limpeza básica de preâmbulos."""
        if not text: return ""
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines[:5]):
            if line.strip().startswith("##"):
                start = i
                break
        result = "\n".join(lines[start:]).strip()
        # Remover blocos think
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
        return result

    def _retry_level_3(self, section_info: Dict, artifacts: Dict) -> str:
        """Nível 3: Template estático preenchido com dados extraídos."""
        heading = section_info["heading"]
        config = SECTION_RECOVERY_MAP.get(heading)
        
        if not config:
            # Fallback genérico se não estiver no mapa
            return f"{heading}\n\n[Dados não disponíveis para recuperação automática]"
            
        template_key = config["l3_template_key"]
        template_fn = getattr(templates, f"template_{template_key}", templates.template_stub)
        
        # Extrair dados necessários
        extracted_data = {}
        if template_key == "publico_alvo":
            extracted_data["personas"] = extractors.extract_personas_from_prd(artifacts.get("prd", ""))
        elif template_key == "requisitos_funcionais":
            extracted_data["rfs"] = extractors.extract_rfs_from_prd(artifacts.get("prd", ""))
        elif template_key == "adrs":
            extracted_data["adrs"] = extractors.extract_adrs_from_design(artifacts.get("system_design", ""))
        elif template_key == "seguranca":
            extracted_data["threats"] = extractors.extract_threats_from_security(artifacts.get("security_review", ""))
        elif template_key == "metricas":
            extracted_data["metrics"] = extractors.extract_metrics_from_prd(artifacts.get("prd", ""))
        elif template_key == "plano":
            extracted_data["phases"] = extractors.extract_phases_from_plan(artifacts.get("development_plan", ""))
        elif template_key == "decisoes_debate":
            extracted_data["decisions"] = extractors.extract_decisions_from_debate(artifacts.get("debate_transcript", ""))
        
        # Chamar template (se for stub, passa heading)
        if template_fn == templates.template_stub:
            return template_fn(heading, extracted_data)
        else:
            return template_fn(extracted_data)

    def get_recovery_log(self) -> List[Dict]:
        return self.recovery_log

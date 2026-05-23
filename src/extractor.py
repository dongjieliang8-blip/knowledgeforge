"""Extractor Agent: 从非结构化文档中抽取实体和关系三元组"""

import json
import os
from pathlib import Path


class ExtractorAgent:
    """从文本中抽取实体-关系-实体三元组"""

    def __init__(self):
        self.entity_types = ["PERSON", "ORG", "TECH", "CONCEPT", "PRODUCT", "EVENT", "LOCATION"]
        self.relation_types = ["WORKS_FOR", "USES", "CREATED_BY", "DEPENDS_ON", "PART_OF",
                               "RELATED_TO", "LOCATED_IN", "OCCURRED_AT", "DEVELOPED_BY"]

    def extract(self, project_path: str, config: dict) -> dict:
        corpus_path = Path(project_path) / "corpus"
        documents = self._load_documents(corpus_path)

        all_triples = []
        doc_entities = {}

        for doc_name, doc_text in documents.items():
            entities = self._extract_entities(doc_text, config)
            relations = self._extract_relations(doc_text, entities, config)
            triples = self._build_triples(entities, relations)

            doc_entities[doc_name] = entities
            all_triples.extend(triples)
            print(f"    文档 [{doc_name}]: 抽取 {len(entities)} 个实体, {len(triples)} 个三元组")

        # 去重
        unique_triples = self._deduplicate(all_triples)

        return {
            "total_documents": len(documents),
            "total_entities": sum(len(e) for e in doc_entities.values()),
            "total_triples": len(unique_triples),
            "triples": unique_triples,
            "entities_by_doc": {k: v for k, v in doc_entities.items()}
        }

    def _load_documents(self, corpus_path: Path) -> dict:
        documents = {}
        if not corpus_path.exists():
            print("    警告: corpus目录不存在，使用示例文档")
            documents["sample.txt"] = (
                "Claude是由Anthropic公司开发的大语言模型。Claude使用Transformer架构。"
                "Anthropic总部位于旧金山。DeepSeek是一个基于Transformer的开源模型。"
                "LangChain框架用于构建LLM应用。"
            )
            return documents

        for f in sorted(corpus_path.glob("**/*")):
            if f.is_file() and f.suffix in (".txt", ".md", ".json"):
                try:
                    text = f.read_text(encoding="utf-8")
                    if f.suffix == ".json":
                        data = json.loads(text)
                        text = json.dumps(data, ensure_ascii=False)
                    documents[f.name] = text
                except Exception as e:
                    print(f"    读取 {f.name} 失败: {e}")

        return documents

    def _extract_entities(self, text: str, config: dict) -> list[dict]:
        """从文本中抽取实体（模拟LLM调用）"""
        # 实际项目中调用 Claude/DeepSeek API
        entities = []
        seen = set()

        # 基于规则的简易抽取（演示用）
        import re
        # 大写开头的连续词组作为潜在实体
        for match in re.finditer(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b', text):
            name = match.group(1)
            if name not in seen and len(name) > 1:
                entity_type = self._classify_entity(name)
                entities.append({
                    "id": f"E{len(entities)+1:04d}",
                    "name": name,
                    "type": entity_type,
                    "source": text[max(0, match.start()-50):match.end()+50]
                })
                seen.add(name)

        # 中文实体抽取
        zh_entities = self._extract_chinese_entities(text)
        for ent in zh_entities:
            if ent["name"] not in seen:
                entities.append({
                    "id": f"E{len(entities)+1:04d}",
                    "name": ent["name"],
                    "type": ent["type"],
                    "source": ent.get("context", "")
                })
                seen.add(ent["name"])

        return entities

    def _extract_chinese_entities(self, text: str) -> list[dict]:
        """简易中文实体识别"""
        entities = []
        # 已知实体词典（演示用，实际应调用LLM）
        known_entities = {
            "Claude": "PRODUCT", "Anthropic": "ORG", "DeepSeek": "PRODUCT",
            "Transformer": "TECH", "旧金山": "LOCATION", "LangChain": "TECH",
            "LLM": "CONCEPT", "GPT": "PRODUCT", "BERT": "TECH",
        }
        for name, etype in known_entities.items():
            if name in text:
                entities.append({"name": name, "type": etype, "context": ""})
        return entities

    def _classify_entity(self, name: str) -> str:
        """简易实体类型分类"""
        tech_keywords = {"Python", "Java", "GPT", "BERT", "Transformer", "LLM",
                         "LangChain", "PyTorch", "TensorFlow", "Kubernetes", "Docker"}
        org_keywords = {"Inc", "Corp", "Ltd", "Company", "Lab", "Foundation"}
        person_keywords = {"Dr", "Prof", "Mr", "Ms"}

        if name in tech_keywords or any(k in name for k in tech_keywords):
            return "TECH"
        if any(k in name for k in org_keywords):
            return "ORG"
        if any(name.startswith(k) for k in person_keywords):
            return "PERSON"
        return "CONCEPT"

    def _extract_relations(self, text: str, entities: list[dict], config: dict) -> list[dict]:
        """从文本中抽取实体间关系"""
        relations = []
        entity_names = [e["name"] for e in entities]

        # 基于模式的简易关系抽取（演示用）
        import re
        patterns = [
            (r'(\w+)\s*(?:由|开发自?|创建自?|研发自?)\s*(\w+)', "CREATED_BY"),
            (r'(\w+)\s*(?:使用|利用|基于|采用)\s*(\w+)', "USES"),
            (r'(\w+)\s*(?:是|为).*?(?:一部分|组件|模块)\s*(?:of|属于)\s*(\w+)', "PART_OF"),
            (r'(\w+)\s*(?:依赖|基于|建立在).*?\s*(\w+)', "DEPENDS_ON"),
            (r'(\w+)\s*(?:位于|坐落在|总部在)\s*(\w+)', "LOCATED_IN"),
            (r'(\w+)\s*(?:开发了?|创造了?|发布了?)\s*(\w+)', "DEVELOPED_BY"),
            (r'(\w+)\s*(?:属于|服务于|就职于)\s*(\w+)', "WORKS_FOR"),
        ]

        for pattern, rel_type in patterns:
            for match in re.finditer(pattern, text):
                subj, obj = match.group(1), match.group(2)
                if subj in entity_names and obj in entity_names:
                    relations.append({
                        "subject": subj,
                        "predicate": rel_type,
                        "object": obj
                    })

        # 补充：对未匹配的实体对添加RELATED_TO
        for i, e1 in enumerate(entity_names[:10]):
            for e2 in entity_names[i+1:i+3]:
                if not any(r["subject"] == e1 and r["object"] == e2 for r in relations):
                    if e1 != e2:
                        relations.append({
                            "subject": e1,
                            "predicate": "RELATED_TO",
                            "object": e2
                        })

        return relations

    def _build_triples(self, entities: list[dict], relations: list[dict]) -> list[dict]:
        """构建三元组"""
        entity_map = {e["name"]: e for e in entities}
        triples = []

        for rel in relations:
            subj = entity_map.get(rel["subject"])
            obj = entity_map.get(rel["object"])
            if subj and obj:
                triples.append({
                    "subject": rel["subject"],
                    "subject_type": subj["type"],
                    "predicate": rel["predicate"],
                    "object": rel["object"],
                    "object_type": obj["type"],
                    "confidence": 0.85
                })

        return triples

    def _deduplicate(self, triples: list[dict]) -> list[dict]:
        """三元组去重"""
        seen = set()
        unique = []
        for t in triples:
            key = (t["subject"], t["predicate"], t["object"])
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

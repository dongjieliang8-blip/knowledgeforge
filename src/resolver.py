"""Resolver Agent: 实体消歧与对齐，合并同义实体"""

import re
from collections import defaultdict


class ResolverAgent:
    """实体消歧：合并同义实体、消解歧义"""

    def __init__(self):
        # 同义词簇（演示用，实际应由LLM生成）
        self.synonym_clusters = {
            "Claude": ["Claude", "claude", "Claude AI", "Claude模型"],
            "Anthropic": ["Anthropic", "Anthropic公司", "Anthropic Inc"],
            "Transformer": ["Transformer", "Transformer架构", "Transformer模型"],
            "DeepSeek": ["DeepSeek", "DeepSeek模型", "DeepSeek AI"],
        }

    def resolve(self, extraction_result: dict, config: dict) -> dict:
        triples = extraction_result["triples"]

        # 构建实体映射
        entity_map = self._build_entity_map(triples)
        print(f"    输入实体数: {len(entity_map)}")

        # 同义实体合并
        merged_map = self._merge_synonyms(entity_map)
        print(f"    合并后实体数: {len(merged_map)}")

        # 重新映射三元组
        resolved_triples = self._remap_triples(triples, entity_map, merged_map)

        # 消解歧义（基于上下文）
        disambiguated = self._disambiguate(resolved_triples)
        print(f"    消歧完成: {len(disambiguated)} 个三元组")

        # 统计
        merge_count = len(entity_map) - len(merged_map)
        clusters = self._find_clusters(entity_map, merged_map)

        return {
            "original_entity_count": len(entity_map),
            "resolved_entity_count": len(merged_map),
            "merged_count": merge_count,
            "clusters": clusters,
            "triples": disambiguated
        }

    def _build_entity_map(self, triples: list[dict]) -> dict:
        """从三元组构建实体名称到类型的映射"""
        entity_map = {}
        for t in triples:
            entity_map[t["subject"]] = t["subject_type"]
            entity_map[t["object"]] = t["object_type"]
        return entity_map

    def _merge_synonyms(self, entity_map: dict) -> dict:
        """基于同义词簇合并实体"""
        # 构建 canonical name 映射
        canonical_map = {}
        for canonical, variants in self.synonym_clusters.items():
            for v in variants:
                canonical_map[v] = canonical

        merged = {}
        for name, etype in entity_map.items():
            canonical = canonical_map.get(name, name)
            if canonical in merged:
                # 保留更具体的类型
                if etype != "CONCEPT" and merged[canonical] == "CONCEPT":
                    merged[canonical] = etype
            else:
                merged[canonical] = etype

        return merged

    def _remap_triples(self, triples: list[dict], entity_map: dict, merged_map: dict) -> list[dict]:
        """将三元组中的实体名映射为合并后的 canonical name"""
        # 构建反向映射
        reverse_map = {}
        for canonical, variants in self.synonym_clusters.items():
            for v in variants:
                reverse_map[v] = canonical

        resolved = []
        for t in triples:
            subj = reverse_map.get(t["subject"], t["subject"])
            obj = reverse_map.get(t["object"], t["object"])
            subj_type = merged_map.get(subj, t["subject_type"])
            obj_type = merged_map.get(obj, t["object_type"])

            resolved.append({
                "subject": subj,
                "subject_type": subj_type,
                "predicate": t["predicate"],
                "object": obj,
                "object_type": obj_type,
                "confidence": t["confidence"]
            })

        return resolved

    def _disambiguate(self, triples: list[dict]) -> list[dict]:
        """基于上下文消解歧义"""
        # 统计实体出现频次
        entity_freq = defaultdict(int)
        for t in triples:
            entity_freq[t["subject"]] += 1
            entity_freq[t["object"]] += 1

        # 高频实体提高置信度，低频实体降低置信度
        disambiguated = []
        for t in triples:
            freq = entity_freq[t["subject"]] + entity_freq[t["object"]]
            if freq > 3:
                conf = min(0.95, t["confidence"] + 0.1)
            elif freq == 1:
                conf = max(0.5, t["confidence"] - 0.15)
            else:
                conf = t["confidence"]

            disambiguated.append({**t, "confidence": round(conf, 4)})

        return disambiguated

    def _find_clusters(self, entity_map: dict, merged_map: dict) -> list[dict]:
        """找出实体合并簇"""
        clusters = []
        for canonical in merged_map:
            variants = [canonical]
            for canon, vars_list in self.synonym_clusters.items():
                if canon == canonical:
                    variants = vars_list
                    break
            if len(variants) > 1:
                clusters.append({
                    "canonical": canonical,
                    "variants": variants,
                    "type": merged_map[canonical]
                })
        return clusters

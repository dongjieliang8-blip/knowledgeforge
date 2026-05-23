"""Validator Agent: 多维度验证知识图谱质量"""


class ValidatorAgent:
    """图谱质量验证：完整性/一致性/覆盖度"""

    def validate(self, extraction_result: dict, resolution_result: dict,
                 graph_result: dict, config: dict) -> dict:
        triples = extraction_result["triples"]
        resolved_triples = resolution_result["triples"]

        checks = {}

        # 1. 完整性检查
        checks["completeness"] = self._check_completeness(triples, resolved_triples)

        # 2. 一致性检查
        checks["consistency"] = self._check_consistency(resolved_triples)

        # 3. 覆盖度检查
        checks["coverage"] = self._check_coverage(resolution_result)

        # 4. 置信度检查
        checks["confidence"] = self._check_confidence(resolved_triples)

        # 5. 孤立节点检查
        checks["orphan_check"] = self._check_orphans(resolved_triples)

        # 综合评分
        scores = [v["score"] for v in checks.values() if "score" in v]
        overall_score = sum(scores) / max(len(scores), 1)

        # 生成建议
        suggestions = self._generate_suggestions(checks)

        # 判断是否通过
        passed = overall_score >= 0.6

        print(f"    完整性: {checks['completeness']['score']:.2%}")
        print(f"    一致性: {checks['consistency']['score']:.2%}")
        print(f"    覆盖度: {checks['coverage']['score']:.2%}")
        print(f"    置信度: {checks['confidence']['score']:.2%}")
        print(f"    综合评分: {overall_score:.2%}")
        print(f"    验证结果: {'通过' if passed else '未通过'}")

        return {
            "passed": passed,
            "overall_score": round(overall_score, 4),
            "checks": checks,
            "suggestions": suggestions
        }

    def _check_completeness(self, original: list, resolved: list) -> dict:
        """完整性：三元组是否完整保留"""
        original_count = len(original)
        resolved_count = len(resolved)
        retention_rate = resolved_count / max(original_count, 1)
        return {
            "score": min(retention_rate, 1.0),
            "detail": f"原始三元组: {original_count}, 保留: {resolved_count}",
            "retention_rate": round(retention_rate, 4)
        }

    def _check_consistency(self, triples: list) -> dict:
        """一致性：三元组是否存在矛盾"""
        # 检查同一实体对是否有多条不同关系
        pair_relations = {}
        for t in triples:
            key = (t["subject"], t["object"])
            if key not in pair_relations:
                pair_relations[key] = set()
            pair_relations[key].add(t["predicate"])

        conflicts = {k: v for k, v in pair_relations.items() if len(v) > 2}
        conflict_count = len(conflicts)

        # 简单评分：无冲突为1.0，每冲突扣0.1
        score = max(0.0, 1.0 - conflict_count * 0.1)
        return {
            "score": score,
            "detail": f"发现 {conflict_count} 个潜在矛盾关系组",
            "conflict_pairs": len(conflicts)
        }

    def _check_coverage(self, resolution_result: dict) -> dict:
        """覆盖度：实体类型的多样性"""
        clusters = resolution_result.get("clusters", [])
        entity_count = resolution_result.get("resolved_entity_count", 0)

        # 覆盖度基于实体数量和合并比例
        if entity_count == 0:
            return {"score": 0.0, "detail": "无实体"}

        merge_ratio = resolution_result.get("merged_count", 0) / max(entity_count, 1)
        # 有合并说明存在同义实体，覆盖度好
        coverage = min(1.0, 0.5 + merge_ratio * 0.5 + min(entity_count / 20, 0.3))

        return {
            "score": round(coverage, 4),
            "detail": f"实体数: {entity_count}, 合并簇: {len(clusters)}"
        }

    def _check_confidence(self, triples: list) -> dict:
        """置信度：三元组平均置信度"""
        if not triples:
            return {"score": 0.0, "detail": "无三元组"}

        confidences = [t["confidence"] for t in triples]
        avg_conf = sum(confidences) / len(confidences)
        low_conf_count = sum(1 for c in confidences if c < 0.6)

        return {
            "score": round(avg_conf, 4),
            "detail": f"平均置信度: {avg_conf:.4f}, 低置信度三元组: {low_conf_count}",
            "avg_confidence": round(avg_conf, 4),
            "low_confidence_count": low_conf_count
        }

    def _check_orphans(self, triples: list) -> dict:
        """孤立节点：仅出现一次的实体"""
        entity_count = {}
        for t in triples:
            entity_count[t["subject"]] = entity_count.get(t["subject"], 0) + 1
            entity_count[t["object"]] = entity_count.get(t["object"], 0) + 1

        orphans = [name for name, count in entity_count.items() if count == 1]
        orphan_ratio = len(orphans) / max(len(entity_count), 1)
        score = max(0.0, 1.0 - orphan_ratio)

        return {
            "score": round(score, 4),
            "detail": f"孤立节点: {len(orphans)}/{len(entity_count)}",
            "orphan_count": len(orphans),
            "orphan_names": orphans[:10]
        }

    def _generate_suggestions(self, checks: dict) -> list[str]:
        """生成改进建议"""
        suggestions = []

        if checks.get("completeness", {}).get("score", 1.0) < 0.8:
            suggestions.append("三元组保留率较低，建议检查消歧规则是否过于激进")

        if checks.get("consistency", {}).get("score", 1.0) < 0.8:
            suggestions.append("存在矛盾关系，建议人工审核冲突三元组")

        if checks.get("coverage", {}).get("score", 1.0) < 0.6:
            suggestions.append("实体覆盖不足，建议扩充语料来源或增加实体类型")

        if checks.get("confidence", {}).get("avg_confidence", 1.0) < 0.7:
            suggestions.append("平均置信度偏低，建议优化抽取Prompt或增加上下文")

        if checks.get("orphan_check", {}).get("score", 1.0) < 0.7:
            suggestions.append("孤立节点较多，建议补充实体间的关联关系")

        if not suggestions:
            suggestions.append("图谱质量良好，无需特别调整")

        return suggestions

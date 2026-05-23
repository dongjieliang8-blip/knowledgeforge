"""
KnowledgeForge — 多Agent协作知识图谱构建流水线

Extractor → Resolver → GraphBuilder → Validator
"""

import json
import sys
from pathlib import Path

from .extractor import ExtractorAgent
from .resolver import ResolverAgent
from .graph_builder import GraphBuilderAgent
from .validator import ValidatorAgent


class KnowledgeForgePipeline:
    def __init__(self):
        self.extractor = ExtractorAgent()
        self.resolver = ResolverAgent()
        self.graph_builder = GraphBuilderAgent()
        self.validator = ValidatorAgent()

    def run(self, project_path: str):
        print("=" * 60)
        print("KnowledgeForge — 知识图谱构建流水线")
        print("=" * 60)

        # 读取配置
        config = self._load_config(project_path)

        output_dir = str(Path(project_path) / "output")

        # Step 1: 实体抽取
        print("\n[1/4] Extractor Agent: 从文档中抽取实体与关系...")
        extraction_result = self.extractor.extract(project_path, config)
        print(f"  文档数: {extraction_result['total_documents']}")
        print(f"  实体数: {extraction_result['total_entities']}")
        print(f"  三元组: {extraction_result['total_triples']}")

        # Step 2: 实体消歧
        print("\n[2/4] Resolver Agent: 实体消歧与对齐...")
        resolution_result = self.resolver.resolve(extraction_result, config)
        print(f"  合并前: {resolution_result['original_entity_count']} 个实体")
        print(f"  合并后: {resolution_result['resolved_entity_count']} 个实体")
        print(f"  合并数: {resolution_result['merged_count']}")

        # Step 3: 图谱构建
        print("\n[3/4] GraphBuilder Agent: 构建知识图谱...")
        graph_result = self.graph_builder.build(resolution_result, config, output_dir)
        print(f"  节点数: {graph_result['node_count']}")
        print(f"  边数: {graph_result['edge_count']}")

        # Step 4: 质量验证
        print("\n[4/4] Validator Agent: 验证图谱质量...")
        validation_result = self.validator.validate(
            extraction_result, resolution_result, graph_result, config
        )
        print(f"  综合评分: {validation_result['overall_score']:.2%}")
        print(f"  验证结果: {'通过' if validation_result['passed'] else '未通过'}")

        # 输出完整报告
        report = {
            "config": config,
            "extraction": {
                "total_documents": extraction_result["total_documents"],
                "total_entities": extraction_result["total_entities"],
                "total_triples": extraction_result["total_triples"]
            },
            "resolution": {
                "original_entity_count": resolution_result["original_entity_count"],
                "resolved_entity_count": resolution_result["resolved_entity_count"],
                "merged_count": resolution_result["merged_count"],
                "clusters": resolution_result["clusters"]
            },
            "graph": {
                "node_count": graph_result["node_count"],
                "edge_count": graph_result["edge_count"],
                "stats": graph_result["stats"]
            },
            "validation": {
                "passed": validation_result["passed"],
                "overall_score": validation_result["overall_score"],
                "checks": validation_result["checks"],
                "suggestions": validation_result["suggestions"]
            }
        }

        report_path = Path(output_dir) / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print(f"流水线完成! 报告已保存至: {report_path}")
        print("=" * 60)

        return report

    def _load_config(self, project_path: str) -> dict:
        config_path = Path(project_path) / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "llm_provider": "claude",
            "model": "claude-sonnet-4-20250514",
            "entity_types": ["PERSON", "ORG", "TECH", "CONCEPT", "PRODUCT"],
            "relation_types": ["WORKS_FOR", "USES", "CREATED_BY", "DEPENDS_ON", "PART_OF"],
            "min_confidence": 0.6,
            "enable_disambiguation": True
        }


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print("用法: python -m src.main run <project_path>")
        sys.exit(1)

    project_path = sys.argv[2]
    pipeline = KnowledgeForgePipeline()
    pipeline.run(project_path)


if __name__ == "__main__":
    main()

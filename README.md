# KnowledgeForge — 多Agent协作知识图谱构建流水线

基于 Claude Code / DeepSeek API 的多智能体知识图谱构建流水线，实现文档实体抽取→实体消歧→图谱构建→质量验证的全自动化闭环。

## 架构

```
Extractor → Resolver → GraphBuilder → Validator
```

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python -m src.main run ./demo/sample_corpus
```

## Agent 说明

- **Extractor**: 从非结构化文档中抽取实体和关系三元组
- **Resolver**: 实体消歧与对齐，合并同义实体
- **GraphBuilder**: 将三元组组装为知识图谱并持久化
- **Validator**: 多维度验证图谱质量（完整性/一致性/覆盖度）

## 技术栈

- Python
- Claude Code / DeepSeek API
- NetworkX（图存储与查询）
- spaCy（文本处理）

## License

MIT

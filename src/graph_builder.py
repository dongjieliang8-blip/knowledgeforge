"""GraphBuilder Agent: 将三元组组装为知识图谱并持久化"""

import json
from pathlib import Path

try:
    import networkx as nx
except ImportError:
    nx = None


class GraphBuilderAgent:
    """将消歧后的三元组构建为知识图谱"""

    def __init__(self):
        self.graph = None

    def build(self, resolution_result: dict, config: dict, output_dir: str = None) -> dict:
        triples = resolution_result["triples"]

        # 初始化图
        if nx is not None:
            self.graph = nx.DiGraph()
            self._build_networkx_graph(triples)
            graph_type = "networkx"
            node_count = self.graph.number_of_nodes()
            edge_count = self.graph.number_of_edges()
        else:
            # 无 networkx 时使用 dict 存储
            self.graph = {"nodes": {}, "edges": []}
            self._build_dict_graph(triples)
            graph_type = "dict"
            node_count = len(self.graph["nodes"])
            edge_count = len(self.graph["edges"])

        print(f"    图类型: {graph_type}")
        print(f"    节点数: {node_count}")
        print(f"    边数: {edge_count}")

        # 计算图统计
        stats = self._compute_stats()

        # 持久化
        if output_dir:
            self._save(output_dir, graph_type)

        return {
            "graph_type": graph_type,
            "node_count": node_count,
            "edge_count": edge_count,
            "stats": stats,
            "output_dir": output_dir
        }

    def _build_networkx_graph(self, triples: list[dict]):
        """使用 NetworkX 构建有向图"""
        for t in triples:
            # 添加节点
            if t["subject"] not in self.graph:
                self.graph.add_node(t["subject"], type=t["subject_type"], label=t["subject"])
            if t["object"] not in self.graph:
                self.graph.add_node(t["object"], type=t["object_type"], label=t["object"])

            # 添加边（避免重复）
            if not self.graph.has_edge(t["subject"], t["object"]):
                self.graph.add_edge(
                    t["subject"], t["object"],
                    predicate=t["predicate"],
                    confidence=t["confidence"]
                )

    def _build_dict_graph(self, triples: list[dict]):
        """使用 dict 构建图（fallback）"""
        for t in triples:
            if t["subject"] not in self.graph["nodes"]:
                self.graph["nodes"][t["subject"]] = {"type": t["subject_type"]}
            if t["object"] not in self.graph["nodes"]:
                self.graph["nodes"][t["object"]] = {"type": t["object_type"]}

            edge_key = (t["subject"], t["object"])
            if not any(e["subject"] == t["subject"] and e["object"] == t["object"]
                       for e in self.graph["edges"]):
                self.graph["edges"].append({
                    "subject": t["subject"],
                    "object": t["object"],
                    "predicate": t["predicate"],
                    "confidence": t["confidence"]
                })

    def _compute_stats(self) -> dict:
        """计算图统计信息"""
        if nx is not None and isinstance(self.graph, nx.DiGraph):
            in_degrees = dict(self.graph.in_degree())
            out_degrees = dict(self.graph.out_degree())
            total_degrees = {n: in_degrees.get(n, 0) + out_degrees.get(n, 0)
                             for n in self.graph.nodes()}

            # 中心度
            try:
                betweenness = nx.betweenness_centrality(self.graph)
                top_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
            except Exception:
                top_nodes = []

            # 连通分量
            try:
                undirected = self.graph.to_undirected()
                num_components = nx.number_connected_components(undirected)
            except Exception:
                num_components = 0

            # 节点类型分布
            type_dist = {}
            for _, data in self.graph.nodes(data=True):
                t = data.get("type", "UNKNOWN")
                type_dist[t] = type_dist.get(t, 0) + 1

            # 边类型分布
            edge_type_dist = {}
            for _, _, data in self.graph.edges(data=True):
                p = data.get("predicate", "UNKNOWN")
                edge_type_dist[p] = edge_type_dist.get(p, 0) + 1

            return {
                "avg_degree": round(sum(total_degrees.values()) / max(len(total_degrees), 1), 2),
                "max_degree_node": max(total_degrees, key=total_degrees.get) if total_degrees else None,
                "top_betweenness": [{"node": n, "score": round(s, 4)} for n, s in top_nodes],
                "num_connected_components": num_components,
                "node_type_distribution": type_dist,
                "edge_type_distribution": edge_type_dist,
                "density": round(nx.density(self.graph), 4)
            }

        # dict fallback
        return {
            "node_count": len(self.graph.get("nodes", {})),
            "edge_count": len(self.graph.get("edges", []))
        }

    def _save(self, output_dir: str, graph_type: str):
        """持久化图谱"""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if graph_type == "networkx" and nx is not None:
            # 保存为 JSON
            graph_data = nx.node_link_data(self.graph)
            with open(out / "graph.json", "w", encoding="utf-8") as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)

            # 保存节点列表
            nodes = [{"id": n, **d} for n, d in self.graph.nodes(data=True)]
            with open(out / "nodes.json", "w", encoding="utf-8") as f:
                json.dump(nodes, f, ensure_ascii=False, indent=2)

            # 保存边列表
            edges = [{"source": u, "target": v, **d} for u, v, d in self.graph.edges(data=True)]
            with open(out / "edges.json", "w", encoding="utf-8") as f:
                json.dump(edges, f, ensure_ascii=False, indent=2)

            # 保存 GML 格式（可导入 Gephi 等工具）
            try:
                nx.write_gml(self.graph, str(out / "graph.gml"))
            except Exception:
                pass

            print(f"    图谱已保存至: {output_dir}/")
            print(f"      graph.json / nodes.json / edges.json / graph.gml")
        else:
            with open(out / "graph.json", "w", encoding="utf-8") as f:
                json.dump(self.graph, f, ensure_ascii=False, indent=2)
            print(f"    图谱已保存至: {output_dir}/graph.json")

    def query(self, entity_name: str) -> dict:
        """查询实体的邻居"""
        if nx is not None and isinstance(self.graph, nx.DiGraph):
            if entity_name not in self.graph:
                return {"error": f"实体 '{entity_name}' 不存在"}
            neighbors = []
            for _, target, data in self.graph.out_edges(entity_name, data=True):
                neighbors.append({"relation": data["predicate"], "target": target})
            for source, _, data in self.graph.in_edges(entity_name, data=True):
                neighbors.append({"relation": data["predicate"], "source": source})
            return {"entity": entity_name, "neighbors": neighbors}
        return {"error": "不支持的图类型"}

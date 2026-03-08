import json

class GraphExporter:
    def __init__(self, graph):
        self.graph = graph

    def export_json(self, output_file):
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "type": data.get("type", "unknown"),
                **data   # include all attributes
            })
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "relation": data.get("relation", "unknown")
            })
        with open(output_file, 'w') as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2)
        print(f"Graph exported to {output_file}")

    def export_json_string(self):
        """Export graph to JSON string (for Lambda)"""
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "type": data.get("type", "unknown"),
                **{k: v for k, v in data.items() if k != 'type'}
            })
        
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "relation": data.get("relation", "unknown"),
                "count": data.get("count", 1)
            })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
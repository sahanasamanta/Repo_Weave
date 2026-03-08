import os
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


class GraphVisualizer:
    def __init__(self, graph, issues=None):
        self.graph = graph
        self.issues = issues or []

    def _get_directory_color(self, file_path, top_dirs):
        """Assign a color to a file based on its top-level directory."""
        parts = file_path.split(os.sep)
        if parts:
            top = parts[0]
        else:
            top = "root"
        colors = ["#FFB6C1", "#FFDAB9", "#E6E6FA", "#C0F0E8", "#F0E68C", "#D8BFD8", "#B0E0E6"]
        idx = hash(top) % len(colors)
        return colors[idx]

    def _identify_entry_points(self):
        """Identify potential entry points."""
        entry_points = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                entry_points.append(node)
        return entry_points

    def _hierarchical_layout(self):
        """Create a hierarchical layout using NetworkX's multipartite layout."""
        try:
            # Try to use multipartite layout for hierarchy
            G = self.graph.copy()

            # Assign layers based on longest path from sources
            sources = [n for n in G.nodes() if G.in_degree(n) == 0]

            if not sources:
                return nx.spring_layout(G, k=2, iterations=50)

            # Assign layers using BFS
            layers = {}
            for source in sources:
                for node, dist in nx.single_source_shortest_path_length(G, source).items():
                    if node not in layers or dist > layers[node]:
                        layers[node] = dist

            # If some nodes weren't reached, give them a default layer
            max_layer = max(layers.values()) if layers else 0
            for node in G.nodes():
                if node not in layers:
                    layers[node] = max_layer + 1

            # Use multipartite layout
            nx.set_node_attributes(G, layers, 'layer')
            pos = nx.multipartite_layout(G, subset_key='layer', align='vertical')

            # Flip y-axis so sources are at top
            for node in pos:
                pos[node][1] = -pos[node][1]

            return pos

        except Exception as e:
            print(f"Hierarchical layout failed: {e}, falling back to spring layout")
            return nx.spring_layout(self.graph, k=2, seed=42, iterations=100)

    def draw_graph(self, output_file="dependency_graph.png", show_calls=True):
        """Draw the graph with hierarchical layout."""
        print("\n===== GENERATING STATIC VISUALIZATION =====")

        plt.figure(figsize=(24, 20))

        # Get hierarchical layout
        pos = self._hierarchical_layout()

        # Prepare node colors and labels
        node_colors = []
        node_labels = {}

        for node, data in self.graph.nodes(data=True):
            ntype = data.get("type", "unknown")

            # Label
            if ntype in ("python_file", "data_file"):
                node_labels[node] = os.path.basename(node)
            elif ntype == "function":
                func_name = data.get("name", node)
                if node.startswith("UNDEF::"):
                    func_name = func_name + " (?)"
                node_labels[node] = func_name[:20]
            else:
                node_labels[node] = node[:20]

            # Color
            if ntype == "python_file":
                node_colors.append(self._get_directory_color(node, set()))
            elif ntype == "data_file":
                node_colors.append("#90EE90")
            elif ntype == "function":
                if node.startswith("UNDEF::") or not data.get("defined", True):
                    node_colors.append("#FFA07A")
                else:
                    node_colors.append("#87CEEB")
            else:
                node_colors.append("#D3D3D3")

        # Draw nodes
        nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, node_size=2000)

        # Draw edges
        edge_colors = []
        edge_widths = []
        edges_to_draw = []

        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relation", "")
            count = data.get("count", 1)

            # Skip intra-file calls if requested
            if rel == "CALLS" and not show_calls:
                if not v.startswith("UNDEF::"):
                    func_data = self.graph.nodes[v]
                    if func_data.get("type") == "function":
                        def_file = func_data.get("file")
                        if def_file and def_file == u:
                            continue

            edges_to_draw.append((u, v))

            if rel == "IMPORTS":
                edge_colors.append("blue")
            elif rel == "CALLS":
                edge_colors.append("orange")
            elif rel in ("READ", "WRITE", "APPEND"):
                edge_colors.append("green")
            else:
                edge_colors.append("gray")

            edge_widths.append(min(1 + count, 5))

        if edges_to_draw:
            nx.draw_networkx_edges(
                self.graph, pos,
                edgelist=edges_to_draw,
                edge_color=edge_colors,
                width=edge_widths,
                arrows=True,
                arrowstyle='->',
                arrowsize=15
            )

        # Draw labels
        nx.draw_networkx_labels(self.graph, pos, node_labels, font_size=8)

        plt.title("Repository Dependency Graph (Hierarchical Layout)")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=200, bbox_inches='tight')
        plt.close()

        print(f"✅ Hierarchical graph saved to {output_file}")
        print(f"   Nodes: {len(self.graph.nodes())}, Edges: {len(edges_to_draw)}")
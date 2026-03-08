import os
import networkx as nx
from pyvis.network import Network


class GraphInteractiveExporter:
    def __init__(self, graph, issues=None):
        self.graph = graph
        self.issues = issues or []

    def _identify_entry_points(self):
        """Identify potential entry points (nodes with no incoming edges)."""
        entry_points = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0:
                entry_points.append(node)
        return entry_points

    def _get_node_color(self, node, data):
        """Get color for node based on its type."""
        ntype = data.get("type", "unknown")

        if ntype == "python_file":
            parts = node.split(os.sep)
            top_dir = parts[0] if parts else "root"
            colors = ["#FFB6C1", "#FFDAB9", "#E6E6FA", "#C0F0E8", "#F0E68C", "#D8BFD8", "#B0E0E6"]
            return colors[hash(top_dir) % len(colors)]
        elif ntype == "data_file":
            return "#90EE90"
        elif ntype == "function":
            if node.startswith("UNDEF::") or not data.get("defined", True):
                return "#FFA07A"
            else:
                return "#87CEEB"
        else:
            return "#D3D3D3"

    def _get_node_shape(self, node, data):
        """Get shape for node based on its type."""
        ntype = data.get("type", "unknown")

        if ntype == "python_file":
            return "hexagon"
        elif ntype == "data_file":
            return "dot"
        elif ntype == "function":
            return "box"
        else:
            return "dot"

    def export_html(self, output_file="dependency_graph.html", show_calls=True):
        """Create an interactive HTML visualization with vertical hierarchy."""
        print("\n===== GENERATING INTERACTIVE VISUALIZATION =====")

        # Create network
        net = Network(height="800px", width="100%", directed=True)

        # Add nodes
        for node, data in self.graph.nodes(data=True):
            ntype = data.get("type", "unknown")

            # Label
            if ntype in ("python_file", "data_file"):
                label = os.path.basename(node)
            elif ntype == "function":
                label = data.get("name", node)
                if node.startswith("UNDEF::"):
                    label = f"{label} ?"
                if len(label) > 20:
                    label = label[:17] + "..."
            else:
                label = node[:20]

            # Title (hover)
            title = f"Type: {ntype}\n"
            if ntype == "python_file":
                title += f"Path: {node}"
            elif ntype == "data_file":
                title += f"Path: {node}"
            elif ntype == "function":
                title += f"Name: {data.get('name', node)}\n"
                if node.startswith("UNDEF::"):
                    title += "⚠️ UNDEFINED FUNCTION"
                else:
                    title += f"Defined in: {data.get('file', 'Unknown')}"

            # Color and shape
            color = self._get_node_color(node, data)
            shape = self._get_node_shape(node, data)

            net.add_node(node, label=label, title=title, color=color, shape=shape, size=20)

        # Add edges
        edge_count = 0
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

            # Edge color
            if rel == "IMPORTS":
                color = "blue"
            elif rel == "CALLS":
                color = "orange"
            elif rel in ("READ", "WRITE", "APPEND"):
                color = "green"
            else:
                color = "gray"

            net.add_edge(u, v, title=f"{rel} (x{count})", color=color, width=min(1 + count, 5), arrows="to")
            edge_count += 1

        print(f"Added {len(self.graph.nodes())} nodes and {edge_count} edges")

        # SIMPLE HIERARCHICAL OPTIONS - No JSON errors
        net.set_options("""
        var options = {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed"
            }
          },
          "physics": {
            "enabled": false
          },
          "interaction": {
            "hover": true,
            "navigationButtons": true
          }
        }
        """)

        # Generate HTML
        html = net.generate_html()

        # Add simple panels
        entry_points = self._identify_entry_points()

        panels = """
        <style>
            .panel { position: absolute; background: white; padding: 10px; border-radius: 5px; 
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2); font-size: 12px; max-width: 250px;
                    border: 1px solid #ddd; z-index: 1000; }
            .panel h4 { margin: 0 0 5px 0; }
            .panel ul { margin: 0; padding-left: 20px; }
            .legend { display: grid; grid-template-columns: repeat(2,1fr); gap: 5px; }
            .legend-item { display: flex; align-items: center; gap: 5px; }
            .color-box { width: 15px; height: 15px; border-radius: 3px; }
        </style>
        """

        # Controls
        panels += '<div class="panel" style="bottom:20px;right:20px;"><h4>Controls</h4>'
        panels += 'Drag nodes • Scroll zoom • Hover for details</div>'

        # Entry points
        if entry_points:
            panels += '<div class="panel" style="top:20px;left:20px;"><h4>📌 Entry Points</h4><ul>'
            for ep in entry_points[:8]:
                panels += f'<li>{os.path.basename(ep)}</li>'
            if len(entry_points) > 8:
                panels += f'<li>... +{len(entry_points) - 8} more</li>'
            panels += '</ul></div>'

        # Issues
        if self.issues:
            panels += '<div class="panel" style="top:20px;right:20px;background:#fff3f3;"><h4>⚠️ Issues</h4><ul>'
            for issue in self.issues[:8]:
                short = issue if len(issue) < 40 else issue[:37] + "..."
                panels += f'<li title="{issue}">{short}</li>'
            if len(self.issues) > 8:
                panels += f'<li>... +{len(self.issues) - 8} more</li>'
            panels += '</ul></div>'

        # Legend
        panels += '<div class="panel" style="bottom:20px;left:20px;"><h4>Legend</h4><div class="legend">'
        panels += '<div class="legend-item"><div class="color-box" style="background:#FFB6C1;"></div> Python</div>'
        panels += '<div class="legend-item"><div class="color-box" style="background:#87CEEB;"></div> Function</div>'
        panels += '<div class="legend-item"><div class="color-box" style="background:#FFA07A;"></div> Undefined</div>'
        panels += '<div class="legend-item"><div class="color-box" style="background:#90EE90;"></div> Data</div>'
        panels += '<div style="grid-column:span2;"><span style="color:orange;">━━▶</span> CALLS</div>'
        panels += '<div style="grid-column:span2;"><span style="color:blue;">━━▶</span> IMPORTS</div>'
        panels += '<div style="grid-column:span2;"><span style="color:green;">━━▶</span> DATA</div>'
        panels += '</div></div>'

        # Insert panels
        html = html.replace('<body>', f'<body>{panels}')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Interactive graph saved to {output_file}")
        print(f"   - Vertical hierarchy (top-to-bottom)")
        print(f"   - {len(self.graph.nodes())} nodes, {edge_count} edges")

        return output_file
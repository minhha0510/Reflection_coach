import json
import os
import webbrowser

def generate_visualization():
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "reflection_graph.json")
    html_path = os.path.join(script_dir, "reflection_graph.html")

    # Load Graph Data
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    links = data.get("links", [])

    # Prepare Nodes for Vis.js
    vis_nodes = []
    for node in nodes:
        # Determine color/shape based on type
        node_type = node.get("type", "Unknown")
        color = "#97C2FC" # Default Blue
        if node_type == "Belief": color = "#FFD700" # Gold
        elif node_type == "Event": color = "#90EE90" # Light Green
        elif node_type == "Emotion": color = "#FFB6C1" # Light Pink
        elif node_type == "Person": color = "#FFA07A" # Light Salmon
        
        # Label is text (truncated)
        label = node.get("text", node.get("description", "Node"))
        if len(label) > 20: label = label[:20] + "..."
        
        # Tooltip is full text
        title = f"<b>{node_type}</b><br>{node.get('text', node.get('description', ''))}"

        vis_nodes.append({
            "id": node["id"],
            "label": label,
            "title": title,
            "color": color,
            "group": node_type
        })

    # Prepare Edges for Vis.js
    vis_edges = []
    for link in links:
        vis_edges.append({
            "from": link["source"],
            "to": link["target"],
            "label": link.get("relation", ""),
            "arrows": "to",
            "color": {"color": "#848484"}
        })

    # HTML Template with Vis.js
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reflection Graph Visualization</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #mynetwork {{
                width: 100%;
                height: 800px;
                border: 1px solid lightgray;
                background-color: #f8f9fa;
            }}
            .legend {{
                margin-bottom: 10px;
                font-family: sans-serif;
            }}
            .legend span {{
                display: inline-block;
                margin-right: 15px;
                padding: 5px 10px;
                border-radius: 4px;
                color: black;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <h2 style="font-family: sans-serif; text-align: center;">Reflection Graph Knowledge Base</h2>
        
        <div class="legend" style="text-align: center;">
            <span style="background-color: #FFD700;">Belief</span>
            <span style="background-color: #90EE90;">Event</span>
            <span style="background-color: #FFB6C1;">Emotion</span>
            <span style="background-color: #FFA07A;">Person</span>
            <span style="background-color: #97C2FC;">Other</span>
        </div>

        <div id="mynetwork"></div>

        <script type="text/javascript">
            // create an array with nodes
            var nodes = new vis.DataSet({json.dumps(vis_nodes)});

            // create an array with edges
            var edges = new vis.DataSet({json.dumps(vis_edges)});

            // create a network
            var container = document.getElementById('mynetwork');
            var data = {{
                nodes: nodes,
                edges: edges
            }};
            var options = {{
                nodes: {{
                    shape: 'dot',
                    size: 16,
                    font: {{
                        size: 14
                    }}
                }},
                edges: {{
                    width: 1,
                    smooth: {{
                        type: 'continuous'
                    }}
                }},
                physics: {{
                    stabilization: false,
                    barnesHut: {{
                        gravitationalConstant: -8000,
                        springConstant: 0.04,
                        springLength: 95
                    }}
                }},
                interaction: {{
                    navigationButtons: true,
                    keyboard: true
                }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Successfully generated: {html_path}")
    print(f"Nodes: {len(vis_nodes)}, Edges: {len(vis_edges)}")

if __name__ == "__main__":
    generate_visualization()

import os
import pickle
from typing import Dict, List, Optional
import logging

import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend for thread safety
# Suppress matplotlib debug logs
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
import matplotlib.pyplot as plt
import networkx as nx

from app import logger


class KnowledgeGraph:
    """
    A knowledge graph for storing and querying data.
    """
    def __init__(self, graph_name: str = "fpa_dev"):
        self.graph = nx.DiGraph()
        self.graph_name = graph_name
        self.graph_path = f"app/data/{graph_name}_schema.pkl"

    def add_node(self, node: str, type: str, name: str, data_type: Optional[str] = None):
        self.graph.add_node(node, type=type, name=name, data_type=data_type)

    def add_edge(self, u: str, v: str, relation: str):
        self.graph.add_edge(u, v, relation=relation)

    def get_graph(self) -> nx.DiGraph:
        return self.graph
    
    def get_schema(self) -> str:
        """Return complete schema - simple but comprehensive."""
        context = []
        
        # Add schema information at the top
        schemas = self.get_schemas()
        if schemas:
            context.append(f"Schema: {schemas[0]}")
            context.append("")  # Empty line for readability
        
        # Add table and column information
        for table in self.get_tables():
            columns = self.get_columns(table)
            col_names = [f"{col['name']}({col['data_type']})" for col in columns]
            context.append(f"{table}: {', '.join(col_names)}")
        
        return "\n".join(context)
    
    def get_schemas(self) -> List[str]:
        """Get list of all schema names."""
        schema_nodes = [node for node in self.graph.nodes() if node.startswith("schema:")]
        return [node.replace("schema:", "") for node in schema_nodes]

    def get_tables(self) -> List[str]:
        """Get list of all table names in the schema."""
        table_nodes = [node for node in self.graph.nodes() if node.startswith("table:")]
        return [node.replace("table:", "") for node in table_nodes]
    
    def get_columns(self, table_name: str) -> List[Dict[str, str]]:
        """Get list of columns for a specific table."""
        table_node = f"table:{table_name}"
        if table_node not in self.graph.nodes():
            return []
        
        columns = []
        for col_node in self.graph.successors(table_node):
            col_data = self.graph.nodes[col_node]
            columns.append({
                "name": col_data.get("name", ""),
                "data_type": col_data.get("data_type", ""),
                "table": table_name
            })
        return columns

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the schema graph."""
        schema_count = len([n for n in self.graph.nodes() if n.startswith("schema:")])
        table_count = len([n for n in self.graph.nodes() if n.startswith("table:")])
        column_count = len([n for n in self.graph.nodes() if n.startswith("column:")])
        
        return {
            "schemas": schema_count,
            "tables": table_count,
            "columns": column_count,
            "total_nodes": len(self.graph.nodes()),
            "edges": len(self.graph.edges())
        }
    
    def save(self, graph: nx.DiGraph) -> bool:
        """Save schema graph to pickle file."""
        with open(self.graph_path, 'wb') as f:
            pickle.dump(graph, f)
        logger.info(f"Schema graph saved to {self.graph_path}")
        return True

    def load(self) -> Optional[nx.DiGraph]:
        """Load schema graph from pickle file."""
        if os.path.exists(self.graph_path):
            with open(self.graph_path, 'rb') as f:
                self.graph = pickle.load(f)
                logger.info(f"Schema graph loaded from {self.graph_path} "
                           f"with {len(self.graph.nodes())} nodes and {len(self.graph.edges())} edges")
                
                # Generate diagram when loading
                self.save_diagram()
                
                return self.graph
        else:
            logger.info(f"Schema graph not found at {self.graph_path}")
            return None
    
    def save_diagram(self):
        """Generate and save a visual diagram of the schema graph."""
        try:
            if not self.graph.nodes():
                logger.warning("No graph data to diagram")
                return
            
            # Create figure
            plt.figure(figsize=(16, 12))
            
            # Separate nodes by type
            schema_nodes = [node for node in self.graph.nodes() if node.startswith("schema:")]
            table_nodes = [node for node in self.graph.nodes() if node.startswith("table:")]
            column_nodes = [node for node in self.graph.nodes() if node.startswith("column:")]
            
            # Create hierarchical layout
            pos = {}
            table_spacing = 3
            
            # Position schema node at the top center
            if schema_nodes:
                schema_center_x = (len(table_nodes) - 1) * table_spacing / 2
                pos[schema_nodes[0]] = (schema_center_x, 2)
            
            for i, table_node in enumerate(table_nodes):
                pos[table_node] = (i * table_spacing, 1)
                
                # Position columns below each table
                table_columns = [col for col in self.graph.successors(table_node)]
                col_spacing = 0.5
                start_x = i * table_spacing - (len(table_columns) - 1) * col_spacing / 2
                
                for j, col_node in enumerate(table_columns):
                    pos[col_node] = (start_x + j * col_spacing, 0)
            
            # Draw nodes and edges
            if schema_nodes:
                nx.draw_networkx_nodes(self.graph, pos, nodelist=schema_nodes,
                                      node_color='gold', node_size=3000, node_shape='D')
            nx.draw_networkx_nodes(self.graph, pos, nodelist=table_nodes, 
                                  node_color='lightblue', node_size=2000, node_shape='s')
            nx.draw_networkx_nodes(self.graph, pos, nodelist=column_nodes,
                                  node_color='lightgreen', node_size=1000, node_shape='o')
            nx.draw_networkx_edges(self.graph, pos, edge_color='gray', arrows=True)
            
            # Add labels
            schema_labels = {node: node.replace("schema:", "") for node in schema_nodes}
            table_labels = {node: node.replace("table:", "") for node in table_nodes}
            column_labels = {node: node.split(".")[-1] for node in column_nodes}
            
            if schema_labels:
                nx.draw_networkx_labels(self.graph, pos, schema_labels, font_size=12, font_weight='bold')
            nx.draw_networkx_labels(self.graph, pos, table_labels, font_size=10, font_weight='bold')
            nx.draw_networkx_labels(self.graph, pos, column_labels, font_size=8)
            
            plt.title(f"Database Schema: {self.graph_name}", fontsize=16, fontweight='bold')
            plt.axis('off')
            
            # Save diagram
            diagram_path = f"app/data/{self.graph_name}_schema_diagram.png"
            plt.savefig(diagram_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            logger.info(f"Schema diagram saved to {diagram_path}")
            
        except ImportError:
            logger.warning("Matplotlib not available - skipping diagram generation")
        except Exception as e:
            logger.error(f"Error generating schema diagram: {e}")
"""
Graph Analysis Tools
Advanced graph algorithms for investigation
"""

from typing import Dict, Any, List, Optional


class GraphAnalysisTools:
    """Advanced graph analysis tools for investigations"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def shortest_path(self, from_address: str, to_address: str, max_hops: int = 10) -> Dict[str, Any]:
        """
        Find shortest path between two addresses
        Useful for tracing fund flows
        """
        query = """
        MATCH path = shortestPath(
            (start:Address {address: $from})-[:TRANSACTION*..%d]-(end:Address {address: $to})
        )
        WHERE start <> end
        RETURN 
            [node in nodes(path) | node.address] as addresses,
            [rel in relationships(path) | {
                from: startNode(rel).address,
                to: endNode(rel).address,
                value: rel.value_eth,
                timestamp: rel.timestamp
            }] as transactions,
            length(path) as hops
        """ % max_hops
        
        with self.driver.session() as session:
            result = session.run(query, {"from": from_address, "to": to_address})
            record = result.single()
            
            if not record:
                return {
                    "found": False,
                    "from": from_address,
                    "to": to_address,
                    "message": "No path found"
                }
            
            return {
                "found": True,
                "from": from_address,
                "to": to_address,
                "hops": record["hops"],
                "path": record["addresses"],
                "transactions": record["transactions"]
            }
    
    def common_neighbors(self, address1: str, address2: str) -> Dict[str, Any]:
        """
        Find common neighbors (addresses both interact with)
        Useful for identifying connections
        """
        query = """
        MATCH (a1:Address {address: $addr1})-[:TRANSACTION]-(common:Address)-[:TRANSACTION]-(a2:Address {address: $addr2})
        WHERE common <> a1 AND common <> a2
        RETURN 
            common.address as address,
            count(*) as connection_strength,
            common.risk_score as risk_score
        ORDER BY connection_strength DESC
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"addr1": address1, "addr2": address2})
            
            neighbors = []
            for record in result:
                neighbors.append({
                    "address": record["address"],
                    "connection_strength": record["connection_strength"],
                    "risk_score": record["risk_score"] or 0
                })
            
            return {
                "address1": address1,
                "address2": address2,
                "common_neighbors": len(neighbors),
                "neighbors": neighbors
            }
    
    def community_detection(self, address: str, depth: int = 2) -> Dict[str, Any]:
        """
        Detect community/gang that address belongs to
        Uses Louvain community from GDS
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[:TRANSACTION*1..%d]-(connected:Address)
        WHERE connected <> a
        WITH a, collect(DISTINCT connected) as community_members
        RETURN 
            a.louvain as community_id,
            a.address as center,
            [m in community_members | {
                address: m.address,
                louvain: m.louvain,
                risk_score: m.risk_score
            }] as members,
            size(community_members) as community_size
        """ % depth
        
        with self.driver.session() as session:
            result = session.run(query, {"address": address})
            record = result.single()
            
            if not record:
                return {
                    "address": address,
                    "community_detected": False
                }
            
            # Filter members in same community
            same_community = [
                m for m in record["members"] 
                if m["louvain"] == record["community_id"]
            ]
            
            return {
                "address": address,
                "community_detected": True,
                "community_id": record["community_id"],
                "community_size": len(same_community),
                "total_connected": record["community_size"],
                "members": same_community[:50]  # Limit to 50
            }
    
    def betweenness_centrality(self, address: str) -> Dict[str, Any]:
        """
        Calculate betweenness centrality (how often address is on shortest paths)
        High values indicate "hub" or "bridge" addresses
        """
        # Note: This is computationally expensive for large graphs
        # In production, you'd use GDS Betweenness Centrality algorithm
        query = """
        MATCH (a:Address {address: $address})
        RETURN 
            a.address as address,
            a.betweenness as betweenness,
            a.degree as degree,
            a.pagerank as pagerank
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"address": address})
            record = result.single()
            
            if not record:
                return {
                    "address": address,
                    "found": False
                }
            
            betweenness = record["betweenness"] or 0
            degree = record["degree"] or 0
            
            # Classify as hub if high betweenness
            is_hub = betweenness > 0.01  # Threshold depends on graph size
            
            return {
                "address": address,
                "found": True,
                "betweenness_centrality": betweenness,
                "degree": degree,
                "pagerank": record["pagerank"] or 0,
                "is_hub": is_hub,
                "interpretation": "High-traffic hub address" if is_hub else "Regular node"
            }
    
    def clustering_coefficient(self, address: str) -> Dict[str, Any]:
        """
        Calculate clustering coefficient (how connected are neighbors)
        High values indicate tight-knit groups
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[:TRANSACTION]-(neighbor:Address)
        WITH a, collect(DISTINCT neighbor) as neighbors, count(DISTINCT neighbor) as degree
        WHERE degree > 1
        
        // Count connections between neighbors
        UNWIND neighbors as n1
        UNWIND neighbors as n2
        WITH a, neighbors, degree, n1, n2
        WHERE n1 <> n2
        OPTIONAL MATCH (n1)-[:TRANSACTION]-(n2)
        WITH a, degree, neighbors, count(*) as neighbor_connections
        
        WITH a, degree, neighbor_connections,
             (2.0 * neighbor_connections) / (degree * (degree - 1)) as clustering
        
        RETURN 
            a.address as address,
            degree,
            neighbor_connections,
            clustering
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"address": address})
            record = result.single()
            
            if not record or record["degree"] is None:
                return {
                    "address": address,
                    "clustering_coefficient": 0,
                    "degree": 0,
                    "interpretation": "Isolated or single connection"
                }
            
            clustering = record["clustering"] or 0
            
            # Interpret clustering
            if clustering > 0.7:
                interpretation = "Highly clustered - tight-knit group"
            elif clustering > 0.3:
                interpretation = "Moderately clustered"
            else:
                interpretation = "Loosely connected"
            
            return {
                "address": address,
                "clustering_coefficient": clustering,
                "degree": record["degree"],
                "neighbor_connections": record["neighbor_connections"],
                "interpretation": interpretation
            }
    
    def find_triangles(self, address: str) -> Dict[str, Any]:
        """
        Find triangle patterns (A->B->C->A)
        Useful for detecting wash trading rings
        """
        query = """
        MATCH (a:Address {address: $address})-[:TRANSACTION]->(b:Address)-[:TRANSACTION]->(c:Address)-[:TRANSACTION]->(a)
        WHERE a <> b AND b <> c AND c <> a
        RETURN 
            collect(DISTINCT [a.address, b.address, c.address]) as triangles,
            count(DISTINCT [b, c]) as triangle_count
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, {"address": address})
            record = result.single()
            
            if not record:
                return {
                    "address": address,
                    "triangles_found": 0,
                    "triangles": []
                }
            
            return {
                "address": address,
                "triangles_found": record["triangle_count"] or 0,
                "triangles": record["triangles"][:20],  # Limit to 20
                "risk_indicator": record["triangle_count"] > 5
            }
    
    def ego_network(self, address: str, depth: int = 2) -> Dict[str, Any]:
        """
        Get ego network (address-centric subgraph)
        Returns all nodes within N hops
        """
        query = """
        MATCH (center:Address {address: $address})
        OPTIONAL MATCH path = (center)-[:TRANSACTION*1..%d]-(connected:Address)
        WITH center, collect(DISTINCT connected) as network_nodes
        
        RETURN 
            center.address as center,
            [n in network_nodes | {
                address: n.address,
                risk_score: n.risk_score,
                distance: 1  // Simplified, would need proper distance calculation
            }] as network,
            size(network_nodes) as network_size
        """ % depth
        
        with self.driver.session() as session:
            result = session.run(query, {"address": address})
            record = result.single()
            
            if not record:
                return {
                    "address": address,
                    "network_size": 0,
                    "network": []
                }
            
            return {
                "address": address,
                "depth": depth,
                "network_size": record["network_size"],
                "network": record["network"][:100]  # Limit to 100
            }


# Global graph tools instance
graph_tools = None

def get_graph_tools(driver):
    """Get or create graph tools"""
    global graph_tools
    if graph_tools is None:
        graph_tools = GraphAnalysisTools(driver)
    return graph_tools


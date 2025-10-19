"""
GraphQL API Module
Flexible query interface for the platform
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


# GraphQL Schema Definition
GRAPHQL_SCHEMA = """
type Address {
    address: String!
    riskScore: Float
    totalInEth: Float
    totalOutEth: Float
    transactionCount: Int
    features: AddressFeatures
    alerts: [Alert]
}

type AddressFeatures {
    pagerank: Float
    degree: Int
    inDegree: Int
    outDegree: Int
    louvain: Int
    triangles: Int
}

type Transaction {
    hash: String!
    from: String!
    to: String!
    valueEth: Float!
    timestamp: Int!
    blockNumber: Int
}

type Alert {
    id: String!
    address: String!
    type: String!
    score: Float!
    createdAt: String!
}

type Pattern {
    patternType: String!
    detected: Boolean!
    riskScore: Int!
    explanation: String
}

type Case {
    caseId: String!
    title: String!
    status: String!
    priority: String!
    assignedTo: String
    createdAt: Int!
}

type Query {
    address(address: String!): Address
    transactions(address: String!, limit: Int): [Transaction]
    alerts(limit: Int): [Alert]
    patterns(address: String!): [Pattern]
    cases(status: String): [Case]
    searchAddresses(query: String!): [Address]
}

type Mutation {
    createAlert(address: String!, type: String!, score: Float!): Alert
    createCase(title: String!, address: String!, caseType: String!, priority: String!): Case
    updateCaseStatus(caseId: String!, status: String!): Case
}

type Subscription {
    alertCreated: Alert
    caseUpdated: Case
}
"""


class GraphQLResolver:
    """GraphQL query and mutation resolvers"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
    
    def resolve_address(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve address query"""
        address = args.get("address")
        
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[t_out:TRANSACTION]->()
        OPTIONAL MATCH (a)<-[t_in:TRANSACTION]-()
        RETURN 
            a.address as address,
            a.risk_score as riskScore,
            sum(t_out.value_eth) as totalOutEth,
            sum(t_in.value_eth) as totalInEth,
            count(t_out) + count(t_in) as transactionCount,
            a.pagerank as pagerank,
            a.degree as degree,
            a.inDegree as inDegree,
            a.outDegree as outDegree,
            a.louvain as louvain,
            a.triangles as triangles
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            if not record:
                return None
            
            return {
                "address": record["address"],
                "riskScore": float(record["riskScore"] or 0),
                "totalInEth": float(record["totalInEth"] or 0),
                "totalOutEth": float(record["totalOutEth"] or 0),
                "transactionCount": record["transactionCount"] or 0,
                "features": {
                    "pagerank": float(record["pagerank"] or 0),
                    "degree": int(record["degree"] or 0),
                    "inDegree": int(record["inDegree"] or 0),
                    "outDegree": int(record["outDegree"] or 0),
                    "louvain": int(record["louvain"] or 0),
                    "triangles": int(record["triangles"] or 0)
                }
            }
    
    def resolve_transactions(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve transactions query"""
        address = args.get("address")
        limit = args.get("limit", 50)
        
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]-(other)
        RETURN 
            t.hash as hash,
            CASE WHEN startNode(t).address = $address THEN $address ELSE other.address END as from_addr,
            CASE WHEN endNode(t).address = $address THEN $address ELSE other.address END as to_addr,
            t.value_eth as valueEth,
            t.timestamp as timestamp,
            t.block_number as blockNumber
        ORDER BY t.timestamp DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, limit=limit)
            records = list(result)
            
            transactions = []
            for record in records:
                transactions.append({
                    "hash": record["hash"],
                    "from": record["from_addr"],
                    "to": record["to_addr"],
                    "valueEth": float(record["valueEth"] or 0),
                    "timestamp": record["timestamp"],
                    "blockNumber": record["blockNumber"]
                })
            
            return transactions
    
    def resolve_alerts(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve alerts query"""
        limit = args.get("limit", 50)
        
        query = """
        MATCH (alert:Alert)
        RETURN alert
        ORDER BY alert.created_at DESC
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, limit=limit)
            records = list(result)
            
            alerts = []
            for record in records:
                alert = dict(record["alert"])
                alerts.append({
                    "id": alert.get("id"),
                    "address": alert.get("address"),
                    "type": alert.get("type"),
                    "score": float(alert.get("score", 0)),
                    "createdAt": alert.get("created_at")
                })
            
            return alerts
    
    def resolve_cases(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve cases query"""
        status = args.get("status")
        
        where_clause = "WHERE c.status = $status" if status else ""
        
        query = f"""
        MATCH (c:Case)
        {where_clause}
        RETURN c
        ORDER BY c.created_at DESC
        LIMIT 50
        """
        
        params = {"status": status} if status else {}
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            records = list(result)
            
            cases = []
            for record in records:
                case = dict(record["c"])
                cases.append({
                    "caseId": case.get("case_id"),
                    "title": case.get("title"),
                    "status": case.get("status"),
                    "priority": case.get("priority"),
                    "assignedTo": case.get("assigned_to"),
                    "createdAt": case.get("created_at")
                })
            
            return cases
    
    def mutation_create_alert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert mutation"""
        # This would integrate with the alerting system
        return {
            "id": "alert-" + str(datetime.now().timestamp()),
            "address": args["address"],
            "type": args["type"],
            "score": args["score"],
            "createdAt": datetime.now().isoformat()
        }
    
    def get_schema(self) -> str:
        """Return GraphQL schema"""
        return GRAPHQL_SCHEMA


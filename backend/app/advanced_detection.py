"""
Advanced Detection Module
- Mixer/Tumbler Detection (Tornado Cash, etc)
- Smart Contract Interaction Analysis
- Token Holdings Analysis (ERC-20/721/1155)
- Bridge Detection (Cross-chain)
- Privacy Coin Conversion
- Oracle Manipulation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics


class AdvancedDetector:
    """Advanced detection for mixers, smart contracts, tokens, and bridges"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
        # Known mixer addresses (Tornado Cash, etc)
        self.known_mixers = {
            '0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936': 'Tornado Cash: 100 ETH',
            '0x910cbd523d972eb0a6f4cae4618ad62622b39dbf': 'Tornado Cash: 10 ETH',
            '0x22aaa7720ddd5388a3c0a3333430953c68f1849b': 'Tornado Cash: 1 ETH',
            '0xba214c1c1928a32bffe790263e38b4af9bfcd659': 'Tornado Cash: 0.1 ETH',
            '0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc': 'Tornado Cash Router',
            '0xd90e2f925da726b50c4ed8d0fb90ad053324f31b': 'Tornado Cash: 1000 ETH',
        }
        
        # Known bridges
        self.known_bridges = {
            '0x3ee18b2214aff97000d974cf647e7c347e8fa585': 'Wormhole Bridge',
            '0xa0c68c638235ee32657e8f720a23cec1bfc77c77': 'Polygon Bridge',
            '0x8484ef722627bf18ca5ae6bcf031c23e6e922b30': 'Arbitrum Bridge',
            '0x99c9fc46f92e8a1c0dec1b1747d010903e884be1': 'Optimism Bridge',
            '0x401f6c983ea34274ec46f84d70b31c151321188b': 'Multichain Bridge',
        }
    
    def detect_mixer_usage(self, address: str, depth: int = 3) -> Dict[str, Any]:
        """
        Detect if address has interacted with known mixers/tumblers
        High risk indicator for money laundering
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[t:TRANSACTION*1..3]-(mixer:Address)
        WHERE mixer.address IN $mixer_addresses
        WITH a, mixer, t,
             [rel in t | {from: startNode(rel).address, to: endNode(rel).address, 
                          value: rel.value_eth, timestamp: rel.timestamp}] as path_details
        RETURN 
            mixer.address as mixer_address,
            length(t) as hops,
            path_details,
            count(t) as interaction_count
        ORDER BY interaction_count DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, mixer_addresses=list(self.known_mixers.keys()))
            records = list(result)
            
            detected_mixers = []
            for record in records:
                if record["mixer_address"]:
                    mixer_name = self.known_mixers.get(record["mixer_address"], "Unknown Mixer")
                    detected_mixers.append({
                        "mixer_address": record["mixer_address"],
                        "mixer_name": mixer_name,
                        "hops": record["hops"],
                        "interaction_count": record["interaction_count"],
                        "path_details": record["path_details"]
                    })
            
            risk_score = 0
            if detected_mixers:
                # Direct interaction with mixer = very high risk
                direct_interactions = [m for m in detected_mixers if m["hops"] == 1]
                indirect_interactions = [m for m in detected_mixers if m["hops"] > 1]
                
                risk_score = len(direct_interactions) * 30 + len(indirect_interactions) * 15
                risk_score = min(risk_score, 100)
            
            return {
                "detection_type": "mixer_usage",
                "detected": len(detected_mixers) > 0,
                "risk_score": risk_score,
                "mixers": detected_mixers,
                "total_mixer_interactions": len(detected_mixers),
                "direct_interactions": len([m for m in detected_mixers if m["hops"] == 1]),
                "explanation": "Interaction with known mixers/tumblers indicates potential money laundering" if detected_mixers else "No mixer usage detected"
            }
    
    def analyze_smart_contract_interactions(self, address: str) -> Dict[str, Any]:
        """
        Analyze smart contract interactions to classify activity
        (DeFi, NFT, Gaming, Scam, etc)
        """
        query = """
        MATCH (a:Address {address: $address})-[t:TRANSACTION]->(contract:Address)
        WHERE contract.is_contract = true OR size(t.input_data) > 10
        WITH contract, 
             count(t) as interaction_count,
             sum(t.value_eth) as total_value,
             collect({timestamp: t.timestamp, value: t.value_eth}) as interactions
        RETURN 
            contract.address as contract_address,
            interaction_count,
            total_value,
            interactions
        ORDER BY interaction_count DESC
        LIMIT 50
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            records = list(result)
            
            contracts = []
            for record in records:
                contract_type = self._classify_contract(record["contract_address"])
                contracts.append({
                    "address": record["contract_address"],
                    "type": contract_type,
                    "interaction_count": record["interaction_count"],
                    "total_value_eth": float(record["total_value"] or 0),
                    "interactions": record["interactions"]
                })
            
            # Categorize
            defi_count = len([c for c in contracts if c["type"] == "DeFi"])
            nft_count = len([c for c in contracts if c["type"] == "NFT"])
            gaming_count = len([c for c in contracts if c["type"] == "Gaming"])
            unknown_count = len([c for c in contracts if c["type"] == "Unknown"])
            
            return {
                "analysis_type": "smart_contract_interactions",
                "total_contracts": len(contracts),
                "defi_contracts": defi_count,
                "nft_contracts": nft_count,
                "gaming_contracts": gaming_count,
                "unknown_contracts": unknown_count,
                "contracts": contracts,
                "risk_factors": {
                    "high_unknown_ratio": unknown_count > len(contracts) * 0.7,
                    "suspicious_pattern": any(c["interaction_count"] > 100 for c in contracts)
                }
            }
    
    def analyze_token_holdings(self, address: str) -> Dict[str, Any]:
        """
        Analyze ERC-20/721/1155 token holdings
        Note: Requires token transfer events to be indexed
        """
        # This would require parsing token transfer events from Etherscan
        # For now, return a structured response with placeholders
        
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)<-[t:TOKEN_TRANSFER]-(from)
        OPTIONAL MATCH (a)-[t2:TOKEN_TRANSFER]->(to)
        RETURN 
            count(t) as tokens_received,
            count(t2) as tokens_sent
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address)
            record = result.single()
            
            return {
                "analysis_type": "token_holdings",
                "note": "Token analysis requires ERC-20/721/1155 event indexing",
                "tokens_received_count": record["tokens_received"] if record else 0,
                "tokens_sent_count": record["tokens_sent"] if record else 0,
                "holdings": [],  # Would be populated with actual token data
                "risk_factors": {
                    "high_token_activity": False,
                    "suspicious_tokens": []
                }
            }
    
    def detect_bridge_usage(self, address: str) -> Dict[str, Any]:
        """
        Detect usage of cross-chain bridges
        Often used to move funds between chains to evade tracking
        """
        query = """
        MATCH (a:Address {address: $address})
        OPTIONAL MATCH (a)-[t:TRANSACTION]-(bridge:Address)
        WHERE bridge.address IN $bridge_addresses
        WITH bridge,
             count(t) as interaction_count,
             sum(t.value_eth) as total_value,
             collect({timestamp: t.timestamp, value: t.value_eth}) as interactions
        WHERE interaction_count > 0
        RETURN 
            bridge.address as bridge_address,
            interaction_count,
            total_value,
            interactions
        ORDER BY interaction_count DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, address=address, bridge_addresses=list(self.known_bridges.keys()))
            records = list(result)
            
            detected_bridges = []
            for record in records:
                bridge_name = self.known_bridges.get(record["bridge_address"], "Unknown Bridge")
                detected_bridges.append({
                    "bridge_address": record["bridge_address"],
                    "bridge_name": bridge_name,
                    "interaction_count": record["interaction_count"],
                    "total_value_eth": float(record["total_value"] or 0),
                    "interactions": record["interactions"]
                })
            
            risk_score = 0
            if detected_bridges:
                # Bridge usage increases risk
                total_interactions = sum(b["interaction_count"] for b in detected_bridges)
                risk_score = min(total_interactions * 5, 60)
            
            return {
                "detection_type": "bridge_usage",
                "detected": len(detected_bridges) > 0,
                "risk_score": risk_score,
                "bridges": detected_bridges,
                "total_bridge_interactions": sum(b["interaction_count"] for b in detected_bridges),
                "explanation": "Cross-chain bridge usage can indicate attempt to evade tracking" if detected_bridges else "No bridge usage detected"
            }
    
    
    def _classify_contract(self, contract_address: str) -> str:
        """Classify contract type based on known patterns"""
        # Simplified classification - would be enhanced with actual contract data
        known_defi = ['uniswap', 'sushiswap', 'aave', 'compound', 'curve', 'balancer']
        known_nft = ['opensea', 'rarible', 'foundation', 'superrare']
        known_gaming = ['axie', 'sandbox', 'decentraland']
        
        addr_lower = contract_address.lower()
        
        if any(d in addr_lower for d in known_defi):
            return "DeFi"
        elif any(n in addr_lower for n in known_nft):
            return "NFT"
        elif any(g in addr_lower for g in known_gaming):
            return "Gaming"
        else:
            return "Unknown"
    
    def analyze_all(self, address: str) -> Dict[str, Any]:
        """Run all advanced detection algorithms"""
        return {
            "address": address,
            "timestamp": datetime.now().isoformat(),
            "mixer_detection": self.detect_mixer_usage(address),
            "smart_contract_analysis": self.analyze_smart_contract_interactions(address),
            "token_holdings": self.analyze_token_holdings(address),
            "bridge_usage": self.detect_bridge_usage(address),
            "overall_risk_score": self._calculate_overall_risk(address)
        }
    
    def _calculate_overall_risk(self, address: str) -> int:
        """Calculate overall risk from all advanced detection methods"""
        mixer = self.detect_mixer_usage(address)
        bridge = self.detect_bridge_usage(address)
        
        total_risk = (
            mixer.get("risk_score", 0) * 1.5 +  # Mixer usage is highest risk
            bridge.get("risk_score", 0) * 1.0
        ) / 2
        
        return min(int(total_risk), 100)


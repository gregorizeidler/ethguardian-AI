"""
Data Enrichment Module
Enrich blockchain data with external sources:
- OFAC Sanctions List
- Known exchange addresses
- DeFi protocol identification
- Token information
- Price data
- Entity labels (from public sources)
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import requests
import json


class DataEnricher:
    """Enrich blockchain data with external information"""
    
    def __init__(self):
        self.ofac_list: Set[str] = set()
        self.exchange_addresses: Dict[str, str] = {}
        self.defi_protocols: Dict[str, Dict[str, Any]] = {}
        self.entity_labels: Dict[str, List[str]] = {}
        self.price_cache: Dict[str, float] = {}
        
        # Initialize with known data
        self._load_static_data()
    
    def _load_static_data(self):
        """Load static enrichment data"""
        # Known major exchanges (sample data)
        self.exchange_addresses = {
            "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": "Binance",
            "0x28c6c06298d514db089934071355e5743bf21d60": "Binance 2",
            "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 3",
            "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance 4",
            "0x56eddb7aa87536c09ccc2793473599fd21a8b17f": "Binance 5",
            "0x9696f59e4d72e237be84ffd425dcad154bf96976": "Binance 6",
            "0x4e9ce36e442e55ecd9025b9a6e0d88485d628a67": "Binance 7",
            "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8": "Binance 8",
            "0x0681d8db095565fe8a346fa0277bffde9c0edbbf": "Binance: Charity Wallet",
            "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
            "0x001866ae5b3de6caa5a51543fd9fb64f524f5478": "Bitfinex",
            "0x742d35cc6634c0532925a3b844bc454e4438f44e": "Bitfinex 2",
            "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa": "Bitfinex 3",
            "0xdcd0272462140d0a3ced6c4bf970c7641f08cd2c": "Bitfinex: Cold Wallet",
            "0x4fdd5eb2fb260149a3903859043e962ab89d8ed4": "Bitfinex: Hot Wallet",
            "0x1151314c646ce4e0efd76d1af4760ae66a9fe30f": "Bitfinex: Multisig 4",
            "0xab7c74abc0c4d48d1bdad5dcb26153fc8780f83e": "Huobi",
            "0xa8660c8ffd6d578f657b72c0c811284aef0b735e": "Huobi 2",
            "0x6748f50f686bfbca6fe8ad62b22228b87f31ff2b": "Huobi 3",
            "0xfdb16996831753d5331ff813c29a93c76834a0ad": "Huobi 4",
            "0xeee28d484628d41a82d01e21d12e2e78d69920da": "Huobi 5",
            "0x5c985e89dde482efe97ea9f1950ad149eb73829b": "Huobi 6",
            "0xdc76cd25977e0a5ae17155770273ad58648900d3": "Huobi 7",
            "0xadb2b42f6bd96f5c65920b9ac88619dce4166f94": "Huobi 8",
            "0xa910f92acdaf488fa6ef02174fb86208ad7722ba": "Huobi 9",
            "0x18709e89bd403f470088abdacebe86cc60dda12e": "Huobi 10",
            "0x46340b20830761efd32832a74d7169b29feb9758": "Coinbase 1",
            "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase 2",
            "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase 3",
            "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase 4",
            "0x3cd751e6b0078be393132286c442345e5dc49699": "Coinbase 5",
            "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511": "Coinbase 6",
            "0xeb2629a2734e272bcc07bda959863f316f4bd4cf": "Coinbase 7",
        }
        
        # Known DeFi protocols
        self.defi_protocols = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {
                "name": "Uniswap V2 Router",
                "type": "DEX",
                "protocol": "Uniswap"
            },
            "0xe592427a0aece92de3edee1f18e0157c05861564": {
                "name": "Uniswap V3 Router",
                "type": "DEX",
                "protocol": "Uniswap"
            },
            "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9": {
                "name": "Aave V2 LendingPool",
                "type": "Lending",
                "protocol": "Aave"
            },
            "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": {
                "name": "Aave V3 Pool",
                "type": "Lending",
                "protocol": "Aave"
            },
            "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b": {
                "name": "Compound Comptroller",
                "type": "Lending",
                "protocol": "Compound"
            }
        }
    
    def enrich_address(self, address: str) -> Dict[str, Any]:
        """Enrich address with all available data"""
        enrichment = {
            "address": address,
            "enriched_at": datetime.now().isoformat(),
            "labels": [],
            "entity_type": "unknown",
            "risk_flags": [],
            "metadata": {}
        }
        
        # Check OFAC sanctions
        if self.is_sanctioned(address):
            enrichment["labels"].append("OFAC_SANCTIONED")
            enrichment["risk_flags"].append("Sanctioned address")
            enrichment["entity_type"] = "sanctioned"
        
        # Check exchanges
        if address.lower() in self.exchange_addresses:
            exchange_name = self.exchange_addresses[address.lower()]
            enrichment["labels"].append(f"EXCHANGE_{exchange_name.upper().replace(' ', '_')}")
            enrichment["entity_type"] = "exchange"
            enrichment["metadata"]["exchange_name"] = exchange_name
        
        # Check DeFi protocols
        if address.lower() in self.defi_protocols:
            protocol_info = self.defi_protocols[address.lower()]
            enrichment["labels"].append(f"DEFI_{protocol_info['protocol'].upper()}")
            enrichment["entity_type"] = "defi_protocol"
            enrichment["metadata"]["protocol"] = protocol_info
        
        # Get additional labels
        if address in self.entity_labels:
            enrichment["labels"].extend(self.entity_labels[address])
        
        return enrichment
    
    def is_sanctioned(self, address: str) -> bool:
        """Check if address is on OFAC sanctions list"""
        # In production, this would check against real OFAC data
        # For demo, using placeholder
        return address.lower() in self.ofac_list
    
    def add_ofac_address(self, address: str):
        """Add address to OFAC list (for testing)"""
        self.ofac_list.add(address.lower())
    
    def identify_entity_type(self, address: str, transaction_patterns: Dict[str, Any]) -> str:
        """
        Identify entity type based on patterns
        Returns: exchange, mixer, defi, contract, wallet, miner, etc.
        """
        # Check known addresses first
        if address.lower() in self.exchange_addresses:
            return "exchange"
        
        if address.lower() in self.defi_protocols:
            return "defi_protocol"
        
        # Analyze patterns
        tx_count = transaction_patterns.get("transaction_count", 0)
        unique_counterparties = transaction_patterns.get("unique_counterparties", 0)
        avg_tx_value = transaction_patterns.get("avg_transaction_value", 0)
        
        # Heuristics for entity identification
        if tx_count > 10000 and unique_counterparties > 1000:
            return "exchange_or_mixer"
        elif tx_count > 1000 and unique_counterparties > 500:
            return "service_provider"
        elif tx_count > 100 and avg_tx_value < 0.01:
            return "bot_or_aggregator"
        elif unique_counterparties < 5 and tx_count > 50:
            return "personal_wallet"
        else:
            return "unknown"
    
    def get_token_info(self, contract_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token information from external API
        Using CoinGecko as example (requires API key in production)
        """
        try:
            # Placeholder - in production would call real API
            # url = f"https://api.coingecko.com/api/v3/coins/ethereum/contract/{contract_address}"
            # response = requests.get(url)
            # if response.status_code == 200:
            #     return response.json()
            
            # For demo, return mock data
            return {
                "name": "Unknown Token",
                "symbol": "???",
                "contract_address": contract_address,
                "total_supply": None,
                "note": "Token info not available in demo mode"
            }
        except Exception as e:
            return None
    
    def get_eth_price(self) -> float:
        """Get current ETH price in USD"""
        try:
            # Check cache (cache for 5 minutes)
            if "eth_usd" in self.price_cache:
                cached_time = self.price_cache.get("eth_usd_time", 0)
                if datetime.now().timestamp() - cached_time < 300:
                    return self.price_cache["eth_usd"]
            
            # Fetch from CoinGecko
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                price = data.get("ethereum", {}).get("usd", 3000)
                
                # Cache it
                self.price_cache["eth_usd"] = price
                self.price_cache["eth_usd_time"] = datetime.now().timestamp()
                
                return price
            else:
                # Return default if API fails
                return 3000.0
        except Exception as e:
            print(f"Failed to fetch ETH price: {e}")
            return 3000.0  # Default fallback price
    
    def convert_eth_to_usd(self, eth_amount: float) -> float:
        """Convert ETH amount to USD"""
        price = self.get_eth_price()
        return eth_amount * price
    
    def get_address_labels(self, address: str) -> List[str]:
        """Get all labels for an address"""
        enrichment = self.enrich_address(address)
        return enrichment["labels"]
    
    def add_custom_label(self, address: str, label: str):
        """Add custom label to address"""
        if address not in self.entity_labels:
            self.entity_labels[address] = []
        if label not in self.entity_labels[address]:
            self.entity_labels[address].append(label)
    
    def batch_enrich(self, addresses: List[str]) -> Dict[str, Dict[str, Any]]:
        """Enrich multiple addresses at once"""
        results = {}
        for address in addresses:
            results[address] = self.enrich_address(address)
        return results
    
    def get_risk_intelligence(self, address: str) -> Dict[str, Any]:
        """
        Get risk intelligence from multiple sources
        Combines OFAC, known bad actors, etc.
        """
        intelligence = {
            "address": address,
            "checked_at": datetime.now().isoformat(),
            "risk_factors": [],
            "protective_factors": [],
            "overall_assessment": "unknown"
        }
        
        enrichment = self.enrich_address(address)
        
        # Risk factors
        if "OFAC_SANCTIONED" in enrichment["labels"]:
            intelligence["risk_factors"].append({
                "factor": "OFAC Sanctioned",
                "severity": "CRITICAL",
                "source": "US Treasury OFAC"
            })
        
        if enrichment["entity_type"] == "exchange_or_mixer":
            intelligence["risk_factors"].append({
                "factor": "Possible mixing service",
                "severity": "HIGH",
                "source": "Pattern analysis"
            })
        
        # Protective factors
        if enrichment["entity_type"] == "exchange":
            intelligence["protective_factors"].append({
                "factor": "Known legitimate exchange",
                "source": "Public exchange database"
            })
        
        if enrichment["entity_type"] == "defi_protocol":
            intelligence["protective_factors"].append({
                "factor": "Known DeFi protocol",
                "source": "DeFi protocol registry"
            })
        
        # Overall assessment
        if len(intelligence["risk_factors"]) > 0:
            intelligence["overall_assessment"] = "high_risk"
        elif len(intelligence["protective_factors"]) > 0:
            intelligence["overall_assessment"] = "low_risk"
        else:
            intelligence["overall_assessment"] = "unknown"
        
        return intelligence


# Global enricher instance
enricher = DataEnricher()


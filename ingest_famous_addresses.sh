#!/bin/bash
# EthGuardian AI - Ingerir Endereços Famosos

API="http://localhost:8001/api"
ADDRESSES=(
    "0x28C6c06298d514Db089934071355E5743bf21d60"  # Binance
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3"  # Coinbase
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap
    "0x722122dF12D4e14e13Ac3b6895a86e84145b6967"  # Tornado Cash
    "0x098B716B8Aaf21512996dC57EB0615e2383E2f96"  # Ronin Hacker
)

NAMES=(
    "Binance"
    "Coinbase"
    "Uniswap"
    "Tornado Cash"
    "Ronin Hacker"
)

echo "🛡️ EthGuardian AI - Ingesting Famous Addresses"
echo "==============================================="
echo ""

for i in "${!ADDRESSES[@]}"; do
    addr="${ADDRESSES[$i]}"
    name="${NAMES[$i]}"
    
    echo "[$((i+1))/${#ADDRESSES[@]}] 📥 Ingesting: $name"
    echo "    Address: $addr"
    
    response=$(curl -s -X POST "$API/ingest/$addr")
    
    if echo "$response" | grep -q '"ok":true'; then
        count=$(echo "$response" | grep -o '"ingested":[0-9]*' | cut -d: -f2)
        echo "    ✅ Success! Ingested $count transactions"
    else
        echo "    ❌ Failed: $response"
    fi
    
    echo ""
    sleep 2  # Rate limit
done

echo "✅ Done! Check Neo4j browser to see the data."

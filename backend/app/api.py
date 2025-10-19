from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from .schemas import GraphResponse, AddressProfile
from .core import driver, ingest_address, expand_graph
from .aml_analytics import run_all_analytics
from .ml_models import run_gds_feature_engineering, get_address_risk_score
from .automation import automation_controller
from .pattern_detection import PatternDetector
from .fraud_detection import FraudDetector
from .enhanced_analytics import EnhancedAnalytics
from .alerting import alert_manager
from .compliance import ComplianceManager
from .enrichment import enricher
from .report_generator import report_generator
from .watchlist import get_watchlist_manager
from .bulk_analysis import get_bulk_analyzer
from .graph_tools import get_graph_tools
from .websocket_manager import ws_manager
from .advanced_detection import AdvancedDetector
from .case_management import CaseManagementSystem
from .graphql_api import GraphQLResolver
from .rate_limiter import rate_limiter
from .webhook_system import get_webhook_manager

router = APIRouter(prefix="/api", tags=["api"])

# Initialize modules
pattern_detector = PatternDetector(driver)
fraud_detector = FraudDetector(driver)
enhanced_analytics = EnhancedAnalytics(driver)
compliance_manager = ComplianceManager(driver)
watchlist_manager = get_watchlist_manager(driver)
bulk_analyzer = get_bulk_analyzer(driver)
graph_tools = get_graph_tools(driver)
advanced_detector = AdvancedDetector(driver)
case_manager = CaseManagementSystem(driver)
graphql_resolver = GraphQLResolver(driver)
webhook_manager = get_webhook_manager(driver)


@router.post("/ingest/{address}")
def ingest(address: str) -> Dict[str, Any]:
    try:
        out = ingest_address(address)
        return {"ok": True, **out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{address}")
def analyze(address: str) -> Dict[str, Any]:
    # 1) AML heuristics -> cria Alert nodes
    try:
        with driver.session() as session:
            analytics = session.execute_write(lambda tx: run_all_analytics(tx, address))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AML analytics failed: {e}")

    # 2) GDS features
    try:
        run_gds_feature_engineering(driver)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GDS failed: {e}")

    # 3) Risk score
    try:
        score = get_address_risk_score(driver, address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk scoring failed: {e}")

    return {"ok": True, "analytics": analytics, "risk_score": score}


@router.get("/alerts")
def get_alerts() -> Dict[str, Any]:
    cypher = """
    MATCH (al:Alert)-[:FOR]->(a:Address)
    RETURN al.id AS id, al.type AS type, al.score AS score, al.created_at AS created_at, a.address AS address
    ORDER BY al.created_at DESC
    LIMIT 200
    """
    with driver.session() as session:
        rows = session.execute_read(lambda tx: list(tx.run(cypher)))
    alerts = [
        {
            "id": r["id"],
            "address": r["address"],
            "type": r["type"],
            "score": float(r["score"]),
            "created_at": int(r["created_at"]),
        }
        for r in rows
    ]
    return {"alerts": alerts}


@router.get("/address/{address}/profile", response_model=AddressProfile)
def address_profile(address: str):
    cypher = """
    MATCH (a:Address {address: $address})
    OPTIONAL MATCH (src:Address)-[rin:TRANSFER]->(a)
    WITH a, count(DISTINCT src) AS fanin, sum(coalesce(rin.value_sum, 0)) AS vin
    OPTIONAL MATCH (a)-[rout:TRANSFER]->(dst:Address)
    WITH a, fanin, vin, count(DISTINCT dst) AS fanout, sum(coalesce(rout.value_sum, 0)) AS vout
    RETURN a.address AS address,
           coalesce(a.risk_score, 0.0) AS risk,
           coalesce(a.pagerank, 0.0) AS pr,
           coalesce(a.degree, 0.0) AS degree,
           coalesce(a.inDegree, 0.0) AS indeg,
           coalesce(a.outDegree, 0.0) AS outdeg,
           coalesce(a.louvain, 0) AS louvain,
           coalesce(a.triangles, 0.0) AS triangles,
           fanin, fanout, vin, vout
    """
    with driver.session() as session:
        rec = session.execute_read(lambda tx: tx.run(cypher, address=address).single())
    if not rec:
        raise HTTPException(status_code=404, detail="Address not found")

    profile = {
        "address": rec["address"],
        "risk_score": float(rec["risk"]),
        "features": {
            "pagerank": float(rec["pr"]),
            "degree": float(rec["degree"]),
            "inDegree": float(rec["indeg"]),
            "outDegree": float(rec["outdeg"]),
            "louvain": int(rec["louvain"]),
            "triangles": float(rec["triangles"]),
        },
        "stats": {
            "fanin_addresses": int(rec["fanin"]),
            "fanout_addresses": int(rec["fanout"]),
            "total_in_eth": float(rec["vin"]),
            "total_out_eth": float(rec["vout"]),
        },
    }
    return profile


@router.get("/address/{address}/graph", response_model=GraphResponse)
def address_graph(address: str, hops: int = Query(2, ge=1, le=3)):
    nodes, links = expand_graph(address, hops=hops)
    # Garantir que o endereço consultado apareça
    if not any(n["id"] == address for n in nodes):
        nodes.append({"id": address, "label": address[:10] + "…", "risk_score": 0.0})
    return {"nodes": nodes, "links": links}


# ============================================================================
# AUTOMATION ENDPOINTS - Crawler, Monitor, Auto-Expansion
# ============================================================================

class CrawlerJobRequest(BaseModel):
    seed_addresses: List[str]
    max_depth: int = 3
    min_value_eth: float = 1.0
    min_risk_score: float = 60.0
    max_addresses: int = 5000
    run_async: bool = True


class MonitorJobRequest(BaseModel):
    min_value_usd: float = 100000.0
    check_interval_minutes: int = 60
    duration_hours: Optional[int] = 1
    run_async: bool = True


class ExpansionJobRequest(BaseModel):
    address: str
    trigger_score: float = 70.0
    expansion_depth: int = 2
    min_value_eth: float = 0.5
    run_async: bool = True


@router.post("/automation/crawler")
def start_crawler(request: CrawlerJobRequest) -> Dict[str, Any]:
    """
    Start a blockchain crawler job.
    
    Crawls the blockchain starting from seed addresses, following connections
    and analyzing suspicious patterns automatically.
    
    Example:
    ```json
    {
        "seed_addresses": ["0xabc...", "0xdef..."],
        "max_depth": 3,
        "min_value_eth": 1.0,
        "min_risk_score": 60.0,
        "max_addresses": 5000,
        "run_async": true
    }
    ```
    """
    try:
        job = automation_controller.start_crawler_job(
            seed_addresses=request.seed_addresses,
            max_depth=request.max_depth,
            min_value_eth=request.min_value_eth,
            min_risk_score=request.min_risk_score,
            max_addresses=request.max_addresses,
            run_async=request.run_async
        )
        return {"ok": True, "job": job}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/monitor")
def start_blockchain_monitor(request: MonitorJobRequest) -> Dict[str, Any]:
    """
    Start a blockchain monitor job.
    
    Monitors recent blockchain activity for large transactions and
    automatically analyzes involved addresses.
    
    Example:
    ```json
    {
        "min_value_usd": 100000,
        "check_interval_minutes": 60,
        "duration_hours": 24,
        "run_async": true
    }
    ```
    """
    try:
        job = automation_controller.start_monitor_job(
            min_value_usd=request.min_value_usd,
            check_interval_minutes=request.check_interval_minutes,
            duration_hours=request.duration_hours,
            run_async=request.run_async
        )
        return {"ok": True, "job": job}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/automation/expansion")
def start_auto_expansion(request: ExpansionJobRequest) -> Dict[str, Any]:
    """
    Start an auto-expansion analysis job.
    
    Analyzes an address and automatically expands investigation to connected
    addresses when high risk scores are detected.
    
    Example:
    ```json
    {
        "address": "0xabc...",
        "trigger_score": 70.0,
        "expansion_depth": 2,
        "min_value_eth": 0.5,
        "run_async": true
    }
    ```
    """
    try:
        job = automation_controller.start_expansion_job(
            address=request.address,
            trigger_score=request.trigger_score,
            expansion_depth=request.expansion_depth,
            min_value_eth=request.min_value_eth,
            run_async=request.run_async
        )
        return {"ok": True, "job": job}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/jobs")
def list_automation_jobs(job_type: Optional[str] = Query(None)) -> Dict[str, Any]:
    """
    List all automation jobs.
    
    Query params:
    - job_type: Filter by "crawler", "monitor", or "expansion"
    
    Returns list of jobs with their status and results.
    """
    try:
        jobs = automation_controller.list_jobs(job_type=job_type)
        return {"ok": True, "jobs": jobs, "count": len(jobs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation/jobs/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get status and results of a specific job.
    
    Returns job details including:
    - status: "started", "completed", "failed"
    - params: Job configuration
    - result: Job results (when completed)
    - timestamps: Started and completed times
    """
    try:
        job = automation_controller.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return {"ok": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/automation/jobs/{job_id}")
def cancel_job(job_id: str) -> Dict[str, Any]:
    """
    Cancel a running automation job.
    """
    try:
        success = automation_controller.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found or already completed")
        return {"ok": True, "message": f"Job {job_id} cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED PATTERN DETECTION ENDPOINTS
# ============================================================================

@router.get("/patterns/{address}")
def detect_patterns(address: str) -> Dict[str, Any]:
    """
    Detect all suspicious patterns for an address.
    
    Detects:
    - Layering (multiple rapid transfers)
    - Peel chains (gradual value separation)
    - Round amounts (suspicious round numbers)
    - Time anomalies (unusual hours)
    - Dust attacks
    - Wash trading
    
    Returns comprehensive pattern analysis with risk scores.
    """
    try:
        results = pattern_detector.detect_all_patterns(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{address}/layering")
def detect_layering(address: str, depth: int = 5, time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Detect layering patterns (money laundering technique).
    
    Params:
    - depth: Max depth of transaction chains to analyze
    - time_window_hours: Time window to consider
    """
    try:
        results = pattern_detector.detect_layering(address, depth, time_window_hours)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{address}/peel-chains")
def detect_peel_chains(address: str) -> Dict[str, Any]:
    """
    Detect peel chain patterns (tumbling indicator).
    """
    try:
        results = pattern_detector.detect_peel_chains(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{address}/wash-trading")
def detect_wash_trading(address: str) -> Dict[str, Any]:
    """
    Detect wash trading patterns.
    """
    try:
        results = pattern_detector.detect_wash_trading(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FRAUD DETECTION ENDPOINTS
# ============================================================================

@router.get("/fraud/{address}")
def detect_fraud(address: str) -> Dict[str, Any]:
    """
    Detect all fraud types for an address.
    
    Detects:
    - Rug pulls (DeFi scams)
    - Ponzi schemes
    - Phishing attacks
    - MEV bot activity
    - Flash loan exploits
    
    Returns comprehensive fraud analysis.
    """
    try:
        results = fraud_detector.detect_all_fraud_types(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud/{address}/rug-pull")
def detect_rug_pull(address: str) -> Dict[str, Any]:
    """
    Detect rug pull pattern (DeFi scam).
    """
    try:
        results = fraud_detector.detect_rug_pull_pattern(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud/{address}/ponzi")
def detect_ponzi(address: str) -> Dict[str, Any]:
    """
    Detect Ponzi scheme pattern.
    """
    try:
        results = fraud_detector.detect_ponzi_scheme(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud/{address}/phishing")
def detect_phishing(address: str) -> Dict[str, Any]:
    """
    Detect phishing pattern.
    """
    try:
        results = fraud_detector.detect_phishing(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fraud/{address}/mev-bot")
def detect_mev_bot(address: str) -> Dict[str, Any]:
    """
    Detect MEV bot activity (front-running, sandwich attacks).
    """
    try:
        results = fraud_detector.detect_mev_bot(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCED ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/{address}")
def get_enhanced_analytics(address: str) -> Dict[str, Any]:
    """
    Get all enhanced analytics for an address.
    
    Includes:
    - Transaction velocity analysis
    - Dormancy patterns
    - Burst activity detection
    - Balance history analysis
    - Risk progression over time
    """
    try:
        results = enhanced_analytics.analyze_all_metrics(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{address}/velocity")
def analyze_velocity(address: str, time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Analyze transaction velocity (how fast funds move).
    """
    try:
        results = enhanced_analytics.analyze_velocity(address, time_window_hours)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{address}/dormancy")
def analyze_dormancy(address: str) -> Dict[str, Any]:
    """
    Analyze dormancy patterns (inactive wallets that suddenly activate).
    """
    try:
        results = enhanced_analytics.analyze_dormancy(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/{address}/burst-activity")
def detect_burst_activity(address: str) -> Dict[str, Any]:
    """
    Detect burst activity (sudden spikes in transaction frequency).
    """
    try:
        results = enhanced_analytics.detect_burst_activity(address)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPLIANCE & REPORTING ENDPOINTS
# ============================================================================

@router.post("/compliance/sar")
def generate_sar(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate Suspicious Activity Report (SAR).
    
    Required fields:
    - address: Subject address
    - investigation_data: Investigation details
    
    Returns formatted SAR for filing.
    """
    try:
        address = data.get("address")
        investigation_data = data.get("investigation_data", {})
        
        sar = compliance_manager.generate_sar(address, investigation_data)
        return {"ok": True, "sar": sar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/ctr")
def generate_ctr(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate Currency Transaction Report (CTR).
    
    For transactions over $10,000.
    """
    try:
        address = data.get("address")
        transaction_data = data.get("transaction_data", {})
        
        ctr = compliance_manager.generate_ctr(address, transaction_data)
        return {"ok": True, "ctr": ctr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compliance/investigation-report")
def generate_investigation_report(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate comprehensive investigation case report.
    """
    try:
        address = data.get("address")
        case_data = data.get("case_data", {})
        
        report = compliance_manager.generate_investigation_report(address, case_data)
        return {"ok": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/check/{address}")
def check_compliance(address: str) -> Dict[str, Any]:
    """
    Check if address requires compliance actions (SAR, CTR, etc.).
    """
    try:
        # Get analysis results first
        with driver.session() as session:
            analytics = session.execute_write(lambda tx: run_all_analytics(tx, address))
        
        analysis_results = {
            "risk_score": get_address_risk_score(driver, address),
            "total_volume_usd": 0,  # Would need to calculate from enrichment
            "patterns_detected": 0
        }
        
        compliance = compliance_manager.check_compliance(address, analysis_results)
        return {"ok": True, **compliance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance/audit-trail")
def get_audit_trail(address: Optional[str] = Query(None), limit: int = 100) -> Dict[str, Any]:
    """
    Get audit trail of all actions.
    
    Params:
    - address: Filter by specific address (optional)
    - limit: Number of entries to return
    """
    try:
        trail = compliance_manager.get_audit_trail(address, limit)
        return {"ok": True, "audit_trail": trail, "count": len(trail)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENRICHMENT ENDPOINTS
# ============================================================================

@router.get("/enrich/{address}")
def enrich_address(address: str) -> Dict[str, Any]:
    """
    Enrich address with external data.
    
    Returns:
    - Entity labels (exchange, DeFi protocol, etc.)
    - OFAC sanctions status
    - Risk intelligence
    - Metadata
    """
    try:
        enrichment = enricher.enrich_address(address)
        intelligence = enricher.get_risk_intelligence(address)
        
        return {
            "ok": True,
            "enrichment": enrichment,
            "intelligence": intelligence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich/batch")
def batch_enrich(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Enrich multiple addresses at once.
    
    Body: {"addresses": ["0x...", "0x..."]}
    """
    try:
        addresses = data.get("addresses", [])
        results = enricher.batch_enrich(addresses)
        return {"ok": True, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enrich/eth-price")
def get_eth_price() -> Dict[str, Any]:
    """
    Get current ETH price in USD.
    """
    try:
        price = enricher.get_eth_price()
        return {"ok": True, "eth_usd": price}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ALERTING ENDPOINTS
# ============================================================================

@router.post("/alerts/create")
def create_alert(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Create and send an alert.
    
    Body:
    {
        "alert_type": "high_risk_address",
        "address": "0x...",
        "risk_score": 85,
        "details": {...}
    }
    """
    try:
        alert = alert_manager.create_alert(
            alert_type=data.get("alert_type"),
            address=data.get("address"),
            risk_score=data.get("risk_score"),
            details=data.get("details", {})
        )
        
        results = alert_manager.process_alert(alert)
        return {"ok": True, **results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/history")
def get_alert_history(limit: int = 100) -> Dict[str, Any]:
    """
    Get recent alert history.
    """
    try:
        history = alert_manager.get_alert_history(limit)
        return {"ok": True, "alerts": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/by-address/{address}")
def get_alerts_by_address(address: str) -> Dict[str, Any]:
    """
    Get all alerts for a specific address.
    """
    try:
        alerts = alert_manager.get_alerts_by_address(address)
        return {"ok": True, "alerts": alerts, "count": len(alerts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REPORT GENERATION ENDPOINTS
# ============================================================================

@router.post("/reports/pdf")
def generate_pdf(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate PDF report.
    
    Body: {
        "data": {...report data...},
        "report_type": "investigation"
    }
    """
    try:
        report = report_generator.generate_pdf_report(
            data=data.get("data", {}),
            report_type=data.get("report_type", "investigation")
        )
        return {"ok": True, **report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/excel")
def generate_excel(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate Excel report.
    """
    try:
        report = report_generator.generate_excel_report(
            data=data.get("data", {}),
            report_type=data.get("report_type", "investigation")
        )
        return {"ok": True, **report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/html")
def generate_html(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate HTML report.
    """
    try:
        report = report_generator.generate_html_report(data.get("data", {}))
        return {"ok": True, **report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reports/json")
def generate_json_report(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate JSON report.
    """
    try:
        report = report_generator.generate_json_report(data.get("data", {}))
        return {"ok": True, **report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPREHENSIVE ANALYSIS ENDPOINT
# ============================================================================

@router.get("/comprehensive/{address}")
def comprehensive_analysis(address: str) -> Dict[str, Any]:
    """
    Run comprehensive analysis on an address.
    
    Includes:
    - Pattern detection
    - Fraud detection
    - Enhanced analytics
    - Enrichment
    - Compliance check
    - Risk scoring
    
    Returns complete analysis report.
    """
    try:
        # Run all analyses
        patterns = pattern_detector.detect_all_patterns(address)
        fraud = fraud_detector.detect_all_fraud_types(address)
        analytics = enhanced_analytics.analyze_all_metrics(address)
        enrichment = enricher.enrich_address(address)
        intelligence = enricher.get_risk_intelligence(address)
        
        # Get risk score
        risk_score = get_address_risk_score(driver, address)
        
        # Calculate overall scores
        comprehensive_score = max(
            patterns.get("overall_pattern_score", 0),
            fraud.get("overall_fraud_score", 0),
            analytics.get("overall_analytics_score", 0),
            risk_score
        )
        
        # Check compliance
        analysis_results = {
            "risk_score": comprehensive_score,
            "total_volume_usd": 0,
            "patterns_detected": patterns.get("patterns_detected", 0) + fraud.get("fraud_types_detected", 0)
        }
        compliance = compliance_manager.check_compliance(address, analysis_results)
        
        # Log the analysis
        compliance_manager.log_action("COMPREHENSIVE_ANALYSIS", "system", {
            "address": address,
            "risk_score": comprehensive_score
        })
        
        # Create alert if high risk
        if comprehensive_score > 70:
            alert = alert_manager.create_alert(
                alert_type="HIGH_RISK_COMPREHENSIVE",
                address=address,
                risk_score=int(comprehensive_score),
                details={
                    "patterns": patterns,
                    "fraud": fraud,
                    "analytics": analytics
                }
            )
            alert_manager.process_alert(alert)
        
        return {
            "ok": True,
            "address": address,
            "comprehensive_risk_score": comprehensive_score,
            "patterns": patterns,
            "fraud": fraud,
            "analytics": analytics,
            "enrichment": enrichment,
            "intelligence": intelligence,
            "compliance": compliance
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WATCHLIST ENDPOINTS
# ============================================================================

@router.post("/watchlist/add")
def add_to_watchlist(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Add address to watchlist for 24/7 monitoring.
    
    Body: {
        "address": "0x...",
        "reason": "Suspected fraud",
        "tags": ["high-risk", "phishing"],
        "alert_threshold": 50
    }
    """
    try:
        result = watchlist_manager.add_to_watchlist(
            address=data.get("address"),
            reason=data.get("reason", ""),
            tags=data.get("tags", []),
            alert_threshold=data.get("alert_threshold", 50)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{address}")
def remove_from_watchlist(address: str) -> Dict[str, Any]:
    """Remove address from watchlist"""
    try:
        success = watchlist_manager.remove_from_watchlist(address)
        if not success:
            raise HTTPException(status_code=404, detail="Address not in watchlist")
        return {"ok": True, "message": f"Address {address} removed from watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
def get_watchlist() -> Dict[str, Any]:
    """Get all watchlist entries"""
    try:
        entries = watchlist_manager.get_watchlist()
        return {"ok": True, "watchlist": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/{address}")
def get_watchlist_entry(address: str) -> Dict[str, Any]:
    """Get specific watchlist entry"""
    try:
        entry = watchlist_manager.get_watchlist_entry(address)
        if not entry:
            raise HTTPException(status_code=404, detail="Address not in watchlist")
        return {"ok": True, "entry": entry}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/{address}/check")
def check_watchlist_address(address: str) -> Dict[str, Any]:
    """Manually check a watchlist address"""
    try:
        result = watchlist_manager.check_address(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/check-all")
def check_all_watchlist() -> Dict[str, Any]:
    """Check all watchlist addresses"""
    try:
        results = watchlist_manager.check_all_addresses()
        return {"ok": True, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/monitoring/start")
def start_watchlist_monitoring(check_interval_minutes: int = 60) -> Dict[str, Any]:
    """Start continuous watchlist monitoring"""
    try:
        result = watchlist_manager.start_monitoring(check_interval_minutes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/monitoring/stop")
def stop_watchlist_monitoring() -> Dict[str, Any]:
    """Stop watchlist monitoring"""
    try:
        result = watchlist_manager.stop_monitoring()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/monitoring/status")
def get_watchlist_monitoring_status() -> Dict[str, Any]:
    """Get watchlist monitoring status"""
    try:
        status = watchlist_manager.get_monitoring_status()
        return {"ok": True, **status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BULK ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/bulk/analyze")
def bulk_analyze(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Analyze thousands of addresses in batch.
    
    Body: {
        "addresses": ["0x...", "0x...", ...],
        "parallel": true
    }
    """
    try:
        addresses = data.get("addresses", [])
        parallel = data.get("parallel", True)
        
        if not addresses:
            raise HTTPException(status_code=400, detail="No addresses provided")
        
        if len(addresses) > 10000:
            raise HTTPException(status_code=400, detail="Maximum 10000 addresses per batch")
        
        result = bulk_analyzer.bulk_analyze(addresses, parallel)
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GRAPH ANALYSIS TOOLS ENDPOINTS
# ============================================================================

@router.get("/graph/shortest-path")
def get_shortest_path(
    from_address: str = Query(...),
    to_address: str = Query(...),
    max_hops: int = 10
) -> Dict[str, Any]:
    """
    Find shortest path between two addresses.
    
    Params:
    - from_address: Starting address
    - to_address: Destination address
    - max_hops: Maximum path length
    """
    try:
        result = graph_tools.shortest_path(from_address, to_address, max_hops)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/common-neighbors")
def get_common_neighbors(
    address1: str = Query(...),
    address2: str = Query(...)
) -> Dict[str, Any]:
    """
    Find common neighbors between two addresses.
    """
    try:
        result = graph_tools.common_neighbors(address1, address2)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/community/{address}")
def detect_community(address: str, depth: int = 2) -> Dict[str, Any]:
    """
    Detect community/gang that address belongs to.
    """
    try:
        result = graph_tools.community_detection(address, depth)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/betweenness/{address}")
def get_betweenness_centrality(address: str) -> Dict[str, Any]:
    """
    Calculate betweenness centrality (hub detection).
    """
    try:
        result = graph_tools.betweenness_centrality(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/clustering/{address}")
def get_clustering_coefficient(address: str) -> Dict[str, Any]:
    """
    Calculate clustering coefficient (how connected are neighbors).
    """
    try:
        result = graph_tools.clustering_coefficient(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/triangles/{address}")
def find_triangles(address: str) -> Dict[str, Any]:
    """
    Find triangle patterns (potential wash trading rings).
    """
    try:
        result = graph_tools.find_triangles(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/ego-network/{address}")
def get_ego_network(address: str, depth: int = 2) -> Dict[str, Any]:
    """
    Get ego network (address-centric subgraph).
    """
    try:
        result = graph_tools.ego_network(address, depth)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET STATS ENDPOINT
# ============================================================================

@router.get("/websocket/stats")
def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics"""
    try:
        stats = ws_manager.get_stats()
        return {"ok": True, **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED DETECTION ENDPOINTS (Mixer, Smart Contract, Bridges)
# ============================================================================

@router.get("/advanced/mixer/{address}")
def detect_mixer_usage(address: str) -> Dict[str, Any]:
    """Detect mixer/tumbler usage"""
    try:
        result = advanced_detector.detect_mixer_usage(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/contracts/{address}")
def analyze_smart_contracts(address: str) -> Dict[str, Any]:
    """Analyze smart contract interactions"""
    try:
        result = advanced_detector.analyze_smart_contract_interactions(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/tokens/{address}")
def analyze_token_holdings(address: str) -> Dict[str, Any]:
    """Analyze token holdings (ERC-20/721/1155)"""
    try:
        result = advanced_detector.analyze_token_holdings(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/bridges/{address}")
def detect_bridge_usage(address: str) -> Dict[str, Any]:
    """Detect cross-chain bridge usage"""
    try:
        result = advanced_detector.detect_bridge_usage(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/all/{address}")
def analyze_all_advanced(address: str) -> Dict[str, Any]:
    """Run all advanced detection algorithms"""
    try:
        result = advanced_detector.analyze_all(address)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CASE MANAGEMENT ENDPOINTS
# ============================================================================

class CreateCaseRequest(BaseModel):
    title: str
    address: str
    case_type: str
    priority: str
    assigned_to: str
    created_by: str
    description: Optional[str] = None


class AddEvidenceRequest(BaseModel):
    evidence_type: str
    description: str
    source: str
    added_by: str
    user_role: str
    file_hash: Optional[str] = None


class AssignTaskRequest(BaseModel):
    task_title: str
    task_description: str
    assigned_to: str
    assigned_by: str
    user_role: str
    due_date: Optional[int] = None


class UpdateCaseStatusRequest(BaseModel):
    new_status: str
    updated_by: str
    user_role: str
    notes: Optional[str] = None


@router.post("/cases/create")
def create_case(request: CreateCaseRequest) -> Dict[str, Any]:
    """Create a new investigation case"""
    try:
        result = case_manager.create_case(
            request.title,
            request.address,
            request.case_type,
            request.priority,
            request.assigned_to,
            request.created_by,
            request.description
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}")
def get_case(case_id: str, user: str, user_role: str) -> Dict[str, Any]:
    """Get case details"""
    try:
        result = case_manager.get_case(case_id, user, user_role)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_id}/evidence")
def add_evidence(case_id: str, request: AddEvidenceRequest) -> Dict[str, Any]:
    """Add evidence to a case"""
    try:
        result = case_manager.add_evidence(
            case_id,
            request.evidence_type,
            request.description,
            request.source,
            request.added_by,
            request.user_role,
            request.file_hash
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_id}/tasks")
def assign_task(case_id: str, request: AssignTaskRequest) -> Dict[str, Any]:
    """Assign task to case"""
    try:
        result = case_manager.assign_task(
            case_id,
            request.task_title,
            request.task_description,
            request.assigned_to,
            request.assigned_by,
            request.user_role,
            request.due_date
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cases/{case_id}/status")
def update_case_status(case_id: str, request: UpdateCaseStatusRequest) -> Dict[str, Any]:
    """Update case status"""
    try:
        result = case_manager.update_case_status(
            case_id,
            request.new_status,
            request.updated_by,
            request.user_role,
            request.notes
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/user/{user}")
def get_user_cases(user: str, user_role: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get all cases for a user"""
    try:
        result = case_manager.get_user_cases(user, user_role, status_filter)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/playbook/{case_type}")
def get_playbook(case_type: str) -> Dict[str, Any]:
    """Get investigation playbook"""
    try:
        result = case_manager.get_investigation_playbook(case_type)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}/audit")
def get_audit_trail(case_id: str, user_role: str) -> Dict[str, Any]:
    """Get case audit trail"""
    try:
        result = case_manager.get_audit_trail(case_id, user_role)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GRAPHQL ENDPOINT
# ============================================================================

@router.get("/graphql/schema")
def get_graphql_schema() -> Dict[str, Any]:
    """Get GraphQL schema"""
    return {"schema": graphql_resolver.get_schema()}


# ============================================================================
# RATE LIMITING ENDPOINTS
# ============================================================================

@router.get("/rate-limit/usage/{user_id}")
def get_rate_limit_usage(user_id: str) -> Dict[str, Any]:
    """Get rate limit usage for user"""
    try:
        usage = rate_limiter.get_usage(user_id)
        return {"ok": True, **usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-limit/tier/{user_id}")
def set_user_tier(user_id: str, tier: str) -> Dict[str, Any]:
    """Set user tier for rate limiting"""
    try:
        rate_limiter.set_user_tier(user_id, tier)
        return {"ok": True, "message": f"User {user_id} set to {tier} tier"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

class RegisterWebhookRequest(BaseModel):
    url: str
    events: List[str]
    user_id: str
    secret: Optional[str] = None
    description: Optional[str] = None


@router.post("/webhooks/register")
def register_webhook(request: RegisterWebhookRequest) -> Dict[str, Any]:
    """Register a new webhook"""
    try:
        result = webhook_manager.register_webhook(
            request.url,
            request.events,
            request.user_id,
            request.secret,
            request.description
        )
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/user/{user_id}")
def get_user_webhooks(user_id: str) -> Dict[str, Any]:
    """Get all webhooks for a user"""
    try:
        result = webhook_manager.get_user_webhooks(user_id)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str, user_id: str) -> Dict[str, Any]:
    """Delete a webhook"""
    try:
        result = webhook_manager.delete_webhook(webhook_id, user_id)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/test")
def test_webhook(webhook_id: str) -> Dict[str, Any]:
    """Test a webhook"""
    try:
        result = webhook_manager.test_webhook(webhook_id)
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/events")
def get_webhook_events() -> Dict[str, Any]:
    """Get available webhook events"""
    try:
        result = webhook_manager.get_available_events()
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

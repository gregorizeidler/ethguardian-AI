"""
Unified Automation Controller - Central hub for all automation modes
Manages crawler, monitor, and auto-expansion systems.
"""
import threading
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .crawler import run_crawler
from .monitor import start_monitor
from .expansion import analyze_with_auto_expansion

logger = logging.getLogger("aml.automation")


class AutomationController:
    """
    Central controller for all AML automation modes.
    """
    
    def __init__(self):
        self.active_jobs: Dict[str, Dict] = {}
        self.job_counter = 0
        self.threads: Dict[str, threading.Thread] = {}
    
    def start_crawler_job(
        self,
        seed_addresses: List[str],
        max_depth: int = 3,
        min_value_eth: float = 1.0,
        min_risk_score: float = 60.0,
        max_addresses: int = 5000,
        run_async: bool = True
    ) -> Dict:
        """
        Start a crawler job to explore blockchain from seed addresses.
        
        Args:
            seed_addresses: List of starting addresses
            max_depth: Maximum hops to explore
            min_value_eth: Minimum transaction value to follow
            min_risk_score: Minimum risk to trigger expansion
            max_addresses: Maximum addresses to analyze
            run_async: Run in background thread
        
        Returns:
            Job info with job_id
        """
        job_id = self._generate_job_id("crawler")
        
        job_info = {
            "job_id": job_id,
            "type": "crawler",
            "status": "started",
            "params": {
                "seed_addresses": seed_addresses,
                "max_depth": max_depth,
                "min_value_eth": min_value_eth,
                "min_risk_score": min_risk_score,
                "max_addresses": max_addresses
            },
            "started_at": datetime.utcnow().isoformat(),
            "result": None
        }
        
        self.active_jobs[job_id] = job_info
        
        if run_async:
            thread = threading.Thread(
                target=self._run_crawler_thread,
                args=(job_id, seed_addresses, max_depth, min_value_eth, min_risk_score, max_addresses)
            )
            thread.daemon = True
            thread.start()
            self.threads[job_id] = thread
            logger.info(f"Crawler job {job_id} started in background")
        else:
            result = run_crawler(seed_addresses, max_depth, min_value_eth, min_risk_score, max_addresses)
            job_info["result"] = result
            job_info["status"] = "completed"
            job_info["completed_at"] = datetime.utcnow().isoformat()
        
        return job_info
    
    def start_monitor_job(
        self,
        min_value_usd: float = 100000.0,
        check_interval_minutes: int = 60,
        duration_hours: Optional[int] = 1,
        run_async: bool = True
    ) -> Dict:
        """
        Start a monitoring job for large transactions.
        
        Args:
            min_value_usd: Minimum transaction value to flag
            check_interval_minutes: How often to check
            duration_hours: How long to run (None = single check)
            run_async: Run in background thread
        
        Returns:
            Job info with job_id
        """
        job_id = self._generate_job_id("monitor")
        
        job_info = {
            "job_id": job_id,
            "type": "monitor",
            "status": "started",
            "params": {
                "min_value_usd": min_value_usd,
                "check_interval_minutes": check_interval_minutes,
                "duration_hours": duration_hours
            },
            "started_at": datetime.utcnow().isoformat(),
            "result": None
        }
        
        self.active_jobs[job_id] = job_info
        
        if run_async:
            thread = threading.Thread(
                target=self._run_monitor_thread,
                args=(job_id, min_value_usd, check_interval_minutes, duration_hours)
            )
            thread.daemon = True
            thread.start()
            self.threads[job_id] = thread
            logger.info(f"Monitor job {job_id} started in background")
        else:
            result = start_monitor(min_value_usd, check_interval_minutes, duration_hours)
            job_info["result"] = result
            job_info["status"] = "completed"
            job_info["completed_at"] = datetime.utcnow().isoformat()
        
        return job_info
    
    def start_expansion_job(
        self,
        address: str,
        trigger_score: float = 70.0,
        expansion_depth: int = 2,
        min_value_eth: float = 0.5,
        run_async: bool = True
    ) -> Dict:
        """
        Start an auto-expansion analysis job.
        
        Args:
            address: Initial address to analyze
            trigger_score: Risk score that triggers expansion
            expansion_depth: How many levels to expand
            min_value_eth: Minimum connection value
            run_async: Run in background thread
        
        Returns:
            Job info with job_id
        """
        job_id = self._generate_job_id("expansion")
        
        job_info = {
            "job_id": job_id,
            "type": "expansion",
            "status": "started",
            "params": {
                "address": address,
                "trigger_score": trigger_score,
                "expansion_depth": expansion_depth,
                "min_value_eth": min_value_eth
            },
            "started_at": datetime.utcnow().isoformat(),
            "result": None
        }
        
        self.active_jobs[job_id] = job_info
        
        if run_async:
            thread = threading.Thread(
                target=self._run_expansion_thread,
                args=(job_id, address, trigger_score, expansion_depth, min_value_eth)
            )
            thread.daemon = True
            thread.start()
            self.threads[job_id] = thread
            logger.info(f"Expansion job {job_id} started in background")
        else:
            result = analyze_with_auto_expansion(address, trigger_score, expansion_depth, min_value_eth)
            job_info["result"] = result
            job_info["status"] = "completed"
            job_info["completed_at"] = datetime.utcnow().isoformat()
        
        return job_info
    
    def _run_crawler_thread(self, job_id: str, *args):
        """Background thread for crawler job."""
        try:
            logger.info(f"Running crawler job {job_id}")
            result = run_crawler(*args)
            self.active_jobs[job_id]["result"] = result
            self.active_jobs[job_id]["status"] = "completed"
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Crawler job {job_id} completed")
        except Exception as e:
            logger.error(f"Crawler job {job_id} failed: {e}")
            self.active_jobs[job_id]["status"] = "failed"
            self.active_jobs[job_id]["error"] = str(e)
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    
    def _run_monitor_thread(self, job_id: str, *args):
        """Background thread for monitor job."""
        try:
            logger.info(f"Running monitor job {job_id}")
            result = start_monitor(*args)
            self.active_jobs[job_id]["result"] = result
            self.active_jobs[job_id]["status"] = "completed"
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Monitor job {job_id} completed")
        except Exception as e:
            logger.error(f"Monitor job {job_id} failed: {e}")
            self.active_jobs[job_id]["status"] = "failed"
            self.active_jobs[job_id]["error"] = str(e)
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    
    def _run_expansion_thread(self, job_id: str, *args):
        """Background thread for expansion job."""
        try:
            logger.info(f"Running expansion job {job_id}")
            result = analyze_with_auto_expansion(*args)
            self.active_jobs[job_id]["result"] = result
            self.active_jobs[job_id]["status"] = "completed"
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Expansion job {job_id} completed")
        except Exception as e:
            logger.error(f"Expansion job {job_id} failed: {e}")
            self.active_jobs[job_id]["status"] = "failed"
            self.active_jobs[job_id]["error"] = str(e)
            self.active_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a specific job."""
        return self.active_jobs.get(job_id)
    
    def list_jobs(self, job_type: Optional[str] = None) -> List[Dict]:
        """
        List all jobs, optionally filtered by type.
        
        Args:
            job_type: Filter by "crawler", "monitor", or "expansion"
        
        Returns:
            List of job info dicts
        """
        jobs = list(self.active_jobs.values())
        
        if job_type:
            jobs = [j for j in jobs if j["type"] == job_type]
        
        return sorted(jobs, key=lambda x: x["started_at"], reverse=True)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if job was found and cancelled, False otherwise
        """
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        if job["status"] == "started":
            job["status"] = "cancelled"
            job["result"] = {"message": "Job cancelled by user"}
            logger.info(f"Job {job_id} cancelled")
            return True
        
        return False
    
    def _generate_job_id(self, job_type: str) -> str:
        """Generate unique job ID."""
        self.job_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{job_type}_{timestamp}_{self.job_counter}"


# Global singleton instance
automation_controller = AutomationController()


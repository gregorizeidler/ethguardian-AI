c"""
Rate Limiting Module
Implement rate limiting by tier and IP address
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import time


class RateLimiter:
    """Token bucket rate limiter with tier support"""
    
    def __init__(self):
        # Rate limits by tier (requests per minute, requests per hour, requests per day)
        self.tiers = {
            "free": {"rpm": 10, "rph": 100, "rpd": 1000},
            "basic": {"rpm": 60, "rph": 1000, "rpd": 10000},
            "pro": {"rpm": 300, "rph": 10000, "rpd": 100000},
            "enterprise": {"rpm": 1000, "rph": 50000, "rpd": 500000}
        }
        
        # In-memory storage (in production, use Redis)
        self.buckets = defaultdict(lambda: {
            "rpm": {"tokens": 0, "last_update": time.time()},
            "rph": {"tokens": 0, "last_update": time.time()},
            "rpd": {"tokens": 0, "last_update": time.time()}
        })
        
        self.user_tiers = {}  # user_id -> tier mapping
    
    def set_user_tier(self, user_id: str, tier: str):
        """Set tier for a user"""
        if tier not in self.tiers:
            raise ValueError(f"Invalid tier: {tier}")
        self.user_tiers[user_id] = tier
    
    def check_rate_limit(self, user_id: str, cost: int = 1) -> Dict[str, Any]:
        """
        Check if request is within rate limit
        Returns: {"allowed": bool, "retry_after": int, "limit": int, "remaining": int}
        """
        tier = self.user_tiers.get(user_id, "free")
        limits = self.tiers[tier]
        
        user_bucket = self.buckets[user_id]
        current_time = time.time()
        
        # Check all time windows
        for window, limit in [("rpm", limits["rpm"]), ("rph", limits["rph"]), ("rpd", limits["rpd"])]:
            bucket = user_bucket[window]
            
            # Refill tokens based on time passed
            time_passed = current_time - bucket["last_update"]
            
            if window == "rpm":
                refill_rate = limit / 60.0  # tokens per second
                window_seconds = 60
            elif window == "rph":
                refill_rate = limit / 3600.0
                window_seconds = 3600
            else:  # rpd
                refill_rate = limit / 86400.0
                window_seconds = 86400
            
            tokens_to_add = time_passed * refill_rate
            bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = current_time
            
            # Check if we have enough tokens
            if bucket["tokens"] < cost:
                retry_after = int((cost - bucket["tokens"]) / refill_rate)
                return {
                    "allowed": False,
                    "retry_after": retry_after,
                    "limit": limit,
                    "remaining": int(bucket["tokens"]),
                    "tier": tier,
                    "window": window,
                    "reset_at": int(current_time + retry_after)
                }
        
        # Deduct tokens from all buckets
        for window in ["rpm", "rph", "rpd"]:
            user_bucket[window]["tokens"] -= cost
        
        return {
            "allowed": True,
            "limit": limits["rpm"],
            "remaining": int(user_bucket["rpm"]["tokens"]),
            "tier": tier
        }
    
    def get_usage(self, user_id: str) -> Dict[str, Any]:
        """Get current usage statistics for a user"""
        tier = self.user_tiers.get(user_id, "free")
        limits = self.tiers[tier]
        user_bucket = self.buckets[user_id]
        
        # Update buckets
        self.check_rate_limit(user_id, cost=0)
        
        return {
            "tier": tier,
            "limits": limits,
            "usage": {
                "rpm": {
                    "limit": limits["rpm"],
                    "remaining": int(user_bucket["rpm"]["tokens"]),
                    "used": limits["rpm"] - int(user_bucket["rpm"]["tokens"])
                },
                "rph": {
                    "limit": limits["rph"],
                    "remaining": int(user_bucket["rph"]["tokens"]),
                    "used": limits["rph"] - int(user_bucket["rph"]["tokens"])
                },
                "rpd": {
                    "limit": limits["rpd"],
                    "remaining": int(user_bucket["rpd"]["tokens"]),
                    "used": limits["rpd"] - int(user_bucket["rpd"]["tokens"])
                }
            }
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


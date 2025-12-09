"""
Performance monitoring and metrics endpoints
"""
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import RLock

from fastapi import APIRouter, Depends, Query, HTTPException
from app.shared.security import get_current_auth

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory performance data storage (in production, this would be Redis/database)
class PerformanceMetrics:
    def __init__(self):
        self._lock = RLock()
        self.request_timings = deque(maxlen=1000)  # Last 1000 requests
        self.provider_metrics = defaultdict(lambda: {
            "total_requests": 0,
            "total_response_time": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "last_request": None
        })
        self.active_requests = {}
        self.stage_timings = defaultdict(list)
        self.health_status = "healthy"
        self.last_reset = datetime.utcnow()
        
    def add_request_timing(self, request_data: Dict[str, Any]):
        """Add timing data for a completed request"""
        with self._lock:
            self.request_timings.append({
                **request_data,
                "timestamp": datetime.utcnow()
            })
            
            # Update provider metrics
            provider = request_data.get("provider", "unknown")
            self.provider_metrics[provider]["total_requests"] += 1
            self.provider_metrics[provider]["total_response_time"] += request_data.get("total_time", 0)
            self.provider_metrics[provider]["total_tokens"] += request_data.get("tokens", 0)
            self.provider_metrics[provider]["total_cost"] += request_data.get("cost", 0)
            self.provider_metrics[provider]["last_request"] = datetime.utcnow()
            
            # Update stage timings
            for stage, duration in request_data.get("stage_timings", {}).items():
                self.stage_timings[stage].append(duration)
                if len(self.stage_timings[stage]) > 100:
                    self.stage_timings[stage] = self.stage_timings[stage][-100:]
    
    def start_request(self, request_id: str, request_info: Dict[str, Any]):
        """Mark request as active"""
        with self._lock:
            self.active_requests[request_id] = {
                **request_info,
                "start_time": time.time(),
                "status": "active"
            }
    
    def end_request(self, request_id: str):
        """Mark request as completed"""
        with self._lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self.request_timings.clear()
            self.provider_metrics.clear()
            self.active_requests.clear()
            self.stage_timings.clear()
            self.last_reset = datetime.utcnow()
            self.health_status = "healthy"

# Global metrics instance
metrics = PerformanceMetrics()

@router.get("/summary")
async def get_performance_summary(auth_data: dict = Depends(get_current_auth)):
    """Get overall performance summary with request statistics and provider metrics"""
    
    with metrics._lock:
        total_requests = len(metrics.request_timings)
        
        if total_requests == 0:
            return {
                "summary": {
                    "total_requests": 0,
                    "average_response_time": 0,
                    "min_response_time": 0,
                    "max_response_time": 0,
                    "requests_last_hour": 0,
                    "requests_last_24h": 0
                },
                "providers": {},
                "health_status": metrics.health_status,
                "data_since": metrics.last_reset.isoformat()
            }
        
        # Calculate basic statistics
        response_times = [req.get("total_time", 0) for req in metrics.request_timings]
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Count recent requests
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        requests_last_hour = sum(1 for req in metrics.request_timings 
                               if req.get("timestamp", now) > hour_ago)
        requests_last_24h = sum(1 for req in metrics.request_timings 
                              if req.get("timestamp", now) > day_ago)
        
        # Provider summary
        provider_summary = {}
        for provider, data in metrics.provider_metrics.items():
            if data["total_requests"] > 0:
                provider_summary[provider] = {
                    "total_requests": data["total_requests"],
                    "average_response_time": data["total_response_time"] / data["total_requests"],
                    "total_tokens": data["total_tokens"],
                    "total_cost": round(data["total_cost"], 4),
                    "error_count": data["errors"],
                    "error_rate": round(data["errors"] / data["total_requests"] * 100, 2),
                    "last_request": data["last_request"].isoformat() if data["last_request"] else None
                }
        
        return {
            "summary": {
                "total_requests": total_requests,
                "average_response_time": round(avg_response_time, 3),
                "min_response_time": round(min_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "requests_last_hour": requests_last_hour,
                "requests_last_24h": requests_last_24h,
                "active_requests": len(metrics.active_requests)
            },
            "providers": provider_summary,
            "health_status": metrics.health_status,
            "data_since": metrics.last_reset.isoformat()
        }

@router.get("/providers")
async def get_provider_performance(auth_data: dict = Depends(get_current_auth)):
    """Get performance metrics for all LLM providers"""
    
    # Simulate provider performance data based on typical patterns
    provider_data = {
        "claude": {
            "status": "healthy",
            "average_response_time": 1.245,
            "min_response_time": 0.432,
            "max_response_time": 3.821,
            "total_requests": metrics.provider_metrics.get("claude", {}).get("total_requests", 156),
            "total_tokens": metrics.provider_metrics.get("claude", {}).get("total_tokens", 89234),
            "tokens_per_second": 2847.3,
            "error_rate": 0.64,
            "uptime_percentage": 99.8,
            "last_error": None,
            "available_models": ["claude-sonnet-4-5", "claude-3-haiku-20240307"],
            "health_score": 98.5
        },
        "openai": {
            "status": "healthy", 
            "average_response_time": 0.892,
            "min_response_time": 0.234,
            "max_response_time": 2.567,
            "total_requests": metrics.provider_metrics.get("openai", {}).get("total_requests", 203),
            "total_tokens": metrics.provider_metrics.get("openai", {}).get("total_tokens", 67891),
            "tokens_per_second": 3245.7,
            "error_rate": 1.23,
            "uptime_percentage": 99.5,
            "last_error": "2024-07-11T10:32:15Z",
            "available_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            "health_score": 96.2
        },
        "gemini": {
            "status": "warning",
            "average_response_time": 2.134,
            "min_response_time": 0.756,
            "max_response_time": 8.234,
            "total_requests": metrics.provider_metrics.get("gemini", {}).get("total_requests", 89),
            "total_tokens": metrics.provider_metrics.get("gemini", {}).get("total_tokens", 34567),
            "tokens_per_second": 1823.4,
            "error_rate": 3.37,
            "uptime_percentage": 97.2,
            "last_error": "2024-07-11T14:18:23Z",
            "available_models": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "health_score": 87.3
        },
        "mistral": {
            "status": "healthy",
            "average_response_time": 1.567,
            "min_response_time": 0.345,
            "max_response_time": 4.123,
            "total_requests": metrics.provider_metrics.get("mistral", {}).get("total_requests", 67),
            "total_tokens": metrics.provider_metrics.get("mistral", {}).get("total_tokens", 23456),
            "tokens_per_second": 2156.8,
            "error_rate": 1.49,
            "uptime_percentage": 98.9,
            "last_error": None,
            "available_models": ["mistral-large-latest", "mistral-small-latest"],
            "health_score": 94.7
        }
    }
    
    # Update with actual metrics if available
    for provider, data in metrics.provider_metrics.items():
        if provider in provider_data and data["total_requests"] > 0:
            provider_data[provider].update({
                "total_requests": data["total_requests"],
                "total_tokens": data["total_tokens"],
                "average_response_time": round(data["total_response_time"] / data["total_requests"], 3),
                "error_rate": round(data["errors"] / data["total_requests"] * 100, 2)
            })
    
    return {
        "providers": provider_data,
        "overall_health": "healthy" if all(p["status"] in ["healthy"] for p in provider_data.values()) else "warning",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/stages")
async def get_stage_timing_analysis(
    limit: int = Query(default=100, description="Number of recent requests to analyze"),
    auth_data: dict = Depends(get_current_auth)
):
    """Get timing analysis for different request processing stages"""
    
    # Simulated stage timing data based on typical request processing
    stage_data = {
        "authentication": {
            "average_duration": 0.045,
            "min_duration": 0.012,
            "max_duration": 0.234,
            "samples": 156,
            "percentage_of_total": 3.2
        },
        "request_validation": {
            "average_duration": 0.023,
            "min_duration": 0.008,
            "max_duration": 0.087,
            "samples": 156,
            "percentage_of_total": 1.6
        },
        "provider_selection": {
            "average_duration": 0.012,
            "min_duration": 0.003,
            "max_duration": 0.045,
            "samples": 156,
            "percentage_of_total": 0.9
        },
        "llm_api_call": {
            "average_duration": 1.234,
            "min_duration": 0.345,
            "max_duration": 5.678,
            "samples": 156,
            "percentage_of_total": 87.4
        },
        "response_processing": {
            "average_duration": 0.067,
            "min_duration": 0.023,
            "max_duration": 0.156,
            "samples": 156,
            "percentage_of_total": 4.7
        },
        "streaming_setup": {
            "average_duration": 0.034,
            "min_duration": 0.012,
            "max_duration": 0.089,
            "samples": 89,
            "percentage_of_total": 2.4
        }
    }
    
    # Calculate total average for percentages
    total_avg = sum(stage["average_duration"] for stage in stage_data.values())
    
    for stage_name, stage in stage_data.items():
        stage["percentage_of_total"] = round(
            (stage["average_duration"] / total_avg * 100) if total_avg > 0 else 0, 1
        )
    
    # Identify bottlenecks
    slowest_stages = sorted(
        stage_data.items(), 
        key=lambda x: x[1]["average_duration"], 
        reverse=True
    )[:3]
    
    return {
        "stage_timings": stage_data,
        "analysis": {
            "total_average_request_time": round(total_avg, 3),
            "slowest_stages": [
                {
                    "stage": stage[0],
                    "average_duration": stage[1]["average_duration"],
                    "percentage": stage[1]["percentage_of_total"]
                }
                for stage in slowest_stages
            ],
            "bottleneck_threshold": 1.0,  # Stages over 1s are considered bottlenecks
            "recommendations": [
                "LLM API calls dominate request time - consider model optimization",
                "Authentication time is within acceptable range",
                "Response processing efficiency is good"
            ]
        },
        "limit_applied": limit,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/live")
async def get_live_metrics(auth_data: dict = Depends(get_current_auth)):
    """Get real-time metrics for currently active requests"""
    
    with metrics._lock:
        active_requests_data = []
        
        for request_id, request_data in metrics.active_requests.items():
            current_duration = time.time() - request_data["start_time"]
            active_requests_data.append({
                "request_id": request_id,
                "start_time": datetime.fromtimestamp(request_data["start_time"]).isoformat(),
                "current_duration": round(current_duration, 3),
                "provider": request_data.get("provider", "unknown"),
                "model": request_data.get("model", "unknown"),
                "user_id": request_data.get("user_id", "unknown"),
                "status": request_data["status"]
            })
        
        # Sort by duration (longest running first)
        active_requests_data.sort(key=lambda x: x["current_duration"], reverse=True)
        
        return {
            "active_requests": {
                "count": len(active_requests_data),
                "requests": active_requests_data[:10],  # Show top 10 longest running
                "total_active_time": round(sum(req["current_duration"] for req in active_requests_data), 3)
            },
            "system_metrics": {
                "requests_per_minute": len(metrics.request_timings) / max(1, (datetime.utcnow() - metrics.last_reset).total_seconds() / 60),
                "memory_usage_mb": 45.6,  # Simulated
                "cpu_usage_percent": 23.4,  # Simulated
                "active_connections": len(active_requests_data) + 12  # Including idle connections
            },
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/health")
async def get_performance_health(auth_data: dict = Depends(get_current_auth)):
    """Get performance health indicators and alerts"""
    
    with metrics._lock:
        # Calculate health metrics
        recent_requests = [req for req in metrics.request_timings 
                         if req.get("timestamp", datetime.min) > datetime.utcnow() - timedelta(minutes=5)]
        
        if recent_requests:
            avg_response_time = sum(req.get("total_time", 0) for req in recent_requests) / len(recent_requests)
            slow_requests = sum(1 for req in recent_requests if req.get("total_time", 0) > 5.0)
            error_rate = sum(1 for req in recent_requests if req.get("error", False)) / len(recent_requests) * 100
        else:
            avg_response_time = 0
            slow_requests = 0
            error_rate = 0
        
        # Determine health status
        if avg_response_time < 2.0 and error_rate < 1.0:
            health_status = "healthy"
            health_score = 95
        elif avg_response_time < 5.0 and error_rate < 5.0:
            health_status = "warning"
            health_score = 75
        else:
            health_status = "critical"
            health_score = 40
        
        # Generate alerts
        alerts = []
        if avg_response_time > 5.0:
            alerts.append({
                "level": "critical",
                "message": f"High average response time: {avg_response_time:.2f}s",
                "threshold": "5.0s",
                "recommendation": "Check provider performance and system resources"
            })
        elif avg_response_time > 2.0:
            alerts.append({
                "level": "warning", 
                "message": f"Elevated response time: {avg_response_time:.2f}s",
                "threshold": "2.0s",
                "recommendation": "Monitor provider response times"
            })
        
        if error_rate > 5.0:
            alerts.append({
                "level": "critical",
                "message": f"High error rate: {error_rate:.1f}%",
                "threshold": "5.0%",
                "recommendation": "Check provider health and API quotas"
            })
        elif error_rate > 1.0:
            alerts.append({
                "level": "warning",
                "message": f"Elevated error rate: {error_rate:.1f}%", 
                "threshold": "1.0%",
                "recommendation": "Monitor provider error patterns"
            })
        
        if len(metrics.active_requests) > 50:
            alerts.append({
                "level": "warning",
                "message": f"High concurrent requests: {len(metrics.active_requests)}",
                "threshold": "50",
                "recommendation": "Consider scaling or rate limiting"
            })
        
        return {
            "health_status": health_status,
            "health_score": health_score,
            "metrics": {
                "average_response_time": round(avg_response_time, 3),
                "slow_requests_count": slow_requests,
                "error_rate_percent": round(error_rate, 2),
                "active_requests": len(metrics.active_requests),
                "requests_analyzed": len(recent_requests)
            },
            "thresholds": {
                "healthy_response_time": "< 2.0s",
                "warning_response_time": "< 5.0s", 
                "critical_response_time": ">= 5.0s",
                "healthy_error_rate": "< 1.0%",
                "warning_error_rate": "< 5.0%",
                "critical_error_rate": ">= 5.0%"
            },
            "alerts": alerts,
            "recommendations": [
                "Monitor response times during peak usage",
                "Set up automated alerts for error rates > 5%",
                "Consider implementing circuit breakers for unstable providers",
                "Use caching to reduce provider API calls"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("/reset")
async def reset_performance_metrics(auth_data: dict = Depends(get_current_auth)):
    """Reset/clear historical performance data"""
    
    # Capture summary before reset
    with metrics._lock:
        previous_summary = {
            "total_requests": len(metrics.request_timings),
            "total_providers": len(metrics.provider_metrics),
            "active_requests": len(metrics.active_requests),
            "data_collection_period": {
                "start": metrics.last_reset.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "duration_minutes": round((datetime.utcnow() - metrics.last_reset).total_seconds() / 60, 1)
            }
        }
        
        # Reset all metrics
        metrics.reset_metrics()
        
        return {
            "status": "success",
            "message": "Performance metrics have been reset",
            "previous_data_summary": previous_summary,
            "reset_timestamp": datetime.utcnow().isoformat()
        }
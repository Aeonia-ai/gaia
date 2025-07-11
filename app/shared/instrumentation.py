"""
Enhanced Performance Instrumentation System

This module provides comprehensive timing and performance instrumentation
for the LLM platform, building on the existing timing infrastructure.
"""

import time
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from uuid import uuid4
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TimingContext:
    """Context for tracking timing across request lifecycle"""
    request_id: str
    start_time: float = field(default_factory=time.time)
    stages: Dict[str, float] = field(default_factory=dict)
    stage_durations: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def record_stage(self, stage_name: str, duration_ms: Optional[float] = None):
        """Record completion of a processing stage"""
        current_time = time.time()
        
        if duration_ms is not None:
            self.stage_durations[stage_name] = duration_ms
        else:
            # Calculate duration since last stage or start
            last_time = max(self.stages.values()) if self.stages else self.start_time
            self.stage_durations[stage_name] = (current_time - last_time) * 1000
        
        self.stages[stage_name] = current_time
        
        logger.info(f"[{self.request_id}] {stage_name}: {self.stage_durations[stage_name]:.2f}ms")
    
    def get_total_duration(self) -> float:
        """Get total request duration in milliseconds"""
        return (time.time() - self.start_time) * 1000
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive timing summary"""
        return {
            "request_id": self.request_id,
            "total_duration_ms": self.get_total_duration(),
            "stage_durations": self.stage_durations.copy(),
            "stages": {k: v for k, v in self.stages.items()},
            "metadata": self.metadata.copy()
        }

@dataclass
class ProviderTiming:
    """Detailed timing for LLM provider API calls"""
    provider: str
    model: str
    request_id: str
    
    # Request timing
    request_start: float = field(default_factory=time.time)
    request_sent: Optional[float] = None
    first_token_received: Optional[float] = None
    response_complete: Optional[float] = None
    
    # Token counts
    input_tokens: int = 0
    output_tokens: int = 0
    
    # Connection details
    connection_time: Optional[float] = None
    dns_lookup_time: Optional[float] = None
    ssl_handshake_time: Optional[float] = None
    
    def record_request_sent(self):
        """Record when request was sent to provider"""
        self.request_sent = time.time()
        if self.request_sent:
            connection_duration = (self.request_sent - self.request_start) * 1000
            logger.info(f"[{self.request_id}] {self.provider} connection: {connection_duration:.2f}ms")
    
    def record_first_token(self):
        """Record Time to First Token (TTFT)"""
        self.first_token_received = time.time()
        if self.request_sent:
            ttft = (self.first_token_received - self.request_sent) * 1000
            logger.info(f"[{self.request_id}] {self.provider} TTFT: {ttft:.2f}ms")
    
    def record_completion(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record completion of provider response"""
        self.response_complete = time.time()
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        
        if self.request_sent:
            total_duration = (self.response_complete - self.request_sent) * 1000
            logger.info(f"[{self.request_id}] {self.provider} total: {total_duration:.2f}ms")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive provider timing metrics"""
        metrics = {
            "provider": self.provider,
            "model": self.model,
            "request_id": self.request_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens
        }
        
        if self.request_sent:
            metrics["connection_time_ms"] = (self.request_sent - self.request_start) * 1000
            
            if self.first_token_received:
                metrics["ttft_ms"] = (self.first_token_received - self.request_sent) * 1000
                
            if self.response_complete:
                metrics["total_response_time_ms"] = (self.response_complete - self.request_sent) * 1000
                
                if self.first_token_received:
                    metrics["generation_time_ms"] = (self.response_complete - self.first_token_received) * 1000
                    
                    if self.output_tokens > 0:
                        generation_time_s = (self.response_complete - self.first_token_received)
                        metrics["tokens_per_second"] = self.output_tokens / generation_time_s if generation_time_s > 0 else 0
        
        return metrics

class PerformanceInstrumentationManager:
    """Manages performance instrumentation across the application"""
    
    def __init__(self):
        self.active_requests: Dict[str, TimingContext] = {}
        self.completed_requests: List[Dict[str, Any]] = []
        self.provider_timings: Dict[str, ProviderTiming] = {}
        self.max_history = 1000  # Keep last 1000 requests
    
    def start_request(self, request_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking a new request"""
        if request_id is None:
            request_id = str(uuid4())
        
        context = TimingContext(
            request_id=request_id,
            metadata=metadata or {}
        )
        
        self.active_requests[request_id] = context
        logger.info(f"[{request_id}] Request started")
        return request_id
    
    def record_stage(self, request_id: str, stage_name: str, duration_ms: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None):
        """Record completion of a processing stage"""
        if request_id not in self.active_requests:
            logger.warning(f"Request {request_id} not found for stage {stage_name}")
            return
        
        context = self.active_requests[request_id]
        context.record_stage(stage_name, duration_ms)
        
        if metadata:
            context.metadata.update(metadata)
    
    def start_provider_timing(self, request_id: str, provider: str, model: str) -> str:
        """Start timing for a provider API call"""
        timing_id = f"{request_id}_{provider}"
        
        self.provider_timings[timing_id] = ProviderTiming(
            provider=provider,
            model=model,
            request_id=request_id
        )
        
        return timing_id
    
    def get_provider_timing(self, timing_id: str) -> Optional[ProviderTiming]:
        """Get provider timing object"""
        return self.provider_timings.get(timing_id)
    
    def complete_request(self, request_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Complete request tracking and return summary"""
        if request_id not in self.active_requests:
            logger.warning(f"Request {request_id} not found for completion")
            return {}
        
        context = self.active_requests[request_id]
        
        if metadata:
            context.metadata.update(metadata)
        
        # Record completion stage
        context.record_stage("request_completed")
        
        # Get summary
        summary = context.get_summary()
        
        # Add provider timing if available
        provider_timings = []
        for timing_id, timing in self.provider_timings.items():
            if timing.request_id == request_id:
                provider_timings.append(timing.get_metrics())
        
        summary["provider_timings"] = provider_timings
        
        # Move to completed requests
        self.completed_requests.append(summary)
        
        # Clean up
        del self.active_requests[request_id]
        
        # Remove old provider timings
        to_remove = [tid for tid, timing in self.provider_timings.items() if timing.request_id == request_id]
        for tid in to_remove:
            del self.provider_timings[tid]
        
        # Maintain history limit
        if len(self.completed_requests) > self.max_history:
            self.completed_requests = self.completed_requests[-self.max_history:]
        
        logger.info(f"[{request_id}] Request completed in {summary['total_duration_ms']:.2f}ms")
        return summary
    
    def get_request_metrics(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific request"""
        # Check active requests
        if request_id in self.active_requests:
            return self.active_requests[request_id].get_summary()
        
        # Check completed requests
        for summary in self.completed_requests:
            if summary["request_id"] == request_id:
                return summary
        
        return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        if not self.completed_requests:
            return {"message": "No completed requests"}
        
        # Calculate statistics
        total_durations = [req["total_duration_ms"] for req in self.completed_requests]
        
        summary = {
            "total_requests": len(self.completed_requests),
            "active_requests": len(self.active_requests),
            "avg_response_time_ms": sum(total_durations) / len(total_durations),
            "min_response_time_ms": min(total_durations),
            "max_response_time_ms": max(total_durations),
            "recent_requests": self.completed_requests[-10:] if len(self.completed_requests) >= 10 else self.completed_requests
        }
        
        # Provider statistics
        provider_stats = {}
        for req in self.completed_requests:
            for provider_timing in req.get("provider_timings", []):
                provider = provider_timing["provider"]
                if provider not in provider_stats:
                    provider_stats[provider] = {
                        "requests": 0,
                        "total_time": 0,
                        "total_tokens": 0,
                        "ttft_times": []
                    }
                
                provider_stats[provider]["requests"] += 1
                provider_stats[provider]["total_time"] += provider_timing.get("total_response_time_ms", 0)
                provider_stats[provider]["total_tokens"] += provider_timing.get("total_tokens", 0)
                
                if "ttft_ms" in provider_timing:
                    provider_stats[provider]["ttft_times"].append(provider_timing["ttft_ms"])
        
        # Calculate averages
        for provider, stats in provider_stats.items():
            if stats["requests"] > 0:
                stats["avg_response_time_ms"] = stats["total_time"] / stats["requests"]
                if stats["ttft_times"]:
                    stats["avg_ttft_ms"] = sum(stats["ttft_times"]) / len(stats["ttft_times"])
        
        summary["provider_stats"] = provider_stats
        
        return summary

# Global instrumentation manager
instrumentation = PerformanceInstrumentationManager()

@contextmanager
def instrument_request(request_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for instrumenting requests"""
    request_id = instrumentation.start_request(request_id, metadata)
    try:
        yield request_id
    finally:
        instrumentation.complete_request(request_id)

def record_stage(request_id: str, stage_name: str, duration_ms: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None):
    """Convenience function for recording stages"""
    instrumentation.record_stage(request_id, stage_name, duration_ms, metadata)

async def instrument_async_operation(request_id: str, operation_name: str, operation):
    """Instrument an async operation"""
    start_time = time.time()
    try:
        result = await operation
        duration_ms = (time.time() - start_time) * 1000
        record_stage(request_id, operation_name, duration_ms, {"success": True})
        return result
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        record_stage(request_id, f"{operation_name}_error", duration_ms, {"success": False, "error": str(e)})
        raise
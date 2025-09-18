"""
Progressive response delivery for KB Agent and complex analysis tasks.
Implements immediate acknowledgment + detailed follow-up pattern.
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional, List
from enum import Enum


class ResponsePhase(Enum):
    """Phases of progressive response delivery."""
    IMMEDIATE = "immediate"      # < 500ms - Quick acknowledgment
    ANALYSIS = "analysis"        # 1-3s - Status updates during processing
    DETAILED = "detailed"        # 3-10s - Full results and insights
    COMPLETE = "complete"        # Final status


class ProgressiveResponse:
    """
    Manages progressive delivery of complex responses.

    Pattern:
    1. IMMEDIATE: "🤖 Coordinating technical, knowledge_management agents..."
    2. ANALYSIS: "📊 Analyzing knowledge base content..."
    3. DETAILED: Full analysis results with insights
    4. COMPLETE: Metadata and wrap-up
    """

    def __init__(self, query_type: str = "kb_analysis"):
        self.query_type = query_type
        self.start_time = time.time()
        self.phase = ResponsePhase.IMMEDIATE
        self.conversation_id: Optional[str] = None
        self.provider: str = "gaia-kb-agent"
        self.model: str = "kb-intelligent-v1"

    def get_immediate_message(self) -> str:
        """Get immediate acknowledgment message based on query type."""
        patterns = {
            "kb_analysis": "🤖 Coordinating technical, knowledge_management agents...",
            "kb_synthesis": "🧠 Coordinating analytical, synthesis agents...",
            "kb_validation": "✅ Coordinating validation, compliance agents...",
            "multi_agent": "🔄 Coordinating technical, analytical agents...",
            "complex_query": "⚡ Processing complex analysis request..."
        }
        return patterns.get(self.query_type, "🤖 Coordinating technical agents...")

    def get_analysis_message(self) -> str:
        """Get analysis status message."""
        patterns = {
            "kb_analysis": "📊 Analyzing knowledge base content and making intelligent decisions...",
            "kb_synthesis": "🔍 Synthesizing information from multiple knowledge sources...",
            "kb_validation": "🔒 Validating against rules and compliance requirements...",
            "multi_agent": "⚙️ Orchestrating multiple specialized agents...",
            "complex_query": "🧮 Processing complex query with specialized tools..."
        }
        return patterns.get(self.query_type, "📊 Analyzing request...")

    async def create_progressive_stream(
        self,
        detailed_generator: AsyncGenerator[Dict[str, Any], None],
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Create progressive response stream with immediate acknowledgment.

        Args:
            detailed_generator: Generator for detailed response content
            conversation_id: Optional conversation ID

        Yields:
            V0.3 format events: metadata, content, done
        """
        self.conversation_id = conversation_id

        # Phase 1: IMMEDIATE acknowledgment (< 500ms)
        yield {
            "type": "metadata",
            "conversation_id": conversation_id,
            "provider": self.provider,
            "model": self.model,
            "phase": "immediate",
            "timestamp": time.time()
        }

        immediate_msg = self.get_immediate_message()
        yield {
            "type": "content",
            "content": immediate_msg + "\n\n",
            "provider": self.provider,
            "model": self.model
        }

        # Small delay to ensure immediate message is displayed first
        await asyncio.sleep(0.1)

        # Phase 2: ANALYSIS status (1-3s)
        self.phase = ResponsePhase.ANALYSIS
        analysis_msg = self.get_analysis_message()
        yield {
            "type": "content",
            "content": analysis_msg + "\n\n",
            "provider": self.provider,
            "model": self.model
        }

        # Phase 3: DETAILED content from generator
        self.phase = ResponsePhase.DETAILED

        async for chunk in detailed_generator:
            # Pass through detailed content, ensuring proper formatting
            if chunk.get("type") == "content":
                yield {
                    **chunk,
                    "provider": self.provider,
                    "model": self.model
                }
            elif chunk.get("type") == "metadata":
                # Merge with our metadata
                yield {
                    **chunk,
                    "conversation_id": conversation_id or chunk.get("conversation_id"),
                    "provider": self.provider,
                    "model": self.model,
                    "phase": "detailed"
                }
            else:
                yield chunk

        # Phase 4: COMPLETE
        self.phase = ResponsePhase.COMPLETE
        total_time = time.time() - self.start_time

        yield {
            "type": "metadata",
            "conversation_id": conversation_id,
            "provider": self.provider,
            "model": self.model,
            "phase": "complete",
            "total_time": round(total_time, 3),
            "timestamp": time.time()
        }


class KBAgentProgressiveResponse(ProgressiveResponse):
    """
    Specialized progressive response for KB Agent operations.
    """

    def __init__(self, operation: str, knowledge_scope: str = "general"):
        # Map KB operations to appropriate query types
        query_type_mapping = {
            "interpret_knowledge": "kb_analysis",
            "synthesize_information": "kb_synthesis",
            "validate_rules": "kb_validation",
            "execute_workflow": "multi_agent",
            "search_analyze": "kb_analysis"
        }

        super().__init__(query_type_mapping.get(operation, "kb_analysis"))
        self.operation = operation
        self.knowledge_scope = knowledge_scope
        self.model = f"kb-{operation}-v1"

    def get_immediate_message(self) -> str:
        """KB-specific immediate acknowledgment."""
        if self.operation == "interpret_knowledge":
            return "🤖 Coordinating technical, knowledge_management agents..."
        elif self.operation == "synthesize_information":
            return "🧠 Coordinating analytical, synthesis agents..."
        elif self.operation == "validate_rules":
            return "✅ Coordinating validation, compliance agents..."
        elif self.operation == "execute_workflow":
            return "⚙️ Coordinating workflow, execution agents..."
        else:
            return "🤖 Coordinating technical, analytical agents..."

    def get_analysis_message(self) -> str:
        """KB-specific analysis status."""
        if self.operation == "interpret_knowledge":
            return f"📊 Analyzing {self.knowledge_scope} knowledge base content and making intelligent decisions..."
        elif self.operation == "synthesize_information":
            return f"🔍 Synthesizing information from {self.knowledge_scope} knowledge sources..."
        elif self.operation == "validate_rules":
            return f"🔒 Validating against {self.knowledge_scope} rules and compliance requirements..."
        elif self.operation == "execute_workflow":
            return f"⚡ Executing {self.knowledge_scope} workflow with intelligent coordination..."
        else:
            return f"📊 Processing {self.knowledge_scope} knowledge base analysis..."


async def create_kb_progressive_stream(
    operation: str,
    detailed_generator: AsyncGenerator[Dict[str, Any], None],
    conversation_id: Optional[str] = None,
    knowledge_scope: str = "general"
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function for KB Agent progressive responses.

    Args:
        operation: KB operation (interpret_knowledge, synthesize_information, etc.)
        detailed_generator: Generator for detailed KB response
        conversation_id: Optional conversation ID
        knowledge_scope: Scope of knowledge (e.g., "development", "deployment", "architecture")

    Yields:
        Progressive V0.3 format events
    """
    kb_response = KBAgentProgressiveResponse(operation, knowledge_scope)

    async for event in kb_response.create_progressive_stream(
        detailed_generator,
        conversation_id
    ):
        yield event


# Example usage patterns for different scenarios
async def example_kb_analysis_stream(
    query: str,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Example of KB analysis with progressive delivery."""

    async def detailed_analysis():
        """Simulated detailed KB analysis generator."""
        # Simulate analysis processing
        await asyncio.sleep(1.0)

        yield {
            "type": "content",
            "content": "## Knowledge Base Analysis Results\n\n"
        }

        await asyncio.sleep(0.5)

        yield {
            "type": "content",
            "content": "**Key Capabilities:**\n"
        }

        await asyncio.sleep(0.3)

        yield {
            "type": "content",
            "content": "- Intelligent decision-making based on KB content\n"
        }

        await asyncio.sleep(0.3)

        yield {
            "type": "content",
            "content": "- Context-aware knowledge interpretation\n"
        }

        await asyncio.sleep(0.3)

        yield {
            "type": "content",
            "content": "- Multi-modal operation (validation, synthesis, workflow)\n\n"
        }

        yield {
            "type": "content",
            "content": "**Intelligence Features:**\n"
        }

        await asyncio.sleep(0.3)

        yield {
            "type": "content",
            "content": "- Model selection based on query complexity\n- Performance-optimized caching\n- Real-time knowledge base adaptation\n"
        }

    # Create progressive stream
    async for event in create_kb_progressive_stream(
        operation="interpret_knowledge",
        detailed_generator=detailed_analysis(),
        conversation_id=conversation_id,
        knowledge_scope="KB Agent capabilities"
    ):
        yield event
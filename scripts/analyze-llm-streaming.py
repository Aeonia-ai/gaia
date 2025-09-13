#!/usr/bin/env python3
"""
Diagnostic script to analyze actual LLM streaming token patterns.
Captures real chunking behavior from different providers.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.chat_service import MultiProviderChatService
from app.services.llm.base import LLMProvider


class StreamingAnalyzer:
    """Analyze streaming patterns from LLM providers."""
    
    def __init__(self):
        self.chat_service = MultiProviderChatService()
        self.results = {}
        
    async def analyze_provider(
        self, 
        provider: LLMProvider, 
        model: str,
        test_prompts: List[str]
    ) -> Dict[str, Any]:
        """Analyze streaming patterns for a specific provider."""
        
        provider_results = {
            "provider": provider.value,
            "model": model,
            "prompts": []
        }
        
        for prompt in test_prompts:
            print(f"\n{'='*60}")
            print(f"Testing: {provider.value} - {model}")
            print(f"Prompt: {prompt[:50]}...")
            print(f"{'='*60}")
            
            chunks_data = []
            full_response = ""
            chunk_count = 0
            
            try:
                # Stream the response
                async for chunk in self.chat_service.chat_completion_stream(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    provider=provider,
                    force_provider=True,
                    temperature=0.7,
                    max_tokens=200
                ):
                    if chunk.get("type") == "content":
                        content = chunk.get("content", "")
                        if content:  # Only track non-empty chunks
                            chunk_count += 1
                            chunk_info = {
                                "index": chunk_count,
                                "content": content,
                                "length": len(content),
                                "repr": repr(content),  # Show escape chars
                                "has_space_start": content.startswith(' '),
                                "has_space_end": content.endswith(' '),
                                "has_newline": '\n' in content,
                                "is_punctuation": content in '.,!?;:',
                                "is_word_fragment": not content.startswith(' ') and not content.endswith(' ') and ' ' not in content and len(content) > 1
                            }
                            
                            # Check for word boundaries
                            if chunk_count > 1:
                                prev = chunks_data[-1] if chunks_data else None
                                if prev:
                                    # Check if this completes a word
                                    combined = prev["content"] + content
                                    chunk_info["completes_word"] = ' ' in combined or content.startswith(' ')
                            
                            chunks_data.append(chunk_info)
                            full_response += content
                            
                            # Print live analysis
                            print(f"Chunk {chunk_count}: {repr(content)[:30]:30} | Len: {len(content):3} | Fragment: {chunk_info['is_word_fragment']}")
            
            except Exception as e:
                print(f"Error streaming from {provider.value}: {e}")
                continue
            
            # Analyze patterns
            prompt_analysis = {
                "prompt": prompt[:50] + "...",
                "total_chunks": chunk_count,
                "full_response_length": len(full_response),
                "chunks": chunks_data[:10],  # First 10 chunks for detail
                "patterns": self._analyze_patterns(chunks_data),
                "sample_response": full_response[:200]
            }
            
            provider_results["prompts"].append(prompt_analysis)
            
            # Print summary
            print(f"\n{'-'*40}")
            print(f"Summary for this prompt:")
            print(f"- Total chunks: {chunk_count}")
            print(f"- Avg chunk size: {len(full_response)/chunk_count if chunk_count > 0 else 0:.1f} chars")
            print(f"- Word fragments: {prompt_analysis['patterns']['word_fragment_count']}/{chunk_count}")
            print(f"- Single chars: {prompt_analysis['patterns']['single_char_chunks']}/{chunk_count}")
            
        return provider_results
    
    def _analyze_patterns(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in chunk data."""
        if not chunks:
            return {}
        
        lengths = [c["length"] for c in chunks]
        
        return {
            "avg_chunk_length": sum(lengths) / len(lengths) if lengths else 0,
            "min_chunk_length": min(lengths) if lengths else 0,
            "max_chunk_length": max(lengths) if lengths else 0,
            "single_char_chunks": sum(1 for l in lengths if l == 1),
            "word_fragment_count": sum(1 for c in chunks if c.get("is_word_fragment", False)),
            "starts_with_space": sum(1 for c in chunks if c.get("has_space_start", False)),
            "ends_with_space": sum(1 for c in chunks if c.get("has_space_end", False)),
            "typical_patterns": self._identify_patterns(chunks)
        }
    
    def _identify_patterns(self, chunks: List[Dict]) -> List[str]:
        """Identify common patterns in chunking."""
        patterns = []
        
        # Check for word-level chunking
        word_chunks = sum(1 for c in chunks if c.get("has_space_end", False))
        if word_chunks > len(chunks) * 0.7:
            patterns.append("word_level_chunking")
        
        # Check for token-level chunking
        fragment_chunks = sum(1 for c in chunks if c.get("is_word_fragment", False))
        if fragment_chunks > len(chunks) * 0.3:
            patterns.append("subword_token_chunking")
        
        # Check for phrase-level chunking
        avg_length = sum(c["length"] for c in chunks) / len(chunks) if chunks else 0
        if avg_length > 10:
            patterns.append("phrase_level_chunking")
        elif avg_length < 3:
            patterns.append("character_level_streaming")
        
        return patterns
    
    async def run_analysis(self):
        """Run the complete analysis."""
        
        # Initialize service
        await self.chat_service.initialize()
        
        # Test prompts designed to reveal chunking patterns
        test_prompts = [
            "Count from 1 to 5 with the word 'Mississippi' between each number.",
            "Write a single sentence about artificial intelligence.",
            'Respond with exactly this JSON: {"action":"test","value":123,"nested":{"key":"data"}}',
            "Say 'The quick brown fox jumps over the lazy dog' word by word.",
            "Write the word 'supercalifragilisticexpialidocious' and explain what it means.",
        ]
        
        # Test each provider
        providers_to_test = [
            (LLMProvider.OPENAI, "gpt-4o-mini"),
            (LLMProvider.CLAUDE, "claude-3-haiku-20240307"),
        ]
        
        all_results = []
        
        for provider, model in providers_to_test:
            try:
                result = await self.analyze_provider(provider, model, test_prompts)
                all_results.append(result)
            except Exception as e:
                print(f"Failed to test {provider.value}: {e}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"streaming_analysis_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Analysis complete! Results saved to: {output_file}")
        print(f"{'='*60}")
        
        # Print summary comparison
        print("\nPROVIDER COMPARISON:")
        print("-" * 40)
        for result in all_results:
            provider = result["provider"]
            model = result["model"]
            
            # Aggregate stats across all prompts
            all_patterns = []
            total_chunks = 0
            total_fragments = 0
            
            for prompt_data in result["prompts"]:
                patterns = prompt_data.get("patterns", {})
                total_chunks += prompt_data.get("total_chunks", 0)
                total_fragments += patterns.get("word_fragment_count", 0)
                all_patterns.extend(patterns.get("typical_patterns", []))
            
            print(f"\n{provider} ({model}):")
            print(f"  Total chunks analyzed: {total_chunks}")
            print(f"  Word fragments: {total_fragments} ({total_fragments/total_chunks*100:.1f}%)" if total_chunks > 0 else "")
            print(f"  Common patterns: {', '.join(set(all_patterns))}")
        
        return all_results


async def main():
    """Run the streaming analysis."""
    print("Starting LLM Streaming Analysis...")
    print("This will make real API calls to analyze chunking patterns.")
    print("-" * 60)
    
    analyzer = StreamingAnalyzer()
    await analyzer.run_analysis()


if __name__ == "__main__":
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set, OpenAI tests will fail")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set, Claude tests will fail")
    
    asyncio.run(main())
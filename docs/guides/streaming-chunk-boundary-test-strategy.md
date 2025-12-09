# Streaming Chunk Boundary Test Strategy

**Created**: January 2025  
**Purpose**: Define comprehensive testing approach for SSE streaming chunk boundary behavior

## The Testing Gap

Current tests use clean, complete chunks but don't test real-world scenarios where:
- Words are split across chunks
- JSON directives are fragmented
- Chunks arrive at arbitrary byte boundaries

## Testing Approach

### 1. Mock LLM Provider with Controlled Chunking

Create a test-only LLM provider that can simulate various chunking patterns:

```python
# tests/mocks/mock_llm_provider.py
class MockChunkingProvider(LLMProviderInterface):
    """Mock provider that chunks text in controlled ways for testing"""
    
    def __init__(self, chunking_strategy: str = "word_split"):
        self.chunking_strategy = chunking_strategy
    
    async def chat_completion_stream(self, request):
        response_text = self._get_test_response(request)
        
        if self.chunking_strategy == "word_split":
            # Split mid-word: "Hello world" -> ["Hel", "lo wo", "rld"]
            chunks = self._split_mid_word(response_text)
        elif self.chunking_strategy == "json_split":
            # Split JSON directive across chunks
            chunks = self._split_json_directive(response_text)
        elif self.chunking_strategy == "byte_boundary":
            # Split at arbitrary byte boundaries
            chunks = self._split_by_bytes(response_text, chunk_size=3)
        elif self.chunking_strategy == "single_char":
            # Extreme case: one character per chunk
            chunks = list(response_text)
        
        for chunk in chunks:
            yield StreamChunk(content=chunk, ...)
            await asyncio.sleep(0.001)  # Simulate network delay
```

### 2. Test Scenarios to Cover

#### A. Word Boundary Tests
```python
@pytest.mark.asyncio
async def test_streaming_splits_words():
    """Test that client can reconstruct words split across chunks"""
    
    # Configure mock to split "Hello beautiful world" as:
    # ["Hel", "lo beau", "tif", "ul wo", "rld"]
    provider = MockChunkingProvider(chunking_strategy="word_split")
    
    # Stream through the service
    chunks = []
    async for chunk in chat_service.stream_with_provider(provider):
        chunks.append(chunk)
    
    # Verify chunks arrive split
    assert chunks[0]["content"] == "Hel"
    assert chunks[1]["content"] == "lo beau"
    
    # Verify full reconstruction
    full_text = "".join(c["content"] for c in chunks)
    assert full_text == "Hello beautiful world"
```

#### B. JSON Directive Splitting Tests
```python
@pytest.mark.asyncio
async def test_streaming_splits_json_directives():
    """Test JSON directives split across multiple chunks"""
    
    # Response with embedded directive
    test_response = 'I\'ll spawn a fairy! {"m":"spawn_character","p":{"type":"fairy"}}'
    
    # Configure to split the JSON across chunks:
    # ['I\'ll spawn a fairy! {"m":"sp', 'awn_char', 'acter","p":{"ty', 'pe":"fairy"}}']
    provider = MockChunkingProvider(chunking_strategy="json_split")
    
    chunks = []
    async for chunk in chat_service.stream_with_provider(provider):
        chunks.append(chunk["content"])
    
    # Individual chunks should have partial JSON
    assert '{"m":"sp' in chunks[0]
    assert 'awn_char' in chunks[1]
    
    # Full message must be reconstructable
    full_message = "".join(chunks)
    assert full_message == test_response
    
    # Directive should be parseable from complete message
    import re
    json_pattern = r'\{[^}]+\}'
    matches = re.findall(json_pattern, full_message)
    assert len(matches) == 1
    
    directive = json.loads(matches[0])
    assert directive["m"] == "spawn_character"
```

#### C. SSE Event Boundary Tests
```python
@pytest.mark.asyncio
async def test_sse_event_boundaries_with_split_content():
    """Test that SSE events are properly formatted even with split content"""
    
    provider = MockChunkingProvider(chunking_strategy="word_split")
    
    # Test through the actual endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "/api/v0.3/chat",
            json={"message": "test", "stream": True},
            headers={"X-Mock-Provider": "word_split"}  # Header to trigger mock
        )
        
        buffer = ""
        events = []
        
        async for chunk in response.aiter_text():
            buffer += chunk
            
            # Parse complete SSE events
            while "\n\n" in buffer:
                event, buffer = buffer.split("\n\n", 1)
                if event.startswith("data: "):
                    events.append(event[6:])
        
        # Each event should be valid JSON or [DONE]
        for event_data in events:
            if event_data != "[DONE]":
                data = json.loads(event_data)  # Should not raise
                assert "choices" in data
```

### 3. Integration Test with Real LLM

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_llm_chunking_behavior():
    """Document actual chunking behavior from real LLMs"""
    
    # Use a prompt designed to trigger various chunking scenarios
    test_prompt = """
    Please respond with exactly this text including the JSON:
    Hello world! Here's a directive: {"m":"test","p":{"value":123}}
    """
    
    chunk_sizes = []
    chunk_contents = []
    
    async for chunk in chat_service.chat_completion_stream(
        messages=[{"role": "user", "content": test_prompt}],
        model="gpt-4o-mini"  # Or claude-3-haiku for comparison
    ):
        chunk_contents.append(chunk["content"])
        chunk_sizes.append(len(chunk["content"]))
    
    # Log actual chunking patterns for documentation
    print(f"Chunk sizes: {chunk_sizes}")
    print(f"Chunk boundaries: {chunk_contents}")
    
    # Verify reconstruction
    full_response = "".join(chunk_contents)
    assert "Hello world" in full_response
    assert '{"m":"test"' in full_response
```

### 4. Client Simulation Tests

```python
class MockUnityClient:
    """Simulates Unity ChatClient's buffer handling"""
    
    def __init__(self):
        self.buffer = ""
        self.complete_message = ""
        self.events = []
    
    async def process_sse_stream(self, stream):
        """Process SSE stream like Unity would"""
        async for chunk in stream:
            self.buffer += chunk
            
            # Process complete events
            while "\n\n" in self.buffer:
                event, self.buffer = self.buffer.split("\n\n", 1)
                
                if event.startswith("data: "):
                    data_str = event[6:]
                    
                    if data_str == "[DONE]":
                        return self.complete_message
                    
                    try:
                        data = json.loads(data_str)
                        if "choices" in data:
                            content = data["choices"][0]["delta"].get("content", "")
                            self.complete_message += content
                    except json.JSONDecodeError:
                        # Log partial JSON for debugging
                        pass
        
        return self.complete_message

@pytest.mark.asyncio
async def test_unity_client_simulation():
    """Test that a Unity-like client can handle our streaming"""
    
    client = MockUnityClient()
    
    # Test with various splitting strategies
    for strategy in ["word_split", "json_split", "single_char"]:
        provider = MockChunkingProvider(chunking_strategy=strategy)
        
        # Get stream from service
        stream = generate_sse_stream(provider)
        
        # Process like Unity would
        message = await client.process_sse_stream(stream)
        
        # Should reconstruct correctly regardless of chunking
        assert "expected content" in message
```

### 5. Performance Impact Tests

```python
@pytest.mark.asyncio
async def test_chunking_performance_impact():
    """Measure performance impact of different chunking strategies"""
    
    strategies = {
        "optimal": 50,      # 50 chars per chunk
        "small": 5,         # 5 chars per chunk
        "tiny": 1,          # 1 char per chunk
        "large": 500        # 500 chars per chunk
    }
    
    results = {}
    
    for name, chunk_size in strategies.items():
        start = time.time()
        
        provider = MockChunkingProvider(chunk_size=chunk_size)
        chunks_received = 0
        
        async for chunk in chat_service.stream_with_provider(provider):
            chunks_received += 1
        
        elapsed = time.time() - start
        results[name] = {
            "time": elapsed,
            "chunks": chunks_received,
            "chunks_per_second": chunks_received / elapsed
        }
    
    # Document performance characteristics
    assert results["tiny"]["chunks"] > results["large"]["chunks"]
    assert results["tiny"]["time"] > results["large"]["time"]  # More overhead
```

## Implementation Plan

1. **Phase 1**: Create `MockChunkingProvider` in test utilities
2. **Phase 2**: Write word boundary splitting tests
3. **Phase 3**: Write JSON directive splitting tests  
4. **Phase 4**: Add SSE event boundary validation
5. **Phase 5**: Create Unity client simulator
6. **Phase 6**: Run integration tests with real LLMs to document behavior
7. **Phase 7**: Add performance benchmarks

## Expected Outcomes

- **Documentation**: Real chunking patterns from different LLM providers
- **Validation**: Proof that clients can handle arbitrary chunking
- **Regression Prevention**: Tests that will catch if we accidentally add buffering
- **Performance Baseline**: Understanding of chunking overhead

## Test File Structure

```
tests/
├── unit/
│   ├── test_streaming_chunk_boundaries.py
│   └── test_json_directive_splitting.py
├── integration/
│   ├── test_real_llm_chunking.py
│   └── test_client_simulation.py
├── mocks/
│   ├── mock_chunking_provider.py
│   └── mock_unity_client.py
└── performance/
    └── test_chunking_performance.py
```

## Success Criteria

- [ ] Tests pass with chunks split at any boundary
- [ ] JSON directives parse correctly after reconstruction
- [ ] No assumptions about chunk boundaries in production code
- [ ] Documentation of real LLM chunking patterns
- [ ] Client simulation handles all test cases
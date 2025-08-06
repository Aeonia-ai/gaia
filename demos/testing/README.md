# GAIA Platform Testing Scripts

This directory contains standalone testing scripts for performance analysis, integration testing, and development workflows.

## 🎯 Purpose

These are **standalone Python scripts** (not pytest tests) designed for:
- **Performance benchmarking** - Measure response times and throughput
- **Integration testing** - Test real service interactions
- **Development workflows** - Quick testing during development
- **API exploration** - Test different endpoint patterns

## 📂 Script Categories

### Performance Testing Scripts (`tests/performance/`)
- **`test_chat_speed.py`** - Measures chat endpoint response times with various queries
- **`test_orchestration_performance.py`** - Tests agent orchestration performance 
- **`test_memory_robust.py`** - Tests conversation persistence with randomized data

### Integration Testing Scripts (`tests/integration/`)
- **`test_services_health.py`** - Health checks for all GAIA services
- **`test_kb_integration.py`** - Knowledge Base service functionality testing

### Demo/Showcase Scripts (`demos/`)
- **`test_jason_luna_*.py`** - Specific user scenario demonstrations
- **`test_clear_history.py`** - History management workflow testing

### Chat Endpoint Testing (`demos/testing/`)
- **`test_all_chat_endpoints.py`** - Comprehensive test of all chat endpoints with performance metrics
- **`test_lightweight_*.py`** - Tests various lightweight chat implementations
- **`test_mcp_agent_workflows.py`** - MCP agent workflow pattern testing

## 🚀 Usage

### Running Performance Tests
```bash
# Test chat endpoint speed
cd tests/performance/
python test_chat_speed.py

# Test orchestration performance
python test_orchestration_performance.py

# Test memory robustness
python test_memory_robust.py
```

### Running Integration Tests
```bash
# Check all service health
cd tests/integration/
python test_services_health.py

# Test KB integration
python test_kb_integration.py
```

### Running Demo Scripts
```bash
# Test specific user scenarios
cd demos/
python test_jason_luna_ultrafast.py
python test_clear_history.py
```

### Running Chat Endpoint Tests
```bash
# Comprehensive endpoint testing
cd demos/testing/
python test_all_chat_endpoints.py

# Test lightweight implementations
python test_lightweight_chat.py
python test_lightweight_direct.py
```

## ⚙️ Configuration

Most scripts use environment variables:
```bash
# Required
export GAIA_BASE_URL="http://localhost:8666"  # or staging/prod URL
export GAIA_API_KEY="your-api-key"

# Optional  
export GAIA_ENVIRONMENT="local"  # local, staging, prod
export PERFORMANCE_ITERATIONS=10
```

## 📊 Expected Output

### Performance Scripts
- Response times (min, max, average)
- Throughput measurements  
- Success/failure rates
- Performance comparisons between endpoints

### Integration Scripts
- Service health status
- Connectivity tests
- Feature availability checks
- Error rate monitoring

### Demo Scripts
- Workflow demonstrations
- Feature showcases
- User scenario validation

## 🔧 Requirements

These scripts require:
- Python 3.11+
- `httpx`, `aiohttp`, or `requests` (depending on script)
- Valid GAIA API key
- Network access to GAIA services

Install dependencies:
```bash
pip install httpx aiohttp requests python-dotenv
```

## 📋 Script Descriptions

| Script | Purpose | Duration | Dependencies |
|--------|---------|----------|--------------|
| `test_all_chat_endpoints.py` | Tests all chat endpoints with performance metrics | 2-5 min | httpx, aiohttp |
| `test_chat_speed.py` | Measures response times for different query types | 1-3 min | httpx |
| `test_orchestration_performance.py` | Tests agent orchestration patterns | 3-10 min | httpx |
| `test_services_health.py` | Health checks for all services | 30s | httpx |
| `test_memory_robust.py` | Tests conversation persistence | 2-5 min | requests |
| `test_kb_integration.py` | KB service functionality tests | 1-2 min | asyncio |
| `test_lightweight_*.py` | Tests lightweight chat implementations | 30s-2min | Various |
| `test_jason_luna_*.py` | User scenario demonstrations | 1-2 min | requests |

## 🚨 Important Notes

1. **Not pytest tests** - These are standalone scripts, run them directly with Python
2. **Real service testing** - Scripts hit actual GAIA services (local/staging/prod)
3. **API key required** - Most scripts need valid authentication
4. **Performance impact** - Some scripts generate significant load
5. **Environment awareness** - Scripts adapt behavior based on target environment

## 🔗 Related Documentation

- [Testing Guide](../../docs/current/development/testing-guide.md) - Comprehensive testing strategy
- [API Documentation](../../docs/api/) - Complete API reference
- [Performance Testing](../../docs/current/development/testing-and-quality-assurance.md) - Performance testing patterns

---

These scripts complement the formal pytest test suite by providing practical, real-world testing scenarios and performance benchmarking capabilities.
#!/bin/bash
# Setup development environment with quality checks

echo "🚀 Setting up Gaia Platform development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Install development dependencies
echo "📦 Installing development dependencies..."
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx ruff black isort mypy beautifulsoup4 deepdiff colorama

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your configuration"
fi

# Run initial tests
echo "🧪 Running initial test suite..."
pytest tests/web/test_auth_flow.py -v

echo "✅ Development environment setup complete!"
echo ""
echo "Pre-commit hooks installed. They will run automatically on git commit."
echo "To run hooks manually: pre-commit run --all-files"
echo ""
echo "To run specific tests:"
echo "  - Auth contract tests: pytest tests/web/test_auth_flow.py"
echo "  - All tests: pytest tests/"
echo "  - With coverage: pytest --cov=app tests/"
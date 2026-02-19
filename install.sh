#!/bin/bash

echo "🔍 Installing codereview..."
echo ""

# Install the package and all dependencies
pip install -e . 2>/dev/null || pip3 install -e . 2>/dev/null || python3 -m pip install -e .

# Verify it worked
if command -v codereview &> /dev/null; then
    echo ""
    echo "✅ codereview installed successfully!"
    echo ""
    codereview --version
    echo ""
    echo "Run 'codereview --setup' to get started."
else
    echo ""
    echo "⚠️  'codereview' command not found in PATH."
    echo "   Try running directly: python3 -m codereview.cli --setup"
    echo ""
    echo "   Or add this alias to your shell:"
    echo '   echo '"'"'alias codereview="python3 -m codereview.cli"'"'"' >> ~/.zshrc && source ~/.zshrc'
fi

#!/bin/bash

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
RESET='\033[0m'

clear

echo ""
echo -e "${BOLD}🔍 codereview — AI-powered code review in your terminal${RESET}"
echo ""
echo -e "${DIM}Installing...${RESET}"
echo ""

# Find the right Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}❌ Python not found. Install Python 3.8+ first: https://python.org${RESET}"
    exit 1
fi

# Check Python version
PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo -e "${RED}❌ Python 3.8+ required. You have Python $PY_VERSION${RESET}"
    exit 1
fi

echo -e "  ${GREEN}✓${RESET} Python $PY_VERSION found"

# Install the package and all dependencies
echo -e "  ${DIM}Installing dependencies (rich, requests)...${RESET}"
$PYTHON -m pip install -e . --quiet 2>/dev/null || $PYTHON -m pip install -e . 2>&1 | tail -1

echo -e "  ${GREEN}✓${RESET} Dependencies installed"

# Verify codereview command works
if command -v codereview &> /dev/null; then
    echo -e "  ${GREEN}✓${RESET} codereview command ready"
    CR_CMD="codereview"
else
    # Add alias if command not in PATH
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_RC" ]; then
        if ! grep -q "codereview" "$SHELL_RC" 2>/dev/null; then
            echo "alias codereview=\"$PYTHON -m codereview.cli\"" >> "$SHELL_RC"
        fi
    fi

    CR_CMD="$PYTHON -m codereview.cli"
    echo -e "  ${GREEN}✓${RESET} codereview configured"
fi

# Done installing — show welcome
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "${BOLD}  ✅ Installation complete!${RESET}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo ""
echo -e "${BOLD}  SETUP (free, 60 seconds)${RESET}"
echo ""
echo -e "  codereview uses an LLM to analyze your code."
echo -e "  The easiest free option is ${BOLD}Groq${RESET} — no credit card needed."
echo ""
echo -e "  ${CYAN}Step 1:${RESET} Get your free API key"
echo ""
echo -e "    Go to: ${CYAN}https://console.groq.com${RESET}"
echo -e "    Sign up with Google or GitHub (30 seconds)"
echo -e "    Click ${BOLD}API Keys${RESET} → ${BOLD}Create API Key${RESET}"
echo -e "    Copy the key (starts with gsk_)"
echo ""
echo -e "  ${CYAN}Step 2:${RESET} Set your key"
echo ""
echo -e "    ${GREEN}export GROQ_API_KEY=\"gsk_paste_your_key_here\"${RESET}"
echo ""
echo -e "  ${CYAN}Step 3:${RESET} Make it permanent (optional but recommended)"
echo ""

if [ -f "$HOME/.zshrc" ]; then
    echo -e "    ${GREEN}echo 'export GROQ_API_KEY=\"gsk_paste_your_key_here\"' >> ~/.zshrc${RESET}"
    echo -e "    ${GREEN}source ~/.zshrc${RESET}"
elif [ -f "$HOME/.bashrc" ]; then
    echo -e "    ${GREEN}echo 'export GROQ_API_KEY=\"gsk_paste_your_key_here\"' >> ~/.bashrc${RESET}"
    echo -e "    ${GREEN}source ~/.bashrc${RESET}"
else
    echo -e "    ${GREEN}echo 'export GROQ_API_KEY=\"gsk_paste_your_key_here\"' >> ~/.profile${RESET}"
    echo -e "    ${GREEN}source ~/.profile${RESET}"
fi

echo ""
echo -e "  ${CYAN}Step 4:${RESET} Initialize codereview"
echo ""
echo -e "    ${GREEN}codereview --init groq${RESET}"
echo ""
echo -e "  ${CYAN}Step 5:${RESET} Review any file"
echo ""
echo -e "    ${GREEN}codereview yourfile.py${RESET}"
echo ""
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${BOLD}OTHER OPTIONS${RESET}"
echo ""
echo -e "  ${YELLOW}OpenAI (paid):${RESET}"
echo -e "    export OPENAI_API_KEY=\"sk-...\""
echo -e "    codereview --init openai"
echo ""
echo -e "  ${YELLOW}Anthropic (paid):${RESET}"
echo -e "    export ANTHROPIC_API_KEY=\"sk-ant-...\""
echo -e "    codereview --init anthropic"
echo ""
echo -e "  ${YELLOW}Ollama (free, fully offline, no API key):${RESET}"
echo -e "    Install from https://ollama.com"
echo -e "    ollama pull llama3"
echo -e "    ollama serve"
echo -e "    codereview --init ollama"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${DIM}Need help later? Run: codereview --setup${RESET}"
echo -e "  ${DIM}Full docs: https://github.com/jaydendancer12/ai-code-review${RESET}"
echo ""

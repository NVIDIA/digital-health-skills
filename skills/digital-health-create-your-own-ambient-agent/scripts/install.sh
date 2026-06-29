#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# Install digital-health-create-your-own-ambient-agent and its skill dependencies for Claude Code.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

LANGCHAIN_SKILLS_DIR="$WORKSPACE_ROOT/references/reference-repos/langchain-skills/config/skills"
NEMOTRON_DEPLOY_SKILL_DIR="$WORKSPACE_ROOT/references/reference-repos/nemotron-voice-agent/.agents/skills/nemotron-voice-agent-deploy"

LANGCHAIN_SKILLS_TO_INSTALL=(
    "langgraph-fundamentals"
    "langchain-fundamentals"
    "langchain-dependencies"
    "langchain-rag"
)

GLOBAL=false
FORCE=false
YES=false
TARGET_DIR=""

usage() {
    echo "Usage: $0 [OPTIONS] [DIRECTORY]"
    echo ""
    echo "Install the digital-health-create-your-own-ambient-agent skill and its dependencies"
    echo "for Claude Code."
    echo ""
    echo "Arguments:"
    echo "  DIRECTORY         Target project directory (default: current directory)"
    echo "                    Ignored with --global"
    echo ""
    echo "Options:"
    echo "  --global, -g    Install globally (~/.claude/skills)"
    echo "  --force, -f     Overwrite skills that already exist"
    echo "  --yes, -y       Skip confirmation prompts"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Prerequisites (must be cloned into <workspace>/references/ before running):"
    echo "  git clone --recurse-submodules https://github.com/langchain-ai/langchain-skills \\"
    echo "      <workspace>/references/reference-repos/langchain-skills"
    echo "  git clone --recurse-submodules https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent \\"
    echo "      <workspace>/references/reference-repos/nemotron-voice-agent"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --global|-g) GLOBAL=true; shift ;;
        --force|-f)  FORCE=true;  shift ;;
        --yes|-y)    YES=true;    shift ;;
        --help|-h)   usage ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            if [ -n "$TARGET_DIR" ]; then
                echo "Error: multiple directories specified: '$TARGET_DIR' and '$1'"
                exit 1
            fi
            TARGET_DIR="$1"; shift ;;
    esac
done

if [ -z "$TARGET_DIR" ]; then
    TARGET_DIR="$(pwd)"
fi

if [ "$GLOBAL" = true ]; then
    INSTALL_DIR="$HOME/.claude"
else
    INSTALL_DIR="$TARGET_DIR/.claude"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ambient Agent SDD — Skill Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Target:    Claude Code"
echo "Location:  $INSTALL_DIR/skills"
if [ "$GLOBAL" = true ]; then
    echo "Scope:     Global (all projects)"
else
    echo "Scope:     Local ($TARGET_DIR)"
fi
echo ""
echo "Skills to install:"
echo "  • digital-health-create-your-own-ambient-agent"
for skill in "${LANGCHAIN_SKILLS_TO_INSTALL[@]}"; do
    echo "  • $skill"
done
echo "  • nemotron-voice-agent-deploy"
echo ""

fetch_langchain_skills() {
    mkdir -p "$WORKSPACE_ROOT/references/reference-repos"
    local dest="$WORKSPACE_ROOT/references/reference-repos/langchain-skills"
    echo "Attempting to fetch langchain-ai/langchain-skills..."
    rm -rf "$dest"
    git clone --recurse-submodules \
        https://github.com/langchain-ai/langchain-skills \
        "$dest"
    echo "✓ Cloned langchain-skills"
}

fetch_nemotron_voice_agent() {
    mkdir -p "$WORKSPACE_ROOT/references/reference-repos"
    local dest="$WORKSPACE_ROOT/references/reference-repos/nemotron-voice-agent"
    echo "Attempting to fetch NVIDIA-AI-Blueprints/nemotron-voice-agent..."
    rm -rf "$dest"
    git clone --recurse-submodules \
        https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent \
        "$dest"
    echo "✓ Cloned nemotron-voice-agent"
}

# Validate source directories exist before prompting. Try to fetch missing
# references once, because GitHub HTTPS may transiently fail in agent sandboxes.
MISSING=false
if [ ! -d "$LANGCHAIN_SKILLS_DIR" ]; then
    fetch_langchain_skills || MISSING=true
fi
if [ ! -d "$NEMOTRON_DEPLOY_SKILL_DIR" ]; then
    fetch_nemotron_voice_agent || MISSING=true
fi
if [ "$MISSING" = true ]; then
    echo "❌ Required helper references are still missing after the full clone attempt. Stop here and resolve the clone failure before invoking the skill."
    exit 1
fi

if [ "$YES" != true ]; then
    read -p "Proceed with installation? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

echo ""
echo "Installing..."
mkdir -p "$INSTALL_DIR/skills"

install_skill() {
    local src="$1"
    local name
    name="$(basename "$src")"
    local dest="$INSTALL_DIR/skills/$name"

    if [ -d "$dest" ]; then
        if [ "$FORCE" = true ]; then
            rm -rf "$dest"
        else
            echo "WARNING: Skipping $name (already exists; use --force to overwrite)"
            return
        fi
    fi

    cp -r "$src" "$dest"
    echo "✓ Installed $name"
}

# This skill
install_skill "$SKILL_DIR"

# Selected LangChain / LangGraph skills
for skill in "${LANGCHAIN_SKILLS_TO_INSTALL[@]}"; do
    install_skill "$LANGCHAIN_SKILLS_DIR/$skill"
done

# Nemotron deploy skill (includes its references/ sub-directory)
install_skill "$NEMOTRON_DEPLOY_SKILL_DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installed to: $INSTALL_DIR/skills/"
echo ""
echo "Start Claude Code and invoke:"
echo "  /digital-health-create-your-own-ambient-agent"

#!/bin/sh
set -e

echo "Waiting for Ollama..."
until curl -sf http://localhost:11434/api/tags >/dev/null; do
  sleep 2
done

echo "Pulling models..."
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
ollama pull phi4-mini:3.8b
ollama pull llava-phi3:mini

echo "Models ready."

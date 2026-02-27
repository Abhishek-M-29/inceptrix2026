#!/usr/bin/env bash
# start_services.sh — runs inside the container
# Starts the REST API and MCP servers as sibling processes, then waits.
set -e

echo "Starting REST API server  on port ${API_PORT:-8090} ..."
python3 api_server.py &
API_PID=$!

echo "Starting MCP server       on port ${MCP_PORT:-8091} ..."
python3 mcp_server.py &
MCP_PID=$!

echo ""
echo "Both servers running."
echo "  REST API  → http://0.0.0.0:${API_PORT:-8090}/"
echo "  MCP       → http://0.0.0.0:${MCP_PORT:-8091}/"
echo ""

# Exit if either process dies
wait -n $API_PID $MCP_PID
echo "A server process exited — shutting down."
kill $API_PID $MCP_PID 2>/dev/null || true

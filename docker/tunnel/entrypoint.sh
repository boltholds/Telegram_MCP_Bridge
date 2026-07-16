#!/bin/sh
set -eu
: "${TUNNEL_ID:?TUNNEL_ID is required}"
: "${CONTROL_PLANE_API_KEY:?CONTROL_PLANE_API_KEY is required}"
profile="${TUNNEL_PROFILE:-telegram-mcp}"
profile_dir="${TUNNEL_PROFILE_DIR:-/data/tunnel-client}"
mcp_url="${MCP_SERVER_URL:-http://telegram-bridge:8765/mcp/}"
tunnel-client init --force --profile "$profile" --profile-dir "$profile_dir" \
  --tunnel-id "$TUNNEL_ID" --mcp-server-url "$mcp_url" --health-listen-addr "0.0.0.0:8080"
exec tunnel-client run --profile "$profile" --profile-dir "$profile_dir"

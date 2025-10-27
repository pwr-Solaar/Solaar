#!/usr/bin/env bash
# Helper to install a LaunchAgent for Solaar to keep it running in the background.
set -euo pipefail

SOLAAR_PATH=${SOLAAR_PATH:-solaar}
SOLAAR_RESOLVED_PATH=$(command -v "${SOLAAR_PATH}" 2>/dev/null || echo "")
if [ -z "${SOLAAR_RESOLVED_PATH}" ]; then
    echo "Warning: '${SOLAAR_PATH}' not found" >&2
    SOLAAR_RESOLVED_PATH="${SOLAAR_PATH}"
fi

LAUNCH_AGENT_DIR="${HOME}/Library/LaunchAgents"
LAUNCH_AGENT_PLIST="${LAUNCH_AGENT_DIR}/io.github.pwr-solaar.solaar.plist"

mkdir -p "${LAUNCH_AGENT_DIR}"

echo "Creating LaunchAgent to keep Solaar running..."

# Unload if already loaded (suppress errors)
launchctl unload "${LAUNCH_AGENT_PLIST}" 2>/dev/null || true

cat > "${LAUNCH_AGENT_PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.github.pwr-solaar.solaar</string>
    <key>ProgramArguments</key>
    <array>
        <string>${SOLAAR_PATH}</string>
        <string>--window=hide</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/Library/Logs/solaar.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/Library/Logs/solaar.error.log</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

launchctl load "${LAUNCH_AGENT_PLIST}"

echo "LaunchAgent created at ${LAUNCH_AGENT_PLIST}"
echo ""
echo "To disable automatic startup:"
echo "  launchctl unload \"${LAUNCH_AGENT_PLIST}\""
echo ""
echo "To re-enable automatic startup:"
echo "  launchctl load \"${LAUNCH_AGENT_PLIST}\""
echo ""
echo "To start Solaar:"
echo "  launchctl start io.github.pwr-solaar.solaar"
echo ""
echo "To stop Solaar:"
echo "  launchctl stop io.github.pwr-solaar.solaar"
echo ""
echo "Logs will be written to:"
echo "  ${HOME}/Library/Logs/solaar.log"
echo "  ${HOME}/Library/Logs/solaar.error.log"

#!/usr/bin/env bash
# Upload every ready platform build in v/ to UCMS.UZ marketplace.
# Usage: bash upload-ucms.sh [linux] [windows] [mac]
set -u
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

TOKEN="${UCMS_TOKEN:-ucmsp_a5e2b9348851588b2073aca184a57ffdf3c5cd385f8b6aa6}"
API_URL="https://api.ucms.uz/api/v1/projects/versions"
VERSION="${UCMS_VERSION:-1.0.1}"

# Defaults for changelog + install instructions.  Apostrophes are
# ASCII-escaped so they can\047t break the shell.  Override via env.
DEFAULT_CHANGELOG=$'KO\047ZGU v1.9.18 - new name, new logo, Donate section, faster streaming, fully audited'
DEFAULT_INSTALL=$'Ikki marta bosib o\047rnating'
CHANGELOG="${UCMS_CHANGELOG:-$DEFAULT_CHANGELOG}"
INSTALL_UZ="${UCMS_INSTALL:-$DEFAULT_INSTALL}"

if [ -z "$TOKEN" ]; then
    echo "X UCMS_TOKEN not set" >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    PLATFORMS=(linux windows mac)
else
    PLATFORMS=("$@")
fi

find_file() {
    local pattern="$1"
    ls -1t "$SCRIPT_DIR"/$pattern 2>/dev/null | head -1
}

upload_one() {
    local platform="$1"
    local file="$2"

    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo "  x $platform: file not found"
        return 1
    fi

    local size_mb
    size_mb=$(du -m "$file" | awk '{print $1}')
    echo "  -> Uploading $platform ($size_mb MB): $file"

    local response status body
    response=$(curl -sS -w "\nHTTP_STATUS:%{http_code}" \
        -X POST "$API_URL" \
        -H "X-Project-Token: $TOKEN" \
        -F "platform=$platform" \
        -F "version=$VERSION" \
        -F "changelog=$CHANGELOG" \
        -F "install_instructions=$INSTALL_UZ" \
        -F "file=@${file}")
    status=$(echo "$response" | sed -n 's/.*HTTP_STATUS://p')
    body=$(echo "$response" | sed '$d')

    if [ "$status" = "200" ] || [ "$status" = "201" ]; then
        echo "    OK $platform uploaded (HTTP $status)"
        echo "    $body" | head -3
    else
        echo "    FAIL $platform (HTTP $status)"
        echo "    $body" | head -8
    fi
}

echo "===================================="
echo "  KO'ZGU -> UCMS.UZ uploader"
echo "  Version: $VERSION"
echo "  Platforms: ${PLATFORMS[*]}"
echo "===================================="

for p in "${PLATFORMS[@]}"; do
    case "$p" in
        linux)
            f=$(find_file "kozgu_*.deb")
            upload_one linux "$f"
            ;;
        windows|win)
            f=$(find_file "KOZGU-*-setup.exe")
            [ -z "$f" ] && f=$(find_file "*.exe")
            upload_one windows "$f"
            ;;
        mac|macos)
            f=$(find_file "KOZGU-*.dmg")
            [ -z "$f" ] && f=$(find_file "*.dmg")
            upload_one mac "$f"
            ;;
        *)
            echo "  Unknown platform: $p (use: linux | windows | mac)"
            ;;
    esac
    echo
done

echo "===================================="
echo "  Done."
echo "===================================="

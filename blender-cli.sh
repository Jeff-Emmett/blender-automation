#!/bin/bash
# Blender Automation CLI Wrapper
# Usage: ./blender-cli.sh [command] [options]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_DIR="$SCRIPT_DIR/blender-4.3.2-linux-x64"
BLENDER_BIN="$BLENDER_DIR/blender"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Blender is installed
check_blender() {
    if [[ ! -f "$BLENDER_BIN" ]]; then
        echo -e "${RED}Error: Blender not found at $BLENDER_BIN${NC}"
        echo "Run: cd $SCRIPT_DIR && tar -xf blender.tar.xz"
        exit 1
    fi
}

# Show help
show_help() {
    echo -e "${BLUE}Blender Automation CLI${NC}"
    echo ""
    echo "Usage: ./blender-cli.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  render          Render a .blend file or test scene"
    echo "  procedural      Generate procedural scenes"
    echo "  interactive     Open Blender with GUI"
    echo "  python          Run custom Python script"
    echo "  version         Show Blender version"
    echo "  help            Show this help"
    echo ""
    echo "Examples:"
    echo "  ./blender-cli.sh render --resolution 1920x1080"
    echo "  ./blender-cli.sh render --scene scene.blend --samples 256"
    echo "  ./blender-cli.sh procedural --preset abstract --complexity 7 --render"
    echo "  ./blender-cli.sh procedural --preset text3d --text 'HELLO' --render"
    echo "  ./blender-cli.sh procedural --preset landscape --seed 42 --render"
    echo "  ./blender-cli.sh python myscript.py -- --arg1 value"
    echo ""
    echo "Render options:"
    echo "  --scene FILE      Path to .blend file"
    echo "  --output DIR      Output directory (default: ./output)"
    echo "  --format FMT      PNG, JPEG, EXR, WEBP (default: PNG)"
    echo "  --resolution WxH  Resolution (default: 1920x1080)"
    echo "  --samples N       Render samples (default: 128)"
    echo "  --engine ENG      CYCLES, BLENDER_EEVEE_NEXT (default: CYCLES)"
    echo "  --device DEV      CPU or GPU (default: CPU)"
    echo "  --name PREFIX     Output filename prefix"
    echo "  --animation       Render animation"
    echo "  --start-frame N   Animation start frame"
    echo "  --end-frame N     Animation end frame"
    echo ""
    echo "Procedural presets:"
    echo "  abstract    Random geometric shapes"
    echo "  geometric   Grid-based patterns"
    echo "  landscape   Procedural terrain with trees"
    echo "  text3d      3D text (use --text 'YOUR TEXT')"
    echo "  particles   Particle system scene"
}

# Render command
cmd_render() {
    check_blender
    echo -e "${GREEN}Starting Blender render...${NC}"
    "$BLENDER_BIN" --background --python "$SCRIPTS_DIR/render.py" -- "$@"
}

# Procedural generation
cmd_procedural() {
    check_blender
    echo -e "${GREEN}Generating procedural scene...${NC}"
    "$BLENDER_BIN" --background --python "$SCRIPTS_DIR/procedural.py" -- "$@"
}

# Interactive mode
cmd_interactive() {
    check_blender
    echo -e "${GREEN}Opening Blender...${NC}"
    "$BLENDER_BIN" "$@"
}

# Custom Python script
cmd_python() {
    check_blender
    if [[ -z "$1" ]]; then
        echo -e "${RED}Error: Please specify a Python script${NC}"
        exit 1
    fi
    SCRIPT="$1"
    shift
    echo -e "${GREEN}Running Python script: $SCRIPT${NC}"
    "$BLENDER_BIN" --background --python "$SCRIPT" -- "$@"
}

# Version
cmd_version() {
    check_blender
    "$BLENDER_BIN" --version
}

# Main
case "$1" in
    render)
        shift
        cmd_render "$@"
        ;;
    procedural)
        shift
        cmd_procedural "$@"
        ;;
    interactive)
        shift
        cmd_interactive "$@"
        ;;
    python)
        shift
        cmd_python "$@"
        ;;
    version)
        cmd_version
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

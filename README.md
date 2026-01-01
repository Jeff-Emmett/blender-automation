# Blender Automation

Automated Blender rendering and procedural scene generation via CLI and Python API.

## Setup

1. Download Blender 4.3.2 (if not already present):
   ```bash
   cd /path/to/blender-automation
   wget "https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz" -O blender.tar.xz
   tar -xf blender.tar.xz
   ```

2. Make CLI executable:
   ```bash
   chmod +x blender-cli.sh
   ```

## Quick Start

### Render a Test Scene
```bash
./blender-cli.sh render --resolution 1920x1080 --samples 64
```

### Generate Procedural Art
```bash
# Abstract composition
./blender-cli.sh procedural --preset abstract --complexity 7 --render

# 3D Text
./blender-cli.sh procedural --preset text3d --text "HELLO WORLD" --render

# Landscape
./blender-cli.sh procedural --preset landscape --seed 42 --render

# Geometric patterns
./blender-cli.sh procedural --preset geometric --complexity 5 --render

# Particle effects
./blender-cli.sh procedural --preset particles --complexity 8 --render
```

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `render` | Render a .blend file or test scene |
| `procedural` | Generate procedural scenes |
| `interactive` | Open Blender with GUI |
| `python` | Run custom Python script |
| `version` | Show Blender version |
| `help` | Show help |

### Render Options

| Option | Default | Description |
|--------|---------|-------------|
| `--scene FILE` | (test scene) | Path to .blend file |
| `--output DIR` | `./output` | Output directory |
| `--format FMT` | `PNG` | PNG, JPEG, EXR, WEBP |
| `--resolution WxH` | `1920x1080` | Render resolution |
| `--samples N` | `128` | Render samples (Cycles) |
| `--engine ENG` | `CYCLES` | CYCLES, BLENDER_EEVEE_NEXT |
| `--device DEV` | `CPU` | CPU or GPU |
| `--name PREFIX` | `render` | Output filename prefix |
| `--animation` | - | Render animation |
| `--start-frame N` | `1` | Animation start |
| `--end-frame N` | `250` | Animation end |

### Procedural Presets

| Preset | Description |
|--------|-------------|
| `abstract` | Random geometric shapes with materials |
| `geometric` | Grid-based patterns and structures |
| `landscape` | Procedural terrain with trees |
| `text3d` | 3D metallic text (use `--text`) |
| `particles` | Particle system scene |

## Python API

```python
from scripts.api import BlenderAPI, RenderConfig, ProceduralConfig

api = BlenderAPI()

# Check version
print(api.get_version())

# Render a scene
config = RenderConfig(
    resolution="1920x1080",
    samples=128,
    engine="CYCLES"
)
output = api.render(config)

# Generate procedural art
config = ProceduralConfig(
    preset="abstract",
    complexity=7,
    seed=42
)
output = api.generate_procedural(config)
```

## Directory Structure

```
blender-automation/
├── blender-cli.sh          # CLI wrapper
├── blender-4.3.2-linux-x64/ # Blender installation (not in git)
├── scripts/
│   ├── render.py           # Render automation
│   ├── procedural.py       # Procedural generation
│   └── api.py              # Python API
├── templates/              # .blend templates
├── assets/                 # Textures, HDRIs, models
├── output/                 # Rendered outputs (not in git)
├── jobs/                   # Job queue files (not in git)
└── config/                 # Configuration files
```

## Examples

### Batch Rendering
```bash
# Render multiple presets
for preset in abstract geometric landscape; do
  ./blender-cli.sh procedural --preset $preset --render --complexity 5
done
```

### High Quality Render
```bash
./blender-cli.sh render \
  --scene my_scene.blend \
  --resolution 3840x2160 \
  --samples 512 \
  --engine CYCLES \
  --device CPU
```

### Animation
```bash
./blender-cli.sh render \
  --scene animation.blend \
  --animation \
  --start-frame 1 \
  --end-frame 120 \
  --format PNG
```

## GPU Rendering

For GPU rendering on systems with NVIDIA GPUs:
```bash
./blender-cli.sh render --device GPU --samples 256
```

Note: GPU rendering requires appropriate drivers and CUDA/OptiX support.

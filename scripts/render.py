#!/usr/bin/env python3
"""
Blender Render Automation Script
Run with: blender --background --python render.py -- [args]
"""

import bpy
import sys
import os
import argparse
import json
from pathlib import Path

# Get script directory for relative imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def parse_args():
    """Parse command line arguments after '--'"""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Blender render automation")
    parser.add_argument("--scene", type=str, help="Path to .blend file to render")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--format", type=str, default="PNG", choices=["PNG", "JPEG", "EXR", "WEBP"],
                        help="Output format")
    parser.add_argument("--resolution", type=str, default="1920x1080", help="Resolution WxH")
    parser.add_argument("--samples", type=int, default=128, help="Render samples")
    parser.add_argument("--frame", type=int, default=1, help="Frame to render")
    parser.add_argument("--animation", action="store_true", help="Render animation")
    parser.add_argument("--start-frame", type=int, default=1, help="Animation start frame")
    parser.add_argument("--end-frame", type=int, default=250, help="Animation end frame")
    parser.add_argument("--engine", type=str, default="CYCLES",
                        choices=["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"],
                        help="Render engine")
    parser.add_argument("--device", type=str, default="CPU", choices=["CPU", "GPU"],
                        help="Compute device")
    parser.add_argument("--name", type=str, default="render", help="Output filename prefix")

    return parser.parse_args(argv)


def setup_render_settings(args):
    """Configure render settings based on arguments"""
    scene = bpy.context.scene
    render = scene.render

    # Resolution
    width, height = map(int, args.resolution.split("x"))
    render.resolution_x = width
    render.resolution_y = height
    render.resolution_percentage = 100

    # Output format
    render.image_settings.file_format = args.format
    if args.format == "PNG":
        render.image_settings.color_mode = 'RGBA'
        render.image_settings.compression = 15
    elif args.format == "JPEG":
        render.image_settings.quality = 90
    elif args.format == "WEBP":
        render.image_settings.quality = 90

    # Render engine
    scene.render.engine = args.engine

    # Samples (for Cycles)
    if args.engine == "CYCLES":
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True

        # Device setup
        if args.device == "GPU":
            scene.cycles.device = 'GPU'
            # Enable GPU compute
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = 'CUDA'  # or 'OPTIX', 'HIP', 'ONEAPI'
            prefs.get_devices()
            for device in prefs.devices:
                device.use = True
        else:
            scene.cycles.device = 'CPU'

    # Output path
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ext = args.format.lower()
    if ext == "jpeg":
        ext = "jpg"

    render.filepath = str(output_dir / f"{args.name}_")

    return render.filepath


def render_still(args):
    """Render a single frame"""
    filepath = setup_render_settings(args)
    bpy.context.scene.frame_set(args.frame)

    ext = args.format.lower()
    if ext == "jpeg":
        ext = "jpg"

    output_path = f"{filepath}{args.frame:04d}.{ext}"
    bpy.context.scene.render.filepath = output_path

    print(f"Rendering frame {args.frame} to {output_path}")
    bpy.ops.render.render(write_still=True)

    print(f"Render complete: {output_path}")
    return output_path


def render_animation(args):
    """Render animation sequence"""
    filepath = setup_render_settings(args)
    scene = bpy.context.scene

    scene.frame_start = args.start_frame
    scene.frame_end = args.end_frame

    print(f"Rendering animation frames {args.start_frame}-{args.end_frame}")
    bpy.ops.render.render(animation=True)

    print(f"Animation render complete: {filepath}")
    return filepath


def create_simple_scene():
    """Create a simple test scene if no scene provided"""
    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Add a cube
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    cube = bpy.context.active_object
    cube.name = "TestCube"

    # Add material
    mat = bpy.data.materials.new(name="TestMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.5
        bsdf.inputs["Roughness"].default_value = 0.3
    cube.data.materials.append(mat)

    # Add light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3

    # Add camera
    bpy.ops.object.camera_add(location=(5, -5, 5))
    camera = bpy.context.active_object
    camera.rotation_euler = (1.1, 0, 0.8)
    bpy.context.scene.camera = camera

    # Add environment lighting
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.05, 0.05, 0.1, 1.0)
        bg.inputs["Strength"].default_value = 0.5

    print("Created simple test scene")


def main():
    args = parse_args()

    # Load scene or create test scene
    if args.scene and os.path.exists(args.scene):
        print(f"Loading scene: {args.scene}")
        bpy.ops.wm.open_mainfile(filepath=args.scene)
    else:
        print("No scene provided, creating test scene")
        create_simple_scene()

    # Render
    if args.animation:
        output = render_animation(args)
    else:
        output = render_still(args)

    print(f"\n{'='*50}")
    print(f"Render complete!")
    print(f"Output: {output}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

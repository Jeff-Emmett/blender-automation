#!/usr/bin/env python3
"""
Procedural Scene Generation for Blender
Run with: blender --background --python procedural.py -- [args]
"""

import bpy
import bmesh
import sys
import os
import math
import random
import argparse
from pathlib import Path
from mathutils import Vector, Euler

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Procedural scene generation")
    parser.add_argument("--preset", type=str, default="abstract",
                        choices=["abstract", "landscape", "geometric", "particles", "text3d"],
                        help="Scene preset to generate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--complexity", type=int, default=5, help="Scene complexity 1-10")
    parser.add_argument("--save", type=str, help="Save .blend file to this path")
    parser.add_argument("--render", action="store_true", help="Render after generation")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--text", type=str, default="BLENDER", help="Text for 3D text preset")
    parser.add_argument("--resolution", type=str, default="1920x1080", help="Render resolution")

    return parser.parse_args(argv)


def clear_scene():
    """Clear all objects from scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def create_material(name, color, metallic=0.0, roughness=0.5, emission=0.0):
    """Create a PBR material"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission > 0:
            bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission

    return mat


def setup_camera_and_lights():
    """Setup camera and lighting"""
    # Camera
    bpy.ops.object.camera_add(location=(10, -10, 8))
    camera = bpy.context.active_object
    camera.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))
    bpy.context.scene.camera = camera

    # Key light
    bpy.ops.object.light_add(type='AREA', location=(8, -5, 10))
    key_light = bpy.context.active_object
    key_light.data.energy = 500
    key_light.data.size = 5
    key_light.rotation_euler = Euler((math.radians(45), 0, math.radians(30)))

    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-5, -8, 5))
    fill_light = bpy.context.active_object
    fill_light.data.energy = 200
    fill_light.data.size = 3
    fill_light.data.color = (0.8, 0.9, 1.0)

    # Environment
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.02, 0.02, 0.05, 1.0)
        bg.inputs["Strength"].default_value = 0.3


def generate_abstract(complexity, seed):
    """Generate abstract geometric composition"""
    random.seed(seed)
    clear_scene()

    primitives = ['cube', 'sphere', 'cylinder', 'cone', 'torus']
    colors = [
        (0.9, 0.2, 0.3),   # Red
        (0.2, 0.6, 0.9),   # Blue
        (0.9, 0.7, 0.1),   # Yellow
        (0.3, 0.9, 0.5),   # Green
        (0.8, 0.3, 0.9),   # Purple
        (1.0, 0.5, 0.2),   # Orange
    ]

    num_objects = complexity * 3

    for i in range(num_objects):
        prim = random.choice(primitives)
        loc = (
            random.uniform(-5, 5),
            random.uniform(-5, 5),
            random.uniform(0, 5)
        )
        scale = random.uniform(0.3, 1.5)
        rot = (
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2),
            random.uniform(0, math.pi * 2)
        )

        if prim == 'cube':
            bpy.ops.mesh.primitive_cube_add(location=loc)
        elif prim == 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(location=loc, segments=32, ring_count=16)
        elif prim == 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(location=loc)
        elif prim == 'cone':
            bpy.ops.mesh.primitive_cone_add(location=loc)
        elif prim == 'torus':
            bpy.ops.mesh.primitive_torus_add(location=loc)

        obj = bpy.context.active_object
        obj.scale = (scale, scale, scale)
        obj.rotation_euler = rot

        # Apply material
        color = random.choice(colors)
        metallic = random.uniform(0, 1)
        roughness = random.uniform(0.1, 0.8)
        emission = random.uniform(0, 2) if random.random() > 0.7 else 0

        mat = create_material(f"AbstractMat_{i}", color, metallic, roughness, emission)
        obj.data.materials.append(mat)

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -0.1))
    ground = bpy.context.active_object
    ground_mat = create_material("Ground", (0.1, 0.1, 0.1), metallic=0.0, roughness=0.8)
    ground.data.materials.append(ground_mat)

    setup_camera_and_lights()
    print(f"Generated abstract scene with {num_objects} objects")


def generate_geometric(complexity, seed):
    """Generate geometric patterns and structures"""
    random.seed(seed)
    clear_scene()

    # Create a grid of objects
    grid_size = complexity
    spacing = 2.0

    for x in range(grid_size):
        for y in range(grid_size):
            for z in range(min(complexity, 3)):
                if random.random() > 0.3:
                    loc = (
                        (x - grid_size / 2) * spacing,
                        (y - grid_size / 2) * spacing,
                        z * spacing
                    )

                    bpy.ops.mesh.primitive_cube_add(location=loc, size=spacing * 0.8)
                    obj = bpy.context.active_object

                    # Gradient color based on position
                    hue = (x + y + z) / (grid_size * 2 + complexity)
                    color = (
                        0.5 + 0.5 * math.sin(hue * math.pi * 2),
                        0.5 + 0.5 * math.sin(hue * math.pi * 2 + 2.094),
                        0.5 + 0.5 * math.sin(hue * math.pi * 2 + 4.189)
                    )

                    mat = create_material(f"GeoMat_{x}_{y}_{z}", color, 0.8, 0.2)
                    obj.data.materials.append(mat)

    setup_camera_and_lights()
    print(f"Generated geometric grid scene")


def generate_landscape(complexity, seed):
    """Generate procedural landscape"""
    random.seed(seed)
    clear_scene()

    # Create terrain
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "Terrain"

    # Subdivide for detail
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=complexity * 10)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Displace vertices for terrain
    mesh = terrain.data
    for vert in mesh.vertices:
        noise_val = (
            math.sin(vert.co.x * 0.5) * math.cos(vert.co.y * 0.5) +
            random.uniform(-0.2, 0.2)
        )
        vert.co.z = noise_val * (complexity / 5)

    # Terrain material
    terrain_mat = create_material("Terrain", (0.2, 0.5, 0.2), 0.0, 0.9)
    terrain.data.materials.append(terrain_mat)

    # Add trees (simple cones)
    num_trees = complexity * 5
    for i in range(num_trees):
        x = random.uniform(-8, 8)
        y = random.uniform(-8, 8)
        # Sample terrain height (approximate)
        z = math.sin(x * 0.5) * math.cos(y * 0.5) * (complexity / 5)

        bpy.ops.mesh.primitive_cone_add(
            location=(x, y, z + 1),
            radius1=0.5,
            depth=2
        )
        tree = bpy.context.active_object
        tree_mat = create_material(f"Tree_{i}", (0.1, 0.4, 0.1), 0.0, 0.8)
        tree.data.materials.append(tree_mat)

    setup_camera_and_lights()

    # Adjust camera for landscape view
    cam = bpy.context.scene.camera
    cam.location = (15, -15, 10)
    cam.rotation_euler = Euler((math.radians(60), 0, math.radians(45)))

    print(f"Generated landscape with {num_trees} trees")


def generate_text3d(text, complexity, seed):
    """Generate 3D text"""
    random.seed(seed)
    clear_scene()

    # Create 3D text
    bpy.ops.object.text_add(location=(0, 0, 0))
    text_obj = bpy.context.active_object
    text_obj.data.body = text

    # Extrude and bevel
    text_obj.data.extrude = 0.3
    text_obj.data.bevel_depth = 0.05
    text_obj.data.bevel_resolution = 3

    # Center text
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    text_obj.location = (0, 0, 0)

    # Material with gradient
    mat = bpy.data.materials.new(name="TextMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Base Color"].default_value = (0.8, 0.6, 0.2, 1.0)  # Gold

    text_obj.data.materials.append(mat)

    # Add floor
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.5))
    floor = bpy.context.active_object
    floor_mat = create_material("Floor", (0.02, 0.02, 0.02), 0.0, 0.1)
    floor.data.materials.append(floor_mat)

    setup_camera_and_lights()

    # Adjust camera for text
    cam = bpy.context.scene.camera
    text_bounds = text_obj.dimensions
    cam_dist = max(text_bounds.x, text_bounds.y) * 1.5 + 5
    cam.location = (0, -cam_dist, cam_dist * 0.5)
    cam.rotation_euler = Euler((math.radians(60), 0, 0))

    print(f"Generated 3D text: '{text}'")


def generate_particles(complexity, seed):
    """Generate particle-based scene"""
    random.seed(seed)
    clear_scene()

    # Emitter object
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=2, location=(0, 0, 3))
    emitter = bpy.context.active_object
    emitter.name = "Emitter"

    # Add particle system
    bpy.ops.object.particle_system_add()
    ps = emitter.particle_systems[0]
    ps.settings.count = complexity * 500
    ps.settings.lifetime = 50
    ps.settings.emit_from = 'FACE'
    ps.settings.physics_type = 'NEWTON'
    ps.settings.normal_factor = 2.0
    ps.settings.factor_random = 0.5
    ps.settings.render_type = 'OBJECT'

    # Particle object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(100, 0, 0))
    particle_obj = bpy.context.active_object
    particle_obj.name = "ParticleObject"
    ps.settings.instance_object = particle_obj

    particle_mat = create_material("ParticleMat", (0.9, 0.5, 0.1), 0.3, 0.3, emission=2.0)
    particle_obj.data.materials.append(particle_mat)

    # Ground
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground_mat = create_material("Ground", (0.05, 0.05, 0.08), 0.0, 0.5)
    ground.data.materials.append(ground_mat)

    # Make emitter invisible in render
    emitter_mat = create_material("EmitterMat", (0.2, 0.2, 0.2), 0.5, 0.5)
    emitter.data.materials.append(emitter_mat)

    setup_camera_and_lights()

    # Set frame for particles to show
    bpy.context.scene.frame_set(25)

    print(f"Generated particle scene with {complexity * 500} particles")


def main():
    args = parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    print(f"Using seed: {seed}")

    # Generate scene based on preset
    if args.preset == "abstract":
        generate_abstract(args.complexity, seed)
    elif args.preset == "geometric":
        generate_geometric(args.complexity, seed)
    elif args.preset == "landscape":
        generate_landscape(args.complexity, seed)
    elif args.preset == "text3d":
        generate_text3d(args.text, args.complexity, seed)
    elif args.preset == "particles":
        generate_particles(args.complexity, seed)

    # Save .blend file if requested
    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
        print(f"Saved: {save_path}")

    # Render if requested
    if args.render:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        width, height = map(int, args.resolution.split("x"))
        bpy.context.scene.render.resolution_x = width
        bpy.context.scene.render.resolution_y = height
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.samples = 64
        bpy.context.scene.cycles.use_denoising = True

        output_path = str(output_dir / f"{args.preset}_{seed}.png")
        bpy.context.scene.render.filepath = output_path
        bpy.context.scene.render.image_settings.file_format = 'PNG'

        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {output_path}")


if __name__ == "__main__":
    main()

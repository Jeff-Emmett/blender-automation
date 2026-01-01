#!/usr/bin/env python3
"""
Blender Automation API
Provides a Python interface for Blender operations.
Can be used standalone or imported into other scripts.
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Literal
from datetime import datetime
import shutil

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BLENDER_DIR = PROJECT_ROOT / "blender-4.3.2-linux-x64"
BLENDER_BIN = BLENDER_DIR / "blender"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
JOBS_DIR = PROJECT_ROOT / "jobs"


@dataclass
class RenderConfig:
    """Render configuration"""
    scene: Optional[str] = None
    output_dir: str = str(OUTPUT_DIR)
    format: Literal["PNG", "JPEG", "EXR", "WEBP"] = "PNG"
    resolution: str = "1920x1080"
    samples: int = 128
    engine: Literal["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"] = "CYCLES"
    device: Literal["CPU", "GPU"] = "CPU"
    name: str = "render"
    frame: int = 1
    animation: bool = False
    start_frame: int = 1
    end_frame: int = 250

    def to_args(self) -> List[str]:
        """Convert to command line arguments"""
        args = [
            f"--output={self.output_dir}",
            f"--format={self.format}",
            f"--resolution={self.resolution}",
            f"--samples={self.samples}",
            f"--engine={self.engine}",
            f"--device={self.device}",
            f"--name={self.name}",
            f"--frame={self.frame}",
        ]
        if self.scene:
            args.append(f"--scene={self.scene}")
        if self.animation:
            args.extend([
                "--animation",
                f"--start-frame={self.start_frame}",
                f"--end-frame={self.end_frame}",
            ])
        return args


@dataclass
class ProceduralConfig:
    """Procedural generation configuration"""
    preset: Literal["abstract", "geometric", "landscape", "text3d", "particles"] = "abstract"
    seed: Optional[int] = None
    complexity: int = 5
    text: str = "BLENDER"
    output_dir: str = str(OUTPUT_DIR)
    resolution: str = "1920x1080"
    save_blend: Optional[str] = None
    render: bool = True

    def to_args(self) -> List[str]:
        args = [
            f"--preset={self.preset}",
            f"--complexity={self.complexity}",
            f"--text={self.text}",
            f"--output={self.output_dir}",
            f"--resolution={self.resolution}",
        ]
        if self.seed is not None:
            args.append(f"--seed={self.seed}")
        if self.save_blend:
            args.append(f"--save={self.save_blend}")
        if self.render:
            args.append("--render")
        return args


@dataclass
class RenderJob:
    """Represents a render job"""
    id: str
    type: Literal["render", "procedural"]
    config: dict
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class BlenderAPI:
    """Python API for Blender automation"""

    def __init__(self, blender_path: Optional[Path] = None):
        self.blender_bin = blender_path or BLENDER_BIN
        self.scripts_dir = SCRIPT_DIR
        self.output_dir = OUTPUT_DIR
        self.jobs_dir = JOBS_DIR

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def check_blender(self) -> bool:
        """Check if Blender is installed"""
        return self.blender_bin.exists()

    def get_version(self) -> str:
        """Get Blender version"""
        if not self.check_blender():
            raise RuntimeError("Blender not found")

        result = subprocess.run(
            [str(self.blender_bin), "--version"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def _run_script(self, script: str, args: List[str]) -> subprocess.CompletedProcess:
        """Run a Blender Python script"""
        if not self.check_blender():
            raise RuntimeError("Blender not found")

        script_path = self.scripts_dir / script
        cmd = [
            str(self.blender_bin),
            "--background",
            "--python", str(script_path),
            "--"
        ] + args

        print(f"Running: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True)

    def render(self, config: RenderConfig) -> str:
        """Render a scene"""
        result = self._run_script("render.py", config.to_args())

        if result.returncode != 0:
            raise RuntimeError(f"Render failed: {result.stderr}")

        # Find output file
        ext = config.format.lower()
        if ext == "jpeg":
            ext = "jpg"

        output_path = Path(config.output_dir) / f"{config.name}_{config.frame:04d}.{ext}"

        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")

        return str(output_path)

    def generate_procedural(self, config: ProceduralConfig) -> str:
        """Generate a procedural scene"""
        result = self._run_script("procedural.py", config.to_args())

        if result.returncode != 0:
            raise RuntimeError(f"Generation failed: {result.stderr}")

        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")

        # Find output - parse from stdout
        for line in result.stdout.split('\n'):
            if "Rendered:" in line:
                return line.split("Rendered:")[-1].strip()

        return str(self.output_dir)

    def run_python_script(self, script_path: str, args: List[str] = None) -> subprocess.CompletedProcess:
        """Run a custom Python script in Blender"""
        if not self.check_blender():
            raise RuntimeError("Blender not found")

        cmd = [
            str(self.blender_bin),
            "--background",
            "--python", script_path,
        ]

        if args:
            cmd.append("--")
            cmd.extend(args)

        return subprocess.run(cmd, capture_output=True, text=True)

    def create_job(self, job_type: str, config: dict) -> RenderJob:
        """Create a new render job"""
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        job = RenderJob(
            id=job_id,
            type=job_type,
            config=config
        )

        job_file = self.jobs_dir / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(asdict(job), f, indent=2)

        return job

    def run_job(self, job: RenderJob) -> RenderJob:
        """Execute a render job"""
        job.status = "running"
        self._save_job(job)

        try:
            if job.type == "render":
                config = RenderConfig(**job.config)
                output = self.render(config)
            elif job.type == "procedural":
                config = ProceduralConfig(**job.config)
                output = self.generate_procedural(config)
            else:
                raise ValueError(f"Unknown job type: {job.type}")

            job.status = "completed"
            job.output_path = output
            job.completed_at = datetime.now().isoformat()

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now().isoformat()

        self._save_job(job)
        return job

    def _save_job(self, job: RenderJob):
        """Save job state to disk"""
        job_file = self.jobs_dir / f"{job.id}.json"
        with open(job_file, 'w') as f:
            json.dump(asdict(job), f, indent=2)

    def list_jobs(self) -> List[RenderJob]:
        """List all jobs"""
        jobs = []
        for job_file in self.jobs_dir.glob("*.json"):
            with open(job_file) as f:
                data = json.load(f)
                jobs.append(RenderJob(**data))
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def list_outputs(self) -> List[Path]:
        """List all output files"""
        outputs = list(self.output_dir.glob("*.png"))
        outputs.extend(self.output_dir.glob("*.jpg"))
        outputs.extend(self.output_dir.glob("*.exr"))
        outputs.extend(self.output_dir.glob("*.webp"))
        return sorted(outputs, key=lambda p: p.stat().st_mtime, reverse=True)


def main():
    """CLI interface for the API"""
    import argparse

    parser = argparse.ArgumentParser(description="Blender Automation API")
    parser.add_argument("command", choices=["version", "render", "procedural", "jobs", "outputs"])
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Add all config options
    parser.add_argument("--scene", type=str)
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR))
    parser.add_argument("--format", type=str, default="PNG")
    parser.add_argument("--resolution", type=str, default="1920x1080")
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--engine", type=str, default="CYCLES")
    parser.add_argument("--device", type=str, default="CPU")
    parser.add_argument("--name", type=str, default="render")
    parser.add_argument("--preset", type=str, default="abstract")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--complexity", type=int, default=5)
    parser.add_argument("--text", type=str, default="BLENDER")

    args = parser.parse_args()

    api = BlenderAPI()

    if args.command == "version":
        if api.check_blender():
            print(api.get_version())
        else:
            print("Blender not installed")
            sys.exit(1)

    elif args.command == "render":
        config = RenderConfig(
            scene=args.scene,
            output_dir=args.output,
            format=args.format,
            resolution=args.resolution,
            samples=args.samples,
            engine=args.engine,
            device=args.device,
            name=args.name,
        )
        output = api.render(config)
        if args.json:
            print(json.dumps({"output": output}))
        else:
            print(f"Output: {output}")

    elif args.command == "procedural":
        config = ProceduralConfig(
            preset=args.preset,
            seed=args.seed,
            complexity=args.complexity,
            text=args.text,
            output_dir=args.output,
            resolution=args.resolution,
        )
        output = api.generate_procedural(config)
        if args.json:
            print(json.dumps({"output": output}))
        else:
            print(f"Output: {output}")

    elif args.command == "jobs":
        jobs = api.list_jobs()
        if args.json:
            print(json.dumps([asdict(j) for j in jobs], indent=2))
        else:
            for job in jobs[:10]:
                print(f"{job.id} [{job.status}] {job.type}")

    elif args.command == "outputs":
        outputs = api.list_outputs()
        if args.json:
            print(json.dumps([str(o) for o in outputs], indent=2))
        else:
            for output in outputs[:10]:
                print(output)


if __name__ == "__main__":
    main()

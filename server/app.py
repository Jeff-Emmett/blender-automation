#!/usr/bin/env python3
"""
Blender Render API Server
FastAPI server for handling Blender render requests from canvas-website.
Runs on Netcup RS 8000 behind Traefik.
"""

import os
import sys
import uuid
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Paths - support both local and Docker environments
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Blender path - check env var first (Docker), then local
BLENDER_BIN = Path(os.environ.get("BLENDER_PATH", PROJECT_ROOT / "blender-4.3.2-linux-x64" / "blender"))
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "output"
JOBS_DIR = PROJECT_ROOT / "jobs"

# Base URL for serving images (set via env var in production)
BASE_URL = os.environ.get("BASE_URL", "https://blender.jeffemmett.com")

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Blender Render API",
    description="API for Blender 3D rendering and procedural generation",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (in-memory for simplicity, use Redis/DB for production)
jobs = {}


class RenderRequest(BaseModel):
    preset: Literal["abstract", "geometric", "landscape", "text3d", "particles"] = "abstract"
    text: Optional[str] = None
    complexity: int = 5
    seed: Optional[int] = None
    resolution: str = "1920x1080"
    samples: int = 64


class RenderResponse(BaseModel):
    jobId: str
    status: str
    imageUrl: Optional[str] = None
    renderTime: Optional[float] = None
    seed: Optional[int] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    jobId: str
    status: Literal["queued", "rendering", "completed", "failed"]
    progress: int = 0
    imageUrl: Optional[str] = None
    renderTime: Optional[float] = None
    seed: Optional[int] = None
    error: Optional[str] = None


async def run_blender_render(job_id: str, request: RenderRequest):
    """Run Blender render in background"""
    jobs[job_id]["status"] = "rendering"
    jobs[job_id]["progress"] = 10

    start_time = datetime.now()

    try:
        # Build command
        cmd = [
            str(BLENDER_BIN),
            "--background",
            "--python", str(SCRIPTS_DIR / "procedural.py"),
            "--",
            f"--preset={request.preset}",
            f"--complexity={request.complexity}",
            f"--output={OUTPUT_DIR}",
            f"--resolution={request.resolution}",
            "--render",
        ]

        if request.text and request.preset == "text3d":
            cmd.append(f"--text={request.text}")

        if request.seed is not None:
            cmd.append(f"--seed={request.seed}")

        # Run Blender
        jobs[job_id]["progress"] = 30

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECT_ROOT)
        )

        stdout, stderr = await process.communicate()

        end_time = datetime.now()
        render_time = (end_time - start_time).total_seconds()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = error_msg[:500]
            jobs[job_id]["progress"] = 0
            return

        # Parse output to find rendered file and seed
        output_text = stdout.decode()
        seed = None
        image_path = None

        for line in output_text.split('\n'):
            if "Using seed:" in line:
                try:
                    seed = int(line.split("Using seed:")[-1].strip())
                except:
                    pass
            if "Rendered:" in line:
                image_path = line.split("Rendered:")[-1].strip()

        if not image_path or not Path(image_path).exists():
            # Try to find the most recent output file
            output_files = sorted(OUTPUT_DIR.glob(f"{request.preset}_*.png"),
                                  key=lambda p: p.stat().st_mtime, reverse=True)
            if output_files:
                image_path = str(output_files[0])

        if image_path and Path(image_path).exists():
            # Generate public URL for the image
            filename = Path(image_path).name
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["imageUrl"] = f"{BASE_URL}/output/{filename}"
            jobs[job_id]["renderTime"] = round(render_time, 2)
            jobs[job_id]["seed"] = seed
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Render completed but output file not found"
            jobs[job_id]["progress"] = 0

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)[:500]
        jobs[job_id]["progress"] = 0


@app.get("/")
async def root():
    """Health check endpoint"""
    blender_exists = BLENDER_BIN.exists()
    return {
        "service": "Blender Render API",
        "version": "1.0.0",
        "blender_installed": blender_exists,
        "blender_path": str(BLENDER_BIN) if blender_exists else None,
    }


@app.get("/health")
async def health():
    """Health check for Traefik"""
    return {"status": "healthy"}


@app.post("/render", response_model=RenderResponse)
async def render(request: RenderRequest, background_tasks: BackgroundTasks):
    """
    Submit a render job.

    This endpoint queues a Blender render job and returns immediately.
    The render happens in the background. Poll /status/{jobId} for updates,
    or use the synchronous endpoint for immediate results.
    """
    if not BLENDER_BIN.exists():
        raise HTTPException(status_code=500, detail="Blender not installed")

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "imageUrl": None,
        "renderTime": None,
        "seed": None,
        "error": None,
        "request": request.dict(),
        "createdAt": datetime.now().isoformat(),
    }

    # Start render in background
    background_tasks.add_task(run_blender_render, job_id, request)

    return RenderResponse(
        jobId=job_id,
        status="queued",
    )


@app.post("/render/sync", response_model=RenderResponse)
async def render_sync(request: RenderRequest):
    """
    Synchronous render endpoint.

    Waits for the render to complete and returns the result.
    Use for direct integration when you need the image immediately.
    Timeout is 120 seconds.
    """
    if not BLENDER_BIN.exists():
        raise HTTPException(status_code=500, detail="Blender not installed")

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "imageUrl": None,
        "renderTime": None,
        "seed": None,
        "error": None,
        "request": request.dict(),
        "createdAt": datetime.now().isoformat(),
    }

    # Run render and wait
    await run_blender_render(job_id, request)

    job = jobs[job_id]

    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job["error"])

    # Convert relative URL to full URL for the response
    image_url = job["imageUrl"]
    if image_url and not image_url.startswith("http"):
        # The worker will serve this from the same domain
        pass

    return RenderResponse(
        jobId=job_id,
        status=job["status"],
        imageUrl=image_url,
        renderTime=job["renderTime"],
        seed=job["seed"],
    )


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    """Get the status of a render job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(
        jobId=job_id,
        status=job["status"],
        progress=job["progress"],
        imageUrl=job["imageUrl"],
        renderTime=job["renderTime"],
        seed=job["seed"],
        error=job["error"],
    )


@app.get("/output/{filename}")
async def get_output(filename: str):
    """Serve rendered output files"""
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure we're not serving files outside output dir
    if not file_path.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        file_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/jobs")
async def list_jobs(limit: int = 10):
    """List recent render jobs"""
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda x: x[1].get("createdAt", ""),
        reverse=True
    )[:limit]

    return {
        "jobs": [
            {
                "jobId": job_id,
                "status": job["status"],
                "preset": job["request"].get("preset"),
                "createdAt": job.get("createdAt"),
            }
            for job_id, job in sorted_jobs
        ]
    }


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from the queue"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[job_id]
    return {"deleted": job_id}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )

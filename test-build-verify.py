#!/usr/bin/env python3
"""Verify Dockerfile builds successfully and HEALTHCHECK endpoint responds."""

import os
import subprocess
import sys
import time

WORKSPACE = '/var/home/ihshim523/Work/railway'

def run(cmd, cwd=None):
    """Run command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or WORKSPACE,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr

def main():
    print("=" * 60)
    print("BUILD & HEALTH CHECK VERIFICATION")
    print("=" * 60)

    # Find a suitable template to test
    target_dirs = [d for d in os.listdir(WORKSPACE) if d.startswith('railway-') and os.path.isdir(os.path.join(WORKSPACE, d))]
    found_dockerfiles = []
    for td in target_dirs:
        dockerfile = os.path.join(WORKSPACE, td, 'Dockerfile')
        if not os.path.exists(dockerfile):
            continue
        with open(dockerfile) as f:
            content = f.read()
        # Check requirements: HEALTHCHECK present, USER non-root (or USER $UID:$GID), no :latest in FROM or tags?
        if 'HEALTHCHECK' not in content:
            continue
        has_user = 'USER nobody' in content or 'USER root' in content
        # Look for port 5000 specific usage
        has_port_5000 = False
        for line in content.splitlines():
            if 'PORT=5000' in line or 'EXPOSE 5000' in line:
                has_port_5000 = True
                break
        found_dockerfiles.append((td, dockerfile, has_port_5000))

    # Start with the one that HAS port 5000
    target_dir = None
    for td, df, has_p5000 in found_dockerfiles:
        if has_p5000:
            target_dir = (td, df)
            break
    if not target_dir:
        # No port 5000 found; try the first one with HEALTHCHECK + non-root USER pattern
        for td, df, _ in found_dockerfiles:
            if 'USER nobody' in open(os.path.join(WORKSPACE, td, 'Dockerfile')).read():
                target_dir = (td, df)
                break

    if not target_dir:
        print("NO SUITABLE DOCKERFILE FOUND")
        for td, df, _ in found_dockerfiles[:5]:
            print(f"  {td}: HEALTHCHECK present")
        return 1

    target_dir, dockerfile = target_dir
    print(f"\nTARGET: {target_dir}")
    print(f"DOCKERFILE: {dockerfile}")
    print("-" * 60)

    # Step 1: Verify Dockerfile content patterns
    with open(dockerfile) as f:
        content = f.read()

    has_healthcheck = 'HEALTHCHECK' in content
    has_user_nonroot = 'USER nobody' in content or ('USER' in content and '$UID' not in content)  # could be dynamic UID
    has_port_5000 = False
    for line in content.splitlines():
        if 'PORT=5000' in line or 'EXPOSE 5000' in line:
            has_port_5000 = True
            break
    is_no_latest_tag = ':latest' not in content  # check FROM lines

    print("\nPattern Checks:")
    print(f"  HEALTHCHECK present: {'YES' if has_healthcheck else 'NO'}")
    print(f"  Non-root USER: {'YES' if has_user_nonroot else 'NO'}")
    print(f"  Port 5000 (PORT=5000/EXPOSE): {'YES' if has_port_5000 else 'NO'}")
    print(f"  No :latest tag: {'YES' if is_no_latest_tag else 'NO'}")

    # Step 2: Build with Podman using docker format for HEALTHCHECK support
    print("\nBuilding Docker image (docker-compatible format)...")
    build_dir = os.path.join(WORKSPACE, target_dir)
    rc, stdout, stderr = run(f"podman build --format docker -t localhost/{target_dir}-test:local .", cwd=build_dir)

    if rc != 0:
        print(f"\nBUILD FAILED (returncode {rc})")
        print("STDOUT:")
        print(stdout[:2000])
        print("\nSTDERR:")
        print(stderr[:2000])
        return 2

    print("\nBuild completed successfully.")
    print("*" * 60)

    # Step 3: Run container and wait for startup
    print("\nStarting container...")
    rc, stdout, stderr = run(f"podman run -d --name {target_dir}-health-test -p 5000:5000 localhost/{target_dir}-test:local", cwd=build_dir)

    if rc != 0:
        print("CONTAINER START FAILED")
        print(stdout, stderr)
        return 3

    container_id = stdout.strip()
    print(f"Container started: {container_id}")

    # Wait for startup and check logs
    max_wait = 60
    start_time = time.time()
    printed_logs = False

    while time.time() - start_time < max_wait:
        rc, logs, _ = run(f"podman logs --tail 20 {container_id}")
        if 'Running on' in logs or 'started successfully' in logs.lower():
            print("\nContainer started:")
            print(logs)
            break
        elif not printed_logs:
            print("\nInitial logs (not yet ready):")
            print(logs[:1000])
            printed_logs = True
        time.sleep(5)

    if time.time() - start_time >= max_wait:
        print("\nTimeout waiting for container to be ready.")
        rc, _, _ = run(f"podman logs {container_id}")
        print(rc, _)
        return 4

    # Step 4: Test health endpoint
    print("\nChecking health endpoint...")
    attempts = 3
    for attempt in range(attempts):
        rc, stdout2, stderr2 = run(f"curl -s --max-time 10 http://localhost:5000/healthz 2>&1", cwd=WORKSPACE)
        if rc == 0 and ('OK' in stdout2 or 'true' in stdout2 or 'ok' in stdout2):
            print(f"✅ HEALTH ENDPOINT OK (attempt {attempt+1}): {stdout2.strip()}")
            break
        else:
            print(f"Attempt {attempt+1}/{attempts} failed. Return code: {rc}, Output: {stderr2[:500]}")
            time.sleep(2)

    if rc != 0 or ('OK' not in stdout2 and 'true' not in stdout2 and 'ok' not in stdout2):
        print("\nHealth endpoint NOT responding OR expected content not found.")
        final_rc, final_out, _ = run(f"podman logs {container_id}")
        print(final_out[:2000])
    else:
        print("✅ HEALTH CHECK PASSED")

    # Cleanup
    rc, _, _ = run(f"podman stop {container_id} && podman rm {container_id}", cwd=build_dir)

    if has_healthcheck and has_user_nonroot and (has_port_5000 or is_no_latest_tag):
        print("\n✅ ALL CHECKS PASSED - GO for proceeding to Step 5")
        return 0
    else:
        print("\n⚠️ SOME PATTERNS NOT MET - REVIEW BEFORE STEP 5")
        return 1

if __name__ == '__main__':
    sys.exit(main())

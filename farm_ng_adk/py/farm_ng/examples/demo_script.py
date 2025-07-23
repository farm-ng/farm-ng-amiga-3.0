import argparse
import asyncio
import logging
import subprocess
from pathlib import Path

from farm_ng import Amiga, nexus as apb


async def run_remote_snapshot_script(user: str, host: str, remote_script: str) -> None:
    ssh_command = [
        "ssh",
        f"{user}@{host}",
        f"bash -c 'source ~/venv/bin/activate && python3 {remote_script}'",
    ]

    try:
        result = subprocess.run(ssh_command, check=True)
        print("Remote script finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Remote script failed with exit code {e.returncode}")


async def main(address: str, user: str, track_dir: str) -> None:
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    track_dir = Path(args.track_dir)
    track_paths = sorted(track_dir.glob("*.json"))

    async def post_job_tasks(route_name: str) -> None:
        # segment finished:
        # > Get Timestamp
        # > Record 0.5 second log; RGB data from Oak1
        # > Engage implement for 2 seconds
        await amiga.activate_tool(0, "hbridge", -2)

        await asyncio.sleep(3)

        # Take a snapshot
        await run_remote_snapshot_script(
            user=f"farm-ng-user-{user}",
            host=address,
            remote_script=f"/mnt/managed_home/farm-ng-user-{user}/oak_snapshot.py",
        )

        # > Disengage implement for 2 seconds
        await amiga.activate_tool(0, "hbridge", 2)

        await asyncio.sleep(3)

        await amiga.deactivate_tool(0, "hbridge")

    async def wait_for_mode(mode: apb.NavigationMode) -> None:
        stop_event = asyncio.Event()

        async def feedback_callback(feedback: apb.Feedback) -> None:
            if feedback.HasField("navigation") and feedback.navigation.mode == mode:
                stop_event.set()

        async with amiga.feedback_sub(feedback_callback):
            await stop_event.wait()

    async def run_track(path: str) -> None:
        print(f"Waiting to be IDLE before starting {path}")
        await wait_for_mode(apb.NavigationMode.NAVIGATION_MODE_IDLE)

        print(f"Sending route: {path}")
        await amiga.repeat_route_from_lon_lats(path)

        print(f"Waiting to detect REPEAT_ROUTE for {path}")
        await wait_for_mode(apb.NavigationMode.NAVIGATION_MODE_REPEAT_ROUTE)

        print(f"Waiting to detect IDLE after {path}")
        await wait_for_mode(apb.NavigationMode.NAVIGATION_MODE_IDLE)

        print(f"Running post-job task for {path}")
        await post_job_tasks(path)

    try:
        print("Starting route repetition...")
        while True:
            for path in track_paths:
                await run_track(str(path))

    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and stream camera data"
    )

    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga robot",
    )

    parser.add_argument(
        "--user",
        type=str,
        help="Username for SSH connection to the remote host",
    )

    parser.add_argument(
        "--track_dir",
        type=str,
        help="Directory containing the track files",
    )

    args = parser.parse_args()
    asyncio.run(main(args.address, args.user, args.track_dir))

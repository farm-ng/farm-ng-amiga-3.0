import argparse
import asyncio
import logging
import time

from farm_ng import Amiga, nexus as apb

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    async def post_job_tasks() -> None:
        # segment finished:
        # > Get Timestamp
        # > Record 0.5 second log; RGB data from Oak1
        # > Engage implement for 2 seconds
        await amiga.activate_tool(0, "hbridge", -2)
        
        await asyncio.sleep(2)
        
        # > Disengage implement for 2 seconds
        await amiga.activate_tool(0, "hbridge", 2)
        
        await asyncio.sleep(3)
        
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
        await post_job_tasks()
                
    try:
        print("Starting route repetition...")
        while True:
            for path in [
                "/home/rusty/projects/tracks/orica1.json",
                "/home/rusty/projects/tracks/orica2.json",
                "/home/rusty/projects/tracks/orica3.json",
                "/home/rusty/projects/tracks/orica4.json",
                "/home/rusty/projects/tracks/orica5.json",
                "/home/rusty/projects/tracks/orica6.json",
                "/home/rusty/projects/tracks/orica7.json",
                "/home/rusty/projects/tracks/orica8.json"
            ]:
               await run_track(path)
            
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and stream camera data"
    )
    
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga robot"
    )

    args = parser.parse_args()
    asyncio.run(main(args.address))
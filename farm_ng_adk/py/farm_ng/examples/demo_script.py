import argparse
import asyncio
import logging
import time

from farm_ng import Amiga, nexus as apb

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    timestamps = {}
                    
                
    async def end_route_callback():
        stop_event = asyncio.Event()
        
        async def feedback_callback(feedback: apb.Feedback) -> None:
            if feedback.HasField("navigation"):
                nav = feedback.navigation
                try:
                    mode = nav.mode
                    if mode == apb.NavigationMode.NAVIGATION_MODE_IDLE:
                        await asyncio.sleep(5) # simulate some processing time
                        stop_event.set()
                except Exception as e:
                    logging.error(f"Error processing navigation mode: {e}")
                    return
        
        async with amiga.feedback_sub(feedback_callback):
            while not stop_event.is_set():
                try:
                    await asyncio.sleep(1)  # Keep the task alive
                except asyncio.CancelledError:
                    logging.info("Feedback task cancelled.")
                    break
            # grab timestamp, we've finished segment
            # do stuff
            return timestamps
                
    try:
        while True:
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track1.json")
            await end_route_task
            
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track2.json")
            await end_route_task
            
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track3.json")
            await end_route_task
            
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track4.json")
            await end_route_task
            
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track5.json")
            await end_route_task
            
            end_route_task = asyncio.create_task(end_route_callback())
            await amiga.repeat_route_from_lon_lats("/mnt/data/tracks/track6.json")
            await end_route_task
        
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
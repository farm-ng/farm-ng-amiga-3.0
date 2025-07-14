import argparse
import asyncio
import logging

from farm_ng import Amiga, nexus as apb
from farm_ng.track_follower_client import TrackFollowerClient

def mapProtoToString(mode: apb.NavigationMode) -> str:
    if mode == apb.NavigationMode.NAVIGATION_MODE_IDLE:
        return "Idle"
    elif mode == apb.NavigationMode.NAVIGATION_MODE_REPEAT_ROUTE:
        return "Repeat Route"
    else:
        return f"Unknown Mode {mode}"

async def stream_track_state(amiga: Amiga):
    """
    Stream the track follower state
    """
    async def feedback_callback(feedback: apb.Feedback) -> None:
        if feedback.HasField("navigation"):
            print(f"Track state: {mapProtoToString(feedback.navigation.mode)}")
            
    async with amiga.feedback_sub(feedback_callback):
        logging.info("Streaming track state...")
        
        while True:
            try:
                await asyncio.sleep(1)  # Keep the task alive
            except asyncio.CancelledError:
                logging.info("Track state streaming cancelled.")
                break
            
def set_track(track_follower: TrackFollowerClient, track_path: str):
    """Set the track of the track follower client

    Args:
        track_follower (TrackFollowerClient): The track follower client instance.
        track_path (str): Path to the track to be repeated;
    """
    print(f"Setting track:\n {track_path}")
    track_follower.set_track(track_path)
    
          
async def start(track_follower: TrackFollowerClient):
    """
    Follow the track
    
    Args:
        track_follower (TrackFollowerClient): The track follower client instance.
    """
    print("Sending request to start following the track...")
    await track_follower.follow_track()
    
    
async def main(track_follower: TrackFollowerClient, track_path: str):
    """
    Run the track follower exmaple. Robot will drive the pre-recorded track.
    
    Args:
        track_follower (TrackFollowerClient): The track follower client instance.
        track_path (str): Path to the track to be repeated; Expected to be a local path
        to the machine running the example, and a JSON of lat/lon waypoints created by the
        Map Recorder application.
    """
    try:
        set_track(track_follower, track_path)
        await start(track_follower)
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")

async def run(args) -> None:
    amiga = Amiga(address=args.address)
    track_follower = TrackFollowerClient(amiga)
    
    tasks: list[asyncio.Task] = [
        asyncio.create_task(main(track_follower, args.track)),
        asyncio.create_task(stream_track_state(amiga)),
    ]
    await asyncio.gather(*tasks)
    
    await track_follower.stop_following()
    logging.info("Track following stopped successfully.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and repeat a track using the Track Follower Client"
    )
    
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga robot"
    )
    
    parser.add_argument(
        "--track",
        type=str,
        required=True,
        help="Path to the track to be repeated; This example uses tracks recorded by the Map Recorder application. Path must be local to the machine running the example.",
    )
    
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
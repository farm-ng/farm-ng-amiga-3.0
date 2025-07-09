import argparse
import asyncio
import logging

from farm_ng import Amiga, TrackFollowerClient, nexus as apb

async def stream_track_state(amiga: Amiga):
    async def feedback_callback(feedback: apb.Feedback) -> None:
        if feedback.HasField("navigation"):
            print(f"Track state: {feedback.navigation.mode}")
            
    async with amiga.feedback_sub(feedback_callback):
        logging.info("Streaming track state...")
        
        while True:
            try:
                await asyncio.sleep(1)  # Keep the task alive
            except asyncio.CancelledError:
                logging.info("Track state streaming cancelled.")
                break
            
def set_track(track_follower: TrackFollowerClient, track_path: str):
    print(f"Setting track:\n {track_path}")
    track_follower.set_track(track_path)
    
          
async def start(track_follower: TrackFollowerClient):
    print("Sending request to start following the track...")
    await track_follower.follow_track()
    
    
async def main(track_follower: TrackFollowerClient, track_path: str):
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
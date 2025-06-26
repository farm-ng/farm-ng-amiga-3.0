import argparse
import asyncio
import logging

from farm_ng import Amiga, nexus as apb


async def feedback_callback(feedback: apb.Feedback) -> None:
    if feedback.HasField("amiga_state"):
        state = feedback.amiga_state
        if state.HasField("global_pose"):
            pose = state.global_pose
            if pose.HasField("position"):
                position = pose.position

                try:
                    coords_obj = {
                        "longitude": position.longitude,
                        "latitude": position.latitude,
                    }
                    print(
                        f"Current position: Latitude: {coords_obj['latitude']}, Longitude: {coords_obj['longitude']}"
                    )
                except Exception as e:
                    logging.error(f"Error processing position: {e}")
                    
async def feedback_task(amiga: Amiga):
    async with amiga.feedback_sub(feedback_callback):
        logging.info("Listening to feedback...")
        
        while True:
            try:
                await asyncio.sleep(1)  # Keep the task alive
            except asyncio.CancelledError:
                logging.info("Feedback task cancelled.")
                break


async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    try:
        feedback_task_instance = asyncio.create_task(feedback_task(amiga))
        
        try:
            await feedback_task_instance
        except asyncio.CancelledError:
            logging.info("Feedback task completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and visualize GPS messages"
    )

    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga",
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))

import argparse
import asyncio
import logging

from farm_ng import Amiga

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    try:
        logging.info("Sending request to start track recording")
        await amiga.start_recording(
            id="my_track_session",
            topics=[]
        )

        logging.info("Recording track... Waiting 5 seconds.")
        await asyncio.sleep(5)

        logging.info("Sending request to stop track recording")
        await amiga.stop_recording(
            id="my_track_session",
        )

        logging.info("Track recording session completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and record data"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga"
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))
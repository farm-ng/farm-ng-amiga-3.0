import argparse
import asyncio
import logging
from farm_ng import Amiga
async def main(address: str, radius: float, arc_angle: float, direction: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    try:
        logging.info(f"Sending request to drive a circular track with radius {radius}, arc angle {arc_angle}, and direction {direction}")
        await amiga.circle_track(radius, arc_angle, direction)
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
    parser.add_argument(
        "--radius",
        type=float,
        default=1.0,
        help="Radius of the circular track"
    )
    parser.add_argument(
        "--arc-angle",
        type=float,
        default=2.0 * 3.14159,  # Default to 2π radians
        help="Arc angle in radians for the circular track"
    )
    parser.add_argument(
        "--direction",
        type=str,
        choices=['left', 'right'],
        default='left',
        help="Direction to drive the circular track (left or right)"
    )
    args = parser.parse_args()
    asyncio.run(main(args.address, args.radius, args.arc_angle, args.direction))
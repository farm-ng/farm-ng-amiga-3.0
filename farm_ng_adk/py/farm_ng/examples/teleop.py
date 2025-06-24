import argparse
import asyncio
import logging

from farm_ng import Amiga

MAX_LINEAR_VELOCITY_MPS = 2.0
MAX_ANGULAR_VELOCITY_RPS = 1.0
VELOCITY_INCREMENT = 0.1


class Teleop:
    def __init__(self, amiga: Amiga):
        self.amiga = amiga
        self.v_axis: float
        self.h_axis: float
        self.lock = asyncio.Lock()
        self.task: asyncio.Task = asyncio.create_task(self.run())

    async def activate(self):
        await self.amiga.activate_teleop()

    async def deactivate(self):
        await self.amiga.deactivate_teleop()

    async def update_command(self, h_axis: float, v_axis: float):
        async with self.lock:
            self.h_axis = h_axis
            self.v_axis = v_axis

    async def run(self):
        while True:
            async with self.lock:
                v = self.v_axis
                h = self.h_axis
            if v != 0.0 or h != 0.0:
                await self.amiga.teleop_command(h_axis=h, v_axis=v)
            asyncio.sleep(0.1)

    async def shutdown(self):
        await self.deactivate()
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass


def update_target(key: str, h: float, v: float) -> tuple[float, float]:
    """Update the target h/v values based on key press."""
    if key == "w":
        v += VELOCITY_INCREMENT
    elif key == "s":
        v -= VELOCITY_INCREMENT
    elif key == "a":
        h -= VELOCITY_INCREMENT
    elif key == "d":
        h += VELOCITY_INCREMENT
    return h, v


async def main(address: str):
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    teleop_handler = Teleop(amiga)

    try:
        input("Press Enter to activate teleop...")
        await teleop_handler.activate()
        logging.info("Teleop activated. Use WASD to drive. Type 'exit' to stop.")

        current_h, current_v = 0.0, 0.0
        update_interval = 0.1  # 100 ms

        while True:
            print("Command (w/a/s/d to adjust, 'stop' to zero, 'exit' to quit): ")
            key = input().strip()

            if key == "exit":
                break
            elif key == "stop":
                current_h, current_v = 0.0, 0.0
                await teleop_handler.update_command(h_axis=current_h, v_axis=current_v)
            else:
                current_h, current_v = update_target(key, current_h, current_v)
                current_h = max(
                    -MAX_ANGULAR_VELOCITY_RPS, min(MAX_ANGULAR_VELOCITY_RPS, current_h)
                )
                current_v = max(
                    -MAX_LINEAR_VELOCITY_MPS, min(MAX_LINEAR_VELOCITY_MPS, current_v)
                )

                await teleop_handler.update_command(h_axis=current_h, v_axis=current_v)
                await asyncio.sleep(update_interval)

        await teleop_handler.deactivate()
        logging.info("Teleop deactivated.")

    except KeyboardInterrupt:
        logging.warning("Interrupted by user (Ctrl+C). Cleaning up...")

    except Exception as e:
        logging.error(f"Error during teleop: {e}")

    finally:
        # Stop the running teleop task
        await teleop_handler.shutdown()

        logging.info("Teleop deactivated.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Connect to Amiga and record data")
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga",
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))

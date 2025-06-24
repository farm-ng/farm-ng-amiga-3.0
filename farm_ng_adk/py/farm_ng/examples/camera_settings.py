import argparse
import asyncio
import logging

from farm_ng import Amiga

DEFAULT_EXPOSURE_TIME = 10000
DEFAULT_ISO_SENSITIVITY = 750
DEFAULT_LENS_POSITION = 140

EXPOSURE_RANGE = (20, 33000)
ISO_RANGE = (100, 1600)
LENS_POSITION_RANGE = (1, 255)


class CameraSettingsHelper:
    def __init__(self):
        self.selected_camera = "oak0"
        self.camera_settings = {
            "oak0": {
                "auto_exposure": True,
                "auto_focus": True,
                "exposure_time_us": None,
                "iso_sensitivity": None,
                "lens_position": None,
            },
            "oak1": {
                "auto_exposure": True,
                "auto_focus": True,
                "exposure_time_us": None,
                "iso_sensitivity": None,
                "lens_position": None,
            },
        }

    def switch_camera(self):
        self.selected_camera = "oak1" if self.selected_camera == "oak0" else "oak0"
        print(f"Switched to camera: {self.selected_camera}")

    def enable_auto_exposure(self):
        self.camera_settings[self.selected_camera]["auto_exposure"] = True
        self.camera_settings[self.selected_camera]["exposure_time_us"] = None
        self.camera_settings[self.selected_camera]["iso_sensitivity"] = None
        print(f"Auto exposure enabled for {self.selected_camera}")

    def enable_auto_focus(self):
        self.camera_settings[self.selected_camera]["auto_focus"] = True
        self.camera_settings[self.selected_camera]["lens_position"] = None
        print(f"Auto focus enabled for {self.selected_camera}")

    def update_exposure_time(self, exposure_time_us: int):
        if not (EXPOSURE_RANGE[0] <= exposure_time_us <= EXPOSURE_RANGE[1]):
            raise ValueError(
                f"Exposure time must be between {EXPOSURE_RANGE[0]} and {EXPOSURE_RANGE[1]} microseconds."
            )

        self.camera_settings[self.selected_camera]["auto_exposure"] = False
        self.camera_settings[self.selected_camera][
            "exposure_time_us"
        ] = exposure_time_us

        print(
            f"Exposure time set to {exposure_time_us} microseconds for {self.selected_camera}"
        )
        if self.camera_settings[self.selected_camera]["iso_sensitivity"] is None:
            self.camera_settings[self.selected_camera][
                "iso_sensitivity"
            ] = DEFAULT_ISO_SENSITIVITY
            print(
                f"ISO sensitivity set to {self.camera_settings[self.selected_camera]['iso_sensitivity']} for {self.selected_camera}"
            )

    def update_iso_sensitivity(self, iso_sensitivity: int):
        if not (ISO_RANGE[0] <= iso_sensitivity <= ISO_RANGE[1]):
            raise ValueError(
                f"ISO sensitivity must be between {ISO_RANGE[0]} and {ISO_RANGE[1]}."
            )

        self.camera_settings[self.selected_camera]["auto_exposure"] = False
        self.camera_settings[self.selected_camera]["iso_sensitivity"] = iso_sensitivity

        print(f"ISO sensitivity set to {iso_sensitivity} for {self.selected_camera}")
        if self.camera_settings[self.selected_camera]["exposure_time_us"] is None:
            self.camera_settings[self.selected_camera][
                "exposure_time_us"
            ] = DEFAULT_EXPOSURE_TIME
            print(
                f"Exposure time set to {self.camera_settings[self.selected_camera]['exposure_time_us']} microseconds for {self.selected_camera}"
            )

    def update_lens_position(self, lens_position: int):
        if not (LENS_POSITION_RANGE[0] <= lens_position <= LENS_POSITION_RANGE[1]):
            raise ValueError(
                f"Lens position must be between {LENS_POSITION_RANGE[0]} and {LENS_POSITION_RANGE[1]}."
            )

        self.camera_settings[self.selected_camera]["auto_focus"] = False
        self.camera_settings[self.selected_camera]["lens_position"] = lens_position

        print(f"Lens position set to {lens_position} for {self.selected_camera}")

    @property
    def current_settings(self):
        return self.camera_settings[self.selected_camera]


def handle_key_press(key: str, helper: CameraSettingsHelper):

    if key == "c":
        helper.switch_camera()

    elif key == "e":
        auto = helper.current_settings["auto_exposure"]
        if auto == True:
            exposure_time = (
                input("Enter exposure time in microseconds (default 10000): ")
                .strip()
                .lower()
            )
        else:
            exposure_time = (
                input(
                    "Enter exposure time in microseconds (default 10000), or press 'a' to revert to auto exposure: "
                )
                .strip()
                .lower()
            )

            if exposure_time == "a":
                helper.enable_auto_exposure()
                return helper.current_settings

        num = int(exposure_time)

        helper.update_exposure_time(num)

        return helper.current_settings

    elif key == "i":
        auto = helper.current_settings["auto_exposure"]
        if auto == True:
            iso_sensitivity = (
                input("Enter ISO sensitivity (default 750): ").strip().lower()
            )
        else:
            iso_sensitivity = (
                input(
                    "Enter ISO sensitivity (default 750), or press 'a' to revert to auto exposure: "
                )
                .strip()
                .lower()
            )

            if iso_sensitivity == "a":
                helper.enable_auto_exposure()
                return helper.current_settings

        num = int(iso_sensitivity)

        helper.update_iso_sensitivity(num)

        return helper.current_settings

    elif key == "l":
        auto = helper.current_settings["auto_focus"]
        if auto == True:
            lens_position = input("Enter lens position (default 140): ").strip().lower()
        else:
            lens_position = (
                input(
                    "Enter lens position (default 140), or press 'a' to revert to auto focus: "
                )
                .strip()
                .lower()
            )

            if lens_position == "a":
                helper.enable_auto_focus()
                return helper.current_settings

        num = int(lens_position)

        helper.update_lens_position(num)

        return helper.current_settings

    elif key == "q":
        print("Exiting...")
        exit(0)

    else:
        print("Invalid key pressed. Please try again.")


async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)

    helper = CameraSettingsHelper()

    try:

        while True:
            print("\nSelected camera: ", helper.selected_camera)
            print("Current camera settings: ", helper.current_settings, "\n")

            key = (
                input(
                    "Press 'c' to change camera, 'e' to set exposure, 'i' to set ISO, 'l' to set lens position, or 'q' to quit: "
                )
                .strip()
                .lower()
            )
            try:
                updated_settings = handle_key_press(key, helper)

                await amiga.update_camera_settings(
                    helper.selected_camera, updated_settings
                )

                print("Camera settings updated successfully.")

            except ValueError as ve:
                logging.error(
                    f"Invalid input, please enter a valid number. Error: {ve}"
                )
                continue

            except RuntimeError as re:
                logging.error(f"An error occurred while updating camera settings: {re}")
                continue

    except KeyboardInterrupt:
        logging.warning("Interrupted by user (Ctrl+C). Cleaning up...")

    except Exception as e:
        logging.error(f"An error occurred: {e}")


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

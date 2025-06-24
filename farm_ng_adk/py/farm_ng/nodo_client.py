from __future__ import annotations

import asyncio
import logging
import struct
from dataclasses import dataclass
from typing import List, Optional
import lz4.block

import pynng
from farm_ng.nexus import nodo_configure_pb2

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class GPSNtripClient:
    """Data class for GPS Ntrip configuration"""

    ntrip_server: str = ""
    ntrip_port: str = ""
    ntrip_mountpoint: str = ""
    ntrip_user: str = ""
    ntrip_password: str = ""


@dataclass
class ImuCalibration:
    """Data class for IMU calibration parameters"""

    robot_r_imu: List[float] | None = None
    gyro_bias: List[float] | None = None
    accel_bias: List[float] | None = None

    def __post_init__(self):
        if self.robot_r_imu is None:
            self.robot_r_imu = []
        if self.gyro_bias is None:
            self.gyro_bias = []
        if self.accel_bias is None:
            self.accel_bias = []


@dataclass
class DriveTrain:
    """Data class for drive train parameters"""

    wheel_base: float = 0.0
    wheel_track: float = 0.0
    wheel_radius: float = 0.0
    gear_ratio: float = 0.0


@dataclass
class Tolerances:
    """Data class for tolerance parameters"""

    path_deviation_threshold: float = 1.0


@dataclass
class RobotSensorModel:
    """Data class for robot sensor model"""

    imu: ImuCalibration | None = None
    drive_train: DriveTrain | None = None
    gps_antenna: List[float] | None = None

    def __post_init__(self):
        if self.imu is None:
            self.imu = ImuCalibration()
        if self.drive_train is None:
            self.drive_train = DriveTrain()
        if self.gps_antenna is None:
            self.gps_antenna = []


@dataclass
class CameraSettings:
    """Data class for camera settings"""

    camera_name: str  # "oak0 or "oak1"
    enable_auto_exposure: Optional[bool] = None
    enable_auto_focus: Optional[bool] = None
    enable_auto_white_balance: Optional[bool] = None
    exposure_time_us: Optional[int] = None
    iso_sensitivity: Optional[int] = None
    color_temperature_kelvins: Optional[int] = None
    lens_position: Optional[int] = None


class NodoNNGClient:
    """
    A wrapper class around pynng for interacting with the Nodo configuration service.

    This version handles LZ4 compression of the protocol buffer messages.
    """

    def __init__(
        self,
        request_address: str,
        timeout: int = 200,
    ):
        self.request_address = request_address
        self.timeout = timeout
        self.req_socket: pynng.Req0 | None = None
        self._request_lock = asyncio.Lock()

    async def _try_connect_request(self, max_retries: int = 3) -> bool:
        """Try to establish request socket connection with retries"""
        for attempt in range(max_retries):
            if self.req_socket is None:
                try:
                    backoff = min(2**attempt, 10)  # Cap at 10 seconds
                    await asyncio.sleep(backoff)
                    self.req_socket = pynng.Req0(
                        recv_timeout=self.timeout, send_timeout=self.timeout
                    )
                    self.req_socket.dial(self.request_address, block=True)
                    return True
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if self.req_socket:
                        self.req_socket.close()
                        self.req_socket = None
            else:
                return True
        return False

    async def stop(self):
        """Stop the client and clean up resources"""
        if self.req_socket:
            self.req_socket.close()
            self.req_socket = None

    def _compress_prepend_size(self, data: bytes) -> bytes:
        """
        Compress data with LZ4 and prepend the uncompressed size.
        """
        # Prepend the uncompressed size as a 32-bit little-endian integer
        uncompressed_size_bytes = struct.pack("<I", len(data))
        compressed = lz4.block.compress(data, store_size=False)

        return uncompressed_size_bytes + compressed

    def _decompress_size_prepended(self, data: bytes) -> bytes:
        """
        Decompress data with LZ4 where the uncompressed size is prepended.
        """
        # Extract the uncompressed size from the first 4 bytes
        if len(data) < 4:
            raise ValueError(f"Data too short for size: {len(data)}")

        uncompressed_size = struct.unpack("<I", data[:4])[0]
        compressed = data[4:]

        return lz4.block.decompress(compressed, uncompressed_size)

    async def request(
        self, message: nodo_configure_pb2.ConfigureRequest
    ) -> Optional[nodo_configure_pb2.ConfigureReply]:
        """
        Send a request to the Nodo service and get the reply.

        Args:
            message: The ConfigureRequest message to send

        Returns:
            ConfigureReply message or None if the request failed
        """
        if not await self._try_connect_request():
            logger.error("Failed to establish request connection")
            return None

        async with self._request_lock:
            try:
                if self.req_socket:
                    # Serialize and compress the message
                    proto_data = message.SerializeToString()
                    compressed_data = self._compress_prepend_size(proto_data)

                    # Send the compressed request
                    await self.req_socket.asend(compressed_data)

                    # Wait for the response
                    try:
                        compressed_response = await self.req_socket.arecv()

                        # Decompress the response
                        try:
                            response_data = self._decompress_size_prepended(
                                compressed_response
                            )

                            # Parse the response
                            reply = nodo_configure_pb2.ConfigureReply()
                            reply.ParseFromString(response_data)

                            return reply

                        except Exception as decompress_error:
                            logger.error(
                                f"Error decompressing or parsing response: {decompress_error}"
                            )
                            return None

                    except pynng.exceptions.Timeout:
                        logger.error("Timeout waiting for response")
                        return None

                return None

            except Exception as e:
                logger.error(f"Request failed: {e}")
                if self.req_socket:
                    self.req_socket.close()
                    self.req_socket = None
                return None

    async def get_all_parameters(
        self,
    ) -> List[nodo_configure_pb2.ParameterWithProperties]:
        """
        Convenience method to retrieve all available parameters.

        Returns:
            List of ParameterWithProperties objects or empty list if request failed
        """
        # Create a list request
        request = nodo_configure_pb2.ConfigureRequest()
        request.list.SetInParent()

        reply = await self.request(request)

        if reply is None:
            logger.warning("No reply received")
            return []

        if not reply.HasField("list"):
            if reply.HasField("failure"):
                logger.error(f"List request failed: {reply.failure.message}")
            else:
                logger.error("Unexpected reply type")
            return []

        return list(reply.list.params)

    async def update_parameters(
        self, parameters: List[nodo_configure_pb2.Parameter]
    ) -> bool:
        """
        Update multiple parameters at once.

        Args:
            parameters: List of Parameter objects to update

        Returns:
            True if successful, False otherwise
        """
        # Create the update request
        request = nodo_configure_pb2.ConfigureRequest()
        request.update.params.extend(parameters)

        logger.info(f"Updating {len(parameters)} parameters")
        reply = await self.request(request)

        if reply is None:
            logger.warning("No reply received")
            return False

        if reply.HasField("failure"):
            logger.error(f"Update request failed: {reply.failure.message}")
            return False
        elif reply.HasField("success"):
            return True
        else:
            logger.error("Unexpected reply type")
            return False

    def create_parameter(
        self, node: str, param: str, value
    ) -> nodo_configure_pb2.Parameter:
        """
        Helper method to create a Parameter message with the appropriate value type.

        Args:
            node: Name of the node
            param: Name of the parameter
            value: The value to set (bool, int, float, str, or list of floats)

        Returns:
            Parameter message with the value set
        """
        parameter = nodo_configure_pb2.Parameter()
        parameter.node = node
        parameter.param = param

        if isinstance(value, bool):
            parameter.value.bool = value
        elif isinstance(value, int):
            parameter.value.int64 = value
        elif isinstance(value, float):
            parameter.value.float64 = value
        elif isinstance(value, str):
            parameter.value.string = value
        elif isinstance(value, list) and all(
            isinstance(x, (int, float)) for x in value
        ):
            parameter.value.vec_float_64.entries.extend([float(x) for x in value])
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

        return parameter

    async def update_ntrip_client(self, new_client: GPSNtripClient) -> bool:
        """Update the GPS Ntrip client configuration."""
        # Create the parameters
        parameters = [
            self.create_parameter("ntrip", "host", new_client.ntrip_server),
            self.create_parameter("ntrip", "port", new_client.ntrip_port),
            self.create_parameter("ntrip", "mountpoint", new_client.ntrip_mountpoint),
            self.create_parameter("ntrip", "username", new_client.ntrip_user),
            self.create_parameter("ntrip", "password", new_client.ntrip_password),
        ]

        # Send the update
        return await self.update_parameters(parameters)

    async def update_imu_calibration(self, imu: ImuCalibration) -> bool:
        """
        Update the IMU calibration in the running system.

        Args:
            imu: ImuCalibration data class containing calibration parameters

        Returns:
            True if successful, False otherwise
        """
        if not imu.robot_r_imu or not imu.gyro_bias:
            logger.error("IMU calibration values are missing")
            return False

        parameters = [
            self.create_parameter("robot_model_facade", "robot_r_imu", imu.robot_r_imu),
            self.create_parameter("robot_model_facade", "imu_gyro_bias", imu.gyro_bias),
        ]

        # Only add accel_bias if it's available
        if imu.accel_bias:
            parameters.append(
                self.create_parameter(
                    "robot_model_facade", "imu_accel_bias", imu.accel_bias
                )
            )

        logger.info("Updating IMU calibration parameters")
        return await self.update_parameters(parameters)

    async def update_drive_train(self, drive_train: DriveTrain) -> bool:
        """
        Update the drive train parameters in the running system.

        Args:
            drive_train: DriveTrain data class containing parameters

        Returns:
            True if successful, False otherwise
        """
        parameters = [
            self.create_parameter(
                "robot_model_facade", "wheel_base", drive_train.wheel_base
            ),
            self.create_parameter(
                "robot_model_facade", "wheel_track", drive_train.wheel_track
            ),
        ]

        logger.info("Updating drive train parameters")
        return await self.update_parameters(parameters)

    async def update_gps_antenna(self, gps_antenna: List[float]) -> bool:
        """
        Update the GPS antenna position in the running system.

        Args:
            gps_antenna: List of [x, y, z] coordinates

        Returns:
            True if successful, False otherwise
        """
        if len(gps_antenna) != 3:
            logger.error(
                f"GPS antenna position must have exactly 3 values, got {len(gps_antenna)}"
            )
            return False

        parameters = [
            self.create_parameter(
                "robot_model_facade", "gps_antenna_position", gps_antenna
            ),
        ]

        logger.info("Updating GPS antenna position")
        return await self.update_parameters(parameters)

    async def update_tolerances(self, tolerances: Tolerances) -> bool:
        """
        Update the tolerances in the running system.

        Args:
            tolerances: List of tolerance values
        Returns:
            True if successful, False otherwise
        """
        parameters = [
            self.create_parameter(
                "main_trajectory_planner",
                "path_reset_distance_threshold",
                tolerances.path_deviation_threshold,
            ),
        ]

        logger.info("Updating tolerances")
        return await self.update_parameters(parameters)

    async def update_camera_settings(self, camera_settings: CameraSettings) -> bool:
        """
        Update the camera settings in the running system.

        Args:
            camera_settings: CameraSettings data class containing camera parameters
        Returns:
            True if successful, False otherwise
        """
        parameters = []

        # First, validate the camera name
        if camera_settings.camera_name not in ["oak0", "oak1"]:
            logger.error(
                f"Invalid camera name: {camera_settings.camera_name}. Must be one of ['oak0', 'oak1']"
            )
            return False

        # Second, validate the camera settings
        # 1. We need to have at least one parameter set
        # Check if all settings are None
        if (
            camera_settings.enable_auto_exposure is None
            and camera_settings.enable_auto_focus is None
            and camera_settings.enable_auto_white_balance is None
            and camera_settings.exposure_time_us is None
            and camera_settings.iso_sensitivity is None
            and camera_settings.color_temperature_kelvins is None
            and camera_settings.lens_position is None
        ):
            logger.error(
                "At least one camera setting must be set. "
                "Please provide at least one of the following: "
                "enable_auto_exposure, enable_auto_focus, enable_auto_white_balance, "
                "exposure_time_us, iso_sensitivity, color_temperature_kelvins, lens_position."
            )
            return False

        # Handle exposure settings
        exposure_valid = True
        if (
            camera_settings.enable_auto_exposure is False
            and camera_settings.exposure_time_us is None
            and camera_settings.iso_sensitivity is None
        ):
            logger.error(
                "When auto exposure is disabled, either exposure_time_us or iso_sensitivity must be provided."
            )
            exposure_valid = False

        if exposure_valid:
            # Only add exposure parameters if they're valid
            if camera_settings.enable_auto_exposure is not None:
                parameters.append(
                    self.create_parameter(
                        camera_settings.camera_name,
                        "enable_auto_exposure",
                        camera_settings.enable_auto_exposure,
                    )
                )

            if camera_settings.exposure_time_us is not None:
                parameters.append(
                    self.create_parameter(
                        camera_settings.camera_name,
                        "exposure_time_us",
                        camera_settings.exposure_time_us,
                    )
                )

            if camera_settings.iso_sensitivity is not None:
                parameters.append(
                    self.create_parameter(
                        camera_settings.camera_name,
                        "iso_sensitivity",
                        camera_settings.iso_sensitivity,
                    )
                )

        # Handle focus settings
        focus_valid = True
        if (
            camera_settings.enable_auto_focus is False
            and camera_settings.lens_position is None
        ):
            logger.error("When auto focus is disabled, lens_position must be provided.")
            focus_valid = False

        if focus_valid:
            # Only add focus parameters if they're valid
            if camera_settings.enable_auto_focus is not None:
                parameters.append(
                    self.create_parameter(
                        camera_settings.camera_name,
                        "enable_auto_focus",
                        camera_settings.enable_auto_focus,
                    )
                )

            if camera_settings.lens_position is not None:
                # Ensure the lens position is within a valid range (0 to 255)
                if not (0 <= camera_settings.lens_position <= 255):
                    logger.error(
                        f"lens_position must be between 0 and 255, got {camera_settings.lens_position}"
                    )
                else:
                    parameters.append(
                        self.create_parameter(
                            camera_settings.camera_name,
                            "lens_position",
                            camera_settings.lens_position,
                        )
                    )

        # Handle white balance settings
        white_balance_valid = True
        if (
            camera_settings.enable_auto_white_balance is False
            and camera_settings.color_temperature_kelvins is None
        ):
            logger.error(
                "When auto white balance is disabled, color_temperature_kelvins must be provided."
            )
            white_balance_valid = False

        if white_balance_valid:
            # Only add white balance parameters if they're valid
            if camera_settings.enable_auto_white_balance is not None:
                parameters.append(
                    self.create_parameter(
                        camera_settings.camera_name,
                        "enable_auto_white_balance",
                        camera_settings.enable_auto_white_balance,
                    )
                )

            if camera_settings.color_temperature_kelvins is not None:
                # Ensure the value is between 1000 and 12000 (according to the depthai documentation)
                # Please see: https://docs.luxonis.com/software/depthai-components/messages/camera_control/
                if not (1000 <= camera_settings.color_temperature_kelvins <= 12000):
                    logger.error(
                        f"color_temperature_kelvins must be between 1000 and 12000, "
                        f"got {camera_settings.color_temperature_kelvins}"
                    )
                else:
                    parameters.append(
                        self.create_parameter(
                            camera_settings.camera_name,
                            "color_temperature_kelvins",
                            camera_settings.color_temperature_kelvins,
                        )
                    )

        # If we have valid parameters, update them
        if parameters:
            return await self.update_parameters(parameters)
        else:
            # If no valid parameters were found, return False
            logger.error("No valid camera parameters to update.")
            return False

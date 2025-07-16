from farm_ng.amiga import Amiga
from farm_ng.nexus import RepeatedLonLat

from typing import Optional


class TrackFollowerClient:
    """A client for following a track on the Amiga robot.

    Args:
        amiga (Amiga): An instance of the Amiga class to interact with the robot.
    """

    def __init__(self, amiga: Amiga):
        self._amiga = amiga
        self._track: Optional[dict] = None

    def set_track(self, track: dict):
        """
        Receive a dictionary representing a track, convert it to a Request proto message, and store it.

        Args:
            track (dict): Dictionary with a list of waypoints, each being a dictionary with 'longitude' and 'latitude' keys.

        Example:
            track = {
                "waypoints": [
                    {"longitude": -121.9358, "latitude": 36.9509},
                    {"longitude": -121.9360, "latitude": 36.9515},
                    {"longitude": -121.9363, "latitude": 36.9521},
                ]
            }
        """
        msg = RepeatedLonLat()
        for wp in track.get("waypoints", []):
            msg.waypoints.add(longitude=wp["longitude"], latitude=wp["latitude"])

        self._track = msg

    def clear_track(self):
        self._track = None

    async def follow_track(self):
        if self._track is None:
            raise ValueError("Track not set. Please set a track before following it.")

        await self._amiga.repeat_route_from_proto(self._track)

    async def stop_following(self):
        await self._amiga.pause_route()

from farm_ng.amiga import Amiga
from typing import Optional

class TrackFollowerClient:
    def __init__(self, amiga: Amiga):
        self._amiga = amiga
        self._track: Optional[str]  = None
        
    def set_track(self, track_path: str):
        self._track = track_path
        
    def clear_track(self):
        self._track = None
        
    async def follow_track(self):
        if self._track is None:
            raise ValueError("Track not set. Please set a track before following it.")
        
        await self._amiga.repeat_route_from_lon_lats(self._track)
        
    async def stop_following(self):
        await self._amiga.pause_route()
        
        
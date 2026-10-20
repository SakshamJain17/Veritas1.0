from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass
class TinyFishResult:
    capability:str; status:str; request:dict; result:Any=None; error:str|None=None; started_at:str|None=None; finished_at:str|None=None

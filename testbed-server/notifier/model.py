from typing import Literal, Optional, TypeAlias
from enum import Enum
from pydantic import BaseModel

ConnType: TypeAlias = Literal["display", "agent"]

class Action(Enum):
    INITIALIZE = "INITIALIZE"
    EXECUTE = "EXECUTE"

class Topic(Enum):
    RECV_COMMAND = "RECV_COMMAND"
    RECV_POSITION = "RECV_POSITION"
    SYSTEM_WIDE = "SYSTEM_WIDE"

class ServerRegistrationMessage(BaseModel):
    action: Literal["INITIALIZE"]
    id: str
    connection_type: ConnType

class CarCommandMessage(BaseModel):
    action: Literal["EXECUTE"]
    steering: int
    speed: int

class ResponseMessage(BaseModel):
    is_success: bool
    message: Optional[str]

class CarState(BaseModel):
    is_registered: bool = False
    is_active: bool = False
    is_inbound: bool = False
    current_pos: Optional[tuple[int, int]] =  None
    current_angle: Optional[float] = None


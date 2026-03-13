from typing import Literal, Optional, Sequence
from enum import Enum
from pydantic import BaseModel

class Action(Enum):
    REGISTER = "REGISTER"
    SUBSCRIBE = "SUBSCRIBE"
    EXECUTE = "EXECUTE"

class Topic(Enum):
    RECV_COMMAND = "RECV_COMMAND"
    RECV_POSITION = "RECV_POSITION"
    SYSTEM_WIDE = "SYSTEM_WIDE"

class CarRegisterMessage(BaseModel):
    action: Literal["REGISTER"]
    car_id: str

class TopicSubscribeMessage(BaseModel):
    action: Literal["SUBSCRIBE"]
    topics: Sequence[Topic]

class CarCommandMessage(BaseModel):
    action: Literal["EXECUTE"]
    steering: int
    speed: int

class CarRegisterErrorMessage(BaseModel):
    message: str

class TopicSubscribeErrorMessage(BaseModel):
    message: str

class ResponseMessage(BaseModel):
    is_success: bool
    message: Optional[str]

class CarState(BaseModel):
    is_registered: bool = False
    is_active: bool = False
    is_inbound: bool = False
    current_pos: Optional[tuple[int, int]] =  None
    current_angle: Optional[float] = None


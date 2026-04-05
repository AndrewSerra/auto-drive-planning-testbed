from typing import Literal, Optional, Union, Annotated
from enum import Enum
from pydantic import BaseModel, TypeAdapter, Field

class Topic(Enum):
    RECV_COMMAND = "RECV_COMMAND"
    RECV_POSITION = "RECV_POSITION"
    SYSTEM_WIDE = "SYSTEM_WIDE"

class AgentRegistrationMessage(BaseModel):
    id: str
    connection_type: Literal["agent"] = "agent"

class DisplayRegistrationMessage(BaseModel):
    id: str
    connection_type: Literal["display"] = "display"

ServerRegistrationMessage = Annotated[
    Union[AgentRegistrationMessage, DisplayRegistrationMessage],
    Field(discriminator="connection_type")]

server_reg_msg_type_adapter = TypeAdapter(ServerRegistrationMessage)


# class CarCommandMessage(RegisterationMessage[Literal["EXECUTE"]]):
#     steering: int
#     speed: int

class ResponseMessage(BaseModel):
    is_success: bool
    message: Optional[str] = None

# class CarState(BaseModel):
#     is_registered: bool = False
#     is_active: bool = False
#     is_inbound: bool = False
#     current_pos: Optional[tuple[int, int]] =  None
#     current_angle: Optional[float] = None


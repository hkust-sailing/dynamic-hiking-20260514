from dataclasses import dataclass
from typing import List
import struct
from enum import IntEnum

#@dataclass
# class CommandMessage:
#      id: int = 55
#      # State command
#      command_code: int = 0  
#      # Sub-state command
#      # 1=step mode; 2=dynamic mode; 3=script mode
#      sub_command_code: int = 0 
     
class CommandCodes(IntEnum):
    None_ = 0
    HeartBeat = 1
    MoveToMiddle = 2
    EmergencyShutdown = 3
    HoldPlatform = 3
    FindBottomInitialize = 4
    ManualMode = 5
    MoveFromBottomToMiddle = 6
    MoveFromMiddleToBottom = 7
    SetDriverParameters = 8
    ContinuousMoving = 9
    SetMovingCenterPoint = 10
    CommandMoving = 11
    MoveToTop = 12
    WorkingWithScript = 13

class SubCommandCodes(IntEnum):
    None_ = 0
    Step = 1
    SineWave = 2
    SlowStop = 3
    # Script = 3,
    Freeze = 4 # Freeze command.
    Thaw = 5 # Thaw command.
    Reset = 6
    ComplexMove = 7
    ComplexMoveStop = 8 # Stop composite motion.
    SquareWave = 9
    WhiteNoise = 10
    FatigueTest = 11 # Fatigue-test mode.

class CommandMessage:
    def __init__(self,
                 command_code: CommandCodes = CommandCodes.None_,
                 sub_command_code: SubCommandCodes = SubCommandCodes.None_,
                 script_file_index: int = 0,
                 do: int = 0,
                 cy_choose: int = 0,
                 jog_speed: int = 0,
                 dofs: List[float] = None,
                 amplitude_array: List[float] = None,
                 frequency_array: List[float] = None,
                 phase_array: List[float] = None,
                 destination_position: List[float] = None,
                 speed: List[float] = None,
                 vxyz: List[float] = None,
                 axyz: List[float] = None,
                 timestamp: int = 0
                 ):
        self.Id = 55
        self.CommandCode = command_code
        self.SubCommandCode = sub_command_code
        self.ScriptFileIndex = script_file_index
        self.DO = do
        self.CyChoose = cy_choose # Selection mask for 6 actuators.
        self.JogSpeed = jog_speed
        self.DOFs = dofs if dofs is not None else [0.0] * 6
        self.AmplitudeArray = amplitude_array if amplitude_array is not None else [0.0] * 6
        self.FrequencyArray = frequency_array if frequency_array is not None else [0.0] * 6
        self.PhaseArray = phase_array if phase_array is not None else [0.0] * 6
        self.DestinationPosition = destination_position if destination_position is not None else [0.0] * 6
        self.Speed = speed if speed is not None else [0.0] * 6
        self.Vxyz = vxyz if vxyz is not None else [0.0] * 3
        self.Axyz = axyz if axyz is not None else [0.0] * 3
        self.Timestamp = timestamp

    def to_bytes(self) -> bytes:
        try:
            args = [
            self.Id,
            self.CommandCode.value,
            self.SubCommandCode.value,
            self.ScriptFileIndex,
            self.DO,
            self.CyChoose,
            self.JogSpeed,
            *self.DOFs,
            *self.AmplitudeArray,
            *self.FrequencyArray,
            *self.PhaseArray,
            *self.DestinationPosition,
            *self.Speed,
            *self.Vxyz,
            *self.Axyz,
            self.Timestamp
            ]

            # Build the struct packing format string.
            format_string = '<B'  # Id (1 byte)
            format_string += 'B'  # CommandCode (1 byte)
            format_string += 'B'  # SubCommandCode (1 byte)
            format_string += 'B'  # ScriptFileIndex (1 byte)
            format_string += 'B'  # DO (1 byte)
            format_string += 'B'  # CyChoose (1 byte)
            format_string += 'h'  # JogSpeed (2 byte)
            format_string += '6f'  # DOFs (6 floats)
            format_string += '6f'  # AmplitudeArray (6 floats)
            format_string += '6f'  # FrequencyArray (6 floats)
            format_string += '6f'  # PhaseArray (6 floats)
            format_string += '6f'  # DestinationPosition (6 floats)
            format_string += '6f'  # Speed (6 floats)
            format_string += '3f'  # Vxyz (3 floats)
            format_string += '3f'  # Axyz (3 floats)
            format_string += 'I'   # Timestamp (4 bytes)

            return struct.pack(format_string, *args)
            #print(f"Number of arguments: {len(args)}")
            #print(args)
            # return struct.pack(
            #     '<BBBBBBh6f6f6f6f6f6f3f3fi',
            #     *args
            # )
        except struct.error as e:
            print(f"Error packing data: {e}")
            return b''
# FeedbackMessage(Id=55, 
#                 DOFStatus=<StatusCodes.MoveToBottomCompleted: 13>, 
#                 DI=0, 
#                 ErrorCode=0, 
#                 AttitudesArray=[0.0, 0.0, 0.0, 0.0, 0.0, -0.24691236019134521], 
#                 CylindersErrorCodeArray=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 
#                 CylindersMotorCodeArray=[0.8599998354911804, 0.8600000143051147, 0.8599998354911804, 0.8600000143051147, 0.8599997162818909, 0.8599998354911804], 
#                 CylindersTorArray=[-8.0, 0.0, -9.0, 7.0, 2.0, -9.0], 
#                 Version=202106, 
#                 Timestamp=491345)

# command = CommandMessage(
#         command_code=CommandCodes.MoveFromBottomToMiddle,
#         dofs=[10.0, 0.0, 0.0, 0.0, 0.0, 0.0],
#         amplitude_array=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
#         frequency_array=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
#         phase_array=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
#         destination_position=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
#         speed=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
#         vxyz=[1.0, 2.0, 3.0],
#         axyz=[0.1, 0.2, 0.3],
#         timestamp=123456789
#     )

# command_bytes = command.to_bytes()
# print(f"Command bytes: {command_bytes}")
# def test_command_message_default_values():
#     """Test default values of CommandMessage."""
#     command = CommandMessage()
#     assert command.id == 55
#     assert command.command_code == 0
#     assert command.sub_command_code == 0
#     assert command.script_file_index == 0
#     assert command.do == 0
#     assert command.cy_choose == 0
#     assert command.jog_speed == 0
#     assert command.dofs == [0.0] * 6
#     assert command.amplitude_array == [0.0] * 6
#     assert command.frequency_array == [0.0] * 6
#     assert command.phase_array == [0.0] * 6
#     assert command.destination_position == [0.0] * 6
#     assert command.speed == [0.0] * 6
#     assert command.vxyz == [0.0] * 3
#     assert command.axyz == [0.0] * 3
#     assert command.timestamp == 0

# def test_command_message_to_bytes():
#     """Test CommandMessage serialization to bytes."""
#     command = CommandMessage(
#         command_code=1,
#         dofs=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
#     )
#     command_bytes = command.to_bytes()
#     assert len(command_bytes) > 0  # Ensure byte array is not empty.

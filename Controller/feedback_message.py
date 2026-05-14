from dataclasses import dataclass
from typing import List
from enum import Enum
import struct

class StatusCodes(Enum):
    Unknown = 255
    FindBottomInitializing = 0
    FindBottomInitialized = 1
    MovingFromBottomToMiddle = 2
    MoveFromBottomToMiddleCompleted = 3
    Moving = 4
    CommandMoving = 5
    SettingCenterPoint = 6
    SettingDriver = 7
    RunningScript = 8
    ScriptCompleted = 9
    MovingToTop = 10
    MoveToTopCompleted = 11
    MovingFromMiddleToBottom = 12
    MoveToBottomCompleted = 13
    MovingToMiddle = 14
    SystemInPreparation = 15
    WriteZeroCode = 16
    LostConnect = 77
    SystemPreparing = 18
    CylinderMoving = 19
    CylinderMiddle = 20
    ManualMode = 32
    EmergencyShutdown = 33
    HoldPlatform = 33
    SystemError34 = 34
    DriverError34 = 34
    SystemInitialized = 55
    DriverError = 119
    DriverError2 = 120


@dataclass
class FeedbackMessage:
    Id: int # Fixed packet identifier value: 55.
    DOFStatus: StatusCodes
    DI: int
    Rev1: int
    AttitudesArray: List[float]
    CylindersErrorCodeArray: List[float]
    CylindersMotorCodeArray: List[float]
    CylindersTorArray: List[float]
    Version: int
    Timestamp: int

    @staticmethod
    def from_bytes(data: bytes) -> 'FeedbackMessage':
        "Build a FeedbackMessage instance from raw bytes."
        #print(data)
        Id = data[0]
        DOFStatus = StatusCodes(data[1])
        DI = data[2]
        Rev1 = data[3]

        
        # Parse packed floating-point arrays using struct.unpack.
        AttitudesArray = list(struct.unpack('<6f', data[4:28]))  
        CylindersErrorCodeArray = list(struct.unpack('<6f', data[28:52]))  
        CylindersMotorCodeArray = list(struct.unpack('<6f', data[52:76])) 
        CylindersTorArray = list(struct.unpack('<6f', data[76:100]))  
        
        Version = int.from_bytes(data[100:104], 'little')
        Timestamp = int.from_bytes(data[104:108], 'little')

        return FeedbackMessage(
            Id=Id,
            DOFStatus=DOFStatus,
            DI=DI,
            Rev1=Rev1,
            AttitudesArray=AttitudesArray,
            CylindersErrorCodeArray=CylindersErrorCodeArray,
            CylindersMotorCodeArray=CylindersMotorCodeArray,
            CylindersTorArray=CylindersTorArray,
            Version=Version,
            Timestamp=Timestamp
        )
    

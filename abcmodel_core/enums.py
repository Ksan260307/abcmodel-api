from enum import Enum


class XState(str, Enum):
    Normal = "Normal"
    Runaway = "Runaway"
    Zero = "Zero"


class Band3(str, Enum):
    Low = "Low"
    Mid = "Mid"
    High = "High"


class VolBand3(str, Enum):
    Stable = "Stable"
    Swing = "Swing"
    Spike = "Spike"
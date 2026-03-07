from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from .enums import XState


class ComponentInput(BaseModel):
    v: float = Field(ge=0, le=2)
    d: float = Field(ge=0, le=2)
    state: XState


class EFInput(BaseModel):
    E0: ComponentInput
    E1: ComponentInput
    E2: ComponentInput
    E3: ComponentInput


class CoreInput(BaseModel):
    A: ComponentInput
    B: ComponentInput
    C: ComponentInput


class ModelInput(BaseModel):
    core: CoreInput
    ef: EFInput
    # オプションの運用状態（時系列運用向け）
    zero_lock: int = 0
    cooldown: Dict[str, int] = {}
    ema_vA_prev: Optional[float] = None
    # パラメータ上書き（未指定は既定）
    version: str = "3.0.0"


class ComponentOutput(BaseModel):
    v_cont: float
    d_cont: float
    v_band: str
    d_band: str
    state: XState
    ruin: float
    ruin_band: int


class EFOutput(BaseModel):
    E0: ComponentOutput
    E1: ComponentOutput
    E2: ComponentOutput
    E3: ComponentOutput
    ruinE: float
    ruinE_band: int


class ModelOutput(BaseModel):
    A: ComponentOutput
    B: ComponentOutput
    C: ComponentOutput
    ruin_core: float
    ruin_core_band: int
    ruin_final: float
    ruin_final_band: int
    r_explain: Dict
    zero_lock: int
    cooldown: Dict[str, int]
    ema_vA: float
    version: str = "3.0.0"


class SequenceInput(BaseModel):
    frames: List[ModelInput]
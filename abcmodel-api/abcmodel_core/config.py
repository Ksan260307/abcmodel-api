from pydantic import BaseModel


class WeightsCore(BaseModel):
    w_vA: float = -1.0
    w_vB: float = +1.0
    w_vC: float = +1.0
    w_dA: float = 1.0
    w_dB: float = 1.0
    w_dC: float = 1.0
    w_sA: float = 1.0
    w_sB: float = 1.0
    w_sC: float = 1.0


class WeightsEF(BaseModel):
    w_vE0: float = 1.0
    w_vE1: float = 1.0
    w_vE2: float = 1.0
    w_vE3: float = 1.0
    w_dE0: float = 1.0
    w_dE1: float = 1.0
    w_dE2: float = 1.0
    w_dE3: float = 1.0
    w_sE0: float = 1.0
    w_sE1: float = 1.0
    w_sE2: float = 1.0
    w_sE3: float = 1.0


class InteractionsK(BaseModel):
    # §13.1 係数
    C_to_A: int = -1
    B_to_C: int = +1
    A_to_B: int = -1
    # 未指定は0（暗黙）


class NonlinearParams(BaseModel):
    g_max: float = 0.5
    alpha_v: float = 0.7
    b_spike: float = 0.35
    eta_gate: float = 1.0  # E2→C抑制係数


class SocialParams(BaseModel):
    gamma_social: float = 1.0  # {1,2} 内部連続可
    kappa_socialC: int = 0     # {0,1,2}


class RuinScoreSoft(BaseModel):
    beta: float = 0.0  # 本番0
    zeta: float = 0.0  # 本番0
    blend_alpha: float = 0.3
    soft_tau: float = 0.5
    use_blend: bool = True
    use_soft: bool = True


class TRParams(BaseModel):
    c1: int = 1
    c2: int = 2
    c3: int = 0
    c4: int = 0
    c5: int = 1
    c6: int = 0
    tr2_vB_thresh: float = 1.6
    tr3_fire: float = 1.55
    tr3_release: float = 1.45
    tr6_m: int = 1
    ema_lambda_default: float = 0.5
    ema_lambda_zero1: float = 0.6
    ema_lambda_zero2: float = 0.7
    theta_E0: float = 0.5  # ZeroLock微増補正用
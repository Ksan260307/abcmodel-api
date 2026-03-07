import math


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def round_half_up(x: float) -> int:
    # 定義: floor(x + 0.5)
    return math.floor(x + 0.5)


def band_v(v: float) -> str:
    # Low: v≤0.5 / Mid: 0.5<v<1.5 / High: v≥1.5
    if v <= 0.5:
        return "Low"
    if v < 1.5:
        return "Mid"
    return "High"


def band_d(d: float) -> str:
    # Stable: d<0.5 / Swing: 0.5≤d<1.5 / Spike: d≥1.5
    if d < 0.5:
        return "Stable"
    if d < 1.5:
        return "Swing"
    return "Spike"


def band_round_R(r_cont: float) -> int:
    # §5.5 Rバンド丸め
    if r_cont < 2.5:
        return 2
    if r_cont < 4.5:
        return 4
    if r_cont < 5.5:
        return 5
    return 6
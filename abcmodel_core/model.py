import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

from .enums import XState
from .utils import clamp, round_half_up, band_v, band_d, band_round_R
from .config import (
    WeightsCore, WeightsEF, InteractionsK, NonlinearParams, SocialParams,
    RuinScoreSoft, TRParams
)
from .schemas import ModelInput, ModelOutput, ComponentOutput, EFOutput


@dataclass
class ABCParams:
    # ミュータブルなデフォルトは default_factory を使う
    w_core: WeightsCore = field(default_factory=WeightsCore)
    w_ef: WeightsEF = field(default_factory=WeightsEF)
    k: InteractionsK = field(default_factory=InteractionsK)
    nl: NonlinearParams = field(default_factory=NonlinearParams)
    soc: SocialParams = field(default_factory=SocialParams)
    rsoft: RuinScoreSoft = field(default_factory=RuinScoreSoft)
    tr: TRParams = field(default_factory=TRParams)


def _state_mag(s: XState) -> int:
    # StateMag: Normal→0, Zero→1, Runaway→2
    return {XState.Normal: 0, XState.Zero: 1, XState.Runaway: 2}[s]


def _state_sgn_for_v(s: XState) -> int:
    # sgn: Runaway:+1, Normal:0, Zero:0（Zeroはvに寄与しない）
    return {XState.Normal: 0, XState.Runaway: +1, XState.Zero: 0}[s]


def _g(v: float, gmax: float, alpha: float) -> float:
    return gmax * math.tanh(alpha * v)


def _boost(d: float, b_spike: float) -> float:
    return 1.0 + b_spike * (1.0 if d >= 1.5 else 0.0)


def _discretize_for_log(x: float) -> int:
    # v/Δ の最終表示・ログ整数化：round_half_up 既定
    return round_half_up(x)


def _apply_EF_overlay(core_v, core_d, core_s, ef, soc: SocialParams, kappa_socialC: int):
    # 入力: dict {'A':(v,d,s), ...}, ef: {'E0':(...), ...}
    A_v, A_d, A_s = core_v['A'], core_d['A'], core_s['A']
    B_v, B_d, B_s = core_v['B'], core_d['B'], core_s['B']
    C_v, C_d, C_s = core_v['C'], core_d['C'], core_s['C']
    E0, E1, E2, E3 = ef['E0'], ef['E1'], ef['E2'], ef['E3']

    adjE2 = min(2.0, E2['v'] + (soc.gamma_social - 1.0))  # 社会感受でE2強調

    vA_p = clamp(A_v - 0.5 * (E1['v'] + E3['v'] + E0['v']), 0, 2)
    vB_p = clamp(B_v + max(0.5 * adjE2, 0.5 * E3['v']), 0, 2)
    vC_p = clamp(C_v + max(0.5 * adjE2, 0.5 * E3['v'], 0.5 * E0['v']), 0, 2)

    dA_p = clamp(max(A_d, E1['d'], E3['d'], E0['d']), 0, 2)
    dB_p = clamp(max(B_d, E2['d'], E3['d']), 0, 2)
    dC_p = clamp(min(2.0, max(C_d, E2['d'], E3['d'], E0['d']) + (kappa_socialC if adjE2 == 2 else 0)), 0, 2)

    # 状態はコピー
    A_s_p, B_s_p, C_s_p = A_s, B_s, C_s

    # 6.1.1 外的Runawayによる内部引上げ
    if E1['state'] == XState.Runaway and vA_p >= 1.0:
        A_s_p = XState.Runaway
    if E3['state'] == XState.Runaway and dC_p >= 1.5:
        C_s_p = XState.Runaway
    if E0['state'] == XState.Runaway and vA_p <= 1.0:
        A_s_p = XState.Zero
    if E0['state'] == XState.Runaway and dC_p >= 1.5:
        C_s_p = XState.Runaway

    # 6.1.2 状態競合（Zero > Runaway > Normal）
    def normalize_priority(s_list):
        if XState.Zero in s_list:
            return XState.Zero
        if XState.Runaway in s_list:
            return XState.Runaway
        return XState.Normal

    A_s_p = normalize_priority([A_s, A_s_p])
    B_s_p = normalize_priority([B_s, B_s_p])
    C_s_p = normalize_priority([C_s, C_s_p])

    return {'A': vA_p, 'B': vB_p, 'C': vC_p}, {'A': dA_p, 'B': dB_p, 'C': dC_p}, {'A': A_s_p, 'B': B_s_p, 'C': C_s_p}, adjE2


def _apply_interactions(vp, dp, sp, k: InteractionsK, nl: NonlinearParams, adjE2: float):
    # 7.1 一般 vX'' 更新
    A_vp, B_vp, C_vp = vp['A'], vp['B'], vp['C']
    A_dp, B_dp, C_dp = dp['A'], dp['B'], dp['C']
    A_sp, B_sp, C_sp = sp['A'], sp['B'], sp['C']

    # 共通係数
    def term(sY, vY, dY, kYtoX):
        sgnY = _state_sgn_for_v(sY)
        wY = 0.9 if sY == XState.Runaway else (0.25 if sY == XState.Zero else 0.0)
        return sgnY * wY * kYtoX * _g(vY, nl.g_max, nl.alpha_v) * _boost(dY, nl.b_spike)

    # vA''
    dA2 = max(
        A_dp,
        1.0 if A_sp == XState.Runaway else 0.0,
        0.5 if A_sp == XState.Zero else 0.0,
        0.5 if ((k.C_to_A != 0 and C_sp in (XState.Runaway, XState.Zero)) or (k.A_to_B != 0 and B_sp in (XState.Runaway, XState.Zero))) else 0.0
    )
    vA2 = clamp(A_vp + term(C_sp, C_vp, C_dp, k.C_to_A), 0, 2)

    # vB''（A→Bのみ）
    dB2 = max(
        B_dp,
        1.0 if B_sp == XState.Runaway else 0.0,
        0.5 if B_sp == XState.Zero else 0.0,
        0.5 if (k.A_to_B != 0 and A_sp in (XState.Runaway, XState.Zero)) else 0.0
    )
    vB2 = clamp(B_vp + term(A_sp, A_vp, A_dp, k.A_to_B), 0, 2)

    # 7.2 vC''（特殊：B→C項のみ連続ゲート）
    gate_E2C = adjE2 / 2.0
    vC2 = clamp(
        C_vp + (1.0 - nl.eta_gate * gate_E2C) * term(B_sp, B_vp, B_dp, k.B_to_C),
        0, 2
    )
    dC2 = max(
        C_dp,
        1.0 if C_sp == XState.Runaway else 0.0,
        0.5 if C_sp == XState.Zero else 0.0,
        0.5 if (k.B_to_C != 0 and B_sp in (XState.Runaway, XState.Zero)) else 0.0
    )

    return {'A': vA2, 'B': vB2, 'C': vC2}, {'A': dA2, 'B': dB2, 'C': dC2}, sp


def _apply_TR(v2, d2, s2, ef_states, params: ABCParams, zero_lock: int, cooldown: Dict[str, int], tr_runaway_absent_count: int) -> Tuple[Dict, Dict, Dict, int, Dict]:
    # クールダウン減衰
    cooldown = {k: max(0, int(v) - 1) for k, v in cooldown.items()}

    A_v, B_v, C_v = v2['A'], v2['B'], v2['C']
    A_d, B_d, C_d = d2['A'], d2['B'], d2['C']
    A_s, B_s, C_s = s2['A'], s2['B'], s2['C']

    r = params.tr

    # ZeroLock中は Zeroを優先保持し、TR-2の評価をスキップ
    def keep_zero(s: XState) -> XState:
        return XState.Zero if zero_lock > 0 else s

    # === TR-1（Zero誘発：C→A） ===
    if cooldown.get("TR1", 0) == 0:
        if C_s == XState.Runaway and C_d >= 1.5 and A_v <= 1.0:
            A_s = XState.Zero
            cooldown["TR1"] = r.c1

    # === TR-2（監視過活動化：B→C） ===
    if cooldown.get("TR2", 0) == 0 and zero_lock == 0:
        # vB'' >= 1.6 または 2フレーム連続の判定は上層で扱う簡略: ここでは閾値のみ
        if B_s == XState.Runaway and A_s == XState.Zero and (B_v >= r.tr2_vB_thresh):
            C_s = XState.Runaway
            cooldown["TR2"] = r.c2

    # === TR-3（安定化：A→B） ===
    # ヒステリシス：ここでは簡略に「発火>=1.55」のみ評価（解除は自然減衰TR-6へ）
    if A_v >= r.tr3_fire and B_d >= 0.5:
        B_d = 1.0  # Swingへ減衰

    # === TR-4（収束：B→C） ===
    if cooldown.get("TR2", 0) == 0 and B_v >= 1.5 and C_d < 0.5 and (zero_lock == 0) and (B_s != XState.Runaway):
        C_s = XState.Normal

    # === TR-5（社会トリガ：E2） ===
    if cooldown.get("TR5", 0) == 0:
        # γ_social=2 ∧ StateE2=Runaway → B=Runaway
        if params.soc.gamma_social == 2 and ef_states['E2'] == XState.Runaway:
            B_s = XState.Runaway
            cooldown["TR5"] = r.c5
            # 注意：TR-2には同フレーム反映しない→ここでは何もせず次フレームへ

    # === TR-6（Δの時間減衰） ===
    # A/B/C全てRunaway不在が m=1 ステップ継続 → ΔX := max(0, ΔX - 1)
    any_runaway = (A_s == XState.Runaway or B_s == XState.Runaway or C_s == XState.Runaway)
    if not any_runaway:
        tr_runaway_absent_count += 1
    else:
        tr_runaway_absent_count = 0

    if tr_runaway_absent_count >= r.tr6_m:
        A_d = max(0.0, A_d - 1.0)
        B_d = max(0.0, B_d - 1.0)
        C_d = max(0.0, C_d - 1.0)
        tr_runaway_absent_count = 0  # リセット

    # ZeroLockの優先保持と上書き原則
    A_s = keep_zero(A_s)
    B_s = keep_zero(B_s)
    C_s = keep_zero(C_s)

    return {'A': A_v, 'B': B_v, 'C': C_v}, {'A': A_d, 'B': B_d, 'C': C_d}, {'A': A_s, 'B': B_s, 'C': C_s}, tr_runaway_absent_count, cooldown


def _ruin_component(v, d, s, wv, wd, ws, beta, zeta) -> Tuple[float, float, bool, bool]:
    # RuinScoreX_base = w_vX·v + w_ΔX·Δ + w_sX·StateMagX
    base = wv * v + wd * d + ws * _state_mag(s)
    soft_add = (beta if (d >= 1.5 and s == XState.Runaway) else 0.0) + (zeta if s == XState.Zero else 0.0)
    pre = base + soft_add
    forced = False
    if d >= 1.5 and s == XState.Runaway:
        pre = max(pre, 5.0)  # R2以上
        forced = True
    if s == XState.Zero:
        pre = max(pre, 3.0)  # R1以上
        forced = True
    return clamp(pre, 0.0, 6.0), base, forced, (soft_add != 0.0)


def _ruin_core_and_E(core_v, core_d, core_s, ef_v, ef_d, ef_s, params: ABCParams):
    w = params.w_core
    re = params.w_ef
    beta, zeta = params.rsoft.beta, params.rsoft.zeta

    # Core
    A_ru, A_base, A_forced, A_soft = _ruin_component(core_v['A'], core_d['A'], core_s['A'], w.w_vA, w.w_dA, w.w_sA, beta, zeta)
    B_ru, B_base, B_forced, B_soft = _ruin_component(core_v['B'], core_d['B'], core_s['B'], w.w_vB, w.w_dB, w.w_sB, beta, zeta)
    C_ru, C_base, C_forced, C_soft = _ruin_component(core_v['C'], core_d['C'], core_s['C'], w.w_vC, w.w_dC, w.w_sC, beta, zeta)

    ruin_core = max(A_ru, B_ru, C_ru)

    # E：adjE2（γ_social考慮）
    adjE2 = min(2.0, ef_v['E2'] + (params.soc.gamma_social - 1.0))
    E0_ru, _, E0_forced, _ = _ruin_component(ef_v['E0'], ef_d['E0'], ef_s['E0'], re.w_vE0, re.w_dE0, re.w_sE0, beta, zeta)
    E1_ru, _, E1_forced, _ = _ruin_component(ef_v['E1'], ef_d['E1'], ef_s['E1'], re.w_vE1, re.w_dE1, re.w_sE1, beta, zeta)
    E2_ru, _, E2_forced, _ = _ruin_component(adjE2, ef_d['E2'], ef_s['E2'], re.w_vE2, re.w_dE2, re.w_sE2, beta, zeta)
    E3_ru, _, E3_forced, _ = _ruin_component(ef_v['E3'], ef_d['E3'], ef_s['E3'], re.w_vE3, re.w_dE3, re.w_sE3, beta, zeta)

    ruinE = max(E0_ru, E1_ru, E2_ru, E3_ru)
    return (A_ru, B_ru, C_ru), ruin_core, (E0_ru, E1_ru, E2_ru, E3_ru), ruinE, \
           {'A_forced': A_forced, 'B_forced': B_forced, 'C_forced': C_forced,
            'E_forced': any([E0_forced, E1_forced, E2_forced, E3_forced]),
            'soft_used': any([A_soft, B_soft, C_soft])}


def _blend_soft(ra, rb, rc, params: ABCParams) -> Tuple[float, float]:
    # 二峰性補足
    scores = [ra, rb, rc]
    sec = sorted(scores)[-2]
    blend = min(6.0, max(scores) + params.rsoft.blend_alpha * sec) if params.rsoft.use_blend else 0.0

    # τ-softmax
    tau = params.rsoft.soft_tau
    exps = [math.exp(x / tau) for x in scores]
    soft = min(6.0, tau * math.log(sum(exps))) if params.rsoft.use_soft else 0.0
    return blend, soft


def evaluate_once(inp: ModelInput, params: ABCParams, tr_state: Dict) -> Tuple[ModelOutput, Dict]:
    """1フレーム評価。tr_stateは時系列用の保持情報（ZeroLock, cooldown, countersなど）"""
    # 取り込み
    A = inp.core.A; B = inp.core.B; C = inp.core.C
    E0 = inp.ef.E0; E1 = inp.ef.E1; E2 = inp.ef.E2; E3 = inp.ef.E3

    core_v = {'A': A.v, 'B': B.v, 'C': C.v}
    core_d = {'A': A.d, 'B': B.d, 'C': C.d}
    core_s = {'A': A.state, 'B': B.state, 'C': C.state}
    ef_v = {'E0': E0.v, 'E1': E1.v, 'E2': E2.v, 'E3': E3.v}
    ef_d = {'E0': E0.d, 'E1': E1.d, 'E2': E2.d, 'E3': E3.d}
    ef_s = {'E0': E0.state, 'E1': E1.state, 'E2': E2.state, 'E3': E3.state}

    # 0) ZeroLock・クールダウン・カウンタ
    zero_lock = int(tr_state.get("zero_lock", inp.zero_lock))
    cooldown: Dict[str, int] = dict(tr_state.get("cooldown", inp.cooldown))
    absent_count = int(tr_state.get("absent_count", 0))
    ema_vA_prev = tr_state.get("ema_vA_prev", inp.ema_vA_prev)

    # 1) EF重畳（§6.1）
    v_p, d_p, s_p, adjE2 = _apply_EF_overlay(
        core_v, core_d, core_s,
        ef={
            'E0': {'v': ef_v['E0'], 'd': ef_d['E0'], 'state': ef_s['E0']},
            'E1': {'v': ef_v['E1'], 'd': ef_d['E1'], 'state': ef_s['E1']},
            'E2': {'v': ef_v['E2'], 'd': ef_d['E2'], 'state': ef_s['E2']},
            'E3': {'v': ef_v['E3'], 'd': ef_d['E3'], 'state': ef_s['E3']}
        },
        soc=params.soc, kappa_socialC=params.soc.kappa_socialC
    )

    # 2) 相互作用I（§7.1〜7.2）
    v2, d2, s2 = _apply_interactions(v_p, d_p, s_p, params.k, params.nl, adjE2)

    # 3) TR（§11） fixed order & cooldown
    v3, d3, s3, absent_count, cooldown = _apply_TR(
        v2, d2, s2, ef_states=ef_s, params=params,
        zero_lock=zero_lock, cooldown=cooldown,
        tr_runaway_absent_count=absent_count
    )

    # 4) clamp（念押し）
    for kx in ('A', 'B', 'C'):
        v3[kx] = clamp(v3[kx], 0, 2)
        d3[kx] = clamp(d3[kx], 0, 2)

    # 5) RuinScore（§5, 6.2）
    # Core
    (A_ru, B_ru, C_ru), ruin_core, (E0_ru, E1_ru, E2_ru, E3_ru), ruinE, flags = _ruin_core_and_E(
        v3, d3, s3, ef_v, ef_d, ef_s, params
    )

    # 6) 二峰性補足（任意）（§6.4）
    blend, soft = _blend_soft(A_ru, B_ru, C_ru, params)
    ruin_final = max(ruin_core, ruinE, blend, soft)

    # 7) 終端強制境界再適用（maxのみ｜冪等）→ clamp → 整数化（Rバンド丸め）
    # Spike×Runaway ≥5／Zero ≥3 はすでに各成分強制適用済みなので max 再適用だけで十分
    ruin_final = clamp(ruin_final, 0.0, 6.0)

    # 状態監査
    r_explain = {
        "top_source": "E" if ruinE >= ruin_core else "Core",
        "forced": [k for k, v in flags.items() if "forced" in k and v] or [],
        "blend_used": params.rsoft.use_blend,
        "soft_used": params.rsoft.use_soft
    }

    # Zero確率・ZeroLockの判定（§8.1, §8.2 簡略サマリ）
    # ユーザインタラクションの裏取り（発話等）はAPI外に出すため、ここではEF Zero加点のみで参考実装
    w_zero_ext = sum(1.0 for e in ('E0', 'E1', 'E2', 'E3') if ef_s[e] == XState.Zero)
    # 参考条件: 内部側は外部。実務ではアプリ層でシグナルを積む。
    w_zero_int = 0.0
    zero_score = w_zero_int + w_zero_ext
    zero_confirmed = (zero_score >= 3.0)

    # ZeroLock: 条件 8.2.1
    if (w_zero_int >= 2.0) and (ef_s['E2'] == XState.Runaway or w_zero_ext >= 2.0):
        zero_lock = max(zero_lock, 2)

    # ZeroLock解除（ランアウェイ不在 n=2）
    # ここでは absent_count 管理により自然に逓減: 不在2回で1段階
    if zero_lock > 0 and absent_count == 0:
        pass  # 維持
    elif zero_lock > 0 and absent_count >= 2:
        zero_lock = max(0, zero_lock - 1)

    # EMA vA（λはZeroLock連動）
    if zero_lock >= 2:
        lam = params.tr.ema_lambda_zero2
    elif zero_lock == 1:
        lam = params.tr.ema_lambda_zero1
    else:
        lam = params.tr.ema_lambda_default

    ema_vA = v3['A'] if ema_vA_prev is None else lam * v3['A'] + (1 - lam) * ema_vA_prev

    # 出力成分まとめ
    def comp_out(name, v, d, s, ruin):
        return ComponentOutput(
            v_cont=v,
            d_cont=d,
            v_band=band_v(v),
            d_band=band_d(d),
            state=s,
            ruin=ruin,
            ruin_band=band_round_R(ruin)
        )

    A_out = comp_out('A', v3['A'], d3['A'], s3['A'], A_ru)
    B_out = comp_out('B', v3['B'], d3['B'], s3['B'], B_ru)
    C_out = comp_out('C', v3['C'], d3['C'], s3['C'], C_ru)

    ef_out = EFOutput(
        E0=comp_out('E0', ef_v['E0'], ef_d['E0'], ef_s['E0'], E0_ru),
        E1=comp_out('E1', ef_v['E1'], ef_d['E1'], ef_s['E1'], E1_ru),
        E2=comp_out('E2', min(2.0, ef_v['E2'] + (params.soc.gamma_social - 1.0)), ef_d['E2'], ef_s['E2'], E2_ru),
        E3=comp_out('E3', ef_v['E3'], ef_d['E3'], ef_s['E3'], E3_ru),
        ruinE=ruinE,
        ruinE_band=band_round_R(ruinE)
    )

    ruin_core_band = band_round_R(ruin_core)
    ruin_final_band = band_round_R(ruin_final)

    out = ModelOutput(
        A=A_out, B=B_out, C=C_out,
        ruin_core=ruin_core, ruin_core_band=ruin_core_band,
        ruin_final=ruin_final, ruin_final_band=ruin_final_band,
        r_explain=r_explain,
        zero_lock=zero_lock,
        cooldown=cooldown,
        ema_vA=ema_vA,
        version=inp.version
    )

    # 次フレーム維持情報
    next_tr_state = {
        "zero_lock": zero_lock,
        "cooldown": cooldown,
        "absent_count": absent_count,
        "ema_vA_prev": ema_vA
    }
    return out, next_tr_state

# **Twelve-Dimensional Personality Vector Model v1.0.0（12次元人格ベクトルモデル）**

## **概要**

本モデルは、人間の性格を **12本の連続値パラメータ**として定義し、ベクトル化・閾値処理・クラスタリング・状態遷移・行動予測を行うための数学的枠組みである。  
視覚表示は **「■」** を用い、1〜5個の■で強度を表す。

***

# **1. パラメータ定義（12軸）**

## **1. Sensitivity（感性・刺激反応性）**

感情・美意識・刺激への反応の強さ。

## **2. Abstraction（抽象思考力）**

抽象化・俯瞰・概念操作。

## **3. FocusDepth（没頭力）**

対象へどれだけ深く潜り込むか。

## **4. SocialFit（社会適応性）**

社会常識・多数派価値観への適合度。

## **5. InterpersonalDistance（対人距離感）**

他者への心理距離・興味の方向性。

## **6. EmotionalRange（情緒可動域）**

感情や行動変動の広さ。

## **7. SelfStandard（自己基準の強さ）**

内的基準・価値観・審美眼の強度。

## **8. PracticalStability（実務安定性）**

タスク管理・継続力・生活的安定度。

## **9. CreativityStyle（創造性のタイプ）**

発想・構築・模倣など創造性の傾向。

## **10. Adaptability（柔軟性）**

状況・意見・新情報への適応度。

## **11. ImpulseDynamics（衝動性）**

刺激やストレスへの即応性。

## **12. ValueOrientation（価値観方向性の強度）**

美・快楽・論理・効率など、価値軸の偏りの強度。

***

# **2. バー表示（「■」）→ 数値変換規則**

| 表示    | 数値  |
| ----- | --- |
| ■     | 0.2 |
| ■■    | 0.4 |
| ■■■   | 0.6 |
| ■■■■  | 0.8 |
| ■■■■■ | 1.0 |

***

# **3. ベクトル表現（12次元）**

    P = (p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12)

各 pi は 0.0〜1.0 の連続値。

***

# **4. 内部帯域（Strength Band）**

    Low : p_i ≤ 0.35  
    Mid : 0.35 < p_i < 0.75  
    High: p_i ≥ 0.75

***

# **5. 変動帯域（Δp\_i）**

    Stable : Δp_i < 0.15  
    Swing  : 0.15 ≤ Δp_i < 0.45  
    Spike  : Δp_i ≥ 0.45

***

# **6. 状態（State\_i）**

    Normal / Runaway / Zero

***

# **7. 閾値判定（Threshold Logic）**

## **7.1 Runaway 判定**

    p_i ≥ 0.80 かつ Δp_i ≥ 0.45
    → State_i = Runaway

## **7.2 Zero 判定**

### 内部要因

    p_i ≤ 0.25              … 1.0  
    Δp_i < 0.10             … 1.0  
    直近2ステップの変動ほぼゼロ … 1.0

### 外部要因（任意）

    環境悪化・疲労・ストレスなど … +1.0

### 判定

    内部 + 外部 ≥ 2.0 → Zero

***

# **8. ヒステリシス（Hysteresis）**

## Runaway

    発火：p_i ≥ 0.80  
    解除：p_i ≤ 0.70

## Zero

    発火：p_i ≤ 0.25  
    解除：p_i ≥ 0.35

## Spike

    発火：Δp_i ≥ 0.45  
    解除：Δp_i ≤ 0.35

***

# **9. 遷移ルール（TR）**

## **TR-1（Runaway誘発）**

    p_i ≥ 0.80 かつ Δp_i ≥ 0.45  
    → Runaway

## **TR-2（Zero誘発）**

    Zero 判定成立  
    → Zero

## **TR-3（安定化：Δ抑制）**

    p_i ≥ 0.75 かつ Δp_i ≥ 0.15  
    → Δp_i := max(Δp_i - 0.15, 0)

## **TR-4（収束：Runaway → Normal）**

    State_i = Runaway  
    Δp_i < 0.15  
    → State_i = Normal

## **TR-5（外部圧 Runaway 誘発）**

    ExternalStress_i ≥ 0.7  
    → Runaway

## **TR-6（クールダウン）**

    前ステップに Runaway が存在しない場合  
    → Δp_i := max(Δp_i - 0.20, 0)

***

# **10. 外部ゲート（Gate）**

    G_i = clamp(ExternalPressure_i, 0.0, 1.0)

更新式の例：

    p_i(next)  = p_i + Δp_i · (1 - G_i)
    Δp_i(next) = Δp_i + noise · G_i

***

# **11. Zero-Lock**

## 定義

    ZeroLock_i ∈ {0,1,2}

## 発動

    Zero 判定が2連続  
    または G_i > 0.8 かつ Zero 判定成立  
    → ZeroLock_i = 2

## 効果

    ZeroLock_i > 0 の間  
    State_i = Zero を維持  
    Runaway への遷移は抑制

## 解除

    Runaway 不在が2ステップ継続  
    → ZeroLock_i -= 1

***

# **12. 最終帯域（Label Bands）**

    L0 : 0.00〜0.35  
    L1 : 0.35〜0.55  
    L2 : 0.55〜0.75  
    L3 : 0.75〜1.00

***

# **13. 類似度計算**

## ユークリッド距離

    D = sqrt( Σ (pi - qi)^2 )

## コサイン類似度

    cosθ = (P · Q) / (||P|| ||Q||)

***

# **14. クラスタリング例**

*   Sensitivity・Abstraction・CreativityStyle が高い群
*   PracticalStability・SocialFit が高い群
*   EmotionalRange と ImpulseDynamics が高い群
*   InterpersonalDistance が大きい独立型の群

***

# **15. 時系列モデル**

    P(t+1) = P(t) + ΔP

***

# **16. 因果ネットワーク（例）**

    Sensitivity → EmotionalRange  
    SelfStandard → PracticalStability  
    FocusDepth → CreativityStyle  
    InterpersonalDistance → SocialFit  
    ImpulseDynamics → EmotionalRange  
    ValueOrientation → DecisionMaking

***

# **17. 行動予測**

    Behavior = f(P, Context, Stress)

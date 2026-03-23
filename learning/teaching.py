from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TeachingGuide:
    skill_tag: str
    title: str
    key_ideas: List[str]
    common_mistakes: List[str]
    practice_goal: str
    mastery_check: str


_SKILL_GUIDES: Dict[str, TeachingGuide] = {
    "四則運算": TeachingGuide(
        skill_tag="四則運算",
        title="四則運算（含括號/乘除順序）",
        key_ideas=[
            "口訣：括號 → 乘除 → 加減；同級由左到右。",
            "每一步都要把中間結果寫出來，不跳步。",
            "做完回頭用估算檢查答案量級是否合理。",
        ],
        common_mistakes=[
            "把加減先算、忽略乘除優先。",
            "同級運算不按左到右。",
            "負號或括號漏寫，導致整串算錯。",
        ],
        practice_goal="連續 10 題運算順序題，正確率 ≥ 85%",
        mastery_check="最近 5 題中至少 4 題一次做對，且不靠提示。",
    ),
    "分數/小數": TeachingGuide(
        skill_tag="分數/小數",
        title="分數應用（先用掉/剩下/再用掉）與分數運算",
        key_ideas=[
            "先定義『整體=1』，分母代表分成幾等份。",
            "看到『剩下』先做 1 − 分數；看到『剩下的又…』第二段以『剩下量』為基準做乘法。",
            "加減要通分；乘法可先約分再乘，降低算錯率。",
        ],
        common_mistakes=[
            "把『剩下的又用掉』誤當成兩次都對原來整體（該用乘法卻用加法）。",
            "通分只乘分母不乘分子。",
            "最後問『剩下』卻回答『用掉』或反之。",
        ],
        practice_goal="同題型 3 題一組練習，連續 2 組都全對（共 6 題）。",
        mastery_check="能口頭說出：第一次剩下怎麼列式、第二次基準是什麼、最後問的是剩下還是用掉。",
    ),
    "比例": TeachingGuide(
        skill_tag="比例",
        title="比例（配方/放大縮小/路程關係）",
        key_ideas=[
            "先寫出對應關係（A:B = C:D），再決定用倍數或交叉相乘。",
            "單位要一致（公分/公尺、分鐘/小時）。",
            "先用簡單數字做『倍數感』檢查是否合理。",
        ],
        common_mistakes=[
            "把比值方向寫反（例如 A/B 與 B/A）。",
            "單位未統一就直接計算。",
        ],
        practice_goal="配方/比例縮放題 8 題，正確率 ≥ 85%",
        mastery_check="能說清楚：哪兩個量成比例、倍數從哪裡來。",
    ),
    "單位換算": TeachingGuide(
        skill_tag="單位換算",
        title="單位換算（長度/重量/容量/時間）",
        key_ideas=[
            "先寫換算表（例如 1 m = 100 cm）。",
            "乘/除 10、100、1000 的方向要用『比大比小』判斷。",
        ],
        common_mistakes=[
            "把乘除方向做反。",
            "少了 0 或多了 0。",
        ],
        practice_goal="同一種換算連續 10 題，錯題立刻訂正並再做 2 題。",
        mastery_check="看到題目能先判斷答案應變大或變小。",
    ),
    "路程時間": TeachingGuide(
        skill_tag="路程時間",
        title="路程-時間-速度（D=RT）",
        key_ideas=[
            "公式：路程 = 速度 × 時間；速度 = 路程 ÷ 時間；時間 = 路程 ÷ 速度。",
            "先統一單位（km/h 與 分鐘/小時）。",
        ],
        common_mistakes=[
            "公式套錯（把乘寫成除）。",
            "單位沒換就算。",
        ],
        practice_goal="D/R/T 三種問法各 3 題，共 9 題，正確率 ≥ 85%",
        mastery_check="能先說：題目問哪個量、已知哪兩個量。",
    ),
    "折扣": TeachingGuide(
        skill_tag="折扣",
        title="折扣（折後=原價×(1-折扣)；原價反推）",
        key_ideas=[
            "先求『折後比例』：1 − 折扣（或直接用折數換算）。",
            "原價反推用除法：原價 = 折後價 ÷ 折後比例。",
        ],
        common_mistakes=[
            "把反推原價也用乘法。",
            "把折扣比例與折後比例搞混。",
        ],
        practice_goal="折扣正推 5 題 + 反推 5 題，正確率 ≥ 85%",
        mastery_check="能說出：題目給的是原價/折後價/折扣？要用乘還是除。",
    ),
    "小數": TeachingGuide(
        skill_tag="小數",
        title="小數運算與分數小數互換",
        key_ideas=[
            "小數對齊小數點再加減；乘法先忽略小數點算整數、再數位數。",
            "除法：除數先化整數（同時移動被除數小數點）。",
            "分數⇔小數互換：分母化 10/100/1000 或長除法。",
        ],
        common_mistakes=[
            "加減時小數點沒對齊。",
            "乘法結果小數位數算錯。",
            "除法移小數點時被除數忘記跟著移。",
        ],
        practice_goal="小數四則混合 10 題，正確率 ≥ 85%",
        mastery_check="能正確完成分數⇔小數互換，且小數四則計算連續 5 題全對。",
    ),
    "體積": TeachingGuide(
        skill_tag="體積",
        title="體積與容量（長方體/正方體/組合體）",
        key_ideas=[
            "長方體體積 = 長 × 寬 × 高；正方體 = 邊長³。",
            "組合體：拆成幾個基本形體加起來，或用大減小。",
            "體積單位換算：1 L = 1000 mL = 1000 cm³。",
        ],
        common_mistakes=[
            "組合體拆解時漏掉或重複計算某部分。",
            "公升和立方公分換算錯（忘記 1 L = 1000 cm³）。",
            "正方體忘記用三次方，只用平方。",
        ],
        practice_goal="體積計算題 8 題（含 2 題組合體），正確率 ≥ 85%",
        mastery_check="能口述組合體拆解策略，並正確換算體積單位。",
    ),
    "幾何": TeachingGuide(
        skill_tag="幾何",
        title="面積與幾何圖形",
        key_ideas=[
            "長方形面積 = 長 × 寬；三角形 = 底 × 高 ÷ 2。",
            "梯形 = (上底 + 下底) × 高 ÷ 2；平行四邊形 = 底 × 高。",
            "公畝/公頃換算：1 公頃 = 10000 m²。",
        ],
        common_mistakes=[
            "三角形忘記 ÷ 2。",
            "梯形只乘一個底。",
            "高與底不對應（用了斜邊當高）。",
        ],
        practice_goal="面積計算 10 題（含 3 題複合圖形），正確率 ≥ 85%",
        mastery_check="能正確辨認底與對應高，並解釋每步面積公式。",
    ),
    "一元方程": TeachingGuide(
        skill_tag="一元方程",
        title="一元一次方程式",
        key_ideas=[
            "移項變號：把含 x 移到左邊、常數移到右邊。",
            "先去括號（分配律）、再合併同類項、最後除以係數。",
            "解完後代回原式檢查。",
        ],
        common_mistakes=[
            "移項時忘記變號（正變負）。",
            "分配律漏乘括號內的某一項。",
            "兩邊同除時忘記每一項都除。",
        ],
        practice_goal="一步/兩步/含括號方程各 3 題，共 9 題，正確率 ≥ 85%",
        mastery_check="能說出每一步的操作理由，代回檢驗答案正確。",
    ),
    "二次方程": TeachingGuide(
        skill_tag="二次方程",
        title="二次方程式（因式分解/配方/公式解）",
        key_ideas=[
            "先嘗試因式分解（十字交乘法）。",
            "因式分解不行就用配方法或公式解：x = (-b ± √(b²-4ac)) / 2a。",
            "判別式 Δ = b²-4ac 決定根的個數。",
        ],
        common_mistakes=[
            "因式分解時正負號搞反。",
            "公式解中 b² 忘記整個 b 平方（含負號）。",
            "漏掉 ± 號只寫一個根。",
        ],
        practice_goal="三種解法各 3 題，共 9 題，正確率 ≥ 80%",
        mastery_check="能選擇合適解法，並用判別式判斷根的情況。",
    ),
    "平均/應用": TeachingGuide(
        skill_tag="平均/應用",
        title="平均數分配與購物應用題",
        key_ideas=[
            "平均 = 總和 ÷ 個數；反推總和 = 平均 × 個數。",
            "購物題：單價 × 數量 = 總價；找零 = 付款 − 總價。",
            "多步驟應用先列出已知/未知，再一步步列式。",
        ],
        common_mistakes=[
            "平均數與中位數搞混。",
            "多步驟題跳步導致中間結果出錯。",
            "忘記回答題目真正問的量。",
        ],
        practice_goal="平均數應用 5 題 + 購物題 5 題，正確率 ≥ 85%",
        mastery_check="能說出題目問什麼、已知什麼、該用什麼算法。",
    ),
}

# English key aliases so both Chinese and English skill_tags work.
_SKILL_GUIDES["decimal"] = _SKILL_GUIDES["小數"]
_SKILL_GUIDES["volume"] = _SKILL_GUIDES["體積"]
_SKILL_GUIDES["geometry"] = _SKILL_GUIDES["幾何"]
_SKILL_GUIDES["linear"] = _SKILL_GUIDES["一元方程"]
_SKILL_GUIDES["quadratic"] = _SKILL_GUIDES["二次方程"]
_SKILL_GUIDES["application"] = _SKILL_GUIDES["平均/應用"]
_SKILL_GUIDES["arithmetic"] = _SKILL_GUIDES["四則運算"]
_SKILL_GUIDES["fraction"] = _SKILL_GUIDES["分數/小數"]
_SKILL_GUIDES["percent"] = _SKILL_GUIDES["比例"]
_SKILL_GUIDES["unit_conversion"] = _SKILL_GUIDES["單位換算"]


def get_teaching_guide(skill_tag: str) -> TeachingGuide:
    key = str(skill_tag or "unknown")
    return _SKILL_GUIDES.get(key) or TeachingGuide(
        skill_tag=key,
        title=f"加強：{key}",
        key_ideas=["先把題目關鍵字圈出來，列式後再算。"],
        common_mistakes=["跳步心算、沒檢查單位或題目問法。"],
        practice_goal="由易到難練習 10 題，正確率 ≥ 80%",
        mastery_check="最近 5 題中至少 4 題做對，且能解釋每一步。",
    )


def suggested_engine_topic_key(skill_tag: str) -> Optional[str]:
    """Map a high-level skill tag to an engine generator key.

    Returns None when no strong mapping exists.
    """

    skill_tag = str(skill_tag or "")

    if skill_tag == "四則運算":
        return "1"
    if skill_tag in ("分數/小數", "折扣"):
        # Fraction word problems cover many multi-step fraction/discount contexts.
        return "11"
    # Other skills may be covered by pack generators if available, but they are optional.
    return None

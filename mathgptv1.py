# =========================
# ✅ (新增) 分數題型：兩位數範圍限制 + 連續加減(三項內)
# 規格：
# - 分數通分 / 分數加減：題目與關鍵過程數值盡量控制在兩位數內
# - 新增「連續加減」：最多 3 個分數 (2~3 項)，運算為 + / - 的連續式
# - 避免產生超範圍 → 用 rejection sampling 重新生成
# =========================

MAX_2DIGIT = 99

def _within_2digit_fraction(f: Fraction) -> bool:
    """限制最簡分數的分子分母為兩位數內"""
    return abs(f.numerator) <= MAX_2DIGIT and abs(f.denominator) <= MAX_2DIGIT

def _within_2digit_int(x: int) -> bool:
    return abs(x) <= MAX_2DIGIT

def _lcm(a: int, b: int) -> int:
    return (a * b) // math.gcd(a, b)

def _lcm3(a: int, b: int, c: int) -> int:
    ab = _lcm(a, b)
    return _lcm(ab, c)

# -------------------------
# (替換) 分數通分：加上兩位數限制
# -------------------------
def gen_fraction_commondenom():
    """分數通分練習（兩位數限制：LCM、新分子控制 <=99）"""
    # 為了控制 LCM <= 99，分母使用較小集合
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]

    for _ in range(500):  # 避免死循環
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        if b1 == b2:
            continue

        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)

        if a1 / b1 == a2 / b2:
            continue

        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue

        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2

        # 兩位數限制：公分母 + 新分子
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        question = f"請將 {a1}/{b1} 和 {a2}/{b2} 通分。\n請依序輸入：公分母 新分子1 新分子2"
        topic = "分數通分"
        answer = f"{lcm_val} {na1} {na2}"

        explanation = [
            f"目標：將 {a1}/{b1} 和 {a2}/{b2} 轉換為相同分母的等值分數。",
            f"步驟 1: **找最小公倍數 (LCM)**：LCM({b1}, {b2}) = {lcm_val}",
            f"步驟 2: **通分倍率**：{lcm_val}/{b1} = {m1}，{lcm_val}/{b2} = {m2}",
            f"步驟 3: **新分子**：{a1}×{m1}={na1}，{a2}×{m2}={na2}",
            f"最終答案 (公分母 新分子1 新分子2)：{answer}"
        ]

        return {
            "topic": topic,
            "difficulty": "easy",
            "question": question,
            "answer": answer,
            "explanation": "\n".join(explanation),
        }

    # 若極端情況找不到，退回原邏輯（但仍可用）
    # （不會中斷系統）
    return {
        "topic": "分數通分",
        "difficulty": "easy",
        "question": "（生成失敗）請重試。",
        "answer": "0 0 0",
        "explanation": "目前條件過嚴導致生成失敗，請再試一次。",
    }

# -------------------------
# (替換) 分數加減：加上兩位數限制（包含中間 LCM 與結果分子分母）
# -------------------------
def gen_fraction_add():
    """真分數加減（兩位數限制：LCM <=99、結果最簡分子分母 <=99）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]

    for _ in range(500):
        b1 = random.choice(den_pool)
        b2 = random.choice(den_pool)
        a1 = random.randint(1, b1 - 1)
        a2 = random.randint(1, b2 - 1)
        op = random.choice(["+", "-"])

        # 先算 LCM，限制中間量
        lcm_val = _lcm(b1, b2)
        if lcm_val > MAX_2DIGIT:
            continue

        # 計算倍率後的分子（中間值也限制 <=99）
        m1 = lcm_val // b1
        m2 = lcm_val // b2
        na1 = a1 * m1
        na2 = a2 * m2
        if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
            continue

        # 產出結果（用 Fraction 最簡化），並限制結果分子分母
        f1 = Fraction(a1, b1)
        f2 = Fraction(a2, b2)

        # 減法確保正值（符合多數國小題型習慣）
        if op == "-" and f1 < f2:
            f1, f2 = f2, f1
            a1, b1 = f1.numerator, f1.denominator
            a2, b2 = f2.numerator, f2.denominator
            # 重新計算中間限制
            lcm_val = _lcm(b1, b2)
            if lcm_val > MAX_2DIGIT:
                continue
            m1 = lcm_val // b1
            m2 = lcm_val // b2
            na1 = a1 * m1
            na2 = a2 * m2
            if not (_within_2digit_int(na1) and _within_2digit_int(na2)):
                continue

        result = f1 + f2 if op == "+" else f1 - f2
        if result <= 0:
            continue
        if not _within_2digit_fraction(result):
            continue

        # 使用原本共用詳解（會把 LCM/通分/分子運算/約分寫出）
        _, expl = _fraction_core(a1, b1, a2, b2, op)

        question = f"{a1}/{b1} {op} {a2}/{b2} = ?"
        return {
            "topic": "分數加減",
            "difficulty": "medium",
            "question": question,
            "answer": f"{result.numerator}/{result.denominator}",
            "explanation": "\n".join(expl),
        }

    return {
        "topic": "分數加減",
        "difficulty": "medium",
        "question": "（生成失敗）請重試。",
        "answer": "0/1",
        "explanation": "目前條件過嚴導致生成失敗，請再試一次。",
    }

# -------------------------
# (新增) 連續加減（最多 3 個分數）
# - 題型：a/b ± c/d ± e/f
# - 控制 LCM(分母們) <= 99、結果最簡分子分母 <= 99
# -------------------------
def gen_fraction_chain():
    """分數連續加減（2~3 項，兩位數限制）"""
    den_pool = [2, 3, 4, 5, 6, 8, 9, 10, 12]
    terms = random.choice([2, 3])

    for _ in range(800):
        fracs = []
        dens = []
        for _i in range(terms):
            b = random.choice(den_pool)
            a = random.randint(1, b - 1)
            fracs.append(Fraction(a, b))
            dens.append(b)

        ops = [random.choice(["+", "-"]) for _ in range(terms - 1)]

        # 限制三分母 LCM
        if terms == 2:
            l = _lcm(dens[0], dens[1])
        else:
            l = _lcm3(dens[0], dens[1], dens[2])
        if l > MAX_2DIGIT:
            continue

        # 計算結果
        result = fracs[0]
        for i, op in enumerate(ops, start=1):
            result = result + fracs[i] if op == "+" else result - fracs[i]

        # 國小題型通常不出負值（這裡要求 >0）
        if result <= 0:
            continue

        if not _within_2digit_fraction(result):
            continue

        # 題目字串
        parts = [f"{fracs[0].numerator}/{fracs[0].denominator}"]
        for i, op in enumerate(ops, start=1):
            parts.append(f"{op} {fracs[i].numerator}/{fracs[i].denominator}")
        question = " ".join(parts) + " = ?"

        # 教學解說（連續加減：統一通分再做分子運算）
        expl = [
            "步驟 1: **連續加減建議做法：先統一通分**（找分母的 LCM）。",
            f"  -> 分母 LCM = {l}",
        ]
        scaled_nums = []
        for f in fracs:
            m = l // f.denominator
            sn = f.numerator * m
            if not _within_2digit_int(sn):
                break
            scaled_nums.append((f.numerator, f.denominator, m, sn))
        else:
            expl.append("步驟 2: **通分換算分子**：")
            for (a, b, m, sn) in scaled_nums:
                expl.append(f"  -> {a}/{b} = {a}×{m}/{b}×{m} = {sn}/{l}")
            expl.append("步驟 3: **同分母做分子連續加減**：")
            expr = str(scaled_nums[0][3])
            cur = scaled_nums[0][3]
            for i, op in enumerate(ops, start=1):
                if op == "+":
                    cur += scaled_nums[i][3]
                    expr += f" + {scaled_nums[i][3]}"
                else:
                    cur -= scaled_nums[i][3]
                    expr += f" - {scaled_nums[i][3]}"
            expl.append(f"  -> 分子計算：{expr} = {cur}")
            expl.append(f"  -> 得到：{cur}/{l}")
            expl.append("步驟 4: **約分**：化為最簡分數。")
            expl.append(f"  -> 最終答案：{result.numerator}/{result.denominator}")

        return {
            "topic": "分數連續加減(三項內)",
            "difficulty": "medium",
            "question": question,
            "answer": f"{result.numerator}/{result.denominator}",
            "explanation": "\n".join(expl),
        }

    return {
        "topic": "分數連續加減(三項內)",
        "difficulty": "medium",
        "question": "（生成失敗）請重試。",
        "answer": "0/1",
        "explanation": "目前條件過嚴導致生成失敗，請再試一次。",
    }

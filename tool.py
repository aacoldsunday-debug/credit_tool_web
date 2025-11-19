# =====================================================
# 単ナビ
# 進級(p): requirements2.txt を使用し、合算要件は  B（専門応用科目）余剰分 + C + E ≥ PROG_BCE_MIN
# 卒業(g): requirements1.txt を使用し、合算要件は  B（専門応用科目）余剰分 + C + D + E ≥ GRAD_BCDE_MIN
# ※B（専門応用科目）余剰分 = B1(自分の取得) + B0余剰からの充当 - B1必要分（0未満は0）
# =====================================================

import os

# ---- 合算要件の基準値 ----
PROG_BCE_MIN = 11   # 進級: B（専門応用科目）余剰分 + C + E
GRAD_BCDE_MIN = 17  # 卒業: B（専門応用科目）余剰分 + C + D + E

# 表示名
DISPLAY = {
    "A":  "A(必修科目)",
    "B0": "B（専門基礎科目）",
    "B1": "B（専門応用科目）",
    "C":  "C(選択科目)",
    "D":  "D(特殊選択科目)",
    "E":  "E(自由科目)",
}
def d(cat: str) -> str:
    return DISPLAY.get(cat, cat)

# -----------------------------------------------------
# 必要単位の読み込み
# -----------------------------------------------------
def read_requirements(filename):
    req = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                cat, val = parts
                req[cat] = int(val)
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        req.setdefault(k, 0)
    return req

# -----------------------------------------------------
# 講義リストの読み込み
# -----------------------------------------------------
def read_courses(filename="courses.txt"):
    courses = {}
    cur = None
    with open(filename, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1]
                courses.setdefault(cur, [])
            else:
                try:
                    name, cr = line.rsplit(" ", 1)
                    courses[cur].append((name, int(cr)))
                except ValueError:
                    continue
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        courses.setdefault(k, [])
    return courses

# -----------------------------------------------------
# 保存済み選択データの読み込み
# -----------------------------------------------------
def read_user_data(student_id):
    fn = f"taken_{student_id}.txt"
    if not os.path.exists(fn):
        return None
    earned_courses = {}
    with open(fn, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                cat, name, cr = parts
                earned_courses.setdefault(cat, []).append((name, int(cr)))
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        earned_courses.setdefault(k, [])
    return earned_courses

# -----------------------------------------------------
# 取得済み講義の選択
# -----------------------------------------------------
def select_courses(courses):
    earned_courses = {cat: [] for cat in courses}
    print("\n=== 取得済み講義を選択してください ===")
    print("複数選ぶときは空白区切りで番号を入力。何も取っていない場合はEnter。")
    for cat, lst in courses.items():
        print(f"\n[{d(cat)}区分]")
        for i, (name, cr) in enumerate(lst, 1):
            print(f"{i}. {name}（{cr}単位）")
        nums = input("取得済み講義の番号 → ").split()
        for n in nums:
            try:
                idx = int(n) - 1
                if 0 <= idx < len(lst):
                    earned_courses[cat].append(lst[idx])
            except ValueError:
                continue
    return earned_courses

# -----------------------------------------------------
# 区分ごとの合計
# -----------------------------------------------------
def calculate_credits(earned_courses):
    earned = {cat: sum(cr for _, cr in subs) for cat, subs in earned_courses.items()}
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        earned.setdefault(k, 0)
    return earned

# -----------------------------------------------------
# 段階的充当：B(専門基礎科目) → B(専門応用科目) → 合算要件
# -----------------------------------------------------
def cascade_allocation(required, earned):
    """
    優先順位: B（専門基礎科目） > B（専門応用科目） > 合算要件
     1) まずB（専門基礎科目）を必要分満たす。超過分は b0_surplus
     2) B（専門応用科目）は 自身の取得 + b0_surplus で満たす。
        満たした後の超過が b1_surplus_for_bundle(合算要件に使う)
    """
    need_b0 = required.get("B0", 0)
    need_b1 = required.get("B1", 0)
    got_b0  = earned.get("B0", 0)
    got_b1  = earned.get("B1", 0)

    b0_surplus = max(0, got_b0 - need_b0)
    b1_after_fill = got_b1 + b0_surplus
    b1_short = max(0, need_b1 - b1_after_fill)
    b1_surplus_for_bundle = max(0, b1_after_fill - need_b1)

    return {
        "need_b0": need_b0,
        "got_b0": got_b0,
        "b0_surplus": b0_surplus,
        "need_b1": need_b1,
        "got_b1_raw": got_b1,
        "b1_after_fill": b1_after_fill,
        "b1_short": b1_short,
        "b1_surplus_for_bundle": b1_surplus_for_bundle
    }

# -----------------------------------------------------
# 合算要件の判定（進級/卒業で異なる）
# -----------------------------------------------------
def compute_bundle(mode, earned, cas):
    c = earned.get("C", 0)
    d = earned.get("D", 0)
    e = earned.get("E", 0)
    b1_surplus = cas["b1_surplus_for_bundle"]

    if mode == "p":  # 進級: B（専門応用科目）余剰分 + C + E
        total = b1_surplus + c + e
        need  = PROG_BCE_MIN
        label = "B（専門応用科目）余剰分 + C + E"
    else:            # 卒業: B（専門応用科目）余剰分 + C + D + E
        total = b1_surplus + c + d + e
        need  = GRAD_BCDE_MIN
        label = "B（専門応用科目）余剰分 + C + D + E"

    ok = total >= need
    return label, total, need, ok

# -----------------------------------------------------
# 出力
# -----------------------------------------------------
def show_remaining(required, earned, courses, earned_courses, cas,
                   bundle_label, bundle_total, bundle_need, bundle_ok):
    print("\n=== 結果 ===")

    for cat in ["A", "B0", "B1", "C", "D", "E"]:
        need = required.get(cat, 0)
        got  = earned.get(cat, 0)

        if cat == "B0":
            remain = max(0, need - got)
            print(f"{d('B0')}区分: 必要{need} / 取得{got} / 残り{remain} ・ 余剰 {cas['b0_surplus']}")

        elif cat == "B1":
            if cas["b1_short"] > 0:
                print(f"{d('B1')}区分: 必要{need} / 取得{got} / {d('B0')}からの充当後 {cas['b1_after_fill']} / 残り{cas['b1_short']}")
            else:
                print(f"{d('B1')}区分: 必要{need} / 取得{got} / 残り0 ・ 合算に用いる{d('B1')}余剰 {cas['b1_surplus_for_bundle']}")

        elif cat == "C":
            print(f"{d('C')}区分: 取得{got}")

        else:
            remain = max(0, need - got)
            print(f"{d(cat)}区分: 必要{need} / 取得{got} / 残り{remain}")

        # 未取得候補
        if cat in courses:
            taken = {n for n, _ in earned_courses.get(cat, [])}
            remaining = [n for n, _ in courses[cat] if n not in taken]
            if remaining:
                print("→ まだ取っていない講義：")
                for n in remaining:
                    print(f"   - {n}")
        print()

    # 合算要件
    print("=== 合算要件の判定 ===")
    status = "達成" if bundle_ok else "未達成"
    print(f"{bundle_label}: 合計 {bundle_total} / 基準 {bundle_need} → {status}")

# -----------------------------------------------------
# 保存
# -----------------------------------------------------
def save_user_data(student_id, earned_courses):
    fn = f"taken_{student_id}.txt"
    with open(fn, "w", encoding="utf-8") as f:
        for cat, subs in earned_courses.items():
            for name, cr in subs:
                f.write(f"{cat} {name} {cr}\n")

# -----------------------------------------------------
# メイン
# -----------------------------------------------------
def main():
    print("=== 単ナビ ===")

    # 進級 or 卒業
    mode = ""
    while mode not in ["p", "g"]:
        mode = input("進級要件(p)か卒業要件(g)かを選んでください： ").strip().lower()

    if mode == "p":
        req_file = "requirements2.txt"
        print("\n→ 進級要件を使用します。合算要件: B（専門応用科目）余剰分 + C + E ≥", PROG_BCE_MIN)
    else:
        req_file = "requirements1.txt"
        print("\n→ 卒業要件を使用します。合算要件: B（専門応用科目）余剰分 + C + D + E ≥", GRAD_BCDE_MIN)

    student_id = input("\n学籍番号を入力してください： ").strip()

    required = read_requirements(req_file)
    courses  = read_courses()

    print("\n--- 必要単位（設定） ---")
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        print(f"{d(k)}: {required.get(k, 0)}単位")
    print("※充当の優先順位は B（専門基礎科目） > B（専門応用科目） > 合算要件")

    # 既存データ
    old = read_user_data(student_id)
    if old:
        print(f"\n前回のデータ（taken_{student_id}.txt）が見つかりました。")
        if input("上書きしますか？(y/n)： ").strip().lower() == "n":
            earned = calculate_credits(old)
            cas = cascade_allocation(required, earned)
            lab, tot, need, ok = compute_bundle(mode, earned, cas)
            show_remaining(required, earned, courses, old, cas, lab, tot, need, ok)
            print("\n※変更なしで終了します。")
            return
        else:
            print("\n新しいデータを入力します（前回の記録は上書きされます）。")

    # 新規入力
    earned_courses = select_courses(courses)
    earned = calculate_credits(earned_courses)

    # 段階的充当と合算要件
    cas = cascade_allocation(required, earned)
    bundle_label, bundle_total, bundle_need, bundle_ok = compute_bundle(mode, earned, cas)

    # 出力
    show_remaining(required, earned, courses, earned_courses, cas,
                   bundle_label, bundle_total, bundle_need, bundle_ok)

    # 保存
    save_user_data(student_id, earned_courses)
    print(f"\nデータを保存しました。（taken_{student_id}.txt）")

# -----------------------------------------------------
if __name__ == "__main__":
    main()



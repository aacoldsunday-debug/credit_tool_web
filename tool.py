# =====================================================
# 単位管理ツール（進級／卒業選択対応＋B0→B1余剰単位対応）
# -----------------------------------------------------
# 機能一覧：
# ① 起動時に「進級(p)」か「卒業(g)」を選択
# ② 対応する requirements ファイルを自動で使用
# ③ 講義リストから取得済み科目を番号で選択
# ④ 結果を区分ごとに出力（残り単位も表示）
# ⑤ B0の余剰単位をB1に自動充当
# ⑥ 学籍番号でデータ保存・上書き確認可能
# =====================================================

import os

# -----------------------------------------------------
# 必要単位を読み込む（requirements1.txt または requirements2.txt）
# -----------------------------------------------------
def read_requirements(filename):
    """必要単位をファイルから読み込む"""
    requirements = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                category, credits = parts
                requirements[category] = int(credits)

    # 欠けている区分があれば0で補完（B0/B1用）
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        requirements.setdefault(k, 0)
    return requirements


# -----------------------------------------------------
# 講義リストを区分ごとに読み込む（courses.txt）
# -----------------------------------------------------
def read_courses(filename="courses.txt"):
    """講義リストを区分ごとに読み込む"""
    courses = {}
    current_cat = None
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                current_cat = line[1:-1]
                courses[current_cat] = []
            else:
                try:
                    name, credit = line.rsplit(" ", 1)
                    courses[current_cat].append((name, int(credit)))
                except ValueError:
                    continue
    # 欠けた区分も空リストで補完
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        courses.setdefault(k, [])
    return courses


# -----------------------------------------------------
# 保存済みデータ（taken_学籍番号.txt）を読み取る
# -----------------------------------------------------
def read_user_data(student_id):
    """保存済みデータを読み取る"""
    filename = f"taken_{student_id}.txt"
    earned_courses = {}
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                cat, name, credit = parts
                earned_courses.setdefault(cat, []).append((name, int(credit)))
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        earned_courses.setdefault(k, [])
    return earned_courses


# -----------------------------------------------------
# 講義を番号で選択させる
# -----------------------------------------------------
def select_courses(courses):
    """ユーザーが取得済み講義を番号で選択"""
    earned_courses = {cat: [] for cat in courses}
    print("\n=== 取得済み講義を選択してください ===")
    print("複数選ぶときは空白区切りで番号を入力。何も取っていない場合はEnter。")

    for cat, subject_list in courses.items():
        print(f"\n[{cat}区分]")
        for i, (name, credit) in enumerate(subject_list, 1):
            print(f"{i}. {name}（{credit}単位）")

        nums = input("取得済み講義の番号 → ").split()
        for n in nums:
            try:
                idx = int(n) - 1
                if 0 <= idx < len(subject_list):
                    earned_courses[cat].append(subject_list[idx])
            except ValueError:
                continue
    return earned_courses


# -----------------------------------------------------
# 各区分の取得単位を計算
# -----------------------------------------------------
def calculate_credits(earned_courses):
    """区分ごとの取得単位数を合計"""
    earned = {cat: sum(credit for _, credit in subjects)
              for cat, subjects in earned_courses.items()}
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        earned.setdefault(k, 0)
    return earned


# -----------------------------------------------------
# B0の余剰単位をB1に充当するロジック（友達のロジック）
# -----------------------------------------------------
def apply_b0_overflow(required, earned):
    """
    B0で必要以上に取得していた単位をB1に加算。
    例: B0が12単位で要件10なら、余剰2単位をB1に回す。
    """
    need_b0 = required.get("B0", 0)
    need_b1 = required.get("B1", 0)
    got_b0 = earned.get("B0", 0)
    got_b1 = earned.get("B1", 0)

    surplus_b0 = max(0, got_b0 - need_b0)  # 余剰分
    eff_b1 = got_b1 + surplus_b0           # 実効B1単位
    remain_b1 = max(0, need_b1 - eff_b1)

    return {
        "surplus_b0": surplus_b0,
        "eff_b1": eff_b1,
        "remain_b1": remain_b1
    }


# -----------------------------------------------------
# 結果を出力（必要／取得／残り、B0→B1反映）
# -----------------------------------------------------
def show_remaining(required, earned, courses, earned_courses, overflow_info):
    """結果の出力"""
    print("\n=== 結果 ===")

    # 区分順序を固定して出力
    for cat in ["A", "B0", "B1", "C", "D", "E"]:
        need = required.get(cat, 0)
        got = earned.get(cat, 0)

        # B1だけは余剰B0を反映して表示
        if cat == "B1":
            remain = overflow_info["remain_b1"]
            surplus = overflow_info["surplus_b0"]
            eff = overflow_info["eff_b1"]
            print(f"{cat}区分: 必要{need} / 取得{got} "
                  f"（B0余剰+{surplus} → 実効{eff}） / 残り{remain}")
        else:
            remain = max(0, need - got)
            print(f"{cat}区分: 必要{need} / 取得{got} / 残り{remain}")

        # 未取得講義も表示
        if cat in courses:
            taken_names = {name for name, _ in earned_courses.get(cat, [])}
            remaining_subjects = [name for name, _ in courses[cat]
                                  if name not in taken_names]
            if remaining_subjects:
                print("→ まだ取っていない講義：")
                for name in remaining_subjects:
                    print(f"   - {name}")
        print()


# -----------------------------------------------------
# データをファイルに保存
# -----------------------------------------------------
def save_user_data(student_id, earned_courses):
    """履修データを保存"""
    filename = f"taken_{student_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for cat, subjects in earned_courses.items():
            for name, credit in subjects:
                f.write(f"{cat} {name} {credit}\n")


# -----------------------------------------------------
# メイン関数（進級/卒業選択＋余剰単位対応）
# -----------------------------------------------------
def main():
    print("=== 単位管理ツール（進級／卒業＋B0→B1余剰単位対応） ===")

    # ▼ 1. 進級 or 卒業の選択
    mode = ""
    while mode not in ["p", "g"]:
        mode = input("進級要件(p)か卒業要件(g)かを選んでください： ").strip().lower()

    if mode == "p":
        req_file = "requirements2.txt"
        print("\n→ 進級要件を使用します。")
    else:
        req_file = "requirements1.txt"
        print("\n→ 卒業要件を使用します。")

    # ▼ 2. 学籍番号入力
    student_id = input("\n学籍番号を入力してください： ").strip()

    # ▼ 3. データ読み込み
    required = read_requirements(req_file)
    courses = read_courses()

    print("\n--- 必要単位（設定） ---")
    for k in ["A", "B0", "B1", "C", "D", "E"]:
        print(f"{k}: {required.get(k, 0)}単位")
    print("※B0の余剰単位は自動的にB1へ充当されます。")

    # ▼ 4. 既存データ確認
    old_data = read_user_data(student_id)
    if old_data:
        print(f"\n前回のデータ（taken_{student_id}.txt）が見つかりました。")
        choice = input("上書きしますか？(y/n)： ").lower()
        if choice == "n":
            print("\n前回のデータを読み込みます。")
            earned = calculate_credits(old_data)
            overflow_info = apply_b0_overflow(required, earned)
            show_remaining(required, earned, courses, old_data, overflow_info)
            print("\n※変更なしで終了します。")
            return
        else:
            print("\n新しいデータを入力します（前回の記録は上書きされます）。")

    # ▼ 5. 新しいデータ入力
    earned_courses = select_courses(courses)
    earned = calculate_credits(earned_courses)

    # ▼ 6. B0→B1余剰計算
    overflow_info = apply_b0_overflow(required, earned)

    # ▼ 7. 結果出力
    show_remaining(required, earned, courses, earned_courses, overflow_info)

    # ▼ 8. データ保存
    save_user_data(student_id, earned_courses)
    print(f"\nデータを保存しました。（taken_{student_id}.txt）")


# -----------------------------------------------------
# 実行エントリーポイント
# -----------------------------------------------------
if __name__ == "__main__":
    main()

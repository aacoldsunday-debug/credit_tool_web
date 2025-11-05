# =====================================================
# 単位管理ツール Web版（Streamlit版）
# -----------------------------------------------------
# 機能：
# ① 「進級」or「卒業」モードを選択可能
# ② 講義リスト(courses.txt)から取得済み講義をチェック形式で選択
# ③ 必要／取得／残り単位を自動計算
# ④ B0余剰単位をB1に自動充当
# =====================================================

import streamlit as st
from tool import read_requirements, read_courses, calculate_credits, apply_b0_overflow

# -----------------------------------------------------
# タイトル
# -----------------------------------------------------
st.title("🎓 単位管理ツール Web版")

# -----------------------------------------------------
# 進級／卒業モード選択
# -----------------------------------------------------
mode = st.radio("判定モードを選択してください", ("進級", "卒業"))
req_file = "requirements2.txt" if mode == "進級" else "requirements1.txt"

# -----------------------------------------------------
# 学籍番号入力（データ分離用）
# -----------------------------------------------------
student_id = st.text_input("学籍番号を入力してください")

# -----------------------------------------------------
# 講義データ読み込み
# -----------------------------------------------------
required = read_requirements(req_file)
courses = read_courses()

st.markdown("---")
st.header("📘 取得済み講義を選択してください")

# -----------------------------------------------------
# 講義選択フォーム
# -----------------------------------------------------
earned_courses = {}
for cat, subject_list in courses.items():
    st.subheader(f"【{cat}区分】")
    if len(subject_list) == 0:
        st.write("（この区分には登録された講義がありません）")
        continue
    selected = st.multiselect(
        f"{cat}区分の講義を選択",
        options=[name for name, _ in subject_list],
        key=cat
    )
    earned_courses[cat] = [(name, credit) for name, credit in subject_list if name in selected]

# -----------------------------------------------------
# 実行ボタン
# -----------------------------------------------------
if st.button("結果を表示"):
    # 各区分の取得単位を集計
    earned = calculate_credits(earned_courses)
    overflow = apply_b0_overflow(required, earned)

    st.markdown("---")
    st.header("📊 結果")

    for cat in ["A", "B0", "B1", "C"]:
        need = required.get(cat, 0)
        got = earned.get(cat, 0)

        # B1はB0の余剰分を加算して表示
        if cat == "B1":
            surplus = overflow["surplus_b0"]
            eff = overflow["eff_b1"]
            remain = overflow["remain_b1"]
            st.write(
                f"**{cat}区分:** 必要 {need} / 取得 {got} "
                f"（B0余剰 +{surplus} → 実効 {eff}） / 残り {remain}"
            )
        else:
            remain = max(0, need - got)
            st.write(f"**{cat}区分:** 必要 {need} / 取得 {got} / 残り {remain}")

    st.markdown("---")

    # 合計単位（目安）も出しておくと便利
    total_required = sum(required.values())
    total_earned = sum(earned.values())
    st.subheader(f"📈 総取得単位数： {total_earned} / {total_required}")

    st.success("判定が完了しました！")

import streamlit as st
import pandas as pd
import os
import re
from tool import read_requirements, read_courses, calculate_credits

st.set_page_config(page_title="単位管理ツール", layout="wide")
st.title(" 単ナビ")

# 表示名（E区分削除）
DISPLAY = {
    "A":  "A(必修科目)",
    "B0": "B(専門基礎科目)",
    "B1": "B(専門応用科目)",
    "C":  "C(選択科目)",
    "D":  "D(特殊選択科目)",
}
def disp(cat: str) -> str:
    return DISPLAY.get(cat, cat)

# ------------------------------
# 進級 or 卒業
# ------------------------------
mode = st.radio("要件を選択してください", ["進級要件", "卒業要件"])
req_file = "requirements2.txt" if mode == "進級要件" else "requirements1.txt"
required = read_requirements(req_file)

# ------------------------------
# 学籍番号入力
# ------------------------------
student_id = st.text_input("学籍番号を入力してください", placeholder="例: 1234567")

# ------------------------------
# 講義一覧読み込み
# ------------------------------
courses = read_courses("courses.txt")

# ------------------------------
# 保存データ読み込み
# ------------------------------
loaded_taken = {}
if student_id:
    filename = f"taken_{student_id}.txt"
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().rsplit(" ", 2)
                if len(parts) != 3:
                    continue
                cat, name, credit = parts
                loaded_taken.setdefault(cat, []).append(name)
        st.success(" 保存されたデータを読み込みました！")
    else:
        st.info(" 保存データはありません（初回利用と思われます）。")

# ------------------------------
# 取得済みの講義選択
# ------------------------------
st.subheader("取得済み講義を選択してください")

earned_courses = {}

# E区分を削除 → A / B0 / B1 / C / D のみ
for cat in ["A", "B0", "B1", "C", "D"]:
    subject_list = courses.get(cat, [])
    st.markdown(f"### {disp(cat)}")
    if not subject_list:
        st.caption("登録講義なし")
        earned_courses[cat] = []
        continue

    # 保存済みの講義名
    taken_names = set(loaded_taken.get(cat, []))

    # 新規選択の候補
    options = [f"{name}（{credit}単位）" for name, credit in subject_list if name not in taken_names]

    selected = st.multiselect(
        f"{disp(cat)}で取得した講義を選択",
        options,
        key=f"sel_{cat}"
    )

    # 保存済み
    earned_courses[cat] = [(name, credit)
                           for name, credit in subject_list
                           if name in taken_names]

    # 新規入力分
    for sel in selected:
        name = sel.split("（")[0]
        m = re.search(r"(\d+)", sel)
        credit = int(m.group(1)) if m else 0
        earned_courses[cat].append((name, credit))

# ------------------------------
# 結果
# ------------------------------
if st.button("結果を表示"):
    earned = calculate_credits(earned_courses)

    st.subheader(" 結果")

    rows = []
    for cat in ["A", "B0", "B1", "C", "D"]:
        need = required.get(cat, 0)
        got = earned.get(cat, 0)
        remain = max(0, need - got)
        rows.append({"区分": disp(cat), "必要": need, "取得": got, "残り": remain})

    st.table(pd.DataFrame(rows))

    # ------------------------------
    # 詳細
    # ------------------------------
    st.subheader("詳細")
    for cat in ["A", "B0", "B1", "C", "D"]:
        if cat not in courses:
            continue
        taken_now = [name for name, _ in earned_courses.get(cat, [])]
        remaining = [
            name for name, _ in courses[cat]
            if name not in set(taken_now)
        ]
        st.markdown(f"#### {disp(cat)}")
        st.write(f"取得済み: {', '.join(taken_now) if taken_now else 'なし'}")
        st.write(f"未取得: {', '.join(remaining) if remaining else 'すべて取得済み'}")

    # ------------------------------
    # 保存
    # ------------------------------
    if student_id:
        filename = f"taken_{student_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for cat, subs in earned_courses.items():
                for name, credit in subs:
                    f.write(f"{cat} {name} {credit}\n")
        st.success(f" データを保存しました！（{filename}）")
    else:
        st.warning("学籍番号を入力するとデータを保存できます。")

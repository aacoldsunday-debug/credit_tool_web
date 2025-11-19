import streamlit as st
import pandas as pd
import os
import re
from tool import read_requirements, read_courses, calculate_credits

st.set_page_config(page_title="単位管理ツール", layout="wide")
st.title(" 単ナビ")

# 表示名
DISPLAY = {
    "A":  "A(必修科目)",
    "B0": "B(専門基礎科目)",
    "B1": "B(専門応用科目)",
    "C":  "C(選択科目)",
    "D":  "D(特殊選択科目)",
    "E":  "E(自由科目)",
}
def disp(cat: str) -> str:
    return DISPLAY.get(cat, cat)

mode = st.radio("要件を選択してください", ["進級要件", "卒業要件"])
req_file = "requirements2.txt" if mode == "進級要件" else "requirements1.txt"
required = read_requirements(req_file)

student_id = st.text_input("学籍番号を入力してください", placeholder="例: 1234567")

courses = read_courses("courses.txt")

# 保存データ読み込み
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

st.subheader("取得済み講義を選択してください")

earned_courses = {}

# 表示順はDISPLAYの順で回す（coursesに無い区分はスキップ）
for cat in ["A", "B0", "B1", "C", "D", "E"]:
    subject_list = courses.get(cat, [])
    st.markdown(f"### {disp(cat)}")
    if not subject_list:
        st.caption("登録講義なし")
        earned_courses[cat] = []
        continue

    # 保存済みを除いた選択肢
    taken_names = set(loaded_taken.get(cat, []))
    options = [f"{name}（{credit}単位）" for name, credit in subject_list if name not in taken_names]

    selected = st.multiselect(
        f"{disp(cat)}で取得した講義を選択",
        options,
        key=f"sel_{cat}"
    )

    # まず保存済み分
    earned_courses[cat] = [(name, credit) for name, credit in subject_list if name in taken_names]
    # 今回の選択分（単位を文字列から抽出：\d+ でOK）
    for sel in selected:
        name = sel.split("（")[0]
        m = re.search(r"(\d+)", sel)     # ← 修正：バックスラッシュ1つ
        credit = int(m.group(1)) if m else 0
        earned_courses[cat].append((name, credit))

if st.button("結果を表示"):
    earned = calculate_credits(earned_courses)

    st.subheader(" 結果")
    rows = []
    for cat in ["A", "B0", "B1", "C", "D", "E"]:
        need = required.get(cat, 0)
        got = earned.get(cat, 0)
        remain = max(0, need - got)
        rows.append({"区分": disp(cat), "必要": need, "取得": got, "残り": remain})
    st.table(pd.DataFrame(rows))

    st.subheader("詳細")
    for cat in ["A", "B0", "B1", "C", "D", "E"]:
        if cat not in courses:
            continue
        taken_now = [name for name, _ in earned_courses.get(cat, [])]
        remaining = [name for name, _ in courses[cat] if name not in set(taken_now)]
        st.markdown(f"#### {disp(cat)}")
        st.write(f"取得済み: {', '.join(taken_now) if taken_now else 'なし'}")
        st.write(f"未取得: {', '.join(remaining) if remaining else 'すべて取得済み'}")

    if student_id:
        filename = f"taken_{student_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            for cat, subs in earned_courses.items():
                for name, credit in subs:
                    f.write(f"{cat} {name} {credit}\n")
        st.success(f" データを保存しました！（{filename}）")
    else:
        st.warning("学籍番号を入力するとデータを保存できます。")

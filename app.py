# =====================================================
# 単位管理ツール Web版（Streamlit + Supabase REST版）
# -----------------------------------------------------
# 機能：
# ① 「進級」or「卒業」モードを選択
# ② courses.txt から取得済み講義をチェックで選択
# ③ 必要／取得／残り単位を自動計算（B0余剰 → B1充当）
# ④ 学籍番号 + モードごとに Supabase(creditsテーブル)へ保存＆自動復元
# =====================================================

import os
import json
import requests
import streamlit as st
from tool import read_requirements, read_courses, calculate_credits, apply_b0_overflow

# -----------------------------------------------------
# Supabase REST API 設定
# -----------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")          # 例: https://xxxxx.supabase.co
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # service_role のキー

if SUPABASE_URL and SUPABASE_KEY:
    CREDITS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/credits"
    BASE_HEADERS = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
else:
    CREDITS_ENDPOINT = None
    BASE_HEADERS = {}


# -----------------------------------------------------
# Supabase にデータ保存（INSERT/UPSERT代わり）
# -----------------------------------------------------
def save_user_data_to_supabase(student_id: str, db_mode: str, earned_courses: dict):
    """
    earned_courses: { "A": [(name, credit), ...], ... } を
    JSONにして credits テーブルに保存する。
    """
    if not CREDITS_ENDPOINT:
        # 環境変数が設定されていない場合は何もしない
        return

    serializable = {
        cat: [{"name": name, "credit": credit} for name, credit in subjects]
        for cat, subjects in earned_courses.items()
    }
    data_json = json.dumps(serializable, ensure_ascii=False)

    row = {
        "student_id": student_id,
        "mode": db_mode,
        "data_json": data_json,
    }

    # 同じ student_id + mode があったら上書きしたいので upsert 的に扱う
    # → on_conflict に複合ユニークキー(student_id,mode)を設定しておくとベスト
    params = {
        "on_conflict": "student_id,mode",
        "return": "representation",
    }

    resp = requests.post(
        CREDITS_ENDPOINT,
        headers={**BASE_HEADERS, "Prefer": "resolution=merge-duplicates"},
        params=params,
        json=row,
        timeout=10,
    )
    resp.raise_for_status()


# -----------------------------------------------------
# Supabase からデータ読み込み
# -----------------------------------------------------
def load_user_data_from_supabase(student_id: str, db_mode: str):
    """
    学籍番号 + モードに対応する最新の1件を取り出し、
    {cat: [(name, credit), ...]} 形式で返す。なければ None。
    """
    if not CREDITS_ENDPOINT:
        return None

    params = {
        "select": "data_json,updated_at",
        "student_id": f"eq.{student_id}",
        "mode": f"eq.{db_mode}",
        "order": "updated_at.desc",
        "limit": "1",
    }

    resp = requests.get(
        CREDITS_ENDPOINT,
        headers=BASE_HEADERS,
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None

    raw = json.loads(data[0]["data_json"])
    earned_courses = {
        cat: [(item["name"], item["credit"]) for item in items]
        for cat, items in raw.items()
    }
    return earned_courses


# =====================================================
# Streamlit アプリ本体
# =====================================================

st.title("🎓 単位管理ツール Web版")

# 進級／卒業モード選択
mode = st.radio("判定モードを選択してください", ("進級", "卒業"))
# DB保存用の内部モード名
db_mode = "progress" if mode == "進級" else "graduate"
req_file = "requirements2.txt" if mode == "進級" else "requirements1.txt"

# 学籍番号
student_id = st.text_input("学籍番号を入力してください（例: t24b123）")

# 必要単位・講義リスト
required = read_requirements(req_file)
courses = read_courses()

st.markdown("---")

# -----------------------------------------------------
# 前回データ読み込み（自動）
# -----------------------------------------------------
loaded_earned_courses = None
if student_id:
    try:
        loaded_earned_courses = load_user_data_from_supabase(student_id, db_mode)
        if loaded_earned_courses:
            st.info("✅ 前回保存されたデータを読み込みました。")
        else:
            st.info("ℹ️ 前回データは見つかりませんでした。新規入力として扱います。")
    except Exception as e:
        st.warning(f"データ読み込み中にエラーが発生しました: {e}")

# -----------------------------------------------------
# 講義選択フォーム
# -----------------------------------------------------
st.header("📘 取得済み講義を選択してください")

earned_courses = {}

for cat, subject_list in courses.items():
    st.subheader(f"【{cat}区分】")

    if not subject_list:
        st.write("（この区分には登録された講義がありません）")
        earned_courses[cat] = []
        continue

    options = [name for name, _ in subject_list]

    # 前回データがあれば初期選択として反映
    default_selected = []
    if loaded_earned_courses and cat in loaded_earned_courses:
        default_selected = [name for name, _ in loaded_earned_courses[cat]]

    selected = st.multiselect(
        f"{cat}区分の講義を選択",
        options=options,
        default=default_selected,
        key=cat,
    )

    earned_courses[cat] = [
        (name, credit) for name, credit in subject_list if name in selected
    ]

# -----------------------------------------------------
# 結果表示ボタン
# -----------------------------------------------------
if st.button("結果を表示"):
    if not student_id:
        st.error("学籍番号を入力してください。")
    else:
        earned = calculate_credits(earned_courses)
        overflow = apply_b0_overflow(required, earned)

        # Supabase に保存（失敗してもアプリ自体は動くようにする）
        try:
            save_user_data_to_supabase(student_id, db_mode, earned_courses)
        except Exception as e:
            st.warning(f"データの保存に失敗しました: {e}")

        st.markdown("---")
        st.header("📊 結果")

        for cat in ["A", "B0", "B1", "C"]:
            need = required.get(cat, 0)
            got = earned.get(cat, 0)

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
                st.write(
                    f"**{cat}区分:** 必要 {need} / 取得 {got} / 残り {remain}"
                )

        st.markdown("---")
        total_required = sum(required.values())
        total_earned = sum(earned.values())
        st.subheader(f"📈 総取得単位数： {total_earned} / {total_required}")

        st.success("判定とデータ保存が完了しました！")


import json
import os
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="后台管理", page_icon="🛠️", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"
USAGE_FILE = DATA_DIR / "usage_stats.json"
FUNDS_FILE = DATA_DIR / "funds.json"
NOTICES_FILE = DATA_DIR / "notices.json"

def ensure_json_file(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=4), encoding="utf-8")

def init_files():
    ensure_json_file(CONFIG_FILE, {})
    ensure_json_file(USAGE_FILE, {"month": datetime.now().strftime("%Y-%m"), "usage": {}})
    ensure_json_file(FUNDS_FILE, [])
    ensure_json_file(NOTICES_FILE, [])

def resolve_json_path(path: Path) -> Path:
    if not path.exists():
        return path
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    local_config = data.get("local_config") if isinstance(data, dict) else None
    if isinstance(local_config, str) and local_config:
        return path.parent / local_config
    return path

def load_json(path: Path):
    target_path = resolve_json_path(path)
    if not target_path.exists():
        return {}
    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    target_path = resolve_json_path(path)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def verify_api_key(api_key, secret_key):
    url = "https://aip.baidubce.com/oauth/2.0/token" + f"?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try:
        res = requests.post(url, timeout=5).json()
        if "access_token" in res:
            return True, "验证成功"
        return False, res.get("error_description", "密钥错误")
    except Exception as e:
        return False, f"网络请求失败: {e}"

def mask_key(val: str):
    s = str(val or "")
    if len(s) <= 8:
        return "*" * len(s)
    return s[:4] + "*" * (len(s) - 8) + s[-4:]

init_files()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123456")
if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

st.title("🛠️ 后台管理")
st.caption("用于管理 OCR 账号、公告、经费。请修改 docker-compose 中的 ADMIN_PASSWORD。")

if not st.session_state.admin_ok:
    pwd = st.text_input("请输入后台密码", type="password")
    if st.button("登录"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("密码错误")
    st.stop()

if st.button("退出登录"):
    st.session_state.admin_ok = False
    st.rerun()

configs = load_json(CONFIG_FILE)
usage = load_json(USAGE_FILE)
funds = load_json(FUNDS_FILE)
notices = load_json(NOTICES_FILE)

tab_api, tab_fund, tab_notice = st.tabs(["🔐 API账号", "💰 经费管理", "📢 公告管理"])

with tab_api:
    st.subheader("现有账号")
    if not configs:
        st.info("暂无 OCR 账号")
    else:
        for name, item in configs.items():
            use_count = usage.get("usage", {}).get(item.get("api_key", ""), 0)
            c1, c2, c3, c4 = st.columns([2, 3, 2, 1])
            c1.write(f"**{name}**")
            c2.write(f"API Key: `{mask_key(item.get('api_key', ''))}`")
            c3.write(f"本月用量: {use_count}")
            if c4.button("删除", key=f"del_api_{name}"):
                configs.pop(name, None)
                save_json(CONFIG_FILE, configs)
                st.success("已删除")
                st.rerun()
    st.markdown("---")
    st.subheader("添加账号")
    with st.form("add_api"):
        new_name = st.text_input("账号名称")
        new_key = st.text_input("Baidu API Key")
        new_secret = st.text_input("Baidu Secret Key", type="password")
        submit_api = st.form_submit_button("验证并保存")
    if submit_api:
        if not (new_name and new_key and new_secret):
            st.warning("请填写完整参数")
        elif new_name in configs:
            st.warning("账号名称已存在")
        else:
            ok, msg = verify_api_key(new_key, new_secret)
            if ok:
                configs[new_name] = {"api_key": new_key, "secret_key": new_secret}
                save_json(CONFIG_FILE, configs)
                st.success("添加成功")
                st.rerun()
            else:
                st.error(msg)

with tab_fund:
    st.subheader("当前经费")
    if not funds:
        st.info("暂无经费")
    else:
        for idx, f in enumerate(funds):
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
            c1.write(f"**{f.get('卡号', '')}**")
            c2.write(f.get("名称", ""))
            c3.write(f.get("负责人", ""))
            c4.write(f"{f.get('类别', '')} / {f.get('备注', '')}")
            if c5.button("删除", key=f"del_fund_{idx}"):
                funds.pop(idx)
                save_json(FUNDS_FILE, funds)
                st.success("已删除")
                st.rerun()
    st.markdown("---")
    st.subheader("添加经费")
    with st.form("add_fund"):
        nf_no = st.text_input("经费卡号 *")
        nf_name = st.text_input("经费名称 *")
        nf_lead = st.text_input("负责人 *")
        nf_type = st.selectbox("经费类别", ["A类", "B类", "C类", "D类"])
        nf_note = st.text_input("备注")
        submit_fund = st.form_submit_button("保存经费")
    if submit_fund:
        if nf_no and nf_name and nf_lead:
            funds.append({"卡号": nf_no, "名称": nf_name, "负责人": nf_lead, "类别": nf_type, "备注": nf_note})
            save_json(FUNDS_FILE, funds)
            st.success("添加成功")
            st.rerun()
        else:
            st.warning("请至少填写卡号、名称、负责人")

with tab_notice:
    st.subheader("发布公告")
    with st.form("add_notice"):
        ntc_level = st.selectbox("级别", ["📘 普通", "⚠️ 重要", "🚨 紧急"])
        ntc_title = st.text_input("标题")
        ntc_content = st.text_area("公告内容", height=120)
        submit_notice = st.form_submit_button("发布公告")
    if submit_notice:
        if ntc_title and ntc_content:
            notices.insert(0, {"id": datetime.now().strftime("%Y%m%d%H%M%S"), "level": ntc_level, "title": ntc_title, "content": ntc_content, "time": datetime.now().strftime("%Y-%m-%d %H:%M"), "active": True})
            save_json(NOTICES_FILE, notices)
            st.success("发布成功")
            st.rerun()
        else:
            st.warning("请填写标题和内容")
    st.markdown("---")
    st.subheader("已发布公告")
    if not notices:
        st.info("暂无公告")
    else:
        for idx, n in enumerate(notices):
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            status = "🟢启用" if n.get("active", True) else "⚫停用"
            c1.write(f"**{n.get('title', '')}**  \n{n.get('level', '')} | {n.get('time', '')} | {status}")
            if c2.button("切换状态", key=f"toggle_notice_{n['id']}"):
                notices[idx]["active"] = not notices[idx].get("active", True)
                save_json(NOTICES_FILE, notices)
                st.rerun()
            if c3.button("删除", key=f"del_notice_{n['id']}"):
                notices.pop(idx)
                save_json(NOTICES_FILE, notices)
                st.rerun()
            with c4.popover("查看内容"):
                st.write(n.get("content", ""))

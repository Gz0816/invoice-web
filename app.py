import base64
import io
import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="陈育伟工作室-发票入库系统", page_icon="🧾", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    .app-header { background: linear-gradient(135deg, #0F2D6E 0%, #1D4ED8 100%); color: white; padding: 18px 28px; border-radius: 14px; margin-bottom: 18px; display: flex; align-items: center; gap: 16px; }
    .app-header-icon { font-size: 36px; line-height: 1; }
    .app-header h1 { color: white; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: .5px; }
    .app-header p  { color: rgba(255,255,255,.65); margin: 3px 0 0; font-size: 12.5px; }
    .badge { display: inline-block; padding: 3px 12px; border-radius: 99px; font-size: 12px; font-weight: 600; line-height: 1.6; }
    .badge-success { background: #DCFCE7; color: #15803D; }
    .badge-warning { background: #FEF3C7; color: #B45309; }
    .badge-danger  { background: #FEE2E2; color: #B91C1C; }
    .file-card { border-radius: 8px; padding: 7px 11px; font-size: 12.5px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .file-done { background: #F0FDF4; border: 1px solid #86EFAC; color: #166534; }
    .file-pending { background: #EFF6FF; border: 1px solid #93C5FD; color: #1E40AF; }
    .fund-card { background: #F0F7FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 10px 14px; margin-top: 6px; font-size: 12px; line-height: 1.8; color: #1E3A5F; }
    .fund-card .fund-name { font-size: 13px; font-weight: 700; color: #1D4ED8; }
    .fund-card .fund-tag { display: inline-block; background: #DBEAFE; color: #1E40AF; border-radius: 99px; padding: 1px 8px; font-size: 11px; margin-left: 6px; }
    .summary-bar { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
    .summary-card { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 18px; text-align: center; flex: 1; min-width: 100px; }
    .summary-card .val { font-size: 22px; font-weight: 700; color: #1D4ED8; }
    .summary-card .lbl { font-size: 11px; color: #94A3B8; margin-top: 2px; }
    .hist-meta { font-size: 12px; color: #94A3B8; margin-top: 2px; }
    .section-title { font-size: 15px; font-weight: 600; color: #1E293B; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
    .notice-banner { border-radius: 10px; padding: 11px 18px; margin-bottom: 14px; display: flex; align-items: flex-start; gap: 12px; font-size: 13.5px; line-height: 1.65; }
    .notice-info { background: #EFF6FF; border: 1px solid #93C5FD; color: #1E3A5F; }
    .notice-warning { background: #FFFBEB; border: 1px solid #FCD34D; color: #78350F; }
    .notice-danger { background: #FFF1F2; border: 1px solid #FDA4AF; color: #881337; }
    .notice-icon { font-size: 20px; flex-shrink: 0; line-height: 1.5; }
    .notice-body { flex: 1; }
    .notice-title { font-weight: 700; font-size: 14px; margin-bottom: 2px; }
    .notice-meta { font-size: 11px; opacity: .6; margin-top: 4px; }
    .notice-popup { border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 10px; font-size: 13.5px; line-height: 1.65; }
    .folder-list { border: 1px dashed #CBD5E1; background: #F8FAFC; border-radius: 8px; padding: 10px 12px; color: #475569; font-size: 12.5px; line-height: 1.7; }
    div[data-testid="stProgress"] > div { height: 6px !important; border-radius: 99px; }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"
USAGE_FILE = DATA_DIR / "usage_stats.json"
HISTORY_FILE = DATA_DIR / "history.json"
FUNDS_FILE = DATA_DIR / "funds.json"
NOTICES_FILE = DATA_DIR / "notices.json"
DISMISSED_NOTICES_FILE = DATA_DIR / "dismissed_notices.json"

INVENTORY_EXPORT_COLUMNS = [
    "材料类型",
    "材料名称",
    "型号规格",
    "计量单位",
    "数量",
    "单价(元)",
    "总价(元)",
    "品牌",
    "经销商",
    "有效时间（天）",
    "低库存告警数",
    "入库时间",
    "存放地点",
    "验收总结",
    "验收人",
    "经费编号",
    "经费名称",
    "所属学院",
    "管理员",
    "备注",
    "进口",
]

INVENTORY_EXPORT_ALIASES = {
    "型号规格": ["规格型号"],
    "单价(元)": ["单价"],
    "总价(元)": ["总价"],
    "有效时间（天）": ["有效时间"],
    "低库存告警数": ["低库存警告"],
    "经费编号": ["经费卡号"],
}

def ensure_json_file(path: Path, default):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=4), encoding="utf-8")

def init_files():
    ensure_json_file(CONFIG_FILE, {})
    ensure_json_file(USAGE_FILE, {"month": datetime.now().strftime("%Y-%m"), "usage": {}})
    ensure_json_file(HISTORY_FILE, [])
    ensure_json_file(FUNDS_FILE, [])
    ensure_json_file(NOTICES_FILE, [])
    ensure_json_file(DISMISSED_NOTICES_FILE, [])

init_files()

_defaults = {
    "processed_files": [],
    "final_df": pd.DataFrame(),
    "usage_stats": {},
    "file_mapping": {},
    "source_previews": {},
    "dismissed_notices": set(),
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def get_current_month():
    return datetime.now().strftime("%Y-%m")

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

def get_dismissed_notice_ids() -> set:
    data = load_json(DISMISSED_NOTICES_FILE)
    return set(data if isinstance(data, list) else [])

def save_dismissed_notice_ids(ids: set):
    save_json(DISMISSED_NOTICES_FILE, sorted(ids))

def build_uploaded_source(file):
    return {
        "key": f"upload::{file.name}",
        "name": file.name,
        "display": file.name,
        "suffix": Path(file.name).suffix.lower(),
        "kind": "upload",
        "file": file,
    }

def build_local_pdf_source(path: Path):
    resolved = path.resolve()
    return {
        "key": f"path::{resolved}",
        "name": path.name,
        "display": str(resolved),
        "suffix": ".pdf",
        "kind": "local",
        "path": resolved,
    }

def read_invoice_source(source: dict) -> bytes:
    if source["kind"] == "local":
        return source["path"].read_bytes()
    return source["file"].getvalue()

def source_is_processed(source: dict) -> bool:
    return source["key"] in st.session_state.processed_files or source["name"] in st.session_state.processed_files

def discover_pdf_sources(folder_text: str):
    sources = []
    errors = []
    seen = set()
    folder_paths = [line.strip().strip('"') for line in re.split(r"[\r\n;]+", folder_text or "") if line.strip()]
    for raw_path in folder_paths:
        folder = Path(os.path.expandvars(os.path.expanduser(raw_path)))
        if not folder.exists():
            errors.append(f"{raw_path} 不存在")
            continue
        if not folder.is_dir():
            errors.append(f"{raw_path} 不是文件夹")
            continue
        for pdf_path in sorted(folder.rglob("*.pdf")):
            try:
                key = str(pdf_path.resolve()).lower()
            except OSError:
                continue
            if key in seen:
                continue
            seen.add(key)
            sources.append(build_local_pdf_source(pdf_path))
    return sources, errors

def remember_source_preview(source: dict, file_bytes: bytes):
    preview = {"name": source["name"], "suffix": source["suffix"], "kind": source["kind"]}
    if source["kind"] == "local":
        preview["path"] = str(source["path"])
    else:
        preview["bytes"] = file_bytes
    st.session_state.source_previews[source["key"]] = preview

def get_token(api_key, secret_key):
    url = "https://aip.baidubce.com/oauth/2.0/token" + f"?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
    try:
        return requests.post(url, timeout=5).json().get("access_token")
    except Exception:
        return None

def increment_usage(api_key):
    stats = load_json(USAGE_FILE)
    if stats.get("month") != get_current_month():
        stats = {"month": get_current_month(), "usage": {}}
    stats["usage"][api_key] = stats["usage"].get(api_key, 0) + 1
    save_json(USAGE_FILE, stats)
    st.session_state.usage_stats = stats

def classify_material(unit_price: float) -> str:
    unit_price = abs(float(unit_price or 0))
    if unit_price < 200:
        return "易耗品"
    if unit_price <= 1000:
        return "低值耐用品"
    return "高额材料物资"

def word_val(obj):
    if isinstance(obj, dict):
        return obj.get("word", "")
    return str(obj) if obj else ""

def safe_float(lst, idx, default=0.0):
    try:
        raw = lst[idx].get("word", str(default)) if idx < len(lst) else str(default)
        raw = str(raw).replace(",", "").strip()
        return float(raw) if raw else default
    except Exception:
        return default

def save_to_history(df: pd.DataFrame, name: str):
    history = load_json(HISTORY_FILE)
    record = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(df),
        "files": st.session_state.processed_files.copy(),
        "data": df.to_dict(orient="records"),
    }
    history.insert(0, record)
    save_json(HISTORY_FILE, history[:20])

def build_inventory_export_df(df: pd.DataFrame) -> pd.DataFrame:
    export_data = {}
    for column in INVENTORY_EXPORT_COLUMNS:
        source_columns = [column] + INVENTORY_EXPORT_ALIASES.get(column, [])
        source = next((name for name in source_columns if name in df.columns), None)
        export_data[column] = df[source] if source else ""
    return pd.DataFrame(export_data, index=df.index)

def build_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        export_df = build_inventory_export_df(df)
        export_df.to_excel(writer, index=False, sheet_name="入库单")
        wb = writer.book
        ws = writer.sheets["入库单"]
        hdr = wb.add_format({"bold": True, "bg_color": "#D7E4BC", "border": 1, "align": "center", "valign": "vcenter"})
        text_fmt = wb.add_format({"valign": "vcenter"})
        number_fmt = wb.add_format({"num_format": "0.00", "valign": "vcenter"})
        money_fmt = wb.add_format({"num_format": "0.00", "valign": "vcenter"})
        for i, col in enumerate(export_df.columns):
            max_len = export_df[col].astype(str).map(len).max() if len(export_df) > 0 else len(col)
            col_w = min(max(max_len, len(col)) + 4, 50)
            fmt = money_fmt if col in {"单价(元)", "总价(元)"} else number_fmt if col in {"数量", "有效时间（天）", "低库存告警数"} else text_fmt
            ws.set_column(i, i, col_w, fmt)
            ws.write(0, i, col, hdr)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(export_df), 1), len(export_df.columns) - 1)
    return output.getvalue()

def normalize_name(name: str) -> str:
    s = str(name or "").strip().lower()
    s = re.sub(r"[\s\*\-_/\\()（）\[\]【】,:：;；]+", "", s)
    return s

def name_match_score(a: str, b: str) -> float:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.95
    return SequenceMatcher(None, na, nb).ratio()

def is_blank_discount_meta(row: dict) -> bool:
    model_blank = not str(row.get("型号规格", "") or row.get("规格型号", "") or "").strip()
    unit_blank = not str(row.get("计量单位", "") or "").strip()
    qty_zero = abs(float(row.get("数量", 0) or 0)) < 1e-9
    price_zero = abs(float(row.get("单价(元)", row.get("单价", 0)) or 0)) < 1e-9
    return model_blank and unit_blank and qty_zero and price_zero

def merge_discount_rows(invoice_rows: list) -> list:
    pos_rows = [r.copy() for r in invoice_rows if r["总价(元)"] >= 0]
    neg_rows = [r.copy() for r in invoice_rows if r["总价(元)"] < 0]
    merged_neg_idx = set()
    for i, neg in enumerate(neg_rows):
        best_idx = None
        best_score = 0.0
        for j, pos in enumerate(pos_rows):
            score = name_match_score(neg["材料名称"], pos["材料名称"])
            if is_blank_discount_meta(neg):
                score += 0.03
            neg_model = str(neg.get("型号规格", "") or neg.get("规格型号", "") or "").strip()
            pos_model = str(pos.get("型号规格", "") or pos.get("规格型号", "") or "").strip()
            if neg_model and pos_model and neg_model == pos_model:
                score += 0.03
            if score > best_score:
                best_score = score
                best_idx = j
        if best_idx is not None and best_score >= 0.88:
            base = pos_rows[best_idx]
            base["总价(元)"] = round(base["总价(元)"] + neg["总价(元)"], 2)
            qty = float(base.get("数量", 0) or 0)
            base["单价(元)"] = round(base["总价(元)"] / qty, 2) if qty else 0.0
            base["材料类型"] = classify_material(base["单价(元)"])
            note = str(base.get("备注", "") or "")
            extra = f"合并折扣:{neg['材料名称']}({neg['总价(元)']})"
            base["备注"] = f"{note}; {extra}".strip("; ")
            merged_neg_idx.add(i)
    result = [r for r in pos_rows if abs(r["总价(元)"]) > 1e-9]
    for i, neg in enumerate(neg_rows):
        if i not in merged_neg_idx:
            result.append(neg)
    return result

def extract_invoice_rows(source: dict, token: str, api_key: str, invoice_id: str, defaults: dict, selected_fund: dict):
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice?access_token={token}"
    file_bytes = read_invoice_source(source)
    file_b64 = base64.b64encode(file_bytes).decode()
    payload = {"pdf_file": file_b64} if source["suffix"] == ".pdf" else {"image": file_b64}
    res = requests.post(url, data=payload, timeout=15).json()
    increment_usage(api_key)
    if "words_result" not in res:
        return [], res.get("error_msg", "未知错误"), file_bytes

    words = res["words_result"]
    seller_name = word_val(words.get("SellerName", ""))
    invoice_num = word_val(words.get("InvoiceNum", ""))
    invoice_date = word_val(words.get("InvoiceDate", ""))
    names = words.get("CommodityName", [])
    nums = words.get("CommodityNum", [])
    amounts = words.get("CommodityAmount", [])
    taxes = words.get("CommodityTax", [])
    models = words.get("CommodityType", [])
    units = words.get("CommodityUnit", [])
    invoice_rows = []
    for i in range(len(names)):
        name = names[i].get("word", "未识别") if i < len(names) else "未识别"
        pretax_amount = safe_float(amounts, i, default=0.0)
        tax_amount = safe_float(taxes, i, default=0.0)
        total_price = round(pretax_amount + tax_amount, 2)
        quantity_raw = safe_float(nums, i, default=0.0)
        quantity = 0.0 if quantity_raw == 0 and total_price < 0 else quantity_raw or 1.0
        unit_price = round(total_price / quantity, 2) if quantity else 0.0
        model = models[i].get("word", "") if i < len(models) else ""
        unit = units[i].get("word", "") if i < len(units) else ""
        invoice_rows.append({
            "发票编号": invoice_id,
            "发票号码": invoice_num,
            "开票日期": invoice_date,
            "材料类型": classify_material(unit_price),
            "材料名称": name,
            "型号规格": model,
            "计量单位": unit,
            "数量": quantity,
            "单价(元)": unit_price,
            "总价(元)": total_price,
            "品牌": "",
            "经销商": seller_name,
            "有效时间（天）": 0,
            "低库存告警数": 0,
            "入库时间": datetime.now().strftime("%Y-%m-%d"),
            "存放地点": defaults["location"],
            "验收总结": defaults["summary"],
            "验收人": defaults["inspector"],
            "经费名称": selected_fund["名称"],
            "经费编号": selected_fund["卡号"],
            "所属学院": defaults["college"],
            "管理员": defaults["admin"],
            "备注": "",
            "进口": "",
        })
    return merge_discount_rows(invoice_rows), None, file_bytes

def render_notice_popup(notices: list):
    dismissed_forever = get_dismissed_notice_ids()
    active = [
        n for n in notices
        if n.get("active", True)
        and str(n.get("id", "")) not in dismissed_forever
        and str(n.get("id", "")) not in st.session_state.dismissed_notices
    ]
    if not active:
        return

    ntc = active[0]
    nid = str(ntc.get("id", ""))
    level_map = {"📘 普通": ("notice-info", "📘"), "⚠️ 重要": ("notice-warning", "⚠️"), "🚨 紧急": ("notice-danger", "🚨")}
    css, icon = level_map.get(ntc.get("level", "📘 普通"), ("notice-info", "📘"))

    def notice_body():
        st.markdown(f"""
            <div class="notice-popup {css}">
                <div class="notice-icon">{icon}</div>
                <div class="notice-body">
                    <div class="notice-title">{ntc.get('title', '公告')}</div>
                    {ntc.get('content', '')}
                    <div class="notice-meta">📅 发布于 {ntc.get('time', '')}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        close_col, dismiss_col = st.columns(2)
        with close_col:
            if st.button("关闭", key=f"close_notice_{nid}", use_container_width=True):
                st.session_state.dismissed_notices.add(nid)
                st.rerun()
        with dismiss_col:
            if st.button("不再显示", key=f"dismiss_notice_{nid}", type="primary", use_container_width=True):
                dismissed_forever.add(nid)
                save_dismissed_notice_ids(dismissed_forever)
                st.session_state.dismissed_notices.add(nid)
                st.rerun()

    dialog_factory = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if dialog_factory:
        try:
            dialog_decorator = dialog_factory("公告", width="small")
        except TypeError:
            dialog_decorator = dialog_factory("公告")

        @dialog_decorator
        def notice_dialog():
            notice_body()

        notice_dialog()
    else:
        with st.container(border=True):
            notice_body()

st.session_state.usage_stats = load_json(USAGE_FILE)
all_configs = load_json(CONFIG_FILE)
all_funds = load_json(FUNDS_FILE)
all_notices = load_json(NOTICES_FILE)

with st.sidebar:
    st.markdown("### 📋 入库参数预设")
    defaults = {
        "location": st.text_input("📍 存放地点", "4#422"),
        "inspector": st.text_input("👤 验收人", "王森远"),
        "admin": st.text_input("🔑 管理员", "何欣"),
        "summary": st.text_input("📝 验收总结", "完好"),
        "college": st.text_input("🏫 所属学院", "物理与光电工程学院"),
    }
    st.markdown("---")
    st.markdown("### 💰 经费选择")
    if all_funds:
        fund_labels = [f"{'[' + f['备注'] + '] ' if f.get('备注') else ''}{f['名称']}" for f in all_funds]
        selected_fund_idx = st.selectbox("选择报销经费", options=range(len(all_funds)), format_func=lambda i: fund_labels[i], label_visibility="collapsed")
        selected_fund = all_funds[selected_fund_idx]
        st.markdown(f"""
            <div class="fund-card">
                <div class="fund-name">{selected_fund['名称']}<span class="fund-tag">{selected_fund['类别']}</span></div>
                卡号：{selected_fund['卡号']}<br>
                负责人：{selected_fund['负责人']}<br>
                {('<span style="color:#B45309">⚠️ ' + selected_fund['备注'] + '</span>') if selected_fund.get('备注') else ''}
            </div>
        """, unsafe_allow_html=True)
    else:
        selected_fund = {"名称": "", "卡号": "", "负责人": "", "类别": "", "备注": ""}
        st.warning("当前没有可用经费，请到“后台管理”页面添加。")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ 清空表格", use_container_width=True):
            st.session_state.processed_files = []
            st.session_state.final_df = pd.DataFrame()
            st.session_state.file_mapping = {}
            st.session_state.source_previews = {}
            st.rerun()
    with c2:
        if st.button("💾 存入历史", use_container_width=True):
            if not st.session_state.final_df.empty:
                save_to_history(st.session_state.final_df, f"会话_{datetime.now().strftime('%m%d_%H%M')}")
                st.success("已存入历史！")
            else:
                st.warning("当前表格为空")
    st.markdown("---")
    st.info("敏感配置已移到“后台管理”页面。")

st.markdown("""
<div class="app-header">
    <div class="app-header-icon">🧾</div>
    <div>
        <h1>陈育伟工作室-发票入库系统</h1>
        <p>支持批量 JPG / PNG / PDF · 自动分类 · 一键导出台账</p>
    </div>
</div>
""", unsafe_allow_html=True)

render_notice_popup(all_notices)

if not all_configs:
    st.warning("当前没有可用百度 OCR 账号，请到“后台管理”页面添加。")
    st.stop()

sc1, sc2, sc3, sc4 = st.columns([2, 2, 2, 4])
with sc1:
    selected_name = st.selectbox("账号", options=list(all_configs.keys()), label_visibility="collapsed")
current_api_key = all_configs[selected_name]["api_key"]
usage_count = st.session_state.usage_stats.get("usage", {}).get(current_api_key, 0)
remain = 1000 - usage_count
with sc2:
    if usage_count >= 1000:
        badge_cls, badge_txt = "badge-danger", "🔴 已耗尽"
    elif usage_count > 800:
        badge_cls, badge_txt = "badge-warning", "🟠 额度紧张"
    else:
        badge_cls, badge_txt = "badge-success", "🟢 额度充裕"
    st.markdown(f"<div style='padding-top:8px'><span class='badge {badge_cls}'>{badge_txt}</span><span style='font-size:12px;color:#94A3B8;margin-left:8px'>{usage_count}/1000 · 剩余 {remain}</span></div>", unsafe_allow_html=True)
with sc3:
    n_files = len(st.session_state.processed_files)
    n_rows = len(st.session_state.final_df)
    st.markdown(f"<div style='padding-top:8px;font-size:13px;color:#64748B'>📄 已处理 <b>{n_files}</b> 张 · <b>{n_rows}</b> 条记录</div>", unsafe_allow_html=True)
with sc4:
    st.progress(min(usage_count / 1000, 1.0))
is_locked = usage_count >= 800
st.markdown("---")

tab_extract, tab_history = st.tabs(["📥 发票提取与核对", "📚 历史存档"])

with tab_extract:
    uploaded_files = st.file_uploader("拖拽或点击上传发票（支持批量，已识别文件自动跳过）", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)
    folder_text = st.text_area("本地 PDF 文件夹路径（一行一个）", height=86, placeholder=r"D:\发票\4月\第一批")
    upload_sources = [build_uploaded_source(f) for f in (uploaded_files or [])]
    folder_sources, folder_errors = discover_pdf_sources(folder_text)
    invoice_sources = upload_sources + folder_sources
    if invoice_sources:
        st.markdown("##### 📂 待识别文件状态")
        cols = st.columns(min(len(invoice_sources), 6))
        for i, source in enumerate(invoice_sources):
            done = source_is_processed(source)
            css = "file-done" if done else "file-pending"
            icon = "✅" if done else "⏳"
            label = source["name"] if source["kind"] == "upload" else source["display"]
            label = label if len(label) <= 16 else label[:14] + "…"
            cols[i % 6].markdown(f"<div class='file-card {css}'>{icon} {label}</div>", unsafe_allow_html=True)
    if folder_text:
        if folder_errors:
            for err in folder_errors:
                st.warning(err)
        st.caption(f"文件夹扫描到 {len(folder_sources)} 个 PDF")
    btn_col, _ = st.columns([2, 8])
    with btn_col:
        start = st.button("🚀 开始智能提取", type="primary", disabled=is_locked or not invoice_sources, use_container_width=True)
    if start:
        new_sources = [source for source in invoice_sources if not source_is_processed(source)]
        if not new_sources:
            st.toast("💡 所有文件均已处理过，无需重复识别！")
        else:
            conf = all_configs[selected_name]
            token = get_token(conf["api_key"], conf["secret_key"])
            if not token:
                st.error("Token 获取失败，请检查后台中的账号配置。")
            else:
                all_new_rows = []
                progress_bar = st.progress(0, text="正在识别中…")
                status_ph = st.empty()
                for idx, source in enumerate(new_sources):
                    display_name = source["display"] if source["kind"] == "local" else source["name"]
                    usage_data = load_json(USAGE_FILE)
                    live_usage = usage_data.get("usage", {}).get(conf["api_key"], 0)
                    if live_usage >= 800:
                        st.error(f"⚠️ 处理「{display_name}」时额度达到 800 次上限，已中止！")
                        break
                    status_ph.info(f"正在识别 {idx + 1}/{len(new_sources)}：{display_name}")
                    try:
                        invoice_idx = len(st.session_state.processed_files) + 1
                        invoice_id = f"第 {invoice_idx} 张"
                        rows, error_msg, file_bytes = extract_invoice_rows(source, token, conf["api_key"], invoice_id, defaults, selected_fund)
                        if error_msg:
                            st.error(f"识别异常（{display_name}）: {error_msg}")
                            continue
                        all_new_rows.extend(rows)
                        st.session_state.file_mapping[invoice_id] = source["key"]
                        remember_source_preview(source, file_bytes)
                        st.session_state.processed_files.append(source["key"])
                    except Exception as e:
                        st.error(f"处理「{display_name}」时出错：{e}")
                    progress_bar.progress((idx + 1) / len(new_sources), text=f"已完成 {idx + 1}/{len(new_sources)}")
                status_ph.empty()
                if all_new_rows:
                    new_df = pd.DataFrame(all_new_rows)
                    st.session_state.final_df = pd.concat([st.session_state.final_df, new_df], ignore_index=True)
                    st.toast(f"✅ 成功提取 {len(all_new_rows)} 条记录！")
                    st.rerun()
    if not st.session_state.final_df.empty:
        st.divider()
        st.markdown('<div class="section-title">📝 数据核对与原件对照</div>', unsafe_allow_html=True)
        show_preview = st.toggle("📖 开启右侧原件分屏预览", value=True)
        if show_preview:
            col_table, col_preview = st.columns([6, 4])
        else:
            col_table, col_preview = st.container(), None
        with col_table:
            dc1, dc2, dc3 = st.columns([3, 2, 5])
            invoice_options = ["请选择…"] + sorted(st.session_state.final_df["发票编号"].unique().tolist()) + ["⚠️ 删除全部"]
            with dc1:
                del_target = st.selectbox("批量操作", invoice_options, label_visibility="collapsed")
            with dc2:
                if st.button("🗑️ 执行删除", type="secondary"):
                    if del_target == "请选择…":
                        st.toast("请先选择要删除的发票")
                    elif del_target == "⚠️ 删除全部":
                        st.session_state.final_df = pd.DataFrame()
                        st.session_state.processed_files = []
                        st.session_state.file_mapping = {}
                        st.session_state.source_previews = {}
                        st.rerun()
                    else:
                        target_key = st.session_state.file_mapping.get(del_target)
                        if target_key and target_key in st.session_state.processed_files:
                            st.session_state.processed_files.remove(target_key)
                        if target_key:
                            st.session_state.source_previews.pop(target_key, None)
                        st.session_state.final_df = st.session_state.final_df[st.session_state.final_df["发票编号"] != del_target].reset_index(drop=True)
                        st.rerun()
            with dc3:
                n = len(st.session_state.final_df)
                nf = len(st.session_state.final_df["发票编号"].unique())
                st.markdown(f"<div style='padding-top:8px;font-size:12.5px;color:#94A3B8'>共 {nf} 张发票 · {n} 条明细</div>", unsafe_allow_html=True)
            edited_df = st.data_editor(
                st.session_state.final_df,
                num_rows="dynamic",
                use_container_width=True,
                height=420,
                column_config={
                    "材料类型": st.column_config.SelectboxColumn("材料类型", options=["易耗品", "低值耐用品", "高额材料物资"], required=True),
                    "单价(元)": st.column_config.NumberColumn("单价(元)", format="¥%.2f"),
                    "总价(元)": st.column_config.NumberColumn("总价(元)", format="¥%.2f"),
                    "单价": st.column_config.NumberColumn("单价", format="¥%.2f"),
                    "总价": st.column_config.NumberColumn("总价", format="¥%.2f"),
                    "数量": st.column_config.NumberColumn("数量", format="%.2f"),
                },
            )
            st.session_state.final_df = edited_df
            total_col = "总价(元)" if "总价(元)" in edited_df.columns else "总价"
            total_amt = edited_df[total_col].sum()
            type_cnt = edited_df["材料类型"].value_counts().to_dict()
            耗材_cnt = type_cnt.get("易耗品", 0)
            低值_cnt = type_cnt.get("低值耐用品", 0)
            高额_cnt = type_cnt.get("高额材料物资", 0)
            st.markdown(f"""
            <div class="summary-bar">
                <div class="summary-card"><div class="val">¥{total_amt:,.0f}</div><div class="lbl">💰 合计金额</div></div>
                <div class="summary-card"><div class="val">{耗材_cnt}</div><div class="lbl">📦 易耗品</div></div>
                <div class="summary-card"><div class="val">{低值_cnt}</div><div class="lbl">🔩 低值耐用品</div></div>
                <div class="summary-card"><div class="val">{高额_cnt}</div><div class="lbl">🔬 高额材料物资</div></div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(label="💾 确认无误，下载 Excel 入库单", data=build_excel(edited_df), file_name=f"422入库单_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", type="primary")
        if show_preview and col_preview is not None:
            with col_preview:
                current_invoice_ids = st.session_state.final_df["发票编号"].unique().tolist()
                if current_invoice_ids:
                    preview_label = st.selectbox("🔍 切换发票原件", current_invoice_ids)
                    preview_key = st.session_state.file_mapping.get(preview_label)
                    preview = st.session_state.source_previews.get(preview_key)
                    if preview:
                        st.markdown(f"<span style='font-size:11.5px;color:#94A3B8'>📄 {preview['name']}</span>", unsafe_allow_html=True)
                        if preview.get("kind") == "local":
                            preview_path = Path(preview["path"])
                            if not preview_path.exists():
                                st.info("⚠️ 原文件已移动或删除，无法预览。")
                                preview_bytes = None
                            else:
                                preview_bytes = preview_path.read_bytes()
                        else:
                            preview_bytes = preview["bytes"]
                        if preview_bytes and preview["suffix"] == ".pdf":
                            b64 = base64.b64encode(preview_bytes).decode()
                            st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="580" style="border:1px solid #E2E8F0;border-radius:10px;"></iframe>', unsafe_allow_html=True)
                        elif preview_bytes:
                            st.image(io.BytesIO(preview_bytes), use_container_width=True)
                    else:
                        st.info("⚠️ 请重新上传对应文件以预览原件。")
                else:
                    st.info("暂无数据可预览。")

with tab_history:
    history = load_json(HISTORY_FILE)
    if not history:
        st.info("暂无历史记录。提取完成后，点击左侧“💾 存入历史”可保存当前会话（最多保留 20 条）。")
    else:
        st.markdown(f"共保存 **{len(history)}** 条历史档案")
        for record in history:
            with st.expander(f"📋 {record['name']}  ·  {record['time']}  ·  {record['count']} 条记录"):
                hist_df = pd.DataFrame(record["data"])
                st.dataframe(hist_df, use_container_width=True, height=260)
                hist_total_col = "总价(元)" if "总价(元)" in hist_df.columns else "总价"
                h_total = hist_df[hist_total_col].sum() if hist_total_col in hist_df.columns else 0
                st.markdown(f"<div class='hist-meta'>发票：{', '.join(record.get('files', [])[:5])} | 合计：¥{h_total:,.2f}</div>", unsafe_allow_html=True)
                hc1, hc2 = st.columns([3, 1])
                with hc1:
                    st.download_button("💾 下载此次 Excel 台账", data=build_excel(hist_df), file_name=f"历史_{record['id']}.xlsx", key=f"dl_{record['id']}")
                with hc2:
                    if st.button("🗑️ 删除记录", key=f"del_{record['id']}"):
                        new_hist = [h for h in history if h["id"] != record["id"]]
                        save_json(HISTORY_FILE, new_hist)
                        st.rerun()

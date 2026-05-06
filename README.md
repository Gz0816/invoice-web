# invoice-web

发票 OCR 识别与入库单导出工具。项目基于 Streamlit 构建，支持批量上传发票图片/PDF，也支持填写多个本地文件夹路径后递归扫描其中的 PDF 文件，自动识别发票明细并导出符合出入库单模板的 Excel。

## 功能

- 批量识别 JPG、PNG、PDF 发票文件
- 支持多个本地文件夹递归扫描 PDF
- 自动提取材料名称、型号规格、计量单位、数量、单价、总价、经销商等字段
- 按出入库单模板导出 Excel
- 支持经费、验收人、存放地点、所属学院、管理员等入库参数预设
- 支持历史记录保存与再次导出
- 后台管理 OCR 账号、经费和公告
- 公告以弹窗显示，关闭后仅本次会话隐藏，刷新页面后会再次弹出

## 目录结构

```text
invoice_web/
├─ app.py                  # 主应用
├─ pages/
│  └─ 后台管理.py          # Streamlit 后台管理页
├─ data/
│  ├─ config_example.json  # OCR 配置示例，会提交到 Git
│  ├─ config.json          # 本地 OCR 配置，不提交到 Git
│  ├─ funds.json           # 经费数据
│  ├─ history.json         # 历史记录
│  ├─ notices.json         # 公告数据
│  └─ usage_stats.json     # OCR 调用统计
├─ requirements.txt
├─ Dockerfile
└─ docker-compose.yml
```

## 本地启动

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 创建本地配置文件：

```bash
copy data\config_example.json data\config.json
```

然后在 `data/config.json` 中填写百度 OCR 的 `api_key` 和 `secret_key`。`data/config.json` 已加入 `.gitignore`，不会提交到 GitHub。

3. 启动应用：

```bash
streamlit run app.py
```

默认访问地址：

```text
http://localhost:8501
```

## Docker 启动

```bash
docker compose up -d --build
```

默认端口是 `8501`。后台管理密码可在 `docker-compose.yml` 的 `ADMIN_PASSWORD` 中修改。

## 使用说明

1. 进入后台管理页，添加百度 OCR 账号、经费和公告。
2. 回到主页面，在左侧选择经费并设置入库参数。
3. 在“发票提取与核对”中上传文件，或在“本地 PDF 文件夹路径”中填写一个或多个文件夹路径。
4. 点击“开始智能提取”。
5. 在表格中核对、修正识别结果。
6. 点击“下载 Excel 入库单”导出。

多个文件夹路径支持一行一个，也可以用英文分号分隔。文件夹扫描只读取运行 Streamlit 的机器上的目录。

## Git 配置说明

会提交：

- `data/config_example.json`
- 代码文件
- Docker 和依赖配置

不会提交：

- `data/config.json`
- Python 缓存
- 编辑器本地配置

如果新增敏感配置，请先加入 `.gitignore` 再提交。

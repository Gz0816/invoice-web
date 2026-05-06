# invoice-web

发票 OCR 识别与入库单导出工具。项目基于 Streamlit 构建，支持批量上传发票图片/PDF，也支持在浏览器中选择或拖入本地 PDF 文件夹，自动识别发票明细并导出符合出入库单模板的 Excel。

## 功能

- 批量识别 JPG、PNG、PDF 发票文件
- 支持浏览器上传本地 PDF 文件夹及子目录文件
- 自动提取材料名称、型号规格、计量单位、数量、单价、总价、经销商等字段
- 按出入库单模板导出 Excel
- 支持经费、验收人、存放地点、所属学院、管理员等入库参数预设
- 支持历史记录保存与再次导出
- 后台管理 OCR 账号、经费和公告
- 公告以弹窗显示，关闭后仅本次会话隐藏，刷新页面后会再次弹出

## 目录结构

```text
invoice_web/
├─ app.py
├─ pages/
│  └─ 后台管理.py
├─ data/
│  ├─ config_example.json
│  ├─ config.json
│  ├─ funds.json
│  ├─ history.json
│  ├─ notices.json
│  └─ usage_stats.json
├─ requirements.txt
├─ Dockerfile
└─ docker-compose.yml
```

## 配置

复制示例配置并填写百度 OCR Key：

```bash
copy data\config_example.json data\config.json
```

`data/config.json` 已加入 `.gitignore`，只保存在本地，不会提交到 GitHub。

后台管理密码通过环境变量 `ADMIN_PASSWORD` 配置；Docker 部署时可在 `docker-compose.yml` 中修改。

## 本地启动

```bash
pip install -r requirements.txt
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

默认访问地址：

```text
http://服务器IP:8501
```

## 使用说明

1. 进入后台管理页，添加百度 OCR 账号、经费和公告。
2. 回到主页面，在左侧选择经费并设置入库参数。
3. 在“发票提取与核对”中选择一种上传方式：
   - 上传发票文件：适合少量 JPG、PNG、PDF 文件。
   - 选择或拖入本地 PDF 文件夹：适合一个文件夹或多层子目录中的 PDF。
4. 点击“开始智能提取”。
5. 在表格中核对、修正识别结果。
6. 点击“下载 Excel 入库单”导出。

## 部署后的文件夹上传说明

网站部署到服务器后，服务器无法直接读取用户电脑上的本地路径。页面里的目录上传是浏览器上传行为：用户在自己的电脑上选择或拖入文件夹，浏览器把文件上传到服务器识别。

因此不要填写 `D:\...`、`C:\...` 这类本地路径让服务器扫描；应使用页面上的文件上传或目录上传控件。

目录上传能力依赖 Streamlit 1.50 或更高版本，项目的 `requirements.txt` 已设置为 `streamlit>=1.50`。

## Git 说明

会提交：

- `data/config_example.json`
- 代码文件
- Docker 和依赖配置
- 公告、经费、历史等项目数据文件

不会提交：

- `data/config.json`
- Python 缓存
- 编辑器本地配置

如果新增敏感配置，请先加入 `.gitignore` 再提交。

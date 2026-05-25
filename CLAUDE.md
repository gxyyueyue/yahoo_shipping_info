# Yahoo 发货信息解析工具

## 环境启动

```bash
# 激活虚拟环境（每次进入项目必须先执行）
source .venv/bin/activate

# 运行程序
python main.py
```

## 项目说明

批量解析 Yahoo!オークション 取引ナビ截图，OCR 识别日文发货地址，导出格式化 Excel。

- OCR 引擎：OpenAI Vision（默认）或 Google Cloud Vision
- GUI 程序，运行后通过界面操作
- 输出文件：`shipping_info.xlsx`

## 配置

- API Key 通过 GUI 右上角 **[⚙ API設定]** 设置，保存到 `config.json`
- `config.json` 不要提交到 git

## 文件结构

- `main.py` — GUI 主程序入口
- `ocr_engine.py` — OCR 引擎
- `parser.py` — 文本解析
- `excel_writer.py` — Excel 导出
- `tic_writer.py` — TIC 格式导出

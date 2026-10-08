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

- OCR 引擎：通义 `qwen3.6-plus`（默认，阿里云百炼）或 豆包 `doubao-seed-2-0-lite-260428`（火山方舟），均走 OpenAI 兼容接口
- 两个模型都是混合推理模型，调用时必须关闭深度思考（通义 `extra_body={"enable_thinking": False}`，豆包 `extra_body={"thinking": {"type": "disabled"}}`），否则单张耗时从 ~20s 涨到 60s+
- 模型会被平台定期下线（2026-09 豆包 `doubao-1-5-vision-pro-32k-250115` 已下线；`qwen-vl-plus` 已被列为旧模型）。模型名在 `main.py` 默认配置 / 下拉框和 `ocr_engine.py` 默认参数中，且 `config.json` 会保存旧值覆盖默认值，换模型时三处都要改
- 豆包新模型需要先在方舟控制台「开通管理」中开通，否则报 `ModelNotOpen`
- 两个引擎都要保留在 GUI 中供选择：豆包快（单张 6–9s）但片假名地址偶有误识别；通义准但慢（单张带图 20–80s，纯文本仅 3s，瓶颈在百炼服务端图片处理，2026-10 实测换 qwen3.7/3.8/3.5/qwen-vl-ocr 等均无改善且多数精度更差；压缩图片能提速但精度下降）
- `Worker` 用线程池并发处理（`_CONCURRENCY = 5`），结果按原文件顺序输出
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

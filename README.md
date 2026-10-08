# Yahoo!オークション 発送情報 一括解析ツール

批量解析 Yahoo!オークション 取引ナビ截图，自动提取发货地址信息并导出 Excel。

---

## 功能说明

- 批量读取文件夹内的 jpg / jpeg / png 截图
- 通过视觉大模型识别日文截图内容（通义 `qwen3.6-plus` 或 豆包 `doubao-seed-2-0-lite-260428`）
- 自动提取：氏名、邮编、都道府县、市区町村、详细地址、配送方法、送料、商品名、落札価格、オークションID、落札者ID
- 无法识别的字段留空，识别状态标记为"需人工确认"（Excel 中以黄色高亮显示）
- 导出为格式化的 `shipping_info.xlsx`

---

## 系统要求

- Python 3.8 或更高版本
- macOS / Windows / Linux

---

## 安装步骤

```bash
# 1. 克隆 / 下载项目到本地
cd yahoo_shipping_info

# 2. （推荐）创建虚拟环境
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

---

## 配置 API Key

### 方式一：通过 GUI 界面设置（推荐）

启动工具后，点击右上角 **[⚙ API設定]** 按钮，填写 API Key 并保存。配置会自动写入同目录的 `config.json`。

### 方式二：环境变量

```bash
# 通义（阿里云百炼 DashScope）
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 豆包（火山方舟 Ark）
export ARK_API_KEY=xxxxxxxxxxxxxxxx
```

### 支持的引擎与模型

| 引擎 | 模型 | API Key 获取 |
|------|------|------|
| `tongyi`（默认） | `qwen3.6-plus` | [阿里云百炼控制台](https://bailian.console.aliyun.com) → API-KEY 管理 |
| `doubao` | `doubao-seed-2-0-lite-260428` | [火山方舟控制台](https://console.volcengine.com/ark) → API Key 管理；**需先在「开通管理」中开通该模型** |

> 两个模型均为混合推理模型，代码中已关闭深度思考（通义 `enable_thinking: False`，豆包 `thinking: disabled`），否则单张识别耗时会大幅增加。
>
> 平台会定期下线旧模型（如原先使用的 `qwen-vl-plus`、`doubao-1-5-vision-pro-32k-250115`）。如调用报错模型不存在，请查看 [百炼模型下线公告](https://help.aliyun.com/zh/model-studio/model-depreciation) / [方舟模型下线公告](https://docs.volcengine.com/docs/ark/model-deprecation-notice?lang=zh)，并在 `main.py` 中更新模型名。

---

## 运行方式

```bash
python main.py
```

### 使用步骤

1. 点击 **[⚙ API設定]** → 选择引擎（tongyi / doubao）→ 输入 API Key → 保存
2. 点击 **画像フォルダ [選択]** → 选择存放截图的文件夹
3. 点击 **出力ファイル [選択]** → 指定 Excel 输出路径（默认为 Downloads/shipping_info.xlsx）
4. 点击 **[▶ 解析開始]** → 等待处理完成
5. 处理完成后弹出提示，Excel 文件已自动保存

---

## 输出 Excel 字段说明

| 列名 | 说明 |
|------|------|
| 原始图片文件名 | 截图文件名 |
| オークションID | 拍卖 ID |
| 落札者ID | 买家 ID |
| 商品名 | 商品名称 |
| 落札価格 | 成交价格 |
| 氏名 | 收件人姓名 |
| 邮编 | 邮政编码 |
| 都道府县 | 都道府县 |
| 市区町村 | 市区町村 |
| 详细地址 | 详细地址 |
| 配送方法 | 配送方式 |
| 送料 | 运费 |
| 识别状态 | `OK` / `需人工确认` / `エラー` |

- **绿色行**：所有关键字段识别成功
- **黄色行**：部分字段识别失败，需人工核对
- **红色行**：OCR 调用出错

---

## 项目结构

```
yahoo_shipping_info/
├── main.py          # GUI 主程序
├── ocr_engine.py    # OCR 引擎（通义 / 豆包，可插拔）
├── parser.py        # 文本解析，提取发货字段
├── excel_writer.py  # Excel 导出
├── tic_writer.py    # TIC 格式导出
├── requirements.txt # 依赖列表
├── config.json      # 本地配置（首次运行后自动生成，勿提交到 git）
└── README.md
```

---

## 打包为独立可执行文件（exe / app）

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 打包命令

**Windows（生成 exe）：**
```bash
pyinstaller --onefile --windowed --name "YahooShippingParser" main.py
# 生成：dist\YahooShippingParser.exe
```

**macOS（生成 .app）：**
```bash
pyinstaller --onefile --windowed --name "YahooShippingParser" main.py
# 生成：dist/YahooShippingParser
```

> **注意：** 打包后的 exe 不包含 `config.json`，首次运行时通过 GUI 设置 API Key，配置文件会自动创建在与 exe 相同的目录下。

### 如果打包后找不到依赖

```bash
pyinstaller --onefile --windowed \
  --hidden-import=openpyxl \
  --hidden-import=openai \
  --name "YahooShippingParser" \
  main.py
```

---

## 常见问题

**Q: 识别率低，很多字段为空**  
A: 建议使用高分辨率（100% 缩放）全屏截图，确保字体清晰。

**Q: 报错 `Incorrect API key` / `InvalidApiKey`**  
A: 确认填写的 Key 与所选引擎对应（通义用百炼的 Key，豆包用方舟的 Key），并确认账户余额充足。

**Q: 豆包报错 `ModelNotOpen`**  
A: 火山方舟账号尚未开通该模型，到方舟控制台「开通管理」中开通 `doubao-seed-2-0-lite-260428` 即可。

**Q: 处理速度慢**  
A: 工具会同时处理 5 张图（`main.py` 中的 `_CONCURRENCY`）。实测 10 张：豆包约 23 秒，通义 `qwen3.6-plus` 约 2 分钟（通义单张带图请求本身需 20–80 秒，慢在阿里云服务端，换其他通义模型也一样）。
- 追求速度：选豆包（片假名地址偶有误识别，建议人工核对）
- 追求准确：选通义

**Q: 在 Windows 上中文/日文显示乱码**  
A: 确保系统已安装日文字体，或将 Excel 文件字体设置为 Meiryo / MS Gothic。

---

## License

MIT

# Yahoo!オークション 発送情報 一括解析ツール

批量解析 Yahoo!オークション 取引ナビ截图，自动提取发货地址信息并导出 Excel。

---

## 功能说明

- 批量读取文件夹内的 jpg / jpeg / png 截图
- 通过 OCR（OpenAI Vision 或 Google Vision）识别日文截图内容
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

> 如果只使用 Google Vision，将 `requirements.txt` 中 `google-cloud-vision` 一行的注释去掉，再重新 `pip install -r requirements.txt`。

---

## 配置 API Key

### 方式一：通过 GUI 界面设置（推荐）

启动工具后，点击右上角 **[⚙ API設定]** 按钮，填写 API Key 并保存。配置会自动写入同目录的 `config.json`。

### 方式二：环境变量

**OpenAI：**
```bash
# macOS / Linux
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# Windows PowerShell
$env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"
```

**Google Cloud Vision：**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### OpenAI API Key 获取方式

1. 访问 [platform.openai.com](https://platform.openai.com)
2. 进入 **API Keys** 页面 → **Create new secret key**
3. 账户需有 GPT-4o 访问权限（需绑定付款方式）

### Google Cloud Vision 认证文件获取方式

1. 在 Google Cloud Console 创建项目
2. 启用 **Cloud Vision API**
3. 创建服务账号，下载 JSON 密钥文件
4. 在 GUI 设置中选择该 JSON 文件路径

---

## 运行方式

```bash
python main.py
```

### 使用步骤

1. 点击 **[⚙ API設定]** → 选择引擎（openai / google）→ 输入 API Key → 保存
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
├── ocr_engine.py    # OCR 引擎（OpenAI / Google / PaddleOCR 可插拔）
├── parser.py        # 文本解析，提取发货字段
├── excel_writer.py  # Excel 导出
├── requirements.txt # 依赖列表
├── config.json      # 本地配置（首次运行后自动生成，勿提交到 git）
└── README.md
```

---

## 添加 PaddleOCR 本地离线模式

如需在无网络环境下使用，可启用 `ocr_engine.py` 中的 `PaddleOCREngine` 存根：

1. 取消 `requirements.txt` 中 `paddlepaddle` / `paddleocr` 的注释
2. `pip install -r requirements.txt`
3. 取消 `ocr_engine.py` 中 `PaddleOCREngine` 类及 `create_engine` 注册的注释
4. 在 GUI 设置中选择引擎 `paddle`

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
A: 建议使用高分辨率（100% 缩放）全屏截图，确保字体清晰。OpenAI gpt-4o 的识别效果优于 gpt-4o-mini。

**Q: OpenAI API 报错 `Incorrect API key`**  
A: 检查 API Key 是否以 `sk-` 开头，确认账户余额充足。

**Q: 处理速度慢**  
A: OpenAI Vision API 每张图约需 3–8 秒，100 张图约 10–15 分钟。如需提速可使用 gpt-4o-mini（精度略低）。

**Q: 在 Windows 上中文/日文显示乱码**  
A: 确保系统已安装日文字体，或将 Excel 文件字体设置为 Meiryo / MS Gothic。

---

## License

MIT

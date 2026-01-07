# Christmas Cat 🐾

一个基于 Streamlit 的「小喵」数字生命应用，集成聊天、联网搜索、图片生成、语音听写与合成、文档解析以及基础代码沙箱等功能，界面做了大量赛博可爱风美化。适合在本地或服务器上快速部署，体验交大模型服务驱动的多模态 AI 助手。

## 功能亮点
- Chat：DeepSeek V3/R1 驱动的可爱猫咪人格聊天，可切换推理模式。
- Scholar Pro：教授-助教多轮研讨链路，先实验再推理论证，适合复杂问题。
- Search：Tavily 实时联网搜索，结果自动注入回答。
- Draw：调用 FLUX.1-schnell 生成插画，自动润色提示词。
- Vision：上传图片后用 qwen3vl 识别内容并加入对话。
- Audio：SenseVoiceSmall 语音识别、CosyVoice2 语音合成；支持英语口语陪练。
- Docs：PDF/Word/TXT/Markdown/Python 文本抽取并注入上下文。
- Code：受限安全沙箱（math/numpy 等）执行模型生成的代码片段。

## 目录结构
- `soul_cat_sjtu.py` 主应用代码（Streamlit）。
- `requirement.txt` 运行所需依赖。
- `双击开启圣诞猫咪.bat` 便捷启动脚本（Windows）。
- `WPy64-310111/` 自带的 WinPython 环境（可选）。

## 环境要求
- Python 3.10+（仓库内附带 WinPython，可直接使用）。
- 系统：Windows / macOS / Linux 均可运行 Streamlit。
- 网络：需要可访问 `https://models.sjtu.edu.cn`、HuggingFace Router、SiliconFlow、Tavily（如有代理，请自行配置）。

## 安装步骤（推荐使用系统已有 Python）
```bash
pip install -r requirement.txt
```

若需使用仓库附带 WinPython（Windows）：  
1) 进入 `WPy64-310111/` 执行 `scripts\env.bat` 或 `WinPython Powershell Prompt.exe`。  
2) 在弹出的终端中安装依赖：`pip install -r ..\requirement.txt`

## 必需的密钥配置
在项目根目录创建 `.streamlit/secrets.toml`，内容示例：
```toml
SJTU_API_KEY = "your-sjtu-key"
HF_API_TOKEN = "your-hf-token"
SILICON_API_KEY = "your-silicon-key"
TAVILY_API_KEY = "your-tavily-key"   # 可选，缺省则禁用联网搜索
ACCESS_PASSWORD = "your-access-password"  # 访问本应用的侧边栏口令
```

> 如果未在 `secrets.toml` 中配置 `ACCESS_PASSWORD`，程序会回退到默认密码 `chuan2410450745`。建议在生产环境中务必设置自己的访问口令。

## 运行
```bash
streamlit run soul_cat_sjtu.py
```
启动后浏览器访问控制台显示的本地地址（如 `http://localhost:8501`），在左侧输入访问密钥后即可使用。

Windows 用户也可双击 `双击开启圣诞猫咪.bat`（如脚本指向的解释器可用）。

## 使用提示
- 侧边栏可切换「学霸 Pro 模式」(R1+V3)、「推理模式」(R1)、「口语模式」等。
- 上传文档后，小喵会将内容作为系统知识库参与回答。
- 生成图片或搜索时会自动将结果注入后续回答。
- 若出现图片/音频处理报错，确认已安装 Pillow 与所需编解码库。

## 依赖列表
见 `requirement.txt`（核心：streamlit、openai、requests、urllib3、Pillow、pdfplumber、python-docx、numpy）。

## 常见问题
- **401/鉴权错误**：检查 `SJTU_API_KEY`、模型名称是否小写 `deepseek-v3`，或密钥配额是否充足。
- **网络超时**：确认代理设置，代码中默认使用 `127.0.0.1:7897` 代理访问 Tavily/HF，可按需修改。
- **图片/音频无法处理**：确保 `Pillow`、`ffmpeg`（播放/转换时）等依赖齐全。
- **启动后停在密码页**：输入正确访问密钥或修改源代码中密码逻辑。

## 许可证
未显式声明许可证，如需开源或分发，请与作者确认。当前内容仅供个人/内部使用。


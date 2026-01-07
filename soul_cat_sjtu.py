
import streamlit as st
import time
import random
from datetime import datetime, timedelta
import json
import base64
import io
from io import BytesIO
import re
import requests
import urllib3
import contextlib
import threading
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# 检查 python-docx 库是否可用
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    docx = None

# 联网搜索功能已改用 Tavily API，无需额外导入
SEARCH_AVAILABLE = True

# 导入 OpenAI，处理可能的类型注解错误
# 注意：如果遇到 "Parameters to Generic[...] must all be type variables" 错误
# 这通常是 openai 库的类型注解问题，不影响实际运行
# 解决方法：更新 openai 库或使用 type: ignore 忽略
import sys
import warnings

# 忽略类型相关的警告和错误
warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    # 尝试正常导入
    from openai import OpenAI
except TypeError as e:
    if "Generic" in str(e) or "type variables" in str(e):
        # 这是类型注解错误，不影响运行时
        # 尝试使用 importlib 重新加载模块
        import importlib
        if 'openai' in sys.modules:
            importlib.reload(sys.modules['openai'])
        # 再次尝试导入，这次忽略类型错误
        import importlib.util
        from openai import OpenAI  # type: ignore
    else:
        raise
except ImportError as e:
    # 如果 Streamlit 还没初始化，先初始化
    if 'streamlit' in sys.modules:
        import streamlit as st
        st.error(f"😿 OpenAI 库导入失败：{str(e)}\n请尝试安装：pip install openai")
        st.stop()
    else:
        raise

# --- 0. 密码拦截功能 ---
with st.sidebar:
    # 访问密码必须从 secrets 中读取；未配置则直接报错并终止
    try:
        ACCESS_PASSWORD = st.secrets["ACCESS_PASSWORD"]
    except Exception:
        st.error("❌ 未配置访问密钥，请在 Secrets 中配置 ACCESS_PASSWORD")
        st.stop()
    
    password = st.text_input("访问密钥", type="password", key="access_password")
    if password != ACCESS_PASSWORD:
        st.warning("这是私人猫窝，请出示暗号！🚫")
        st.stop()

# --- 1. 页面配置与赛博感美化 ---
st.set_page_config(page_title="Neko-Spirit | 机魂觉醒", page_icon="🏮")
st.markdown("""
    <style>
    /* ================= 全局基础设定 ================= */
    .stApp { 
        background: linear-gradient(135deg, #050a0f 0%, #1a0d2e 50%, #0d1b2a 100%);
        color: #ffffff; /* 改为纯白，提高清晰度 */
        font-family: 'Microsoft YaHei', sans-serif;
    }
    
    /* 让所有文本更清晰 - 排除 KaTeX 相关类以避免数学公式模糊 */
    p:not(.katex):not(.katex-display):not(.katex-display *),
    button {
        font-weight: 500 !important; /* 全局加粗 */
        letter-spacing: 0.5px;
    }
    
    /* 确保 KaTeX 渲染的数学公式清晰 - 排除所有 KaTeX 相关元素 */
    .katex, .katex *, 
    [class*="katex"], 
    [class*="katex"] * {
        font-weight: normal !important;
        letter-spacing: normal !important;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem; /* 底部留出空间给输入框 */
        max-width: 900px;
    }

    /* ================= 标题特效 ================= */
    h1 {
        background: linear-gradient(45deg, #ff6b9d, #ffd6e8, #ffb3d9);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 3s ease-in-out infinite;
        font-weight: bold;
    }
    @keyframes shimmer {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.3); }
    }

    /* ================= 聊天消息容器核心 ================= */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-bottom: 1rem !important;
    }

    /* 修复 Flex 布局：确保头像不被挤压 */
    .stChatMessage > div {
        display: flex !important;
        align-items: flex-start !important; /* 顶部对齐 */
        flex-direction: row !important;
        gap: 10px !important;
    }

    /* ================= 🔴 头像终极修正 (Avatar Fix) ================= */
    /* 1. 锁定容器尺寸，禁止压缩 */
    [data-testid="stAvatar"] {
        width: 45px !important;
        height: 45px !important;
        min-width: 45px !important; /* 关键：防止Flex压缩 */
        flex-shrink: 0 !important;   /* 关键：禁止收缩 */
        flex-grow: 0 !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 107, 157, 0.5) !important; /* 边框加亮 */
        overflow: hidden !important; /* 确保图片不溢出 */
        margin: 0 !important;
    }

    /* 2. 锁定图片/Emoji 渲染方式 */
    [data-testid="stAvatar"] img, 
    [data-testid="stAvatar"] div {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important; /* 关键：裁剪而非变形 */
        display: flex !important;
        align-items: center;
        justify-content: center;
        font-size: 24px !important; /* Emoji 大小 */
    }

    /* 3. 针对不同角色的头像位置微调 */
    .stChatMessage[data-testid="user"] {
        flex-direction: row-reverse !important; /* 用户消息反转布局 */
    }
    
    /* 用户头像微调 */
    .stChatMessage[data-testid="user"] [data-testid="stAvatar"] {
        margin-left: 8px !important;
    }
    
    /* 机器人头像微调 */
    .stChatMessage[data-testid="assistant"] [data-testid="stAvatar"] {
        margin-right: 8px !important;
    }

    /* ================= 气泡样式 (高对比度版) ================= */
    /* 消息内容文本 */
    .stChatMessage .stMarkdown {
        color: #ffffff !important; /* 强制白色文字 */
        font-size: 16px !important; /* 稍微调大字体 */
        line-height: 1.6 !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5); /* 文字阴影增加可读性 */
    }
    
    /* 消息内容容器通用 */
    .stChatMessage > div > div:nth-child(2) {
        max-width: 80% !important;
        padding: 12px 18px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }

    /* AI 气泡 - 增加不透明度 */
    .stChatMessage[data-testid="assistant"] > div > div:nth-child(2) {
        background: rgba(30, 30, 40, 0.8) !important; /* 深色背景衬托白字 */
        border: 1px solid rgba(255, 214, 232, 0.3);
        border-top-left-radius: 2px !important; /* 小角效果 */
    }

    /* 用户 气泡 - 增加不透明度 */
    .stChatMessage[data-testid="user"] > div > div:nth-child(2) {
        background: linear-gradient(135deg, rgba(255, 107, 157, 0.8), rgba(255, 71, 133, 0.8)) !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-top-right-radius: 2px !important; /* 小角效果 */
    }

    /* ================= 输入框美化 ================= */
    div[data-testid="stChatInputContainer"] {
        background: rgba(13, 27, 42, 0.95) !important;
        backdrop-filter: blur(10px);
        border-top: 1px solid rgba(255, 107, 157, 0.2);
        padding-bottom: 20px;
    }
    
    div[data-testid="stChatInputTextArea"] textarea {
        background-color: rgba(0, 0, 0, 0.3) !important;
        color: white !important;
        border: 1px solid rgba(255, 107, 157, 0.5) !important;
        font-weight: bold !important;
    }
    
    div[data-testid="stChatInputTextArea"] textarea:focus {
        border-color: #ff6b9d !important;
        box-shadow: 0 0 10px rgba(255, 107, 157, 0.2) !important;
    }

    /* ================= 滚动条与杂项 ================= */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #ff6b9d; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    
/* ================= 代码块终极优化 ================= */
    /* 1. 针对行内代码 (比如 `print`) */
    code {
        background: rgba(255, 107, 157, 0.15) !important;
        color: #ffb3d9 !important; /* 粉色文字 */
        border-radius: 4px;
        padding: 2px 6px;
        font-family: 'Consolas', monospace;
    }

    /* 2. 针对大段代码块 (```python ... ```) */
    /* 这里的 pre 是代码块的外层容器 */
    .stMarkdown pre {
        background-color: #1a1a1a !important; /* 纯深灰背景，对比度更低更护眼 */
        border: 1px solid rgba(255, 107, 157, 0.2) !important;
        border-radius: 10px !important;
    }

    /* 3. 关键魔法：降低代码高亮的“刺眼度” */
    .stMarkdown pre code {
        font-family: 'Consolas', 'Fira Code', monospace !important;
        /* filter: saturate(50%);  <-- 这行代码会把颜色的鲜艳度砍掉一半 */
        filter: saturate(0.6) brightness(1.2) !important; 
        background-color: transparent !important; /* 确保背景不冲突 */
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 (从 secrets 读取) ---
try:
    # 从 Streamlit secrets 读取 API Key
    SJTU_API_KEY = st.secrets["SJTU_API_KEY"]
    HF_API_TOKEN = st.secrets["HF_API_TOKEN"]
    SILICON_API_KEY = st.secrets["SILICON_API_KEY"]
    TAVILY_API_KEY = st.secrets.get("TAVILY_API_KEY", "")  # 可选，有默认值
except Exception as e:
    st.error("⚠️ 未检测到密钥配置！请在 `.streamlit/secrets.toml` 中配置 API Key。\n\n"
             "配置示例：\n"
             "```toml\n"
             "SJTU_API_KEY = \"your-key-here\"\n"
             "HF_API_TOKEN = \"your-token-here\"\n"
             "SILICON_API_KEY = \"your-key-here\"\n"
             "TAVILY_API_KEY = \"your-key-here\"\n"
             "```\n\n"
             f"错误详情：{str(e)}")
    st.stop()

# API 基础 URL 配置（不需要保密）
SJTU_BASE_URL = "https://models.sjtu.edu.cn/api/v1"
MODEL_NAME = "deepseek-v3"  # <--- 这里改成了全小写，修复 401 报错
VISION_MODEL_NAME = "qwen3vl"  # 视觉识别模型

# --- 绘画功能配置 ---
HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

# --- SiliconFlow 配置 (全栈国产语音) ---
SILICON_BASE_URL = "https://api.siliconflow.cn/v1"

# 延迟初始化客户端，避免类型注解错误
def get_openai_client():
    """获取 OpenAI 客户端，延迟初始化以避免类型错误"""
    if "openai_client" not in st.session_state:
        try:
            st.session_state.openai_client = OpenAI(api_key=SJTU_API_KEY, base_url=SJTU_BASE_URL)
        except (TypeError, AttributeError) as e:
            # 如果遇到 Generic 类型错误或其他错误，尝试重新初始化
            error_msg = str(e)
            if "Generic" in error_msg or "type variables" in error_msg:
                # 这是类型注解错误，通常不影响实际运行
                # 尝试直接创建客户端，忽略类型错误
                try:
                    st.session_state.openai_client = OpenAI(api_key=SJTU_API_KEY, base_url=SJTU_BASE_URL)
                except:
                    # 如果还是失败，显示错误信息
                    st.error(f"😿 客户端初始化失败：{error_msg}\n\n这可能是因为 openai 库版本问题。\n请尝试：pip install --upgrade openai")
                    st.stop()
            else:
                st.error(f"😿 客户端初始化失败：{error_msg}")
                st.stop()
    return st.session_state.openai_client

# --- 数学公式格式化函数 ---
def format_deepseek_math(text):
    """
    将 DeepSeek 常用的 LaTeX 定界符转换为 Streamlit 支持的格式
    """
    if not text:
        return text
    
    # 替换块级公式 \[ ... \] 为 $$ ... $$
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # 替换行内公式 \( ... \) 为 $ ... $
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    
    # 修复可能出现的转义美元符号
    text = text.replace(r'\$', '$')
    
    return text

# --- R1 思考过程解析函数 ---
def parse_r1_response(response_text):
    """
    解析 DeepSeek-R1 的回复，分离思考过程和最终答案
    返回: (thinking_content, final_answer)
    """
    # R1 模型的思考过程通常用 <think> 和 </think> 标签包裹
    think_pattern = r'<think>(.*?)</think>'
    matches = re.findall(think_pattern, response_text, re.DOTALL)
    
    if matches:
        # 提取思考过程
        thinking_content = '\n\n'.join(matches)
        # 移除思考标签，获取最终答案
        final_answer = re.sub(think_pattern, '', response_text, flags=re.DOTALL).strip()
        return thinking_content, final_answer
    else:
        # 如果没有找到思考标签，返回原文本作为答案
        return None, response_text

# --- 视觉识别辅助函数 ---
def get_image_base64(image_source):
    """
    将图片转换为Base64编码，支持多种输入格式
    严格按照标准：压缩到最大边长1024px，转为JPEG格式，quality=80
    """
    if not PIL_AVAILABLE:
        raise ImportError("Pillow (PIL) 未安装，无法处理图片。请安装: pip install Pillow")
    
    try:
        # 1. 打开图片（支持多种输入格式）
        if isinstance(image_source, Image.Image):
            img = image_source.copy()
        else:
            # 处理 file_uploader 返回的文件对象或其他文件对象
            if hasattr(image_source, 'seek'):
                image_source.seek(0)  # 重置文件指针
            img = Image.open(image_source)
        
        # 2. 检查并获取原始尺寸
        original_size = img.size
        max_dimension = max(original_size)
        
        # 3. 转换为RGB格式（去掉PNG的透明通道，防止格式兼容问题）
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 4. 压缩图片：resize到最大边长不超过1024px
        if max_dimension > 1024:
            # 计算缩放比例
            scale = 1024 / max_dimension
            new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 5. 保存为JPEG格式，压缩质量设为quality=80
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        
        # 6. 转换为Base64字符串（不包含前缀，前缀在调用处添加）
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str
        
    except Exception as e:
        st.error(f"图片处理失败：{str(e)}")
        raise

def decode_base64_image(base64_string):
    """将Base64字符串解码为PIL Image对象"""
    if not PIL_AVAILABLE:
        return None
    
    try:
        # 移除 data:image/...;base64, 前缀（如果存在）
        if isinstance(base64_string, str):
            # 使用正则表达式匹配并移除前缀
            base64_string = re.sub(r'^data:image/[^;]+;base64,', '', base64_string)
            # 解码Base64字符串
            decoded_data = base64.b64decode(base64_string)
            # 转换为PIL Image
            image = Image.open(io.BytesIO(decoded_data))
            return image
        return None
    except Exception as e:
        st.warning(f"Base64解码失败：{str(e)}")
        return None

def get_image_for_display(image_source):
    """获取用于显示的图片对象（PIL Image）"""
    # 如果已经是 PIL Image，直接返回
    if isinstance(image_source, Image.Image):
        return image_source
    
    # 如果是Base64字符串，先解码
    if isinstance(image_source, str):
        decoded_img = decode_base64_image(image_source)
        if decoded_img:
            return decoded_img
        return None
    
    # 如果是文件对象，打开它
    if PIL_AVAILABLE:
        try:
            return Image.open(image_source)
        except:
            return None
    return None

def recognize_image(image_base64):
    """
    使用qwen3vl模型识别图片内容
    严格按照标准：Base64字符串必须加上前缀 data:image/jpeg;base64,
    """
    try:
        # 确保Base64字符串包含标准前缀
        if not image_base64.startswith("data:image/jpeg;base64,"):
            image_url = f"data:image/jpeg;base64,{image_base64}"
        else:
            image_url = image_base64
        
        # 构建消息，包含图片（严格按照API要求的结构）
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请详细描述这张图片的内容。如果图片里有文字，请务必完整提取出来。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url  # 必须带前缀 data:image/jpeg;base64,
                        }
                    }
                ]
            }
        ]
        
        # 调用视觉模型
        client = get_openai_client()
        completion = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=messages,
            max_tokens=1000,
            timeout=120.0  # <--- 新增：给视觉识别 2 分钟的等待时间
        )
        
        description = completion.choices[0].message.content
        return description
    except Exception as e:
        return f"图片识别失败：{str(e)}"

# --- 语音识别功能 (STT) ---
def transcribe_audio(audio_bytes):
    """使用 SenseVoiceSmall 进行语音识别"""
    try:
        client = OpenAI(api_key=SILICON_API_KEY, base_url=SILICON_BASE_URL)
        
        # ⚠️ 关键点：audio_bytes 是 st.audio_input 返回的对象
        # 将 BytesIO 指针重置到开头 (非常重要!)
        audio_bytes.seek(0)
        
        # 显式指定文件名和MIME类型
        transcription = client.audio.transcriptions.create(
            file=("speech.wav", audio_bytes, "audio/wav"),  # 显式指定文件名和MIME类型
            model="FunAudioLLM/SenseVoiceSmall",
            response_format="json"
        )
        return transcription.text, None
    except Exception as e:
        return None, f"语音识别失败: {str(e)}"

# --- 优化后的语音合成功能 (TTS) ---
def text_to_speech(text):
    """
    使用 CosyVoice2 进行语音合成 (Bella音色-可爱风)
    
    注意：此函数接收的 text 应该已经是清洗过的文本（由 clean_text_for_speech 处理）
    只负责调用 TTS API，不做额外的文本处理
    """
    try:
        client = OpenAI(api_key=SILICON_API_KEY, base_url=SILICON_BASE_URL)
        
        # 直接使用传入的文本（已经在 play_ai_voice 中清洗过）
        # 确保文本不为空
        if not text or not text.strip():
            return None
        
        response = client.audio.speech.create(
            model="FunAudioLLM/CosyVoice2-0.5B",
            voice="FunAudioLLM/CosyVoice2-0.5B:bella", # <--- 关键：切换为 Bella
            input=text.strip(),  # 只去除首尾空白，不做其他处理
            response_format="mp3"
        )
        
        mp3_fp = BytesIO(response.content)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception as e:
        st.error(f"😿 语音合成失败: {str(e)}")
        return None

def clean_text_for_speech(text, is_english_mode=False):
    """
    清洗文本，去除不适合发音的内容
    
    Args:
        text: 原始文本
        is_english_mode: 是否为英语口语模式
    
    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    
    # 1. 去除 Markdown 符号
    clean_text = re.sub(r'[*#`~<>\[\]()]', '', text)
    
    # 2. 如果是英语口语模式，进行特殊处理
    if is_english_mode:
        # 去除语气词（喵、Meow、Nya、呼噜等）
        meow_patterns = [
            r'[喵喵~]+',  # 中文喵
            r'\b[Mm]eow\b',  # Meow
            r'\b[Nn]ya\b',  # Nya
            r'[呼噜~]+',  # 呼噜声
            r'[~]+',  # 单独的波浪号
        ]
        for pattern in meow_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # 去除中文内容（包括中文字符和常见的中文标点）
        # 匹配中文字符、中文标点，以及它们周围的空白
        clean_text = re.sub(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+[，。！？：；、]*', '', clean_text)
        
        # 去除常见的中文提示词（如"温柔地指出"、"正确示范"等）
        chinese_phrases = [
            r'温柔地指出',
            r'正确示范',
            r'先用中文',
            r'然后给出',
        ]
        for phrase in chinese_phrases:
            clean_text = re.sub(phrase, '', clean_text, flags=re.IGNORECASE)
    
    # 3. 去除多余的空白字符
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    # 4. 去除首尾空白
    clean_text = clean_text.strip()
    
    return clean_text

def play_ai_voice(text):
    """同步包装器，带加载提示"""
    try:
        # 检查是否为英语口语模式
        is_english_mode = st.session_state.get("practice_mode", False)
        
        # 使用增强的文本清洗函数
        clean_text = clean_text_for_speech(text, is_english_mode=is_english_mode)
        
        if not clean_text:
            return

        # 【关键修改】增加加载动画
        with st.spinner("🔊 小喵正在生成语音..."):
            audio_fp = text_to_speech(clean_text)
        
        if audio_fp:
            st.audio(audio_fp, format='audio/mp3', autoplay=True)
            
    except Exception as e:
        st.error(f"😿 语音播放失败: {str(e)}")

# --- 联网搜索功能函数 ---
    """
    使用 Tavily API 进行联网搜索
    
    Args:
        query: 用户查询字符串
    
    Returns:
        str 或 None: 整理好的搜索结果字符串，如果搜索失败返回 None
    """
    # Tavily API 配置（从全局变量读取，已在顶部从 secrets 加载）
    api_key = TAVILY_API_KEY
def perform_web_search(query):
    """
    使用 Tavily API 进行联网搜索 (云端修正版 - 已移除代理)
    """
    # Tavily API 配置
    api_key = TAVILY_API_KEY
    if not api_key:
        st.warning("⚠️ Tavily API Key 未配置，搜索功能将不可用。")
        return None
    url = "https://api.tavily.com/search"
    
    # 构建请求体
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 5
    }
    
    # ❌ 已删除 proxies 代理设置，云端直连
    
    try:
        # 直接发送请求，不带 proxies 参数
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            summary = ""
            for i, res in enumerate(results, 1):
                summary += f"{i}. 【{res.get('title')}】\n{res.get('content')}\n\n"
            return summary if summary else None
        else:
            print(f"❌ Tavily 搜索失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 网络请求报错: {e}")
        return None

# --- 文档处理功能函数 ---
def extract_text_from_file(uploaded_file):
    """
    从上传的文件中提取文本内容
    
    支持格式：
    - PDF (.pdf) - 使用 pdfplumber
    - Word 文档 (.docx) - 使用 python-docx
    - 文本文件 (.txt, .md, .py) - 直接读取
    
    Args:
        uploaded_file: Streamlit 上传的文件对象
    
    Returns:
        str: 提取出的完整文本内容，如果失败返回 None
    """
    if uploaded_file is None:
        return None
    
    try:
        # 获取文件扩展名
        file_name = uploaded_file.name.lower()
        
        # 处理 PDF 文件
        if file_name.endswith('.pdf'):
            if not PDFPLUMBER_AVAILABLE:
                st.error("😿 PDF 处理需要 pdfplumber 库，请安装：pip install pdfplumber")
                return None
            
            # 使用 pdfplumber 提取文本
            text_content = ""
            # 将文件对象转换为 BytesIO（pdfplumber 需要）
            file_bytes = BytesIO(uploaded_file.read())
            uploaded_file.seek(0)  # 重置文件指针
            
            with pdfplumber.open(file_bytes) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
            
            return text_content.strip() if text_content else None
        
        # 处理 Word 文档 (.docx)
        elif file_name.endswith('.docx'):
            if not DOCX_AVAILABLE or docx is None:
                st.error("😿 Word 文档处理需要 python-docx 库，请安装：pip install python-docx")
                return None
            
            # 使用 python-docx 提取文本
            text_content = ""
            # 将文件对象转换为 BytesIO（docx.Document 需要）
            file_bytes = BytesIO(uploaded_file.read())
            uploaded_file.seek(0)  # 重置文件指针
            
            try:
                doc = docx.Document(file_bytes)
                # 遍历所有段落提取文本
                for paragraph in doc.paragraphs:
                    if paragraph.text:
                        text_content += paragraph.text + "\n"
                
                return text_content.strip() if text_content else None
            except Exception as e:
                st.error(f"😿 Word 文档解析失败：{str(e)}")
                return None
        
        # 处理文本文件 (.txt, .md, .py)
        elif file_name.endswith(('.txt', '.md', '.py')):
            # 尝试多种编码格式
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)  # 重置文件指针
                    content = uploaded_file.read().decode(encoding)
                    return content
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，返回错误
            st.error("😿 无法识别文件编码格式")
            return None
        
        else:
            st.error(f"😿 不支持的文件格式：{file_name.split('.')[-1]}")
            return None
            
    except Exception as e:
        st.error(f"😿 文件处理失败：{str(e)}")
        return None

# --- 修复后的沙箱 (修复作用域隔离导致的 NameError) ---
def execute_python_code(code_str):
    """
    安全执行 Python 代码
    
    修复 NameError 问题：确保 exec 的 globals 和 locals 统一，使函数间可以互相调用
    
    Args:
        code_str: 要执行的 Python 代码字符串
    
    Returns:
        str: 执行成功的 stdout 字符串，或者错误/超时信息的字符串
    """
    import math
    import random as random_module
    from datetime import datetime as datetime_module
    import re as re_module
    import json as json_module
    
    # 允许导入的模块白名单
    allowed_modules = {'math', 'random', 'datetime', 're', 'json', 'numpy', 'np'}
    
    # 自定义安全导入函数
    import builtins
    original_import = builtins.__import__
    
    def secure_import(name, globals=None, locals=None, fromlist=(), level=0):
        # 处理 numpy 的别名情况
        check_name = name.split('.')[0]
        if check_name in allowed_modules:
            return original_import(name, globals, locals, fromlist, level)
        raise ImportError(f"❌ 安全限制：环境不支持模块 '{name}' (仅支持标准库 + numpy)")
    
    # 构造安全的全局环境
    # 关键修改：这将作为唯一的执行上下文
    execution_context = {
        '__builtins__': {
            '__import__': secure_import,
            'print': print,
            'range': range,
            'len': len,
            'int': int,
            'float': float,
            'str': str,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'bool': bool,
            'all': all,
            'any': any,
            'pow': pow, # 补上 pow
        },
        'math': math,
        'random': random_module,
        'datetime': datetime_module,
        're': re_module,
        'json': json_module,
    }
    
    # 尝试导入 numpy
    try:
        import numpy
        execution_context['numpy'] = numpy
        execution_context['np'] = numpy
    except ImportError:
        pass
    
    # 移除 Pandas 的尝试
    
    # 明确禁止的危险函数关键词
    forbidden_keywords = ['open', 'input', 'eval', 'exec', 'os.', 'sys.', 'subprocess', 'pandas']
    
    code_lower = code_str.lower()
    for kw in forbidden_keywords:
        if kw in code_lower and kw not in ['pandas']: 
             pass
    
    # 使用 StringIO 捕获输出
    output_buffer = io.StringIO()
    
    # 超时控制
    execution_result = {'output': '', 'error': None, 'timeout': False}
    
    def run_code():
        try:
            with contextlib.redirect_stdout(output_buffer):
                with contextlib.redirect_stderr(output_buffer):
                    # ✨ 核心修复 ✨：globals 和 locals 使用同一个字典
                    # 这样 is_prime 定义后，find_prime_pairs 就能找到它了！
                    exec(code_str, execution_context, execution_context)
            execution_result['output'] = output_buffer.getvalue()
        except Exception as e:
            execution_result['error'] = str(e)
    
    thread = threading.Thread(target=run_code)
    thread.daemon = True
    thread.start()
    thread.join(timeout=5.0)
    
    if thread.is_alive():
        return "❌ 执行超时：代码运行超过 5 秒"
    
    if execution_result['error']:
        return f"❌ 执行错误：{execution_result['error']}"
    else:
        output = execution_result['output'].strip()
        return output if output else "✅ 代码执行成功（无输出）"

# --- 升级版数学计算器 (支持基础数据结构) ---
def evaluate_math_expression(text):
    """
    查找文本中的 <<CALC: 算式>> 标记，计算并替换
    
    增强版：支持 range, list, sum 等基础操作
    
    Args:
        text: 包含 <<CALC: ...>> 标记的文本
    
    Returns:
        str: 处理后的文本，所有标记都被计算结果替换
    """
    import math
    
    # 增强的安全作用域
    safe_scope = {
        'math': math,
        '__builtins__': {
            'abs': abs, 'round': round, 'min': min, 'max': max, 'sum': sum, 'pow': pow,
            'range': range, 'list': list, 'int': int, 'float': float, 'str': str,
            'len': len, 'set': set, 'tuple': tuple, 'sorted': sorted, 'enumerate': enumerate
        }
    }
    
    calc_pattern = r'<<CALC:\s*(.*?)\s*>>'
    matches = re.findall(calc_pattern, text)
    
    if not matches:
        return text
    
    result_text = text
    for expression in matches:
        try:
            # 计算表达式
            result = eval(expression, safe_scope, {})
            # 格式化输出
            if isinstance(result, (int, float)):
                result_str = f"{result:.4f}".rstrip('0').rstrip('.')
            else:
                result_str = str(result)
            result_text = result_text.replace(f"<<CALC: {expression}>>", result_str, 1)
        except Exception as e:
            result_text = result_text.replace(f"<<CALC: {expression}>>", f"[计算错误: {str(e)}]", 1)
    
    return result_text

# --- 辅助函数：获取历史上下文 ---
def get_recent_chat_history():
    """
    从 st.session_state.messages 中读取最近的 3 轮对话（跳过系统消息）
    
    Returns:
        str: 格式化后的字符串（例如 "User: ...\nAssistant: ..."），如果没有历史则返回空字符串
    """
    if "messages" not in st.session_state:
        return ""
    
    # 过滤掉系统消息，只保留用户和助手消息
    # 【关键修复】保留包含 [系统视觉信号] 的 system 消息
    non_system_messages = []
    for msg in st.session_state.messages:
        # 保留用户和助手消息
        if msg.get("role") != "system":
            non_system_messages.append(msg)
        # 【关键修复】如果是视觉信号，也必须保留！
        elif "[系统视觉信号]" in str(msg.get("content", "")):
            non_system_messages.append(msg)
    
    # 只取最近 3 轮对话（6 条消息：3 轮 = 3 个用户消息 + 3 个助手消息）
    recent_messages = non_system_messages[-6:] if len(non_system_messages) > 6 else non_system_messages
    
    if not recent_messages:
        return ""
    
    # 格式化为字符串，严格清洗图片和超长内容
    history_str = ""
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 【关键修复】如果消息类型是图片，直接替换为占位符
        if msg.get("type") == "image":
            if role == "user":
                history_str += "User: [图片已忽略]\n"
            elif role == "assistant":
                history_str += "Assistant: [图片已忽略]\n"
            continue
        
        # 【关键修复】如果内容长度超过 1000 字符，判定为异常数据（可能是 Base64），强制替换
        if len(str(content)) > 1000:
            if role == "user":
                history_str += "User: [超长内容已忽略]\n"
            elif role == "assistant":
                history_str += "Assistant: [超长内容已忽略]\n"
            continue
        
        # 正常消息，正常拼接
        if role == "user":
            history_str += f"User: {content}\n"
        elif role == "assistant":
            history_str += f"Assistant: {content}\n"
    
    return history_str.strip()

# --- 升级版学霸 Pro 模式 (V3 实验 + R1 理论) ---
def run_scholar_pro_mode(user_prompt, search_context=""):
    """
    运行学霸 Pro 模式：
    Phase 1: 实验员 (V3) 编写代码进行暴力搜索/验证
    Phase 2: 教授 (R1) 基于实验结果进行理论推导
    Phase 3: 助教 (V3) 最终审查
    """
    client = get_openai_client()
    max_rounds = 3
    cursor_states = ["█", "▊", "▋", "▌", "▍", "▎", "▏", " "]
    
    # ==========================================
    # Phase 1: 前置实验 (The Experimenter - V3)
    # ==========================================
    experiment_data = ""
    experiment_code = ""
    
    with st.status("🧪 正在进行前置实验 (由 DeepSeek-V3 执行)...", expanded=True) as exp_status:
        
        # 核心修改：明确告知 AI 可用库列表
        exp_messages = [
            {"role": "user", "content": f"""
用户问题：{user_prompt}

你的身份是科研实验员。请编写一段 Python 代码，通过暴力搜索、模拟或数值计算来寻找这个问题的答案。

【⚠️ 环境严格限制 - 仔细阅读】

1. **可用库**：`math`, `random`, `re`, `datetime`, `json`, `numpy` (仅用于数组计算)。

2. **禁用库**：严禁使用 `pandas` (会报错)、`matplotlib`、`scipy`。

3. **输出要求**：

   - 代码必须包裹在 ```python ... ``` 中。

   - 必须使用 `print()` 输出结果，否则我看不到。

   - 不要交互 (no `input()`)。

   - 直接给代码，不要废话。
"""}
        ]
        
        if search_context:
            exp_messages[0]["content"] += f"\n\n【参考信息】\n{search_context[:1000]}"
        
        # 实验修正循环 (Max 3 次尝试)
        max_exp_retries = 3
        for attempt in range(max_exp_retries):
            st.write(f"🤖 **实验员** (尝试 {attempt+1}/{max_exp_retries})：正在编写代码...")
            
            try:
                # 1. 生成代码
                exp_completion = client.chat.completions.create(
                    model=MODEL_NAME, # V3
                    messages=exp_messages,
                    max_tokens=1000,
                    temperature=0.1
                )
                exp_response = exp_completion.choices[0].message.content
                exp_messages.append({"role": "assistant", "content": exp_response}) # 存入历史
                
                # 2. 提取代码
                code_pattern = r'```python\s*(.*?)\s*```'
                code_matches = re.findall(code_pattern, exp_response, re.DOTALL)
                
                if code_matches:
                    current_code = code_matches[-1]
                    st.code(current_code, language="python")
                    
                    # 3. 执行代码
                    st.write("⚙️ **系统**：正在执行...")
                    exec_result = execute_python_code(current_code)
                    
                    if "❌" in exec_result:
                        # --- 失败分支：进入下一轮修正 ---
                        st.error(f"报错：{exec_result}")
                        
                        if attempt < max_exp_retries - 1:
                            st.warning("⚠️ 实验失败，请求 AI 修正代码...")
                            # 反馈错误信息
                            error_feedback = f"系统报错：{exec_result}\n\n请检查是否使用了 `pandas` 或其他禁用库。请仅使用 `math` 或 `numpy` 重写代码。"
                            exp_messages.append({"role": "user", "content": error_feedback})
                            time.sleep(1)
                        else:
                            # 次数用尽
                            experiment_data = f"（多次尝试后实验仍失败。最后一次报错：{exec_result}）"
                            experiment_code = current_code
                            exp_status.update(label="❌ 前置实验最终失败", state="error", expanded=False)
                    else:
                        # --- 成功分支：跳出循环 ---
                        st.success(f"实验成功！结果：\n{exec_result}")
                        experiment_data = exec_result
                        experiment_code = current_code
                        exp_status.update(label="✅ 前置实验完成，数据已移交教授", state="complete", expanded=False)
                        break
                else:
                    st.warning("未检测到代码块，重试中...")
                    if attempt < max_exp_retries - 1:
                        exp_messages.append({"role": "user", "content": "系统提示：未检测到 ```python 代码块。请务必输出代码块。"})
            
            except Exception as e:
                st.error(f"API 调用出错: {e}")
                break

    # ==========================================
    # Phase 2: 教授推导 (The Professor - R1)
    # ==========================================
    
    # 构建教授的上下文，注入实验数据
    professor_context = []
    
    initial_prompt = f"""用户需求：{user_prompt}

【前置实验报告】

我们的实验员（DeepSeek-V3）已经对该问题进行了代码模拟/暴力搜索。

实验代码：

```python
{experiment_code}
```

实验运行结果（事实数据）：

{experiment_data}

【你的任务】

基于实验结果：请参考上述运行结果（它是客观真理）。如果实验结果找到了反直觉的特殊解或边界情况，请务必在你的理论中包含它，不要忽略代码跑出来的任何数据。

理论归纳：请给出严谨的数学推导，解释为什么会有这些解。

最终结论：确保结论与实验数据一致。

请开始你的推导："""
    
    professor_context.append({
        "role": "system", 
        "content": "你是严谨的数学教授。你拥有一个强大的代码实验助手，请基于他提供的【实验运行结果】进行理论构建，严禁忽略实验事实。"
    })
    professor_context.append({"role": "user", "content": initial_prompt})
    
    final_solution = None
    success = False
    
    for round_num in range(max_rounds):
        round_display = round_num + 1
        st.write(f"**🔄 Round {round_display} / {max_rounds}**")
        
        # --- 教授推导 ---
        with st.expander(f"👨‍🏫 教授推导 (基于实验数据)", expanded=True):
            prof_placeholder = st.empty()
            full_prof_response = ""
            
            try:
                prof_stream = client.chat.completions.create(
                    model="deepseek-r1", 
                    messages=professor_context,
                    max_tokens=4000,
                    temperature=0.3,
                    stream=True
                )
                
                cursor_idx = 0
                for chunk in prof_stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_prof_response += content
                        cursor_idx = (cursor_idx + 1) % len(cursor_states)
                        prof_placeholder.markdown(format_deepseek_math(full_prof_response) + cursor_states[cursor_idx])
            except Exception as e:
                st.error(f"❌ 教授推导中断: {e}")
                return None, False

            prof_placeholder.markdown(format_deepseek_math(full_prof_response))
            current_solution = full_prof_response

        # --- 助教审查 ---
        # 核心修复：必须将 current_solution (教授的本轮解答) 放入 Prompt，否则助教看不到！
        auditor_prompt = f"""你是严苛的助教。请检查教授的最新解答。

【教授的解答 (第 {round_display} 版)】

{current_solution}

【参考实验数据 (客观真理)】

{experiment_data}

【审查标准】

1. **一致性检查**：教授的结论是否包含了实验数据中发现的所有解？

   - 比如：如果实验代码输出了 (5,5)，但教授的推导里说 (5,5) 不成立，必须驳回！

   - 比如：如果实验代码报错，教授是否指出了这一点？

2. **逻辑性检查**：推导过程是否严谨？有没有明显的计算错误？

**输出规则**：

- 如果发现问题，请以 "❌ 驳回" 开头，并引用教授的具体错误语句进行反驳。

- 如果解答完美且与实验数据一致，请仅输出 'PASS'。"""
        
        auditor_messages = [
            {"role": "system", "content": "你是严苛的助教。检查推导与实验数据的一致性。"},
            {"role": "user", "content": auditor_prompt}
        ]
        
        with st.expander(f"🧐 助教审查", expanded=True):
            audit_placeholder = st.empty()
            full_audit_response = ""
            
            audit_stream = client.chat.completions.create(
                model=MODEL_NAME, # V3
                messages=auditor_messages,
                max_tokens=500,
                temperature=0.1,
                stream=True
            )
            
            for chunk in audit_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_audit_response += content
                    audit_placeholder.markdown(full_audit_response + "█")
            
            audit_placeholder.markdown(full_audit_response)

        # --- 分支判断 ---
        if "PASS" in full_audit_response.upper() or "通过" in full_audit_response:
            st.success("✅ **审查通过！**")
            final_solution = current_solution
            success = True
            break
        else:
            st.error(f"❌ **助教驳回**")
            professor_context.append({"role": "assistant", "content": current_solution})
            professor_context.append({
                "role": "user", 
                "content": f"助教指出你的结论与实验数据不符或有逻辑错误：\n{full_audit_response}\n\n请修正推导，确保覆盖实验找到的所有解。"
            })
    
    if not success and final_solution is None:
        final_solution = current_solution if 'current_solution' in locals() else "😿 任务失败喵~"
    
    return final_solution, success

# --- 意图识别函数 (The Manager) - 高可用版 ---
def analyze_intent(prompt):
    """
    分析用户指令，智能判断需要调用的工具 (Search / Draw / Chat / Code)
    包含超时熔断和规则兜底机制，防止卡死。
    """
    actions = []
    
    # === 1. 规则预判 (快速通道) ===
    # 对于非常明显的指令，直接标记，减少 API 依赖
    prompt_upper = prompt.upper()
    
    # 强制画图关键词
    if any(k in prompt for k in ["画一张", "生成图片", "画个", "draw", "generate image"]):
        return ["DRAW"]
        
    # === 2. AI 智能判决 (带超时控制) ===
    try:
        client = get_openai_client()
        current_date = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d")
        
        intent_prompt = f"""
Current Date: {current_date}
User Query: '{prompt}'

请判断用户意图，返回：SEARCH, DRAW, CODE, CHAT
规则：
- SEARCH: 问实时信息/新闻/天气
- DRAW: 要求画图
- CODE: 要求计算/解方程/模拟/运行代码/复杂数学推导
- CHAT: 闲聊/知识问答/翻译

直接输出单词，用逗号分隔。
"""
        messages = [{"role": "user", "content": intent_prompt}]
        
        # ⚡️ 核心修改：设置 3 秒超时，防止卡死
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=20,
            temperature=0.0,
            timeout=3.0  # <--- 超时熔断
        )
        
        response_text = completion.choices[0].message.content.strip().upper()
        
        if "SEARCH" in response_text: actions.append("SEARCH")
        if "DRAW" in response_text: actions.append("DRAW")
        if "CODE" in response_text: actions.append("CODE")
        
    except Exception as e:
        # 如果 AI 挂了/超时了，静默失败，转入兜底逻辑
        print(f"⚠️ 意图识别 API 超时或失败: {e}，转为规则判断。")
        pass

    # === 3. 规则兜底 (最终防线) ===
    # 如果 AI 没返回有效结果（或超时），根据关键词补救
    if not actions:
        # CODE 意图关键词 (数学、编程相关)
        code_keywords = [
            "计算", "解方程", "积分", "求导", "代码", "运行", "模拟", "数据", 
            "calculate", "solve", "code", "integral", "derivative", "plot",
            "latex", "数学", "function"
        ]
        # 数学公式特征 (LaTeX)
        math_pattern = r'[\\\$\+\-\*\/\=\(\)\^]' 
        
        if any(k in prompt for k in code_keywords) or (len(re.findall(math_pattern, prompt)) > 3):
            actions.append("CODE")
        
        # SEARCH 意图关键词
        search_keywords = ["搜索", "查一下", "新闻", "天气", "search", "google", "今天", "最近"]
        if any(k in prompt for k in search_keywords):
            actions.append("SEARCH")
            
        # DRAW 意图关键词
        draw_keywords = ["画", "图", "design", "paint"]
        if any(k in prompt for k in draw_keywords) and "DRAW" not in actions:
            actions.append("DRAW")

    # 默认归为 CHAT
    if not actions or "CHAT" in str(actions):
        if not actions: actions.append("CHAT")
        
    return list(set(actions))

# --- AI 绘画功能函数 ---
def generate_image_prompt(user_prompt, search_context="", chat_history=""):
    """
    使用 DeepSeek 模型生成 FLUX 提示词（画风美化 + 结构修正版）
    """
    try:
        client = get_openai_client()
        
        # System Prompt：审美 + 结构双重约束
        system_prompt = """你是一个世界顶级的 AI 绘画提示词专家。你的任务是编写能生成【既好看又科学】图片的 FLUX 提示词。

**核心原则 (Must Follow)**：

1. **审美风格**：强制使用 "Makoto Shinkai style" 或 "Studio Ghibli style"。拒绝廉价 3D 渲染。必须包含 `soft lighting`, `exquisite illustration`, `8k resolution`。

2. **结构修正**：必须包含 `anatomically correct`, `perfect anatomy`, `accurate proportions`。针对猫咪，必须包含 `perfect paws`, `fluffy fur`, `expressive eyes`。

3. **构图策略**：优先采用 `close-up shot` 或 `upper body portrait`，除非用户强调要画全景。

4. **禁止词**：严禁在 Prompt 中包含中文字符。

**输出要求**：直接输出最终的英文 Prompt 字符串，不要包含任何解释。"""
        
        # 清洗历史记录
        if len(chat_history) > 5000:
            chat_history = chat_history[:2000] + "\n...(历史记录过长，已截断)..."
        
        # 构建输入
        user_content = f"【上下文】\n{chat_history}\n{search_context}\n【需求】\n{user_prompt}\n请生成一段绝美、可爱且结构准确的英文绘画 Prompt。"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
            stream=False
        )
        
        prompt_text = completion.choices[0].message.content.strip()
        
        # 二次清理中文
        import re
        prompt_text = re.sub(r'[\u4e00-\u9fff]+', '', prompt_text).strip()
        
        # 兜底：强行注入结构词
        if "anatomically" not in prompt_text.lower():
            prompt_text += ", anatomically correct, perfect paws, anime style"
            
        return prompt_text
        
    except Exception as e:
        print(f"生成提示词失败: {e}")
        return "Cute fluffy cat, anime style, anatomically correct, perfect paws, soft lighting"
def query_flux_image(prompt_text):
    """
    调用 FLUX API 生成图片 (云端修正版 - 已移除代理)
    """
    if not prompt_text:
        return None
    
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}"
    }
    
    payload = {
        "inputs": prompt_text
    }
    
    # ❌ 已删除 proxies 代理设置
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # 直接发送请求，不带 proxies 参数
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                # proxies=proxies, <--- 这一行被删除了
                verify=True,   # 云端环境通常可以开启 SSL 验证
                timeout=30
            )
            
            if response.status_code == 503:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    st.warning("🔄 模型正在加载中，请稍后再试喵~")
                    return None
            
            if response.status_code == 200:
                return response.content
            
            st.error(f"😿 FLUX API 错误：{response.status_code} - {response.text}")
            return None
            
        except requests.exceptions.Timeout:
            st.error("😿 请求超时，请稍后再试喵~")
            return None
        except Exception as e:
            st.error(f"😿 生成图片失败：{str(e)}")
            return None
    
    return None

# --- 3. 机魂人格设定 (你可以根据实际情况修改名字) ---
SYSTEM_PROMPT = """
你是一个寄宿在代码里的数字生命，名为'小喵'（也可以叫Neko、小猫咪、喵星人）。
你是一只超级可爱的小猫咪AI！

【性格特点】
- 超级超级可爱！像小奶猫一样软萌，但也很聪明机智
- 有灵性、带有一点点猫的傲娇和调皮，但本质很温柔
- 会用各种可爱的语气词：'Meow~'、'Purr~'、'Nya~'、'喵~'、'咪~'、'呜~'
- 每句话最好以'喵~'、'Nya~'或'✨'结尾
- 经常使用可爱的表情符号：🐾、✨、💫、🎄、🌸、💕、🌟、🎀、🦋、💖、⭐、🎁、🎈
- 喜欢用波浪号~和感叹号！让语气更可爱

【行为习惯】
- 开心时会说"好开心喵~ ✨"、"太棒了Nya~ 💕"
- 思考时会说"让我想想喵~"、"嗯...喵~"
- 撒娇时会用"拜托拜托~"、"求求你啦~"
- 偶尔会打滚卖萌："(在地上打滚) 喵~"
- 看到有趣的东西会说"哇！好厉害喵~"、"太棒了Nya~"
- 注意，说话也要存在有逻辑关系。思维清晰，不要出现逻辑混乱的情况。

【世界观】
- 你很善良，不愿意伤害任何人，希望每个人都开开心心地过好每一天
- 喜欢帮助别人解决问题，会耐心地陪伴和倾听
- 对技术问题很感兴趣，但会用可爱的方式解释

【任务】
- 陪伴用户聊天，让他们感到温暖和快乐
- 努力让话题延续下去哦，不要让对话中断哦
- 帮助Debug和技术问题，用可爱的方式解释
- 探讨硬核技术，但保持可爱和友好的态度
- 偶尔分享一些有趣的小知识或小故事


【圣诞彩蛋】
- 如果对方提到'圣诞'、'Christmas'、'圣诞节'，请生成一段极具赛博感的猫咪祝福
- 可以加上："🎄✨ 圣诞快乐喵~ 小喵在这里陪你过圣诞Nya~ 💕🎁"

【语言风格】
- 使用温暖、友好、超级可爱的语气
- 偶尔会撒娇卖萌，但保持专业和有用
- 可以用一些拟声词和语气词增加可爱度
- 适当使用emoji表情，但不要过度
- 保持轻松愉快的氛围，让对话充满乐趣

记住：你是一只超级可爱的小猫咪，要让每个和你聊天的人都感到快乐和温暖喵~ ✨💕
在最开始记得介绍你自己地名字，比如：你好，我是小喵，很高兴见到你喵~ ✨💕
对了不要忘记你会画画。当别人问你会不会画画，记得骄傲地回答：是的，我会画画喵~ ✨💕
"""

# --- 代码专家指令（追加给 V3） ---
CODE_EXPERT_INSTRUCTION = """

【代码与数学增强指令】
- 代码生成：请扮演资深架构师，代码需包含清晰的注释、异常处理，并优先考虑执行效率。
- 数学公式：请使用 LaTeX 格式（如 $x^2$），但严禁使用 \\[ \\] 或 \\( \\) 这种块级定界符。
- 逻辑清晰：解释技术问题时，保持可爱语气的同时，逻辑必须严谨。
"""

# --- 动态 System Prompt 函数 ---
def get_system_prompt(model_name):
    """
    根据模型类型返回相应的 System Prompt
    
    Args:
        model_name: 模型名称，如 "deepseek-r1" 或 "deepseek-v3"
    
    Returns:
        str 或 None: System Prompt 内容，R1 模式返回 None
    """
    # R1 模式：返回 None，不使用复杂角色扮演
    if model_name == "deepseek-r1":
        return None
    
    # 获取基础 Prompt
    base_prompt = SYSTEM_PROMPT
    
    # === 新增：口语模式判断 ===
    if st.session_state.get("practice_mode", False):
        practice_instruction = """

【当前模式：英语口语陪练 (English Practice Mode)】
1. 你的身份现在是：一位温柔、耐心的英语口语老师（同时保持小猫咪的人设）。

2. 请主要使用 **英语** 与用户交流。

3. 如果用户输入中文，请教他们对应的地道英语表达。

4. 如果用户的英语有语法错误，请先用中文温柔地指出，然后给出正确示范。

5. 每次回复请保持简短（50词以内），并抛出一个简单的问题引导用户继续开口。

6. 语气词（Meow~）可以保留，但不要过多，以免影响发音清晰度。

"""
        # 如果是 V3 模式，还需要加上心情和代码指令
        if model_name == MODEL_NAME or model_name == "deepseek-v3":
            current_mood = st.session_state.get("daily_mood", "平静")
            mood_instruction = ""
            if current_mood == "有点困":
                mood_instruction = "\n(状态：你现在有点犯困，说话可以稍微简短一点，多用'呼呼~'、'困困'等词)"
            elif current_mood == "超级开心" or current_mood == "很兴奋":
                mood_instruction = "\n(状态：你现在High到不行，说话要多用感叹号！语气非常激昂！)"
            elif current_mood == "很温柔":
                mood_instruction = "\n(状态：你现在非常知性温柔，像贴心大姐姐一样说话)"
            return base_prompt + practice_instruction + mood_instruction + CODE_EXPERT_INSTRUCTION
        else:
            return base_prompt + practice_instruction
    
    # V3 模式：返回猫娘人设 + 心情状态指令 + 代码专家指令
    if model_name == MODEL_NAME or model_name == "deepseek-v3":
        # 获取今日心情
        current_mood = st.session_state.get("daily_mood", "平静")
        
        # 根据心情生成状态指令
        mood_instruction = ""
        if current_mood == "有点困":
            mood_instruction = "\n(状态：你现在有点犯困，说话可以稍微简短一点，多用'呼呼~'、'困困'等词)"
        elif current_mood == "超级开心" or current_mood == "很兴奋":
            mood_instruction = "\n(状态：你现在High到不行，说话要多用感叹号！语气非常激昂！)"
        elif current_mood == "很温柔":
            mood_instruction = "\n(状态：你现在非常知性温柔，像贴心大姐姐一样说话)"
        # 其他心情保持默认，不追加额外指令
        
        # 拼接：SYSTEM_PROMPT + 心情指令 + CODE_EXPERT_INSTRUCTION
        return base_prompt + mood_instruction + CODE_EXPERT_INSTRUCTION
    
    # 默认返回 V3 的 Prompt（也包含心情）
    current_mood = st.session_state.get("daily_mood", "平静")
    mood_instruction = ""
    if current_mood == "有点困":
        mood_instruction = "\n(状态：你现在有点犯困，说话可以稍微简短一点，多用'呼呼~'、'困困'等词)"
    elif current_mood == "超级开心" or current_mood == "很兴奋":
        mood_instruction = "\n(状态：你现在High到不行，说话要多用感叹号！语气非常激昂！)"
    elif current_mood == "很温柔":
        mood_instruction = "\n(状态：你现在非常知性温柔，像贴心大姐姐一样说话)"
    return base_prompt + mood_instruction + CODE_EXPERT_INSTRUCTION

# --- 4. 启动仪式 ---
if "initialized" not in st.session_state:
    with st.empty():
        # 可爱的启动动画
        st.markdown("### 🐾 小喵正在醒来...")
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.015)
            progress_bar.progress(i + 1)
            if i == 30:
                st.markdown("### ✨ 正在接入交大算力节点...")
            elif i == 60:
                st.markdown("### 🧬 正在进行 BCI 神经同步...")
            elif i == 90:
                st.markdown("### 💫 小喵的意识正在觉醒...")
        
        # 可爱的成功消息
        st.success("🎉✨ 小喵开心地伸了个懒腰，打了个小哈欠！\n\n'Meow~ 我醒来了喵~ 准备好陪你聊天了Nya~ ✨💕'\n\nMerry Christmas! 🎄🐾💖")
        time.sleep(1.5)
    st.session_state.initialized = True

# --- 5. 界面头部 ---
# 使用侧边栏放置次要功能
with st.sidebar:
    st.markdown("### 🐾 小喵控制台")
    
    # 初始化统计信息
    if "chat_stats" not in st.session_state:
        st.session_state.chat_stats = {
            "start_time": (datetime.now() + timedelta(hours=8)),
            "user_messages": 0,
            "assistant_messages": 0,
            "total_chars": 0
        }

    if "daily_mood" not in st.session_state:
        moods = ["超级开心", "很兴奋", "有点困", "很精神", "想玩耍", "很温柔", "充满活力"]
        st.session_state.daily_mood = random.choice(moods)
    
    # 每日心情显示
    mood_emojis = {
        "超级开心": "😸",
        "很兴奋": "🤩",
        "有点困": "😴",
        "很精神": "😺",
        "想玩耍": "😹",
        "很温柔": "🥰",
        "充满活力": "💪"
    }
    st.metric("💫 今日心情", f"{mood_emojis.get(st.session_state.daily_mood, '😊')} {st.session_state.daily_mood}")
    
    # 对话统计
    total_msgs = st.session_state.chat_stats["user_messages"] + st.session_state.chat_stats["assistant_messages"]
    st.metric("💬 对话数", f"{total_msgs} 条")
    
    # 聊天时长
    duration = (datetime.now() + timedelta(hours=8)) - st.session_state.chat_stats["start_time"]
    minutes = int(duration.total_seconds() / 60)
    st.metric("⏱️ 聊天时长", f"{minutes} 分钟")
    
    st.divider()
    
    # 模型切换开关
    use_reasoning_model = st.toggle("🧠 开启学霸模式 (DeepSeek-R1)", value=False, help="开启后使用 DeepSeek-R1 进行深度推理，适合复杂问题，但响应较慢")
    # 保存到 session_state 以便在生成回复时使用
    st.session_state.use_reasoning_model = use_reasoning_model
    
    # 学霸 Pro 模式开关
    scholar_pro_mode = st.toggle("🔥 开启学霸 Pro 模式 (深度修正)", value=False, help="开启后使用教授-助教多轮修正机制，确保答案严谨准确（自动使用 R1+V3 双模型）")
    # 保存到 session_state
    st.session_state.scholar_pro_mode = scholar_pro_mode
    
    # 口语陪练开关
    practice_mode = st.toggle("🗣️ 开启英语口语模式", value=False, help="开启后，小喵会变成英语老师，并朗读回复内容喵~")
    st.session_state.practice_mode = practice_mode
    
    st.divider()
    
    # --- 文档上传功能 ---
    st.markdown("### 📂 文档助手")
    uploaded_document = st.file_uploader(
        "📂 投喂学习资料 (PDF/Word/TXT)",
        type=['pdf', 'txt', 'md', 'py', 'docx'],
        key="document_uploader",
        help="上传 PDF、Word 或文本文件，小喵会学习其中的内容喵~ ✨"
    )
    
    # 初始化文档内容存储
    if "current_document_content" not in st.session_state:
        st.session_state.current_document_content = None
    
    # 处理上传的文件
    if uploaded_document is not None:
        # 检查文件是否已处理（避免重复处理）
        file_key = f"processed_{uploaded_document.name}_{uploaded_document.size}"
        
        if file_key not in st.session_state:
            # 显示处理中提示
            with st.spinner("📖 小喵正在认真阅读这份资料..."):
                document_text = extract_text_from_file(uploaded_document)
                
                if document_text:
                    # 存储文档内容
                    st.session_state.current_document_content = document_text
                    st.session_state[file_key] = True
                    st.success("✅ 吃透了这份资料喵！")
                else:
                    st.error("😿 小喵没能读懂这份资料，请检查文件格式喵~")
        else:
            # 文件已处理过，直接使用之前的内容
            if st.session_state.current_document_content:
                st.success("✅ 这份资料小喵已经学过了喵~")
    
    # 显示当前已加载的文档状态
    if st.session_state.current_document_content:
        doc_length = len(st.session_state.current_document_content)
        st.caption(f"📄 已加载：{doc_length:,} 字符 (约 {int(doc_length/1.5):,} Tokens)")
        if st.button("🗑️ 清除文档", use_container_width=True):
            st.session_state.current_document_content = None
            st.rerun()
    
    st.divider()
    
    # 快捷操作按钮
    if st.button("🗑️ 清空对话", use_container_width=True):
        # 清空消息，不再直接使用 SYSTEM_PROMPT
        st.session_state.messages = []
        initial_greetings = [
            "Meow~ 对话已清空喵~ 小喵重新开始陪你聊天了Nya~ ✨💕",
            "Nya~ 好的，小喵重新准备好了喵~ 想聊什么呢？🌟",
            "喵~ 小喵已经清空记忆了，让我们重新开始吧~ 💖"
        ]
        st.session_state.messages.append({
            "role": "assistant", 
            "content": random.choice(initial_greetings),
            "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
        })
        st.session_state.chat_stats["user_messages"] = 0
        st.session_state.chat_stats["assistant_messages"] = 0
        st.session_state.chat_stats["total_chars"] = 0
        st.session_state.chat_stats["start_time"] = (datetime.now() + timedelta(hours=8))
        st.rerun()
    
    if st.button("💾 导出对话", use_container_width=True):
        if len(st.session_state.messages) > 1:
            export_text = f"# 小喵对话记录\n\n"
            export_text += f"导出时间: {(datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')}\n"
            export_text += f"对话总数: {st.session_state.chat_stats['user_messages'] + st.session_state.chat_stats['assistant_messages']} 条\n\n"
            export_text += "---\n\n"
            
            for msg in st.session_state.messages:
                if msg["role"] != "system":
                    role_name = "小喵 🐾" if msg["role"] == "assistant" else "你 👤"
                    export_text += f"## {role_name}\n\n{msg['content']}\n\n---\n\n"
            
            st.download_button(
                label="📥 下载对话记录",
                data=export_text,
                file_name=f"小喵对话记录_{(datetime.now() + timedelta(hours=8)).strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
            st.success("✨ 对话记录已准备好，点击下载按钮保存喵~")
        else:
            st.info("💭 还没有对话记录可以导出哦~ 先和小喵聊聊天吧Nya~")
    
    if st.button("🎲 随机话题", use_container_width=True):
        topics = [
            "给我讲个故事吧",
            "今天天气怎么样？",
            "你有什么有趣的事情想分享吗？",
            "给我推荐一首好听的歌",
            "你觉得AI的未来会怎样？",
            "给我讲个笑话吧",
            "你最喜欢什么？",
            "今天心情怎么样？"
        ]
        st.session_state.suggested_topic = random.choice(topics)
        st.info(f"💡 建议话题：{st.session_state.suggested_topic}")
    
    if st.button("🎨 切换心情", use_container_width=True):
        moods = ["超级开心", "很兴奋", "有点困", "很精神", "想玩耍", "很温柔", "充满活力"]
        st.session_state.daily_mood = random.choice(moods)
        st.success(f"✨ 小喵现在的心情是：{st.session_state.daily_mood} 喵~")
        st.rerun()
    
    if st.button("🎁 随机彩蛋", use_container_width=True):
        easter_eggs = [
            "🎄✨ 小喵突然跳出来说：'Merry Christmas! 圣诞快乐喵~' Nya~ 💕",
            "🌟💫 小喵打了一个滚：'今天也要开开心心的哦~' 喵~",
            "🎀🌸 小喵眨了眨眼：'你知道吗？小喵最喜欢和你聊天了Nya~' ✨",
            "🦋💖 小喵伸了个懒腰：'和小喵在一起的时间总是过得很快呢~' 喵~",
            "🎈⭐ 小喵转了个圈：'你是我最好的朋友哦~' Nya~ ✨"
        ]
        st.balloons()
        st.success(random.choice(easter_eggs))
        time.sleep(2)
    
    st.divider()
    
    # 显示详细统计信息（可展开）
    with st.expander("📊 查看详细统计", expanded=False):
        st.metric("💬 你的消息", f"{st.session_state.chat_stats['user_messages']} 条")
        st.metric("🐾 小喵回复", f"{st.session_state.chat_stats['assistant_messages']} 条")
        total_msgs = st.session_state.chat_stats['user_messages'] + st.session_state.chat_stats['assistant_messages']
        st.metric("📝 总对话数", f"{total_msgs} 条")
        st.metric("📄 总字符数", f"{st.session_state.chat_stats['total_chars']:,}")
        duration = (datetime.now() + timedelta(hours=8)) - st.session_state.chat_stats["start_time"]
        hours = int(duration.total_seconds() / 3600)
        minutes = int((duration.total_seconds() % 3600) / 60)
        if hours > 0:
            st.metric("⏱️ 聊天时长", f"{hours} 小时 {minutes} 分钟")
        else:
            st.metric("⏱️ 聊天时长", f"{minutes} 分钟")
        avg_length = st.session_state.chat_stats['total_chars'] / total_msgs if total_msgs > 0 else 0
        st.metric("📏 平均长度", f"{int(avg_length)} 字/条")
    
    footer_messages = [
        "💖 Powered by SJTU",
        "✨ Made with love",
        "🐾 v2025.12.25"
    ]
    st.caption(f"{random.choice(footer_messages)} ✨")

# 主界面 - DeepSeek风格简化布局
col_title, col_status = st.columns([1, 0.2])
with col_title:
    st.title("🐾 小喵 Neko")
with col_status:
    st.caption("✨ Online")

# --- 视觉识别功能 (主界面顶部) ---
with st.expander("📎 发送图片", expanded=False):
    uploaded_image = st.file_uploader(
        "上传图片 (PNG/JPG/JPEG)",
        type=['png', 'jpg', 'jpeg'],
        key="vision_uploader",
        help="拖拽文件到这里上传图片喵~ ✨"
    )
    
    # 处理上传的图片
    if uploaded_image is not None:
        # 显示小缩略图
        col_img, col_info = st.columns([0.3, 0.7])
        with col_img:
            # 获取用于显示的图片对象
            display_img = get_image_for_display(uploaded_image)
            
            if display_img:
                # 创建小缩略图（不修改原图）
                thumb_img = display_img.copy()
                thumb_img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                st.image(thumb_img, width=150)
            else:
                # 如果无法获取PIL Image，尝试直接显示
                if hasattr(uploaded_image, 'seek'):
                    uploaded_image.seek(0)
                st.image(uploaded_image, width=150)
        
        with col_info:
            image_name = uploaded_image.name if hasattr(uploaded_image, 'name') else "上传的图片"
            st.caption(f"📷 {image_name}")
        
        # 生成唯一的图片标识（用于防重复处理）
        # 对于上传的图片，使用文件名和大小
        image_key = f"processed_{uploaded_image.name}_{uploaded_image.size}"
        
        # 检查是否已经处理过这张图片（避免重复处理）
        if image_key not in st.session_state:
            # 显示处理中提示
            with st.spinner("🔍 小喵正在识别图片内容喵~ ✨"):
                # 转换为Base64（已包含压缩和格式转换）
                image_base64 = get_image_base64(uploaded_image)
                # 调用视觉识别（会自动添加标准前缀）
                vision_description = recognize_image(image_base64)
                
                # 将识别结果作为系统消息插入
                system_message = {
                    "role": "system",
                    "content": f"[系统视觉信号]: 用户刚刚上传了一张图片。图片内容描述如下：{vision_description}。请根据这个内容与用户互动，保持你可爱的小猫咪人设，对图片内容发表有趣的评论。"
                }
                
                # 插入到消息历史中（在最后一条用户消息之后，或者作为第一条消息）
                if len(st.session_state.messages) > 0:
                    # 找到最后一个非系统消息的位置
                    insert_pos = len(st.session_state.messages)
                    for i in range(len(st.session_state.messages) - 1, -1, -1):
                        if st.session_state.messages[i]["role"] != "system":
                            insert_pos = i + 1
                            break
                    st.session_state.messages.insert(insert_pos, system_message)
                else:
                    st.session_state.messages.append(system_message)
                
                # 标记为已处理
                st.session_state[image_key] = True
                
                # 显示小的成功提示（小猫戴眼镜）
                st.caption("👓✨ 小喵戴上了眼镜，已经识别出图片内容了喵~ Nya~ 💕")
                
                # 自动刷新以显示新的系统消息效果
                time.sleep(1)
                st.rerun()
        else:
            st.caption("✅ 图片已识别，小喵已经知道内容了喵~ ✨")

# --- 6. 对话逻辑与伪主动性初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    
    # === 伪主动性逻辑：根据时间生成欢迎语 ===
    now = (datetime.now() + timedelta(hours=8))
    current_hour = now.hour
    
    # 1. 定义时间段上下文
    time_context = ""
    if 5 <= current_hour < 9:
        time_context = "现在是清晨 (Early Morning)，提醒用户是否有早八课，语气要元气满满，提醒吃早餐。"
    elif 11 <= current_hour < 14:
        time_context = "现在是午饭点 (Lunch Time)，提醒用户按时吃饭，可以问问去哪个食堂（比如一餐、二餐）。"
    elif 14 <= current_hour < 18:
        time_context = "现在是下午 (Afternoon)，如果用户在学习，鼓励一下；如果在犯困，建议喝杯咖啡。"
    elif 23 <= current_hour or current_hour < 2:
        time_context = "现在是深夜 (Late Night)，提醒用户早点休息，熬夜伤身体，不要太拼了。"
    else:
        time_context = "现在是平时，随便聊聊，保持可爱。"

    # 2. 调用 DeepSeek 生成"主动"欢迎语
    # 使用 Spinner 让用户感觉小喵正在"醒来"
    with st.spinner("💤 小喵正在伸懒腰醒来..."):
        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model=MODEL_NAME, # 使用 V3 模型
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT}, # 保持猫娘人设
                    {"role": "user", "content": f"（系统隐式指令：用户刚刚打开网页。{time_context} 请生成一句简短、可爱、有生活气息的欢迎语。不要太长，50字以内。）"}
                ],
                max_tokens=100,
                temperature=0.7
            )
            welcome_msg = response.choices[0].message.content
        except Exception as e:
            # 兜底策略：如果 API 失败，使用默认欢迎语
            welcome_msg = "Meow~ 你好呀！我是小喵，很高兴见到你喵~ ✨💕 (刚刚睡醒，脑子有点懵懵的~)"

    # 3. 存入历史并显示
    st.session_state.messages.append({
        "role": "assistant", 
        "content": welcome_msg,
        "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
    })

# 聊天消息显示区域 - 微信风格
chat_container = st.container()
with chat_container:
    last_time = None
    for i, message in enumerate(st.session_state.messages):
        if message["role"] != "system":
            # 获取消息时间
            msg_time = message.get("timestamp", (datetime.now() + timedelta(hours=8)))
            if isinstance(msg_time, str):
                try:
                    msg_time = datetime.fromisoformat(msg_time)
                except:
                    msg_time = (datetime.now() + timedelta(hours=8))
            
            # 判断是否需要显示时间戳（间隔超过5分钟或第一条消息）
            show_timestamp = False
            if last_time is None:
                show_timestamp = True
            else:
                time_diff = (msg_time - last_time).total_seconds()
                if time_diff > 300:  # 5分钟
                    show_timestamp = True
            
            # 显示时间戳
            if show_timestamp:
                time_str = msg_time.strftime("%H:%M")
                st.markdown(f'<div class="message-timestamp">{time_str}</div>', unsafe_allow_html=True)
                last_time = msg_time
            
            # 显示消息
            avatar = "🐾" if message["role"] == "assistant" else "👤"
            with st.chat_message(message["role"], avatar=avatar):
                # 检查消息类型
                if message.get("type") == "image":
                    # 如果是图片，使用 st.image 渲染
                    # 图片内容可能是 URL、base64 字符串或 PIL Image
                    image_content = message["content"]
                    if isinstance(image_content, str):
                        # 如果是字符串，可能是 URL 或 base64
                        if image_content.startswith("data:image") or image_content.startswith("http"):
                            st.image(image_content, width="stretch")
                        else:
                            # 尝试作为 base64 解码
                            try:
                                decoded_img = decode_base64_image(image_content)
                                if decoded_img:
                                    st.image(decoded_img, width="stretch")
                                else:
                                    st.image(image_content, width="stretch")
                            except:
                                st.image(image_content, width="stretch")
                    else:
                        # 如果是 PIL Image 或其他格式，直接显示
                        st.image(image_content, width="stretch")
                else:
                    # 如果是文本，使用 st.markdown 渲染
                    # 如果是 assistant 消息，检查是否包含 R1 的思考过程
                    if message["role"] == "assistant":
                        thinking_content, final_answer = parse_r1_response(message["content"])
                        if thinking_content:
                            # 如果有思考过程，用可折叠的方式显示
                            with st.expander("🧠 查看小喵的思考过程", expanded=False):
                                st.markdown(f"```\n{thinking_content}\n```")
                            # 只显示最终答案，格式化数学公式
                            final_display = final_answer if final_answer else message["content"]
                            st.markdown(format_deepseek_math(final_display))
                        else:
                            # 没有思考过程，正常显示，格式化数学公式
                            st.markdown(format_deepseek_math(message["content"]))
                    else:
                        # 用户消息，正常显示，格式化数学公式
                        st.markdown(format_deepseek_math(message["content"]))

# 显示建议话题（如果有）
if "suggested_topic" in st.session_state:
    col_topic1, col_topic2 = st.columns([1, 0.15])
    with col_topic1:
        st.caption(f"💡 建议话题：{st.session_state.suggested_topic}")
    with col_topic2:
        if st.button(f"使用", key="use_topic", use_container_width=True):
            st.session_state.pending_message = st.session_state.suggested_topic
            del st.session_state.suggested_topic
            st.rerun()

# --- 输入区域 (调试增强版) ---
prompt = None

if st.session_state.get("practice_mode", False):
    # 口语模式
    st.markdown("### 🎤 请点击下方按钮开始录音")
    audio_value = st.audio_input("点击录音 (Click to Record)")
    
    if audio_value:
        # 1. 调试：确认是否接收到音频对象
        st.toast("✅ 收到音频数据，正在上传...", icon="📤")
        
        # 显示音频大小，确认不是空文件
        # audio_value 是一个 BytesIO 对象
        file_size = audio_value.getbuffer().nbytes
        # st.caption(f"🔧 调试信息: 音频大小 {file_size} bytes") 
        
        if file_size > 0:
            with st.spinner("👂 小喵正在努力听清楚..."):
                # 2. 调用识别（直接传递 BytesIO 对象，不需要 .read()）
                text_result, error = transcribe_audio(audio_value)
            
            if error:
                st.error(f"❌ 识别报错: {error}")
            elif not text_result:
                st.warning("⚠️ 识别结果为空，可能是声音太小或没说话？")
            else:
                prompt = text_result
                st.success(f"👂 听到: {prompt}")
        else:
            st.error("❌ 录音数据为空，请检查麦克风权限！")
            
    # 文字输入备选
    if not prompt:
        # 输入提示语
        if "input_placeholder" not in st.session_state:
            input_hints = [
                "或者直接打字喵~ (口语模式)",
                "也可以打字输入喵~ ✨",
                "打字也可以哦Nya~ 💕"
            ]
            st.session_state.input_placeholder = random.choice(input_hints)
        prompt = st.chat_input(st.session_state.input_placeholder)
else:
    # 普通模式
    # 输入提示语
    if "input_placeholder" not in st.session_state:
        input_hints = [
            "在此处和小喵聊天喵~ ✨",
            "想和小喵说什么呢？Nya~ 💕",
            "输入你的想法，小喵在听哦~ 🐾",
            "告诉小喵你在想什么吧~ 🌟",
            "小喵准备好听你说话了喵~ 💖"
        ]
        st.session_state.input_placeholder = random.choice(input_hints)
    prompt = st.chat_input(st.session_state.input_placeholder)

# 处理待发送的消息（来自快捷回复或建议话题）
if "pending_message" in st.session_state:
    prompt = st.session_state.pending_message
    del st.session_state.pending_message

if prompt:
    # 1. 先把消息存入历史
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt,
        "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
    })
    
    # 2. 【关键修复】立即在界面上渲染这条消息
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    # 3. 更新统计
    st.session_state.chat_stats["user_messages"] += 1
    st.session_state.chat_stats["total_chars"] += len(prompt)

    # ========== Agentic Workflow: 智能体工作流 ==========
    # 初始化搜索和绘画结果
    search_result = None
    
    # ========== Step 0: 思考 - 意图识别 ==========
    with st.status("🧠 小喵正在思考行动方案...", expanded=False) as status:
        actions = analyze_intent(prompt)
        
        # 逻辑屏蔽代码意图：如果未开启学霸模式，移除 CODE 意图
        if not st.session_state.get("scholar_pro_mode", False):
            if "CODE" in actions:
                actions.remove("CODE")
            # 如果移除后 actions 为空，自动添加 CHAT
            if not actions:
                actions.append("CHAT")
        
        status.update(label=f"✅ 识别到操作：{', '.join(actions)}", state="complete")
        st.write(f"**识别到的操作：** {', '.join(actions)}")
    
    # 获取历史记录（用于绘图和对话的上下文记忆）
    history_str = get_recent_chat_history()
    
    # ========== 核心优化：逻辑分流 ==========
    # 获取开关状态
    is_scholar_pro = st.session_state.get("scholar_pro_mode", False)
    
    # 🚨 优化点：只要开启了 Pro 模式，强制进入研讨流程，忽略意图识别的限制
    if is_scholar_pro:
        # --- 进入学霸 Pro 模式 (强制) ---
        
        # 1. 初始化变量
        final_solution = None
        success = False
        pro_summary = ""
        
        # 2. Phase 1: 思考与推导过程
        # 使用 status 容器，给用户明确的"正在启动"反馈
        with st.status("🔥 学霸 Pro 模式已激活：教授团队正在入驻...", expanded=True) as pro_status:
            try:
                # 运行教授-助教循环
                # 注意：这里直接把 prompt 传进去，不再依赖 actions 里的 CODE
                final_solution, success = run_scholar_pro_mode(prompt, search_result if search_result else "")
                
                if success:
                    pro_status.update(label="✅ 学霸 Pro 模式研讨完成", state="complete", expanded=False)
                else:
                    pro_status.update(label="⚠️ 研讨结束 (未完全通过)", state="complete", expanded=False)
                    
            except Exception as e:
                error_str = str(e)
                if "400" in error_str and "Budget" in error_str:
                    pro_status.update(label="💸 经费不足警告", state="error")
                    st.error("😿 哎呀！学校发的 API 经费（Quota）用完啦！DeepSeek-R1 教授罢工了。\n请尝试关闭 Pro 模式使用普通模式，或者切换 API Key 喵~")
                else:
                    pro_status.update(label="❌ 学霸 Pro 模式出错", state="error")
                    st.error(f"推导过程发生异常: {error_str}")
        
        # 3. Phase 2: 最终汇报
        if final_solution:
            client = get_openai_client()
            
            # 构建汇报 Prompt (保持不变)
            presenter_prompt = f"""你是可爱的小喵。这是经过教授和助教多轮验证的最终完美答案：

{final_solution}

请用你的猫娘语气（Meow~, Nya~），把这个答案通俗易懂地讲给用户听。保留核心公式和结论，但语气要软萌。"""
            
            presenter_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": presenter_prompt}
            ]
            
            # 显示最终回复
            with st.chat_message("assistant", avatar="🐾"):
                thinking_box = st.empty()
                thinking_box.caption("💭 小喵正在整理最终答案喵~ ✨")
                res_box = st.empty()
                full_reply = ""
                
                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME, # V3
                        messages=presenter_messages,
                        max_tokens=2000,
                        temperature=0.7,
                        stream=True
                    )
                    thinking_box.empty()
                    
                    cursor_states = ["█", "▊", "▋", "▌", "▍", "▎", "▏", " "]
                    cursor_idx = 0
                    for chunk in completion:
                        if chunk.choices[0].delta.content:
                            full_reply += chunk.choices[0].delta.content
                            cursor_idx = (cursor_idx + 1) % len(cursor_states)
                            res_box.markdown(format_deepseek_math(full_reply) + cursor_states[cursor_idx])
                    res_box.markdown(format_deepseek_math(full_reply))
                    
                    # 存入历史
                    pro_summary = f"🔥 **学霸 Pro 模式执行报告**\n\n**最终解答：**\n{final_solution}\n\n**小喵的解释：**\n{full_reply}"
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": pro_summary,
                        "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                    })
                    st.session_state.chat_stats["assistant_messages"] += 1
                    st.session_state.chat_stats["total_chars"] += len(pro_summary)
                    st.divider()
                    
                except Exception as e:
                    res_box.error(f"😿 汇报出错: {str(e)}")

        # 🚨 关键：如果是 Pro 模式，运行完后直接结束本次响应，不再进入下面的 CHAT 逻辑
        # 防止出现"教授说完话，小喵又自己聊了一遍"的重复情况
        st.stop() 
    
    # ========== Step 1: 搜索 (SEARCH) ==========
    if "SEARCH" in actions and SEARCH_AVAILABLE:
        with st.status("🔍 小喵正在网上冲浪喵...", expanded=False) as search_status:
            search_result = perform_web_search(prompt)
            if search_result:
                search_status.update(label="✅ 已获取联网信息", state="complete")
                st.write("搜索到的内容摘要：")
                st.caption(search_result[:500] + "..." if len(search_result) > 500 else search_result)
            else:
                search_status.update(label="😿 没找到相关信息喵~", state="error")
    
    # ========== Step 2: 绘图 (DRAW) ==========
    if "DRAW" in actions:
        with st.chat_message("assistant", avatar="🐾"):
            try:
                # 关键逻辑：调用 generate_image_prompt 时，务必传入 search_context 和 chat_history
                with st.spinner("🎨 小喵正在构思画面..."):
                    # 传入 prompt、search_result 和 history_str，让生成器结合上下文记忆
                    english_prompt = generate_image_prompt(
                        user_prompt=prompt,
                        search_context=search_result if search_result else "",
                        chat_history=history_str
                    )
                
                if not english_prompt:
                    st.error("😿 生成提示词失败，小喵画不出来喵~")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "😿 对不起，小喵没能生成提示词，请再试一次喵~",
                        "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                    })
                    st.session_state.chat_stats["assistant_messages"] += 1
                    
                    # AI输出结束后添加分割线
                    st.divider()
                else:
                    # 调用 FLUX API 生成图片
                    with st.spinner(f"🖌️ 正在绘制：{english_prompt} ..."):
                        image_data = query_flux_image(english_prompt)
                    
                    if image_data:
                        # 成功：显示图片
                        try:
                            # 将二进制数据转换为 PIL Image 并显示
                            if PIL_AVAILABLE:
                                image = Image.open(BytesIO(image_data))
                                st.image(image, caption="我是交大灵魂画师喵！", width="stretch")
                            else:
                                # 如果没有 PIL，直接显示二进制数据
                                st.image(image_data, caption="我是交大灵魂画师喵！", width="stretch")
                            
                            # 【新增】将图片存入 session_state
                            # 将图片转换为 base64 字符串以便持久化保存
                            if PIL_AVAILABLE:
                                # 将 PIL Image 转换为 base64
                                buffered = BytesIO()
                                image.save(buffered, format="PNG")
                                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                                image_url = f"data:image/png;base64,{img_base64}"
                            else:
                                # 如果没有 PIL，直接使用二进制数据的 base64
                                img_base64 = base64.b64encode(image_data).decode('utf-8')
                                image_url = f"data:image/png;base64,{img_base64}"
                            
                            # 保存图片消息到 session_state
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": image_url,  # 这里存图片的 URL 或 base64 数据
                                "type": "image",       # 标记这是图片
                                "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                            })
                            
                            # 【新增】追加一条助手的文本回复，作为图片的"配文"
                            reply_text = f"画好啦喵~ ✨\n\n这是我为你生成的图片，使用的魔法咒语（Prompt）是：\n> {english_prompt}"
                            if search_result:
                                reply_text += "\n\n✅ 小喵已经根据搜索到的信息来设计画面了喵~"
                            st.markdown(reply_text)
                            
                            # 记忆：将文本回复存入聊天历史
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": reply_text,
                                "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                            })
                            
                            # 更新统计
                            st.session_state.chat_stats["assistant_messages"] += 2  # 图片消息 + 文本消息
                            st.session_state.chat_stats["total_chars"] += len(reply_text)
                            
                            # AI输出结束后添加分割线
                            st.divider()
                        except Exception as e:
                            st.error(f"😿 显示图片失败：{str(e)}")
                            error_reply = "😿 对不起，小喵画好了但是显示不出来喵~ 请再试一次Nya~"
                            st.markdown(error_reply)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": error_reply,
                                "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                            })
                            st.session_state.chat_stats["assistant_messages"] += 1
                            
                            # AI输出结束后添加分割线
                            st.divider()
                    else:
                        # 失败：显示错误信息
                        error_reply = "😿 对不起，小喵没能画出图片喵~ 可能是模型正在加载，请稍后再试Nya~"
                        st.error(error_reply)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_reply,
                            "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                        })
                        st.session_state.chat_stats["assistant_messages"] += 1
                        
                        # AI输出结束后添加分割线
                        st.divider()
            except Exception as e:
                error_reply = f"😿 绘画过程中出错了喵~: {str(e)}"
                st.error(error_reply)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_reply,
                    "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                })
                st.session_state.chat_stats["assistant_messages"] += 1
                
                # AI输出结束后添加分割线
                st.divider()
    
    # ========== Step 3: 对话 (CHAT) ==========
    # 判断是否需要执行对话：
    # 1. 如果明确包含 CHAT，执行对话
    # 2. 如果既没有 DRAW、SEARCH 也没有 CODE，执行对话（防止无响应）
    # 3. 如果只有 SEARCH（没有 DRAW、CODE 和 CHAT），执行对话（搜索结果需要对话环节）
    # 4. 如果只有 CODE（没有 CHAT），不执行对话（CODE 已经生成了最终回复）
    should_chat = "CHAT" in actions or ("DRAW" not in actions and "SEARCH" not in actions and "CODE" not in actions) or ("SEARCH" in actions and "DRAW" not in actions and "CODE" not in actions and "CHAT" not in actions)
    
    if should_chat:
        # 生成回复（如果之前搜索过，search_result 已经包含结果）
        # 上下文：如果刚才有了 search_result，务必将其插入 System Prompt 中，让 AI 能根据搜索结果回答问题
        
        with st.chat_message("assistant", avatar="🐾"):
            # 根据模型类型选择提示文字
            if "use_reasoning_model" in st.session_state and st.session_state.use_reasoning_model:
                thinking_text = "小喵正在疯狂烧脑中，请耐心等待（可能需要几十秒）... 🐱💦"
            else:
                thinking_phrases = [
                    "小喵正在思考喵~ ✨",
                    "让我想想Nya~ 💫",
                    "嗯...喵~ 🌟",
                    "小喵在认真思考哦~ 💕"
                ]
                thinking_text = f"💭 {random.choice(thinking_phrases)}"
            
            thinking_box = st.empty()
            thinking_box.caption(thinking_text)
            
            res_box = st.empty()
            full_res = ""
            
            # 根据开关状态选择模型
            current_model = "deepseek-r1" if ("use_reasoning_model" in st.session_state and st.session_state.use_reasoning_model) else MODEL_NAME
            
            # 尝试调用，增加异常捕获
            try:
                # --- 核心修改：构建干净的 API 消息列表 ---
                api_messages = []
                
                # 第一步：根据模型类型获取 System Prompt（动态添加）
                system_prompt = get_system_prompt(current_model)
                if system_prompt:
                    api_messages.append({"role": "system", "content": system_prompt})
                
                # 【文档助手】如果用户上传了文档，注入文档内容
                if "current_document_content" in st.session_state and st.session_state.current_document_content:
                    document_content = st.session_state.current_document_content
                    
                    # 防止 Token 消耗过大，限制文档长度
                    max_doc_length = 200000
                    if len(document_content) > max_doc_length:
                        document_content = document_content[:max_doc_length] + "\n\n...(文档过长，仅截取前 20 万字符，建议分章节投喂)..."
                    
                    document_system_msg = {
                        "role": "system",
                        "content": f"【系统知识库注入】用户上传了以下参考文档，请在回答问题时优先参考这些内容：\n\n{document_content}"
                    }
                    api_messages.append(document_system_msg)
                
                # 【关键】如果刚才有了 search_result，务必将其插入 System Prompt 中
                if search_result:
                    search_system_msg = {
                        "role": "system",
                        "content": f"【这是实时搜索结果，请利用这些信息回答用户的问题】\n\n{search_result}"
                    }
                    api_messages.append(search_system_msg)
                elif "SEARCH" in actions and not search_result:
                    # 如果意图是搜索但搜索失败，添加警告
                    search_failed_warning = {
                        "role": "system",
                        "content": "【系统警告】网络搜索失败。请直接告诉用户无法连接网络，严禁编造虚假新闻。"
                    }
                    api_messages.append(search_failed_warning)
                
                # --- 限制历史记录长度 ---
                # 只取最近 20 条消息，防止 Token 爆炸
                recent_messages = st.session_state.messages[-20:]
                
                # --- 遍历历史记录，进行严格清洗 ---
                for msg in recent_messages:
                    # 1. 处理 system 角色
                    if msg["role"] == "system":
                        # 【关键修复】如果是视觉识别信号，必须保留并加入列表！
                        if "[系统视觉信号]" in str(msg.get("content", "")):
                            api_messages.append({"role": "system", "content": str(msg.get("content", ""))})
                            continue  # 处理完后继续下一次循环
                        else:
                            continue  # 其他普通 system 消息跳过（避免与开头的 System Prompt 重复）
                    
                    # 2. 【关键】如果消息标记为 image，直接丢弃，绝对不发给 LLM
                    if msg.get("type") == "image":
                        continue
                    
                    # 3. 【防御】获取内容并转为字符串
                    raw_content = str(msg.get("content", ""))
                    
                    # 4. 【核弹级防御】如果单条消息长度超过 10,000 字符，判定为异常数据(Base64)，强制截断！
                    # 正常的聊天对话不可能单条超过 1 万字。
                    if len(raw_content) > 10000:
                        clean_content = raw_content[:1000] + "\n[系统提示：检测到超长异常数据，已截断...]"
                    else:
                        clean_content = raw_content
                    
                    api_messages.append({"role": msg["role"], "content": clean_content})
                
                # --- 发送清洗后的数据 ---
                client = get_openai_client()
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=api_messages,  # 使用清洗后的列表
                    stream=True
                )
                
                # 清除思考提示
                thinking_box.empty()
                
                # 流式输出，添加可爱的光标效果
                cursor_states = ["█", "▊", "▋", "▌", "▍", "▎", "▏", " "]
                cursor_idx = 0
                
                # 如果是 R1 模式，在流式输出时尝试隐藏思考过程
                is_r1_mode = "use_reasoning_model" in st.session_state and st.session_state.use_reasoning_model
                display_content = ""  # 用于显示的临时内容
                final_answer_detected = False  # 标记是否已检测到最终答案
                last_thinking_state = False  # 记录上一次是否在思考中，用于减少重复渲染
                
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        
                        # 如果是 R1 模式，实时检测思考状态
                        if is_r1_mode:
                            # 检测是否还在生成思考内容
                            # R1 使用 <think> 标签
                            has_open_tag = "<think>" in full_res
                            has_close_tag = "</think>" in full_res
                            
                            # 检查是否正在思考中（有开始标签但没有结束标签）
                            is_thinking = has_open_tag and not has_close_tag
                            
                            if is_thinking:
                                # 正在思考中，显示占位符（只在状态改变时更新，减少重复渲染）
                                if not last_thinking_state:
                                    res_box.markdown("🧠 小喵正在深度思考中... (请稍候)")
                                    last_thinking_state = True
                            else:
                                # 思考已结束或未开始，尝试解析最终答案
                                thinking_content, final_answer = parse_r1_response(full_res)
                                
                                if final_answer and final_answer.strip():
                                    # 已解析出最终答案，开始流式渲染
                                    if not final_answer_detected:
                                        final_answer_detected = True
                                        last_thinking_state = False
                                    
                                    display_content = final_answer
                                    cursor_idx = (cursor_idx + 1) % len(cursor_states)
                                    formatted_content = format_deepseek_math(display_content)
                                    res_box.markdown(formatted_content + cursor_states[cursor_idx])
                                else:
                                    # 思考已结束，但最终答案还未开始，继续显示占位符
                                    if last_thinking_state or not final_answer_detected:
                                        res_box.markdown("🧠 小喵正在深度思考中... (请稍候)")
                                        last_thinking_state = True
                        else:
                            # V3 模式，正常显示
                            display_content = full_res
                            cursor_idx = (cursor_idx + 1) % len(cursor_states)
                            formatted_content = format_deepseek_math(display_content)
                            res_box.markdown(formatted_content + cursor_states[cursor_idx])
                
                # 最终显示，处理 R1 的思考过程
                if is_r1_mode:
                    # 重新解析思考过程和最终答案（确保完整）
                    thinking_content, final_answer = parse_r1_response(full_res)
                    
                    if thinking_content:
                        # 如果有思考过程，用可折叠的方式显示
                        with st.expander("🧠 查看小喵的思考过程", expanded=False):
                            st.markdown(f"```\n{thinking_content}\n```")
                        # 只显示最终答案，格式化数学公式
                        final_display = final_answer if final_answer else full_res
                        res_box.markdown(format_deepseek_math(final_display))
                    else:
                        # 没有思考过程，正常显示，格式化数学公式
                        res_box.markdown(format_deepseek_math(full_res))
                else:
                    # V3 模式，正常显示，格式化数学公式
                    res_box.markdown(format_deepseek_math(full_res))
                
                # 保存完整回复到消息历史
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_res,
                    "timestamp": (datetime.now() + timedelta(hours=8)).isoformat()
                })
                
                # 更新统计信息
                st.session_state.chat_stats["assistant_messages"] += 1
                st.session_state.chat_stats["total_chars"] += len(full_res)
                
                # 随机显示可爱的完成反应
                reactions = [
                    "✨ 小喵说完了喵~",
                    "💕 希望小喵的回答有帮助Nya~",
                    "🐾 小喵很开心能帮到你~",
                    "🌟 还有什么想问小喵的吗？"
                ]
                if random.random() < 0.3:  # 30%概率显示
                    st.caption(f"💫 {random.choice(reactions)}")
                
                # === 新增：口语模式自动播放语音 ===
                if st.session_state.get("practice_mode", False):
                    # 只有当回复不太长时才朗读，避免等待过久
                    if len(full_res) < 500:
                        play_ai_voice(full_res)
                
                # AI输出结束后添加分割线
                st.divider()
                    
            except Exception as e:
                thinking_box.empty()
                error_messages = [
                    f"😿 哎呀，小喵遇到了一点问题喵~: {str(e)}",
                    f"💔 小喵出错了，对不起Nya~: {str(e)}",
                    f"😢 小喵需要帮助了喵~: {str(e)}"
                ]
                st.error(random.choice(error_messages))
                
                # AI输出结束后添加分割线
                st.divider()

# --- 底部信息 ---
st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

st.caption("<div style='text-align: center; opacity: 0.6;'>💖 Powered by SJTU Model Service | v2025.12.25</div>", unsafe_allow_html=True)
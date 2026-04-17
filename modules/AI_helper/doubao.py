"""
process_local_file(INPUT_FILE, OUTPUT_FILE, cosplay_prompt)
INPUT_FILE          #要分析的文件路径
OUTPUT_FILE         #要写回的文件路径，文件类型自行定义，提示词内需要含有文件类型
cosplay_prompt      #提示词
"""


import os
import logging
from datetime import datetime
import config
from volcenginesdkarkruntime import Ark  # 官方SDK

# ===================== 日志配置（你原来的） =====================
LOG_DIR = config.LOG_DIR / "AI_helper"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"doubao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ===================== 官方SDK客户端初始化 =====================
def get_ark_client():
    # 你自己的 API Key
    api_key = "bdb1dd5f-a94d-4295-94e1-108aec9bb5af"  # 直接填写
    client = Ark(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key
    )
    return client


# ===================== 官方SDK调用函数（纯文本版） =====================
def call_doubao_api(prompt: str) -> str:
    try:
        logger.info("开始调用 火山方舟 官方SDK API")
        client = get_ark_client()

        response = client.responses.create(
            model="doubao-seed-2-0-lite-260215",
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}]
                }
            ]
        )

        # ===================== 正确提取代码 =====================
        answer = ""
        for item in response.output:
            # 找到真正的消息输出
            if hasattr(item, "content"):
                for content_item in item.content:
                    if hasattr(content_item, "text"):
                        answer = content_item.text
                        break
                break

        logger.info("API 调用成功！")
        return answer

    except Exception as e:
        logger.error(f"API 调用异常：{str(e)}")
        return f"API 调用异常：{str(e)}"


# ===================== 保存结果到文件 =====================
def save_result_to_file(result: str, output_path: str):
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        logger.info(f"结果已保存至：{output_path}")
        return True
    except Exception as e:
        logger.error(f"保存文件失败：{str(e)}")
        return False


# ===================== 读取本地文件 + 处理 =====================
def process_local_file(input_file_path: str, output_file_path: str, cosplay_prompt: str):
    try:
        logger.info(f"读取文件：{input_file_path}")
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"文件读取成功，长度：{len(content)} 字符")

        # 提示词
        prompt = f"""{cosplay_prompt} 文件内容：{content}"""

        # 调用官方API
        ai_result = call_doubao_api(prompt)

        # 保存结果
        if not ai_result.startswith("API"):
            save_result_to_file(ai_result, output_file_path)
        return ai_result

    except FileNotFoundError:
        logger.error(f"文件不存在：{input_file_path}")
        return "错误：文件不存在"
    except Exception as e:
        logger.error(f"处理失败：{str(e)}")
        return f"处理失败：{str(e)}"
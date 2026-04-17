# D:\Program_WorkStation\Project\Pycharm\CN_Bert_RumorAnalysis\config.py
import os
from pathlib import Path

# 1. 项目根目录
BASE_DIR = Path(__file__).resolve().parent  # 对应: CN_Bert_RumorAnalysis/

# 2. 模型相关路径
MODEL_BASE_DIR = BASE_DIR / "model"
# bert-base-chinese 模型的具体路径
BERT_MODEL_DIR = MODEL_BASE_DIR / "bert-base-chinese"

# 3. 其他常用路径
DATA_DIR = BASE_DIR / "data"          # 数据目录
LOG_DIR = BASE_DIR / "logs"           # 日志目录
OUTPUT_DIR = BASE_DIR / "data"      # 输出目录（如预测结果、模型 checkpoint）
AI_DIR = BASE_DIR / "modules" / "AI_helper"  #AI助手目录

# 4. AI提示词
DATA_PROCESS = "你是数据处理专家，请处理以下文件内容：1. 区分谣言与真相 2. 清洗冗余信息 3. 输出结构化训练数据,分别是rumor,truth,source 4. 结果返回json格式，不需要任何前缀说明（你返回的结果我会直接复制进json文件）"


#bert 相关的超参数也放在这里，统一管理
BERT_CONFIG = {
    "max_seq_len": 128,
    "batch_size": 32,
    "learning_rate": 2e-5,
    "num_epochs": 10,
    "model_path": str(BERT_MODEL_DIR)  # 转成字符串，适配部分库的路径要求
}

# 自动创建缺失的目录，避免运行时报错
def init_dirs():
    for dir_path in [MODEL_BASE_DIR, DATA_DIR, LOG_DIR, OUTPUT_DIR]:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"创建目录: {dir_path}")



if __name__ == "__main__":
    init_dirs()
    # 打印路径，验证是否正确
    print(f"项目根目录: {BASE_DIR}")
    print(f"BERT模型路径: {BERT_MODEL_DIR}")
    print(f"BERT模型路径(字符串): {str(BERT_MODEL_DIR)}")
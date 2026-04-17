import os

# 设置环境变量解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
from transformers import BertTokenizer, BertForSequenceClassification
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 配置参数
class Config:
    def __init__(self):
        # 模型路径
        self.model_dir = r'D:\Program_WorkStation\Project\Pycharm\CN_Bert_RumorAnalysis\output\model'

        # 模型配置
        self.max_seq_length = 128

        # 设备配置
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# 加载模型和tokenizer
def load_model(config):
    try:
        logger.info(f"Loading model from {config.model_dir}")

        # 检查模型文件是否存在
        required_files = ['config.json', 'model.safetensors', 'tokenizer.json', 'tokenizer_config.json']
        for file in required_files:
            file_path = os.path.join(config.model_dir, file)
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Model file not found: {file_path}")

        # 加载tokenizer
        tokenizer = BertTokenizer.from_pretrained(config.model_dir)
        logger.info("Tokenizer loaded successfully")

        # 加载模型
        model = BertForSequenceClassification.from_pretrained(config.model_dir)
        model.to(config.device)
        model.eval()
        logger.info(f"Model loaded successfully and moved to {config.device}")

        return model, tokenizer
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise


# 预处理文本
def preprocess_text(text, tokenizer, config):
    try:
        # 编码文本
        encoding = tokenizer(
            text,
            add_special_tokens=True,
            max_length=config.max_seq_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # 移动到设备
        input_ids = encoding['input_ids'].to(config.device)
        attention_mask = encoding['attention_mask'].to(config.device)

        return input_ids, attention_mask
    except Exception as e:
        logger.error(f"Error preprocessing text: {e}")
        raise


# 预测谣言概率
def predict_rumor_probability(text, model, tokenizer, config):
    try:
        # 预处理文本
        input_ids, attention_mask = preprocess_text(text, tokenizer, config)

        # 模型推理
        with torch.no_grad():
            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits

            # 计算概率
            probabilities = torch.softmax(logits, dim=1)
            rumor_probability = probabilities[0][1].item()  # 索引1表示谣言

        return rumor_probability
    except Exception as e:
        logger.error(f"Error predicting rumor probability: {e}")
        raise


# 主函数
def main():
    try:
        # 初始化配置
        config = Config()
        logger.info("Configuration initialized")

        # 加载模型和tokenizer
        model, tokenizer = load_model(config)

        logger.info("\n=== 文本谣言概率预测程序 ===")
        logger.info("输入文本后按Enter提交，输入 'exit' 退出程序")

        while True:
            try:
                # 读取单行输入（按Enter直接提交）
                logger.info("\n请输入文本:")
                text = input().strip()

                # 退出逻辑
                if text.lower() == 'exit':
                    logger.info("退出程序")
                    return

                # 检查输入是否为空
                if not text:
                    logger.warning("输入文本为空，请重新输入")
                    continue

                # 预测谣言概率
                rumor_prob = predict_rumor_probability(text, model, tokenizer, config)

                # 输出结果
                logger.info(f"\n=== 预测结果 ===")
                logger.info(f"输入文本: {text[:100]}..." if len(text) > 100 else f"输入文本: {text}")
                logger.info(f"谣言概率: {rumor_prob * 100:.2f}%")

                # 解释结果
                if rumor_prob >= 0.7:
                    logger.info("预测结果: 该文本很可能是谣言")
                elif rumor_prob >= 0.4:
                    logger.info("预测结果: 该文本可能是谣言")
                else:
                    logger.info("预测结果: 该文本不太可能是谣言")

            except KeyboardInterrupt:
                logger.info("\n退出程序")
                return
            except Exception as e:
                logger.error(f"处理输入时出错: {e}")
                continue

    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        return


if __name__ == '__main__':
    main()
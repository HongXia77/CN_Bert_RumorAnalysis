import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, get_linear_schedule_with_warmup
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import config
from tqdm import tqdm

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置参数
class Config:
    def __init__(self):
        # 数据配置
        self.data_path = r'D:\Program_WorkStation\Project\Pycharm\CN_Bert_RumorAnalysis\data\final_all_data.csv'
        self.output_dir = r'D:\Program_WorkStation\Project\Pycharm\CN_Bert_RumorAnalysis\output'
        
        # 模型配置
        self.model_name = config.BERT_MODEL_DIR
        self.max_seq_length = 128
        
        # 训练配置
        self.batch_size = 32
        self.learning_rate = 2e-5
        self.epochs = 5
        self.warmup_steps = 0
        self.weight_decay = 0.01
        
        # 设备配置
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 评估配置
        self.test_size = 0.2
        self.random_state = 42

# 创建输出目录
def create_output_dir(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    else:
        logger.info(f"Output directory already exists: {output_dir}")

# 数据集类
class RumorDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_seq_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        # 编码文本
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_seq_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'label': torch.tensor(label, dtype=torch.long)
        }

# 加载和预处理数据
def load_and_preprocess_data(config):
    logger.info(f"Loading data from {config.data_path}")
    
    # 加载数据
    df = pd.read_csv(config.data_path)
    logger.info(f"Data loaded successfully. Shape: {df.shape}")
    
    # 检查数据
    logger.info(f"Label distribution: {df['label'].value_counts().to_dict()}")
    
    # 分割数据
    texts = df['text'].tolist()
    labels = df['label'].tolist()
    
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=config.test_size, random_state=config.random_state
    )
    
    logger.info(f"Train size: {len(train_texts)}, Test size: {len(test_texts)}")
    
    # 加载tokenizer
    tokenizer = BertTokenizer.from_pretrained(config.model_name)
    
    # 创建数据集
    train_dataset = RumorDataset(train_texts, train_labels, tokenizer, config.max_seq_length)
    test_dataset = RumorDataset(test_texts, test_labels, tokenizer, config.max_seq_length)
    
    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False)
    
    return train_loader, test_loader, tokenizer

# 构建模型
def build_model(config):
    logger.info(f"Building model: {config.model_name}")
    model = BertForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=2,
        output_attentions=False,
        output_hidden_states=False
    )
    model.to(config.device)
    logger.info(f"Model built and moved to {config.device}")
    return model

# 训练模型
def train_model(model, train_loader, config):
    logger.info("Starting training")
    
    # 优化器
    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        eps=1e-8,
        weight_decay=config.weight_decay
    )
    
    # 学习率调度器
    total_steps = len(train_loader) * config.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=config.warmup_steps,
        num_training_steps=total_steps
    )
    
    # 损失函数
    loss_fn = nn.CrossEntropyLoss()
    
    # 训练记录
    training_stats = []
    
    for epoch in range(config.epochs):
        logger.info(f"\n====================================")
        logger.info(f"Epoch {epoch + 1}/{config.epochs}")
        logger.info(f"====================================")
        
        # 训练模式
        model.train()
        total_loss = 0
        
        # 进度条
        progress_bar = tqdm(train_loader, desc=f"Training Epoch {epoch + 1}", unit="batch")
        
        for i, batch in enumerate(progress_bar):
            # 移动数据到设备
            input_ids = batch['input_ids'].to(config.device)
            attention_mask = batch['attention_mask'].to(config.device)
            labels = batch['label'].to(config.device)
            
            # 清零梯度
            model.zero_grad()
            
            # 前向传播
            outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            
            # 更新参数
            optimizer.step()
            scheduler.step()
            
            # 更新进度条
            current_loss = loss.item()
            avg_loss = total_loss / (i + 1)
            progress_bar.set_postfix({
                'current_loss': f'{current_loss:.4f}',
                'avg_loss': f'{avg_loss:.4f}'
            })
            
            # 每100批次打印一次详细信息
            if (i + 1) % 100 == 0:
                logger.info(f"Batch {i + 1}/{len(train_loader)} - Loss: {current_loss:.4f}, Avg Loss: {avg_loss:.4f}")
        
        # 计算平均损失
        avg_train_loss = total_loss / len(train_loader)
        logger.info(f"\nEpoch {epoch + 1} completed")
        logger.info(f"Average training loss: {avg_train_loss:.4f}")
        
        # 评估模型
        logger.info("Evaluating model on training data...")
        eval_accuracy, eval_loss = evaluate_model(model, train_loader, config)
        logger.info(f"Training accuracy: {eval_accuracy:.4f}, Training loss: {eval_loss:.4f}")
        
        # 记录训练统计
        training_stats.append({
            'epoch': epoch + 1,
            'training_loss': avg_train_loss,
            'training_accuracy': eval_accuracy
        })
    return model, training_stats

# 评估模型
def evaluate_model(model, data_loader, config):
    model.eval()
    total_loss = 0
    predictions = []
    true_labels = []
    
    loss_fn = nn.CrossEntropyLoss()
    
    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(config.device)
            attention_mask = batch['attention_mask'].to(config.device)
            labels = batch['label'].to(config.device)
            
            outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()
            
            # 获取预测
            logits = outputs.logits
            predictions.extend(torch.argmax(logits, dim=1).cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
    
    avg_loss = total_loss / len(data_loader)
    accuracy = accuracy_score(true_labels, predictions)
    
    return accuracy, avg_loss

# 计算详细评估指标
def calculate_metrics(model, test_loader, config):
    model.eval()
    predictions = []
    true_labels = []
    
    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch['input_ids'].to(config.device)
            attention_mask = batch['attention_mask'].to(config.device)
            labels = batch['label'].to(config.device)
            
            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            predictions.extend(torch.argmax(logits, dim=1).cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
    
    # 计算指标
    accuracy = accuracy_score(true_labels, predictions)
    precision = precision_score(true_labels, predictions, average='binary')
    recall = recall_score(true_labels, predictions, average='binary')
    f1 = f1_score(true_labels, predictions, average='binary')
    cm = confusion_matrix(true_labels, predictions)
    
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'confusion_matrix': cm
    }
    
    return metrics

# 保存模型
def save_model(model, tokenizer, config):
    model_path = os.path.join(config.output_dir, 'model')
    os.makedirs(model_path, exist_ok=True)
    
    # 保存模型
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)
    logger.info(f"Model saved to {model_path}")

# 保存评估结果
def save_evaluation_results(metrics, training_stats, config):
    # 保存指标
    metrics_path = os.path.join(config.output_dir, 'evaluation_metrics.txt')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        f.write("Evaluation Metrics\n")
        f.write("==================\n")
        f.write(f"Accuracy: {metrics['accuracy']:.4f}\n")
        f.write(f"Precision: {metrics['precision']:.4f}\n")
        f.write(f"Recall: {metrics['recall']:.4f}\n")
        f.write(f"F1 Score: {metrics['f1']:.4f}\n")
        f.write("\nConfusion Matrix:\n")
        f.write(str(metrics['confusion_matrix']))
    
    logger.info(f"Evaluation metrics saved to {metrics_path}")
    
    # 保存训练统计
    stats_path = os.path.join(config.output_dir, 'training_stats.csv')
    df = pd.DataFrame(training_stats)
    df.to_csv(stats_path, index=False)
    logger.info(f"Training stats saved to {stats_path}")

# 绘制混淆矩阵
def plot_confusion_matrix(cm, config):
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Non-rumor', 'Rumor'],
                yticklabels=['Non-rumor', 'Rumor'])
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('True')
    
    cm_path = os.path.join(config.output_dir, 'confusion_matrix.png')
    plt.savefig(cm_path)
    logger.info(f"Confusion matrix plot saved to {cm_path}")

# 绘制训练曲线
def plot_training_curve(training_stats, config):
    plt.figure(figsize=(12, 4))
    
    # 损失曲线
    plt.subplot(1, 2, 1)
    plt.plot([stat['epoch'] for stat in training_stats],
             [stat['training_loss'] for stat in training_stats],
             label='Training Loss')
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    
    # 准确率曲线
    plt.subplot(1, 2, 2)
    plt.plot([stat['epoch'] for stat in training_stats],
             [stat['training_accuracy'] for stat in training_stats],
             label='Training Accuracy')
    plt.title('Training Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    
    curve_path = os.path.join(config.output_dir, 'training_curve.png')
    plt.tight_layout()
    plt.savefig(curve_path)
    logger.info(f"Training curve plot saved to {curve_path}")

# 主函数
def main():
    try:
        # 初始化配置
        config = Config()
        logger.info("Configuration initialized")
        
        # 创建输出目录
        create_output_dir(config.output_dir)
        
        # 加载和预处理数据
        train_loader, test_loader, tokenizer = load_and_preprocess_data(config)
        
        # 构建模型
        model = build_model(config)
        
        # 训练模型
        model, training_stats = train_model(model, train_loader, config)
        
        # 评估模型
        metrics = calculate_metrics(model, test_loader, config)
        logger.info(f"Evaluation results: {metrics}")
        
        # 保存模型
        save_model(model, tokenizer, config)
        
        # 保存评估结果
        save_evaluation_results(metrics, training_stats, config)
        
        # 绘制图表
        plot_confusion_matrix(metrics['confusion_matrix'], config)
        plot_training_curve(training_stats, config)
        
        logger.info("Training completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during training: {e}")
        raise

if __name__ == '__main__':
    main()

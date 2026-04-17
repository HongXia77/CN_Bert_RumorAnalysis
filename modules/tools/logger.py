import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime

class Logger:
    """专业日志工具类"""
    
    def __init__(self, log_dir=None, max_bytes=10*1024*1024, backup_count=5):
        """
        初始化日志工具
        :param log_dir: 日志目录，默认使用项目根目录下的logs文件夹
        :param max_bytes: 单个日志文件最大大小，默认10MB
        :param backup_count: 日志文件备份数量，默认5个
        """
        # 设置日志目录
        if log_dir is None:
            self.log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        else:
            self.log_dir = Path(log_dir)
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件配置
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 日志分类
        self.log_categories = {
            'system': 'system.log',      # 系统启动与初始化日志
            'request': 'request.log',    # 请求处理日志
            'error': 'error.log',        # 错误与异常日志
            'database': 'database.log',  # 数据库操作日志
            'business': 'business.log',  # 业务逻辑处理日志
            'performance': 'performance.log'  # 性能监控日志
        }
        
        # 日志记录器字典
        self.loggers = {}
        
        # 初始化所有日志记录器
        self._init_loggers()
    
    def _init_loggers(self):
        """初始化所有日志记录器"""
        for category, filename in self.log_categories.items():
            logger = logging.getLogger(category)
            logger.setLevel(logging.DEBUG)
            
            # 避免重复添加处理器
            if logger.handlers:
                continue
            
            # 创建文件处理器，使用时间轮转
            log_path = self.log_dir / filename
            handler = TimedRotatingFileHandler(
                filename=str(log_path),
                when='midnight',  # 每天凌晨轮转
                interval=1,        # 间隔1天
                backupCount=7,      # 保留7天的日志
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(handler)

            # 控制台输出
            logging.StreamHandler()
            
            # 保存日志记录器
            self.loggers[category] = logger
    
    def get_logger(self, category):
        """
        获取指定分类的日志记录器
        :param category: 日志分类
        :return: 日志记录器
        """
        if category not in self.loggers:
            # 如果分类不存在，创建新的日志记录器
            logger = logging.getLogger(category)
            logger.setLevel(logging.DEBUG)
            
            # 创建文件处理器
            log_path = self.log_dir / f"{category}.log"
            handler = TimedRotatingFileHandler(
                filename=str(log_path),
                when='midnight',
                interval=1,
                backupCount=7,
                encoding='utf-8'
            )
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(handler)
            
            # 保存日志记录器
            self.loggers[category] = logger
        
        return self.loggers[category]
    
    # 系统日志方法
    def system(self, message, level=logging.INFO):
        """系统启动与初始化日志"""
        logger = self.get_logger('system')
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)
        elif level == logging.CRITICAL:
            logger.critical(message)
    
    # 请求日志方法
    def request(self, message, level=logging.INFO):
        """请求处理日志"""
        logger = self.get_logger('request')
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)
        elif level == logging.CRITICAL:
            logger.critical(message)
    
    # 错误日志方法
    def error(self, message, exc_info=False, level=logging.ERROR):
        """错误与异常日志"""
        logger = self.get_logger('error')
        if level == logging.ERROR:
            logger.error(message, exc_info=exc_info)
        elif level == logging.CRITICAL:
            logger.critical(message, exc_info=exc_info)
    
    # 数据库日志方法
    def database(self, message, level=logging.INFO):
        """数据库操作日志"""
        logger = self.get_logger('database')
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)
    
    # 业务日志方法
    def business(self, message, level=logging.INFO):
        """业务逻辑处理日志"""
        logger = self.get_logger('business')
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)
    
    # 性能日志方法
    def performance(self, message, level=logging.INFO):
        """性能监控日志"""
        logger = self.get_logger('performance')
        if level == logging.DEBUG:
            logger.debug(message)
        elif level == logging.INFO:
            logger.info(message)
        elif level == logging.WARNING:
            logger.warning(message)
        elif level == logging.ERROR:
            logger.error(message)

# 创建全局日志实例
logger = Logger()

if __name__ == "__main__":
    # 测试日志功能
    logger.system("系统启动成功")
    logger.request("收到API请求: /api/login")
    logger.error("发生错误: 数据库连接失败")
    logger.database("执行SQL: SELECT * FROM users")
    logger.business("用户注册成功: user123")
    logger.performance("API响应时间: 120ms")
    
    # 测试异常日志
    try:
        1 / 0
    except Exception as e:
        logger.error(f"发生异常: {e}", exc_info=True)
    
    print("日志测试完成，查看logs目录下的日志文件")

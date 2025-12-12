# time_tool.py
from datetime import datetime

def get_current_time():
    """获取当前时间"""
    return f"当前时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"
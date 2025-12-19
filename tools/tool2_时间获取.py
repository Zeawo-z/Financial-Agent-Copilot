from langchain_core.tools import tool
from datetime import datetime
import pytz

# 🔥 核心修改：加一个 text: str = ""
# 这样无论 Agent 传进来 "" 还是什么都不传，函数都能接住，不会报错
@tool
def get_current_time(text: str = ""):
    """
    获取当前系统时间。
    """
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    return f"当前时间是：{now.strftime('%Y-%m-%d %H:%M:%S')} (星期{now.isoweekday()})"
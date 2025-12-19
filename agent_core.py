import asyncio
from typing import AsyncIterable, Any, Union

from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool, render_text_description
from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ⬇️ 核心修复：导入必要的格式化工具和链式工具
from langchain.agents.format_scratchpad import format_log_to_str
from langchain_core.runnables import RunnablePassthrough
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain_core.agents import AgentAction, AgentFinish

# 导入工具函数
from tools.tool1_天气查询 import get_weather
from tools.tool2_时间获取 import get_current_time
from tools.tool4_finance import get_stock_data
from tools.tool5_rag import knowledge_base_tool as rag_tool_func
from datetime import datetime
import pytz
load_dotenv()


# ==========================================
# 1. 定义工具 (保持不变)
# ==========================================
class StockInput(BaseModel):
    ticker: str = Field(description="股票代码...")


class SearchInput(BaseModel):
    query: str = Field(description="查询关键词")


class WeatherInput(BaseModel):
    city: str = Field(description="城市名称...")


@tool("stock_tool", args_schema=StockInput)
def stock_tool(ticker: str):
    """
    查询股票的实时价格、市值、PE等基本面数据。
    如果不知道代码，请先使用 search_tool 查询。
    """
    return get_stock_data(ticker)


search = DuckDuckGoSearchRun()


@tool("search_tool", args_schema=SearchInput)
def search_tool(query: str):
    """
    用于搜索互联网上的实时信息：
    1. 股票代码（如'茅台 股票代码'）
    2. 近期财经新闻（如'Tesla latest news'）
    3. 通用知识查询
    """
    return search.run(query)


@tool("weather_tool", args_schema=WeatherInput)
def weather_tool(city: str):
    """
    获取指定城市的实时天气信息。
    输入参数为城市名称（如'杭州'）。
    """
    return get_weather(city)


@tool("time_tool")
def time_tool(any_text: str = ""):
    """
    获取当前系统时间。无需输入参数。
    """
    # 解释：
    # 1. Agent 会传 "" (空字符串)。
    # 2. 我们定义参数 any_text 为 str 类型。
    # 3. str 对 str，类型完美匹配，Pydantic 闭嘴。
    # 4. 我们在函数里直接无视这个参数。

    try:
        tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(tz)
        return f"当前时间是：{now.strftime('%Y-%m-%d %H:%M:%S')} (星期{now.isoweekday()})"
    except Exception as e:
        return f"获取时间失败: {e}"

knowledge_base_tool = rag_tool_func

tools = [weather_tool, time_tool, search_tool, stock_tool, knowledge_base_tool]
tool_names = [t.name for t in tools]


# ==========================================
# 2. 自定义宽容解析器 (保持不变)
# ==========================================
class LooseReActParser(ReActSingleInputOutputParser):
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            return super().parse(text)
        except Exception:
            return AgentFinish(
                return_values={"output": text.strip()},
                log=text
            )


# ==========================================
# 3. 记忆管理
# ==========================================
store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


# ==========================================
# 4. Agent 初始化 (🔥 核心修复区域)
# ==========================================
global_agent = None


def init_agent(model_name="qwen-plus", system_prompt=None):
    global global_agent

    # 1. 设置 Prompt
    base_template = """
【工具能力】
你可以使用以下工具：
{tools}

【思考流程】
1. 闲聊 (如"你好") -> 直接回答，不要用 Action。
2. 任务 (如"查天气") -> 使用 ReAct 格式：
   Thought: 思考...
   Action: 工具名 (必须是 [{tool_names}] 之一)
   Action Input: 参数
   Observation: ...

开始！

Question: {input}
{agent_scratchpad}
    """

    if system_prompt:
        final_template = f"【系统设定】：{system_prompt}\n\n" + base_template
    else:
        final_template = "你是一位全能智能助手。\n\n" + base_template

    prompt = PromptTemplate.from_template(final_template).partial(
        tools=render_text_description(tools),
        tool_names=", ".join([t.name for t in tools])
    )

    # 2. 初始化 LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.1,
        streaming=True,
        max_retries=3,
        model_kwargs={
            "stop": ["\nObservation:", "Observation:"]
        }
    )

    # 3. 🔥 构建 Agent 链 (修复了 missing variable 问题)
    # RunnablePassthrough.assign 负责把 intermediate_steps 转换成 agent_scratchpad
    agent = (
            RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_log_to_str(x["intermediate_steps"])
            )
            | prompt
            | llm
            | LooseReActParser()
    )

    # 4. 创建执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5
    )

    # 5. 记忆功能
    agent_with_history = RunnableWithMessageHistory(
        agent_executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    global_agent = agent_with_history
    print(f"🔄 Agent 已更新 | 模型: {model_name}")
    return agent_with_history


# ==========================================
# 5. 辅助函数
# ==========================================
init_agent()


def update_agent_settings(model, prompt):
    init_agent(model_name=model, system_prompt=prompt)
    return f"Agent 已更新为 {model}"


async def get_stream_response(query: str, session_id: str) -> AsyncIterable[str]:
    try:
        async for event in global_agent.astream_events(
                {"input": query},
                config={"configurable": {"session_id": session_id}},
                version="v1",
        ):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield content
    except Exception as e:
        yield f"Final Answer: 发生错误: {str(e)}"
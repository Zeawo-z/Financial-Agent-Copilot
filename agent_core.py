import asyncio
from typing import AsyncIterable, Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.tools import tool, render_text_description
from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.pydantic_v1 import BaseModel,Field
from langchain.callbacks.base import AsyncCallbackHandler

from dotenv import load_dotenv
from tools.tool1_天气查询 import get_weather
from tools.tool2_时间获取 import get_current_time
from tools.tool4_finance import get_stock_data

load_dotenv()

# 此处的大模型不是简单的云端调用
# 而是需要封装工具，也就是 Agent = LLM + Tools
# REACT Reasoning-->Action-->Observation
# 注册工具
class StockInput(BaseModel):
    ticker: str = Field(
        description="股票代码。美股直接用代码(如AAPL)，A股需加后缀(如600519.SS表示茅台)，港股加后缀(如00700.HK)。")
class SearchInput(BaseModel):
    query: str = Field(description="搜索引擎的查询关键词")
@tool("stock_tool",args_schema=StockInput)
def stock_tool(ticker:str):
    """
    查询股票的实时价格、市值、PE等基本面数据。
    如果不知道代码，请先使用 search_tool 查询。
    """
    return get_stock_data(ticker)

search = DuckDuckGoSearchRun()
@tool("search_tool", args_schema=SearchInput)
def search_tool(query: str):
    """
    用于搜索：
    1. 股票代码（如'茅台 股票代码'）
    2. 近期财经新闻（如'Tesla latest news'）
    """
    return search.run(query)
class WeatherInput(BaseModel):
    # Field 里的 description 非常重要，大模型是看这个来理解参数含义的
    city: str = Field(description="需要查询天气的城市名称，例如：杭州、北京、上海")

@tool("weather_tool", args_schema=WeatherInput)
def weather_tool(city: str):
    """获取指定城市的实时天气信息。输入参数为城市名称（如'杭州'）。"""
    print(f"🕵️ [Agent Action] 正在调用高德API查询: {city}")
    return get_weather(city)

@tool
def time_tool():
    """获取当前系统时间。无需输入参数。"""
    return get_current_time()

tools = [weather_tool, time_tool, search_tool,stock_tool]
tool_names = [t.name for t in tools]

# 初始化LLM

template = """
你是一位资深的华尔街金融分析师。你的目标是利用工具回答用户的金融问题。

你可以使用的工具如下：
{tools}

请严格按照以下格式进行思考和回答（不要遗漏任何步骤）：

Question: 用户输入的问题
Thought: 我应该思考接下来做什么
Action: 工具名称，必须是 [{tool_names}] 中的一个
Action Input: 工具的输入参数
Observation: 工具返回的结果
... (Thought/Action/Action Input/Observation 这个过程可以重复多次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终回答（请使用Markdown格式，包含【数据概览】【分析】【建议】）

开始！

Question: {input}
Thought:{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)
# 1. 把工具列表转换成字符串描述 (例如: "weather: 获取天气...")
#tools_text = render_text_description(tools)

# 2. 把工具名字列表转换成逗号分隔的字符串 (例如: "weather, search")
#tool_names_str = ", ".join([t.name for t in tools])

# 3. 填充模板
#prompt = PromptTemplate.from_template(template).partial(
#    tools=tools_text,           # 传入字符串
#    tool_names=tool_names_str,  # 传入字符串
#)

llm = ChatOpenAI(
    model="Qwen/Qwen3-8B",
    temperature=0.1,
    streaming=True
)
# 创建智能体REACT-Agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt,
    #stop_sequence=["\nObservation:"]
)

# 初始化Agent执行器
agent_executor=AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)
# 记忆管理
store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


agent_with_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


# 流式生成器
async def get_stream_response(query: str, session_id: str) -> AsyncIterable[str]:
    """
    流式输出。
    注意：ReAct Agent 的输出比较复杂。
    如果想让用户看到 'Thought' (思考过程)，可以放宽过滤条件。
    如果只想让用户看到 'Final Answer'，则只过滤 Final Answer。
    """
    try:
        async for event in agent_with_history.astream_events(
                {"input": query},
                config={"configurable": {"session_id": session_id}},
                version="v1",
        ):
            kind = event["event"]

            # 1. 捕获 LLM 的输出流
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # 这里的 content 包含了 Thought, Action, Final Answer 所有内容
                    # 直接 yield 出去，用户就能看到 AI "一边思考一边打字" 的效果
                    yield content

    except Exception as e:
        yield f"发生错误: {str(e)}"
import streamlit as st
import requests
import uuid
import yfinance as yf
import pandas as pd
import re

# 1. 页面配置
st.set_page_config(page_title="智能助手 Pro", page_icon="🤖", layout="wide")

# 2. 初始化 Session
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "history" not in st.session_state:
    st.session_state.history = []


def clear_history():
    st.session_state.history = []
    st.session_state.session_id = str(uuid.uuid4())


# 后端地址
BACKEND_URL = "http://127.0.0.1:8000"

# 3. 侧边栏
with st.sidebar:
    st.title("🎛️ 智能体控制台")
    st.markdown(f"当前会话: `{st.session_state.session_id}`")

    with st.expander("🛠️ 模型配置", expanded=True):
        model_options = ["qwen-plus", "qwen-turbo", "glm-4-flash", "deepseek-chat"]
        selected_model = st.selectbox("选择模型", model_options)
        system_prompt = st.text_area("系统提示词", value="你是一位全能智能助手。", height=100)

        if st.button("🔄 更新 Agent 配置"):
            try:
                res = requests.post(f"{BACKEND_URL}/update_config", json={
                    "model": selected_model,
                    "system_prompt": system_prompt
                })
                if res.status_code == 200:
                    st.success("配置已生效！")
            except Exception as e:
                st.error(f"连接失败: {e}")

    with st.expander("📚 知识库管理", expanded=False):
        uploaded_file = st.file_uploader("上传 PDF", type=["pdf"])
        if uploaded_file and st.button("📂 上传"):
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            requests.post(f"{BACKEND_URL}/upload", files=files)
            st.success("上传成功")

    st.divider()
    st.subheader("📈 市场观察")
    ticker_input = st.text_input("输入股票代码", value="AAPL")
    if st.button("生成K线图"):
        try:
            with st.spinner("正在加载数据..."):
                # 获取历史数据
                stock = yf.Ticker(ticker_input)
                # 获取最近 3 个月数据
                hist = stock.history(period="3mo")

                if not hist.empty:
                    st.success(f"{ticker_input} 近3个月走势")
                    # Streamlit 自带的折线图，非常丝滑
                    st.line_chart(hist['Close'])

                    # 显示涨跌幅
                    current = hist['Close'].iloc[-1]
                    start = hist['Close'].iloc[0]
                    delta = ((current - start) / start) * 100
                    st.metric("区间涨跌幅", f"{delta:.2f}%", f"{current:.2f}")
                else:
                    st.error("未获取到数据，请检查代码是否正确")
        except Exception as e:
            st.error(f"绘图失败: {e}")

    st.divider()
    st.button("🗑️ 清空记录", on_click=clear_history)
    check_stream = st.checkbox("流式输出", value=True)

# 4. 主界面
st.title("🤖 智能助手")

for role, msg in st.session_state.history:
    avatar = "🧑‍💻" if role == "human" else "🤖"
    st.chat_message(role, avatar=avatar).markdown(msg)


# ==========================================
# 🔥 核心：强力清洗函数
# ==========================================
def parse_agent_output(text):
    """
    将后端返回的混合文本拆分为 (思考过程, 最终答案)
    """
    # 1. 优先尝试寻找标准的 "Final Answer:" 分界线
    split_pattern = r"(?i)Final\s*Answer\s*[:：]|Answer\s*[:：]|回答\s*[:：]"
    match = re.search(split_pattern, text)
    if match:
        thought = text[:match.start()].strip()
        answer = text[match.end():].strip()
        return thought, answer

    # 2. 如果没找到 Final Answer，尝试切除 ReAct 的技术日志
    # 优化正则：不再贪婪地吃掉 Action Input 后的所有内容
    # 逻辑：找到 "Action Input:"，只吃掉它前面的部分，保留后面的内容作为潜在答案

    # 查找最后一次出现的 Action Input
    action_input_pattern = r"(?i)Action\s*Input\s*[:：]"
    matches = list(re.finditer(action_input_pattern, text))

    if matches:
        last_match = matches[-1]
        # split_point 是 "Action Input:" 这个词结束的位置
        split_point = last_match.end()

        # 提取 "Action Input:" 之后的内容
        potential_answer = text[split_point:].strip()

        # 简单的启发式规则：
        # 如果 Action Input 后面跟着的内容很短（比如只是个城市名 "杭州"），那它可能是参数，不是答案，我们把它归为思考。
        # 如果内容很长（比如 "现在是2025年..."），那它大概率是模型偷懒直接给出的答案。
        if len(potential_answer) > 20:  # 阈值设为 20 个字符
            thought = text[:split_point].strip()
            answer = potential_answer
            return thought, answer

        # 否则，按照老规矩，把整行都当成思考（配合换行符）
        react_end_pattern = r"Thought:[\s\S]*?Action\s*Input\s*[:：].*?(\n|$)"
        match = re.search(react_end_pattern, text)
        if match:
            return text[:match.end()].strip(), text[match.end():].strip()

    # 3. 如果既没 Final Answer 也没 Thought，那全是答案 (比如闲聊)
    if not text.strip().startswith("Thought:"):
        return "", text

    # 4. 兜底：如果是纯思考，但流已经结束了（在外部调用逻辑中处理），这里暂且返回原样
    return text, ""


# 5. 输入处理逻辑
if prompt := st.chat_input("请输入问题..."):
    st.session_state.history.append(("human", prompt))
    st.chat_message("human", avatar="🧑‍💻").markdown(prompt)

    with st.chat_message("ai", avatar="🤖"):
        # 状态框
        status_box = st.status("🤔 智能体正在思考...", expanded=True)
        with status_box:
            thought_placeholder = st.empty()

        answer_placeholder = st.empty()
        full_buffer = ""
        final_answer_text = ""

        try:
            payload = {"query": prompt, "session_id": st.session_state.session_id}

            with requests.post(f"{BACKEND_URL}/chat", json=payload, stream=True) as r:
                if r.status_code == 200:
                    if check_stream:
                        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                            if chunk:
                                full_buffer += chunk

                                # 🔥 调用清洗函数
                                thought, answer = parse_agent_output(full_buffer)

                                # 更新 UI
                                if thought:
                                    thought_placeholder.markdown(thought)

                                if answer:
                                    # 一旦有了答案，就把思考框关掉
                                    status_box.update(label="✅ 思考完毕", state="complete", expanded=False)
                                    answer_placeholder.markdown(answer + "▌")
                                    final_answer_text = answer
                                else:
                                    # 还没答案，说明还在想
                                    status_box.update(label="🤔 智能体正在思考...", state="running", expanded=True)

                        # 循环结束
                        # 再次清洗，确保最终结果正确
                        thought, answer = parse_agent_output(full_buffer)
                        if not answer and full_buffer and not thought:
                            # 兜底：如果全是答案
                            answer = full_buffer

                        answer_placeholder.markdown(answer)
                        status_box.update(label="✅ 完成", state="complete", expanded=False)
                        st.session_state.history.append(("ai", answer))

                    else:
                        st.markdown(r.text)
                else:
                    st.error(f"错误: {r.text}")

        except Exception as e:
            status_box.update(label="❌ 错误", state="error")
            st.error(f"连接失败: {e}")
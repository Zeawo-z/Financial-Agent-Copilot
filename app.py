import streamlit as st
import requests
import uuid
import yfinance as yf
import pandas as pd

# 1. 页面配置必须是第一个 Streamlit 命令
st.set_page_config(page_title="智能助手 Pro", page_icon="🤖")

# ==========================================
# 2. 核心修复：必须最先初始化 Session State
# ==========================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "history" not in st.session_state:
    st.session_state.history = []


# ==========================================
# 3. 定义回调函数
# ==========================================
def clear_history():
    st.session_state.history = []
    # 重置会话ID
    st.session_state.session_id = str(uuid.uuid4())


# ==========================================
# 4. 页面布局代码
# ==========================================

# --- 侧边栏 ---
with st.sidebar:
    st.title("🛠️ 市场观察")
    st.write("在下方输入代码查看走势图")
    # 默认给个AAPL
    ticker_input = st.text_input("输入股票代码", value="AAPL")
    # 现在这里绝对不会报错了，因为 session_id 已经在第2步初始化了
    st.markdown(f"当前会话 ID:\n`{st.session_state.session_id}`")

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

    st.button("🗑️ 清空历史记录", on_click=clear_history)
    check_stream = st.checkbox("是否流式输出", value=True)
    st.info("本项目基于 ReAct 范式构建，支持天气查询、联网搜索等工具调用。")

# --- 主界面 ---
st.title("🤖 私人智能助手")

# 渲染历史消息
for role, msg in st.session_state.history:
    avatar = "🧑‍💻" if role == "human" else "🤖"
    st.chat_message(role, avatar=avatar).markdown(msg)

# 输入框
if prompt := st.chat_input("请输入你的问题（例如：杭州天气怎么样？）"):
    # 1. 显示用户输入
    st.session_state.history.append(("human", prompt))
    st.chat_message("human", avatar="🧑‍💻").markdown(prompt)

    # 2. 请求后端并流式显示
    with st.chat_message("ai", avatar="🤖"):
        placeholder = st.empty()
        full_response = ""
        placeholder.markdown("🤔 正在思考并调用工具...")

        try:
            # 确保你的后端地址和端口正确
            backend_url = "http://127.0.0.1:8000/chat"
            payload = {
                "query": prompt,
                "session_id": st.session_state.session_id
            }

            with requests.post(backend_url, json=payload, stream=True) as r:
                if r.status_code == 200:
                    # --- 核心修改开始 ---

                    # 1. 创建一个“状态容器”用来显示思考过程 (默认展开)
                    # state="running" 会显示一个转圈圈的动画
                    status_box = st.status("🤔 智能体正在思考...", expanded=True)

                    # 在状态容器里创建一个占位符，专门打印 Thought 和 Action
                    with status_box:
                        thought_placeholder = st.empty()

                    # 2. 在外面创建一个占位符，专门打印最终回答
                    answer_placeholder = st.empty()

                    full_buffer = ""  # 用于累积所有接收到的字符
                    final_answer = ""  # 用于存储最终答案部分
                    is_thinking = True  # 标记当前是否还在思考阶段

                    if check_stream:
                        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                            if chunk:
                                full_buffer += chunk

                                # 核心逻辑：检测是否出现了 "Final Answer:" 分界线
                                if is_thinking:
                                    # 如果还没找到分界线，就把所有内容都显示在“思考框”里
                                    if "Final Answer:" in full_buffer:
                                        is_thinking = False  # 切换状态

                                        # 1. 拆分：前面是思考，后面是正文
                                        parts = full_buffer.split("Final Answer:")
                                        thought_content = parts[0]
                                        final_answer = parts[1]  # 把刚才多读进来的那一点点正文存起来

                                        # 2. 更新思考框的内容（定格）
                                        thought_placeholder.markdown(thought_content)

                                        # 3. 改变思考框的状态：标记为完成，并自动折叠收起！
                                        status_box.update(label="✅ 思考完毕", state="complete", expanded=False)

                                        # 4. 开始在外面显示正文
                                        answer_placeholder.markdown(final_answer)
                                    else:
                                        # 没找到分界线，继续在思考框里打印
                                        thought_placeholder.markdown(full_buffer + "▌")
                                else:
                                    # 已经是回答阶段了
                                    # 这里的 chunk 属于正文，我们需要把它拼接到 final_answer 里
                                    # 注意：此时 full_buffer 还在变大，但我们只需要 split 后的第二部分
                                    parts = full_buffer.split("Final Answer:")
                                    if len(parts) > 1:
                                        final_answer = parts[1]
                                        answer_placeholder.markdown(final_answer + "▌")

                        # 循环结束，把最后的光标去掉
                        answer_placeholder.markdown(final_answer)

                        # 存入历史记录时，只存最终答案，不存思考过程（让历史记录更干净）
                        st.session_state.history.append(("ai", final_answer))

                    else:
                        # 非流式处理（逻辑类似，只是不循环）
                        text = r.text
                        parts = text.split("Final Answer:")
                        if len(parts) > 1:
                            with status_box:
                                st.markdown(parts[0])
                            status_box.update(label="✅ 思考完毕", state="complete", expanded=False)
                            st.markdown(parts[1])
                            st.session_state.history.append(("ai", parts[1]))
                        else:
                            st.markdown(text)
                            st.session_state.history.append(("ai", text))

                    # --- 核心修改结束 ---
                else:
                    st.error(f"请求失败: {r.status_code}")
        except Exception as e:
            st.error(f"无法连接到后端服务器: {str(e)}")
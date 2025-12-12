from langchain_community.tools import DuckDuckGoSearchRun
search_engine = DuckDuckGoSearchRun()

def web_search(query: str):
    """联网搜索"""
    try:
        return search_engine.run(query)
    except Exception as e:
        return f"搜索失败: {str(e)}"

if __name__ == "__main__":
    search_result = web_search("特朗普与马斯克的冲突")
    print(search_result)

    search_result = web_search("浙江农林大学智科专业怎么样？")
    print(search_result)
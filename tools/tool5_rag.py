import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.tools import tool


# ==========================================
# 1. 使用类作为容器，彻底避免 NameError
# ==========================================
class RAGStorage:
    """
    一个简单的容器类，用来存放向量库和模型。
    这样 Python 永远能通过 RAGStorage.vector_store 找到它。
    """
    vector_store = None
    embeddings = None
    db_path = "faiss_index_db"


# ==========================================
# 2. 核心逻辑函数
# ==========================================

def get_embeddings():
    """获取或初始化 Embedding 模型"""
    if RAGStorage.embeddings is None:
        print("🚀 正在初始化 Embedding 模型...")
        try:
            RAGStorage.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception as e:
            print(f"❌ Embedding 加载失败: {e}")
            raise e
    return RAGStorage.embeddings


def load_vector_store():
    """尝试加载知识库"""
    # 1. 如果内存里已经有了，直接返回
    if RAGStorage.vector_store is not None:
        return RAGStorage.vector_store

    # 2. 如果硬盘上有存档，加载它
    if os.path.exists(RAGStorage.db_path):
        print(f"📂 检测到本地存档 {RAGStorage.db_path}，正在加载...")
        try:
            emb = get_embeddings()
            RAGStorage.vector_store = FAISS.load_local(
                RAGStorage.db_path,
                emb,
                allow_dangerous_deserialization=True
            )
            print("✅ 知识库加载成功！")
            return RAGStorage.vector_store
        except Exception as e:
            print(f"⚠️ 加载存档失败: {e}")
            return None
    return None


def initialize_knowledge_base(file_path):
    """构建并保存知识库"""
    try:
        emb = get_embeddings()
        print(f"📄 处理文件: {file_path}...")

        loader = PyPDFLoader(file_path)
        docs = loader.load()

        if not docs:
            return False

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)

        print("🧠 构建 FAISS 索引...")
        # 直接存入类属性中
        RAGStorage.vector_store = FAISS.from_documents(splits, emb)

        print(f"💾 保存到硬盘...")
        RAGStorage.vector_store.save_local(RAGStorage.db_path)

        print("✅ 知识库处理完毕！")
        return True
    except Exception as e:
        print(f"❌ 构建失败: {e}")
        return False


# ==========================================
# 3. 工具定义
# ==========================================

@tool("knowledge_base_tool")
def knowledge_base_tool(query: str):
    """
    只有当用户询问关于'上传文档'、'知识库'、'这篇报告'或'文件'相关内容时，才使用此工具。
    """
    # 1. 自动尝试加载
    db = load_vector_store()

    if db is None:
        return "当前知识库为空。请先上传 PDF 文档。"

    try:
        # 2. 检索
        retriever = db.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(query)

        if not docs:
            return "知识库里没找到相关信息。"

        # 3. 结果拼接
        context = "\n\n".join([d.page_content for d in docs])
        return f"【从文档中搜索到的内容】：\n{context}"
    except Exception as e:
        return f"检索时发生错误: {str(e)}"
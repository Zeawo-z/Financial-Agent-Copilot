import shutil
import os
from fastapi import FastAPI,Body,UploadFile,File,HTTPException
from fastapi.responses import StreamingResponse
from agent_core import get_stream_response,global_agent,update_agent_settings
from tools.tool5_rag import initialize_knowledge_base

# 初始化FasrAPI应用
app = FastAPI(title="Smart Agent API",description="基于langChain的智能体服务")
"""
FastAPI默认会将路径参数或者查询参数作为函数参数，
但是在前端UI界面我们使用requests库请求后端服务网址的时候
传参传的是JSON数据，所以使用Body()来接收
"""
# 1. 聊天接口
@app.post("/chat")
async def chat(
    query: str = Body(..., title="用户问题"),
    session_id: str = Body(..., title="会话ID")
):
    """
    流式对话接口
    """
    return StreamingResponse(
        get_stream_response(query, session_id),
        media_type="text/event-stream"
    )
# 2. Agent 配置更新接口 (多模型 & 提示词管理)
@app.post("/update_config")
async def update_config(
    model: str = Body(..., embed=True, description="模型名称，如 Qwen/Qwen3-8B"),
    system_prompt: str = Body(..., embed=True, description="自定义系统提示词")
):
    """
    动态更新 Agent 的底层模型和人设
    """
    try:
        print(f"正在更新配置: Model={model}, Prompt长度={len(system_prompt)}")
        msg = update_agent_settings(model, system_prompt)
        return {"message": msg, "status": "success"}
    except Exception as e:
        print(f"配置更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. 知识库文件上传接口 (RAG)
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传 PDF 文件并构建向量知识库
    """
    # 1. 创建临时目录保存上传的文件
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    file_path = os.path.join(temp_dir, file.filename)

    try:
        # 2. 将上传的文件写入硬盘
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"文件已保存至: {file_path}")

        # 3. 调用 RAG 工具进行初始化 (切分 -> 向量化 -> 存库)
        success = initialize_knowledge_base(file_path)

        if success:
            return {"message": f"文件 '{file.filename}' 已成功加载入知识库！", "status": "success"}
        else:
            # 如果构建失败，返回 500 错误
            raise HTTPException(status_code=500, detail="知识库构建失败，请检查后端日志")

    except Exception as e:
        print(f"上传处理出错: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
    finally:
        # 可选：处理完后是否删除临时文件？
        # 为了演示 RAG 效果，建议保留，或者由 initialize_knowledge_base 内部处理持久化
        pass
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app)
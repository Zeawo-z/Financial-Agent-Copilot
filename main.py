from fastapi import FastAPI,Body
from fastapi.responses import StreamingResponse
from agent_core import get_stream_response

# 初始化FasrAPI应用
app = FastAPI(title="Smart Agent API")
@app.get("/")
async def root():
    return {"status": "running", "message": "Welcome to Smart Agent API"}


"""
FastAPI默认会将路径参数或者查询参数作为函数参数，
但是在前端UI界面我们使用requests库请求后端服务网址的时候
传参传的是JSON数据，所以使用Body()来接收
"""
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
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app)
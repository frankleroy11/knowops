# 中文导读：
# 本地开发启动入口：监听回环地址并启用热重载
# 此入口只启动 API，不会自动启动数据库、Milvus 或 Celery Worker

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8010, reload=True)

#!/usr/bin/env python3
"""
ShitSpace Mirror Backend - 启动入口

使用方法:
    python main.py

或者直接使用 uvicorn:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

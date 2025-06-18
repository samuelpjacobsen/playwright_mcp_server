import asyncio
import json
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from server_playwright import PlaywrightEngine
import os

app = FastAPI(title="Playwright MCP Server SSE", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

playwright_engine = PlaywrightEngine()

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "playwright-mcp-server-sse"}

@app.get("/sse")
async def sse_endpoint():
    """Endpoint SSE para N8N MCP Client"""
    
    async def event_stream():
        try:
            server_info = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "playwright-server",
                        "version": "1.0.0"
                    }
                }
            }
            yield f"data: {json.dumps(server_info)}\n\n"
            
            tools_response = {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "navigate",
                            "description": "Navigate to a URL",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string", "description": "URL to navigate to"}
                                },
                                "required": ["url"]
                            }
                        },
                        {
                            "name": "take_screenshot",
                            "description": "Take a screenshot",
                            "inputSchema": {
                                "type": "object", 
                                "properties": {
                                    "path": {"type": "string", "description": "Screenshot path"}
                                }
                            }
                        },
                        {
                            "name": "get_page_content",
                            "description": "Get current page content",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
            yield f"data: {json.dumps(tools_response)}\n\n"
            
            counter = 0
            while True:
                await asyncio.sleep(30)
                heartbeat = {
                    "type": "ping",
                    "timestamp": counter
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                counter += 1
                
        except asyncio.CancelledError:
            print("🔌 Stream SSE cancelado pelo cliente")
        except Exception as e:
            print(f"❌ Erro no stream SSE: {e}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/mcp")
async def mcp_endpoint(data: dict):
    """Endpoint principal para comandos MCP"""
    print(f"🔧 Comando MCP: {data}")
    
    try:
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")
        
        if method == "initialize":
            playwright_engine.initialized = True
            result = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                        "roots": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "playwright-server", 
                        "version": "1.0.0"
                    },
                    "instructions": "Playwright MCP Server ready for automation tasks"
                }
            }
            return result
        
        elif method == "tools/list":
            tools = [
                {
                    "name": "navigate",
                    "description": "Navigate to a URL",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"}
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "take_screenshot",
                    "description": "Take a screenshot",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Screenshot path"}
                        }
                    }
                },
                {
                    "name": "click",
                    "description": "Click on element",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "get_page_content",
                    "description": "Get page content", 
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools}
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            print(f"🛠️ Executando ferramenta: {tool_name} com args: {arguments}")
            
            await playwright_engine.ensure_browser_ready()
            
            if tool_name == "navigate":
                result = await playwright_engine.navigate(arguments["url"])
            elif tool_name == "take_screenshot":
                result = await playwright_engine.take_screenshot(arguments.get("path", "screenshot.png"))
            elif tool_name == "click":
                result = await playwright_engine.click(arguments["selector"])
            elif tool_name == "type_text":
                result = await playwright_engine.type_text(arguments["selector"], arguments["text"])
            elif tool_name == "get_page_content":
                result = await playwright_engine.get_page_content()
            else:
                raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
            
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": result[0].text}]}
            }
            print(f"✅ Resultado: {result[0].text}")
            return response
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
            
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {"code": -32603, "message": str(e)}
        }
        print(f"❌ Erro: {e}")
        return error_response

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Playwright MCP Server SSE",
        "version": "1.0.0",
        "endpoints": {
            "sse": "/sse",
            "mcp": "/mcp",
            "health": "/health"
        },
        "n8n_compatible": True,
        "status": "ready"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print("🚀 Iniciando Playwright MCP Server SSE...")
    print(f"📡 SSE endpoint: http://{host}:{port}/sse")
    print(f"🔧 MCP endpoint: http://{host}:{port}/mcp")
    uvicorn.run(app, host=host, port=port, log_level="info")
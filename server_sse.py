import asyncio
import json
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from server import PlaywrightMCPServer
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities

class PlaywrightMCPServerSSE(PlaywrightMCPServer):
    """Versão SSE do servidor MCP para N8N"""
    
    def __init__(self):
        from mcp.server import Server
        self.server = Server("playwright-server")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.setup_handlers()
        self.initialized = False

app = FastAPI(title="Playwright MCP Server SSE", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

server_instance = PlaywrightMCPServerSSE()

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "playwright-mcp-server-sse"}

@app.get("/sse")
async def sse_endpoint():
    """Endpoint SSE para N8N MCP Client"""
    
    async def event_stream():
        """Stream de eventos SSE"""
        try:
            init_event = {
                "type": "init",
                "data": {
                    "server": "playwright-mcp-server",
                    "version": "1.0.0",
                    "capabilities": ["navigate", "screenshot", "click", "type", "content"]
                }
            }
            yield f"data: {json.dumps(init_event)}\n\n"
            
            tools_event = {
                "type": "tools",
                "data": [
                    {"name": "navigate", "description": "Navigate to URL"},
                    {"name": "take_screenshot", "description": "Take screenshot"},
                    {"name": "click", "description": "Click element"},
                    {"name": "type_text", "description": "Type text"},
                    {"name": "get_page_content", "description": "Get page content"}
                ]
            }
            yield f"data: {json.dumps(tools_event)}\n\n"
            
            counter = 0
            while True:
                await asyncio.sleep(10)
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": counter,
                    "status": "alive",
                    "server": "playwright-mcp"
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                counter += 1
                
                print(f"📡 SSE Heartbeat enviado: {counter}")
                
        except asyncio.CancelledError:
            print("🔌 Stream SSE cancelado pelo cliente")
        except Exception as e:
            print(f"❌ Erro no stream SSE: {e}")
            error_event = {
                "type": "error",
                "message": str(e)
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
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

@app.post("/sse")
async def sse_post_endpoint(data: dict):
    """Endpoint POST SSE para enviar comandos"""
    print(f"📥 Comando recebido: {data}")
    try:
        return {"status": "success", "data": data, "processed": True}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/mcp")
async def mcp_endpoint(data: dict):
    """Endpoint principal para comandos MCP"""
    print(f"🔧 Comando MCP: {data}")
    
    try:
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")
        
        if method == "initialize":
            server_instance.initialized = True
            result = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "playwright-server", "version": "1.0.0"}
                }
            }
            print(f"✅ Initialize: {result}")
            return result
        
        elif method == "tools/list":
            if not server_instance.initialized:
                raise HTTPException(status_code=400, detail="Server not initialized")
            
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
                }
            ]
            
            result = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools}
            }
            print(f"📋 Tools list: {len(tools)} ferramentas")
            return result
        
        elif method == "tools/call":
            if not server_instance.initialized:
                raise HTTPException(status_code=400, detail="Server not initialized")
            
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            print(f"🛠️ Executando ferramenta: {tool_name} com args: {arguments}")
            
            await server_instance.ensure_browser_ready()
            
            if tool_name == "navigate":
                result = await server_instance.navigate(arguments["url"])
            elif tool_name == "take_screenshot":
                result = await server_instance.take_screenshot(arguments.get("path"))
            elif tool_name == "click":
                result = await server_instance.click(arguments["selector"])
            elif tool_name == "type_text":
                result = await server_instance.type_text(arguments["selector"], arguments["text"])
            elif tool_name == "get_page_content":
                result = await server_instance.get_page_content()
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
            "sse": "/sse (GET para stream, POST para comandos)",
            "mcp": "/mcp (comandos MCP principais)",
            "health": "/health"
        },
        "n8n_compatible": True,
        "status": "ready"
    }

if __name__ == "__main__":
    print("🚀 Iniciando Playwright MCP Server SSE...")
    print("📡 SSE endpoint: http://0.0.0.0:9000/sse")
    print("🔧 MCP endpoint: http://0.0.0.0:9000/mcp")
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
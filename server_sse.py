import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from server_playwright import PlaywrightEngine

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
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "playwright-mcp-server-sse",
        "port": os.getenv("PORT", "unknown"),
        "host": os.getenv("HOST", "unknown"),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    port = os.getenv("PORT", "unknown")
    host = os.getenv("HOST", "0.0.0.0")
    
    return {
        "service": "Playwright MCP Server SSE",
        "version": "1.0.0",
        "status": "running",
        "port": port,
        "host": host,
        "endpoints": {
            "health": "/health",
            "sse": "/sse", 
            "mcp": "/mcp"
        },
        "mcp_compatible": True,
        "playwright_ready": playwright_engine.initialized
    }

@app.post("/mcp")
async def mcp_endpoint(data: dict):
    """Main MCP endpoint"""
    print(f"📨 MCP Request: {json.dumps(data, indent=2)}")
    
    try:
        method = data.get("method")
        params = data.get("params", {})
        msg_id = data.get("id")
        
        print(f"🎯 Method: {method}, ID: {msg_id}")
        
        if method == "initialize":
            print("🚀 Initializing MCP server...")
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
                    "instructions": "Playwright MCP Server ready for browser automation"
                }
            }
            playwright_engine.initialized = True
            print("✅ MCP server initialized successfully")
            return result
        
        elif method == "tools/list":
            print("📋 Listing available tools...")
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
                    "description": "Take a screenshot of current page",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Screenshot filename", "default": "screenshot.png"}
                        }
                    }
                },
                {
                    "name": "click",
                    "description": "Click on an element",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "type_text",
                    "description": "Type text into an element",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector"},
                            "text": {"type": "string", "description": "Text to type"}
                        },
                        "required": ["selector", "text"]
                    }
                },
                {
                    "name": "get_page_content",
                    "description": "Get current page HTML content",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
            
            result = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools}
            }
            print(f"✅ Listed {len(tools)} tools")
            return result
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            print(f"🔧 Calling tool: {tool_name}")
            print(f"📝 Arguments: {arguments}")
            
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
                "result": {
                    "content": [{"type": "text", "text": result[0].text}]
                }
            }
            
            print(f"✅ Tool result: {result[0].text}")
            return response
        
        else:
            print(f"❌ Unknown method: {method}")
            raise HTTPException(status_code=400, detail=f"Unknown method: {method}")
            
    except Exception as e:
        print(f"❌ Error processing MCP request: {e}")
        import traceback
        traceback.print_exc()
        
        error_response = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "error": {
                "code": -32603,
                "message": str(e),
                "data": {"type": type(e).__name__}
            }
        }
        return error_response

@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint for streaming"""
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
            
            counter = 0
            while True:
                await asyncio.sleep(30)
                heartbeat = {
                    "type": "heartbeat",
                    "counter": counter,
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                counter += 1
                
        except asyncio.CancelledError:
            print("🔌 SSE connection cancelled")
        except Exception as e:
            print(f"❌ SSE error: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("🚀 INICIANDO PLAYWRIGHT MCP SERVER SSE")
    print("=" * 50)
    print(f"🌐 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"📡 Health: http://{host}:{port}/health")
    print(f"🔧 MCP: http://{host}:{port}/mcp")
    print(f"📡 SSE: http://{host}:{port}/sse")
    print("=" * 50)
    
    print("🔧 ENVIRONMENT VARIABLES:")
    for key in ["PORT", "HOST", "DISPLAY", "COOLIFY_FQDN"]:
        value = os.getenv(key, "not set")
        print(f"   {key}: {value}")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host=host, 
        port=port, 
        log_level="info",
        access_log=True
    )
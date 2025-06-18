import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource, ServerCapabilities
import base64
import os
import time

class PlaywrightMCPServer:
    def __init__(self):
        self.server = Server("playwright-server")
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all MCP handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="click",
                    description="Perform click on a web page element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the element to click"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="navigate",
                    description="Navigate to a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="take_screenshot",
                    description="Take a screenshot of the current page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to save screenshot"},
                            "full_page": {"type": "boolean", "description": "Capture full page", "default": False}
                        }
                    }
                ),
                Tool(
                    name="type_text",
                    description="Type text into an element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the element"},
                            "text": {"type": "string", "description": "Text to type"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["selector", "text"]
                    }
                ),
                Tool(
                    name="select_option",
                    description="Select an option in a dropdown",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the select element"},
                            "value": {"type": "string", "description": "Value to select"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["selector", "value"]
                    }
                ),
                Tool(
                    name="wait_for_selector",
                    description="Wait for an element to appear",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector to wait for"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="get_page_content",
                    description="Get the HTML content of the current page",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="close_browser",
                    description="Close the browser",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="open_new_tab",
                    description="Open a new tab",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to open in new tab"}
                        }
                    }
                ),
                Tool(
                    name="hover_mouse",
                    description="Hover over an element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the element"},
                            "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 30000}
                        },
                        "required": ["selector"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                await self.ensure_browser_ready()
                
                if name == "navigate":
                    return await self.navigate(arguments["url"], arguments.get("timeout", 30000))
                elif name == "click":
                    return await self.click(arguments["selector"], arguments.get("timeout", 30000))
                elif name == "take_screenshot":
                    return await self.take_screenshot(arguments.get("path"), arguments.get("full_page", False))
                elif name == "type_text":
                    return await self.type_text(arguments["selector"], arguments["text"], arguments.get("timeout", 30000))
                elif name == "select_option":
                    return await self.select_option(arguments["selector"], arguments["value"], arguments.get("timeout", 30000))
                elif name == "wait_for_selector":
                    return await self.wait_for_selector(arguments["selector"], arguments.get("timeout", 30000))
                elif name == "get_page_content":
                    return await self.get_page_content()
                elif name == "close_browser":
                    return await self.close_browser()
                elif name == "open_new_tab":
                    return await self.open_new_tab(arguments.get("url"))
                elif name == "hover_mouse":
                    return await self.hover_mouse(arguments["selector"], arguments.get("timeout", 30000))
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
    async def ensure_browser_ready(self):
        """Ensure browser is ready for use"""
        try:
            if not self.playwright:
                print("🚀 Iniciando Playwright...")
                self.playwright = await async_playwright().start()
                
            if not self.browser:
                print("🌐 Lançando Chromium...")
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-features=TranslateUI',
                        '--disable-web-security',
                        '--no-first-run',
                        '--disable-default-apps'
                    ]
                )
                
            if not self.context:
                print("📱 Criando contexto do browser...")
                self.context = await self.browser.new_context()
                
            if not self.page:
                print("📄 Abrindo nova página...")
                self.page = await self.context.new_page()
                
            print("✅ Browser pronto para uso!")
            
        except Exception as e:
            print(f"❌ Erro ao preparar browser: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    async def navigate(self, url: str, timeout: int = 30000) -> List[TextContent]:
        """Navigate to a URL"""
        try:
            await self.page.goto(url, timeout=timeout)
            return [TextContent(type="text", text=f"Successfully navigated to {url}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to navigate to {url}: {str(e)}")]
    
    async def click(self, selector: str, timeout: int = 30000) -> List[TextContent]:
        """Click on an element"""
        try:
            await self.page.click(selector, timeout=timeout)
            return [TextContent(type="text", text=f"Successfully clicked on {selector}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to click on {selector}: {str(e)}")]
    
    async def take_screenshot(self, path: str = "screenshot.png") -> List[TextContent]:
        """Take a screenshot"""
        try:
            await self.ensure_browser_ready()
            
            if not self.page:
                return [TextContent(type="text", text="Failed to initialize browser for screenshot")]
                
            screenshot_path = f"/app/screenshots/{path}"
            await self.page.screenshot(path=screenshot_path)
            
            import os
            if os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                return [TextContent(type="text", text=f"Screenshot saved to {path} ({file_size} bytes)")]
            else:
                return [TextContent(type="text", text=f"Screenshot file not found at {screenshot_path}")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to take screenshot: {str(e)}")]
    
    async def type_text(self, selector: str, text: str, timeout: int = 30000) -> List[TextContent]:
        """Type text into an element"""
        try:
            await self.page.type(selector, text, timeout=timeout)
            return [TextContent(type="text", text=f"Successfully typed '{text}' into {selector}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to type into {selector}: {str(e)}")]
    
    async def select_option(self, selector: str, value: str, timeout: int = 30000) -> List[TextContent]:
        """Select an option in a dropdown"""
        try:
            await self.page.select_option(selector, value, timeout=timeout)
            return [TextContent(type="text", text=f"Successfully selected '{value}' in {selector}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to select option in {selector}: {str(e)}")]
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> List[TextContent]:
        """Wait for an element to appear"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return [TextContent(type="text", text=f"Element {selector} appeared")]
        except Exception as e:
            return [TextContent(type="text", text=f"Element {selector} did not appear: {str(e)}")]
    
    async def get_page_content(self) -> List[TextContent]:
        """Get the current page content"""
        try:
            await self.ensure_browser_ready()
            
            if not self.page:
                return [TextContent(type="text", text="Failed to initialize browser for content extraction")]
                
            content = await self.page.content()
            if len(content) > 5000:
                content = content[:5000] + "... (content truncated)"
                
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to get page content: {str(e)}")]
    
    async def close_browser(self) -> List[TextContent]:
        """Close the browser"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            return [TextContent(type="text", text="Browser closed successfully")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to close browser: {str(e)}")]
    
    async def open_new_tab(self, url: Optional[str] = None) -> List[TextContent]:
        """Open a new tab"""
        try:
            new_page = await self.context.new_page()
            if url:
                await new_page.goto(url)
            self.page = new_page
            return [TextContent(type="text", text=f"New tab opened{' and navigated to ' + url if url else ''}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to open new tab: {str(e)}")]
    
    async def hover_mouse(self, selector: str, timeout: int = 30000) -> List[TextContent]:
        """Hover over an element"""
        try:
            await self.page.hover(selector, timeout=timeout)
            return [TextContent(type="text", text=f"Successfully hovered over {selector}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to hover over {selector}: {str(e)}")]

async def main():
    """Main function to run the MCP server"""
    server_instance = PlaywrightMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="playwright-server",
                server_version="1.0.0",
                capabilities=ServerCapabilities(
                    tools={}
                )
            )
        )

if __name__ == "__main__":
    print("Servidor MCP iniciado")
    asyncio.run(main())
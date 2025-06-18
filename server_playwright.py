from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from mcp.types import TextContent
import asyncio

class PlaywrightEngine:
    """Engine Playwright puro - sem dependências do MCP server"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.initialized = False
    
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
                        '--disable-features=TranslateUI,VizDisplayCompositor',
                        '--disable-web-security',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--disable-background-networking',
                        '--disable-component-extensions-with-background-pages',
                        '--disable-client-side-phishing-detection',
                        '--disable-hang-monitor',
                        '--disable-prompt-on-repost',
                        '--disable-ipc-flooding-protection',
                        '--force-color-profile=srgb',
                        '--memory-pressure-off',
                        '--max_old_space_size=4096'
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
    
    async def navigate(self, url: str, timeout: int = 60000) -> List[TextContent]:
        """Navigate to a URL"""
        try:
            await self.page.goto(url, timeout=timeout, wait_until="networkidle")
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
            screenshot_path = f"/app/screenshots/{path}"
            
            await self.page.screenshot(
                path=screenshot_path, 
                full_page=True,
                type='png',
                quality=80
            )
            
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
    
    async def get_page_content(self) -> List[TextContent]:
        """Get the current page content"""
        try:
            content = await self.page.content()
            if len(content) > 5000:
                content = content[:5000] + "... (content truncated)"
                
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to get page content: {str(e)}")]
    
    async def close_browser(self) -> List[TextContent]:
        """Close the browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            
            return [TextContent(type="text", text="Browser closed successfully")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to close browser: {str(e)}")]
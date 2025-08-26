import os
import re
import aiohttp
import asyncio
import json
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import zipfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
from config import API_ID, API_HASH, BOT_TOKEN
from fake_useragent import UserAgent
import aiofiles
from typing import Optional, List, Dict, Set
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the app and user clients
app = Client(
    "app_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Directory to save the downloaded files temporarily
DOWNLOAD_DIRECTORY = "./downloads/"
TEMP_DIRECTORY = "./temp/"

# Ensure directories exist
for directory in [DOWNLOAD_DIRECTORY, TEMP_DIRECTORY]:
    if not os.path.exists(directory):
        os.makedirs(directory)

@dataclass
class ScrapingConfig:
    """Configuration for scraping parameters"""
    img_flag: bool = True
    css_flag: bool = True
    js_flag: bool = True
    font_flag: bool = True
    video_flag: bool = False
    audio_flag: bool = False
    use_js_rendering: bool = True
    max_retries: int = 3
    timeout: int = 30
    concurrent_downloads: int = 10
    use_proxy: bool = False
    follow_redirects: bool = True

class AdvancedWebScraper:
    """Professional website scraper with multiple engines and anti-detection"""
    
    def __init__(self, config: ScrapingConfig = None):
        self.config = config or ScrapingConfig()
        self.soup = None
        self.session = None
        self.ua = UserAgent()
        self.semaphore = asyncio.Semaphore(self.config.concurrent_downloads)
        
        # Comprehensive file extensions
        self.extensions = {
            'css': ['.css', '.scss', '.sass', '.less'],
            'js': ['.js', '.mjs', '.jsx', '.ts', '.tsx'],
            'img': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp'],
            'font': ['.woff', '.woff2', '.ttf', '.otf', '.eot'],
            'video': ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.flv'],
            'audio': ['.mp3', '.wav', '.ogg', '.aac', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.xml', '.json']
        }
        
        # Proxy list (add your proxies here)
        self.proxies = [
            # "http://proxy1:port",
            # "http://proxy2:port",
        ]
        
        # Common headers for different browsers
        self.headers_templates = {
            'chrome': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            },
            'firefox': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Upgrade-Insecure-Requests': '1'
            }
        }

    def get_random_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid detection"""
        template = random.choice(list(self.headers_templates.values()))
        headers = template.copy()
        headers['User-Agent'] = self.ua.random
        return headers

    def get_proxy(self) -> Optional[str]:
        """Get a random proxy if available"""
        if self.config.use_proxy and self.proxies:
            return random.choice(self.proxies)
        return None

    async def create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with optimized settings"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=False
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.get_random_headers()
        )

    async def fetch_with_retry(self, url: str, retries: int = None) -> Optional[bytes]:
        """Fetch URL with retry mechanism and exponential backoff"""
        retries = retries or self.config.max_retries
        
        for attempt in range(retries):
            try:
                async with self.semaphore:
                    proxy = self.get_proxy()
                    
                    async with self.session.get(
                        url, 
                        proxy=proxy,
                        allow_redirects=self.config.follow_redirects
                    ) as response:
                        if response.status == 200:
                            return await response.read()
                        elif response.status == 429:  # Rate limited
                            await asyncio.sleep(2 ** attempt)
                            continue
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
                continue
                
        return None

    async def render_js_content(self, url: str) -> Optional[str]:
        """Render JavaScript content using playwright (if available)"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set random user agent
                await page.set_user_agent(self.ua.random)
                
                # Navigate and wait for network idle
                await page.goto(url, wait_until='networkidle')
                
                # Wait for potential dynamic content
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                await browser.close()
                
                return content
                
        except ImportError:
            logger.warning("Playwright not installed. Falling back to basic scraping.")
            return None
        except Exception as e:
            logger.error(f"JS rendering failed: {str(e)}")
            return None

    async def scrape_with_selenium(self, url: str) -> Optional[str]:
        """Alternative scraping using selenium"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'--user-agent={self.ua.random}')
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            content = driver.page_source
            driver.quit()
            
            return content
            
        except ImportError:
            logger.warning("Selenium not installed.")
            return None
        except Exception as e:
            logger.error(f"Selenium scraping failed: {str(e)}")
            return None

    def get_file_type(self, url: str) -> str:
        """Determine file type based on URL and extension"""
        parsed_url = urlparse(url.lower())
        path = parsed_url.path
        
        for file_type, extensions in self.extensions.items():
            if any(path.endswith(ext) for ext in extensions):
                return file_type
                
        return 'other'

    def should_download_resource(self, url: str, resource_type: str) -> bool:
        """Determine if a resource should be downloaded based on config"""
        type_flags = {
            'css': self.config.css_flag,
            'js': self.config.js_flag,
            'img': self.config.img_flag,
            'font': self.config.font_flag,
            'video': self.config.video_flag,
            'audio': self.config.audio_flag
        }
        
        return type_flags.get(resource_type, True)

    async def save_page(self, url: str, page_folder: str = 'page') -> Optional[str]:
        """Main method to save webpage with all resources"""
        try:
            # Ensure the URL has a scheme
            if not urlparse(url).scheme:
                url = "https://" + url

            self.session = await self.create_session()
            
            try:
                # Try multiple scraping methods
                content = None
                
                # Method 1: Basic HTTP request
                response = await self.fetch_with_retry(url)
                if response:
                    content = response.decode('utf-8', errors='ignore')
                
                # Method 2: JavaScript rendering (if enabled and basic method failed)
                if not content and self.config.use_js_rendering:
                    content = await self.render_js_content(url)
                
                # Method 3: Selenium fallback
                if not content:
                    content = await self.scrape_with_selenium(url)
                
                if not content:
                    raise Exception("Failed to fetch content with all methods")

                self.soup = BeautifulSoup(content, "html.parser")
                
                # Create directory structure
                if not os.path.exists(page_folder):
                    os.makedirs(page_folder)
                
                # Create subdirectories for different resource types
                subdirs = ['css', 'js', 'images', 'fonts', 'media', 'other']
                for subdir in subdirs:
                    subdir_path = os.path.join(page_folder, subdir)
                    if not os.path.exists(subdir_path):
                        os.makedirs(subdir_path)
                
                # Download all resources concurrently
                tasks = []
                
                # CSS files
                if self.config.css_flag:
                    tasks.extend(self._create_download_tasks(url, page_folder, 'link', 'href', 'css'))
                
                # JavaScript files
                if self.config.js_flag:
                    tasks.extend(self._create_download_tasks(url, page_folder, 'script', 'src', 'js'))
                
                # Images
                if self.config.img_flag:
                    tasks.extend(self._create_download_tasks(url, page_folder, 'img', 'src', 'images'))
                    tasks.extend(self._create_download_tasks(url, page_folder, 'source', 'srcset', 'images'))
                
                # Fonts and other resources
                tasks.extend(self._find_additional_resources(url, page_folder))
                
                # Execute all download tasks
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Save the main HTML file with updated paths
                html_file_path = os.path.join(page_folder, 'index.html')
                async with aiofiles.open(html_file_path, 'w', encoding='utf-8') as file:
                    await file.write(self.soup.prettify())
                
                # Create metadata file
                await self._create_metadata_file(url, page_folder)
                
                # Create zip file
                zip_path = self._create_zip_file(page_folder, url)
                return zip_path
                
            finally:
                await self.session.close()
                
        except Exception as e:
            logger.error(f"save_page() failed: {str(e)}")
            return None

    def _create_download_tasks(self, base_url: str, page_folder: str, tag: str, attr: str, resource_type: str) -> List:
        """Create download tasks for specific resource types"""
        tasks = []
        
        for element in self.soup.find_all(tag):
            if element.has_attr(attr):
                attr_value = element.get(attr)
                if attr_value:
                    # Handle srcset attribute specially
                    if attr == 'srcset':
                        urls = self._parse_srcset(attr_value)
                        for url in urls:
                            tasks.append(self._download_resource_task(base_url, url, page_folder, element, attr, resource_type))
                    else:
                        tasks.append(self._download_resource_task(base_url, attr_value, page_folder, element, attr, resource_type))
        
        return tasks

    def _parse_srcset(self, srcset: str) -> List[str]:
        """Parse srcset attribute to extract URLs"""
        urls = []
        parts = srcset.split(',')
        for part in parts:
            url = part.strip().split()[0]
            if url:
                urls.append(url)
        return urls

    def _find_additional_resources(self, base_url: str, page_folder: str) -> List:
        """Find additional resources in CSS files and inline styles"""
        tasks = []
        
        # Find resources in inline styles
        for element in self.soup.find_all(attrs={"style": True}):
            style = element.get('style')
            urls = re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', style)
            for url in urls:
                resource_type = self.get_file_type(url)
                subdir = self._get_subdir_for_type(resource_type)
                tasks.append(self._download_resource_task(base_url, url, page_folder, element, 'style', subdir))
        
        return tasks

    def _get_subdir_for_type(self, resource_type: str) -> str:
        """Get subdirectory name for resource type"""
        type_mapping = {
            'css': 'css',
            'js': 'js',
            'img': 'images',
            'font': 'fonts',
            'video': 'media',
            'audio': 'media'
        }
        return type_mapping.get(resource_type, 'other')

    async def _download_resource_task(self, base_url: str, resource_url: str, page_folder: str, element, attr: str, resource_type: str):
        """Download a single resource"""
        try:
            # Skip data URLs and already processed resources
            if resource_url.startswith('data:') or resource_url.startswith('#'):
                return
            
            # Create absolute URL
            absolute_url = urljoin(base_url, resource_url)
            
            # Determine file type and check if should download
            file_type = self.get_file_type(absolute_url)
            if not self.should_download_resource(absolute_url, file_type):
                return
            
            # Generate filename
            parsed_url = urlparse(absolute_url)
            filename = os.path.basename(parsed_url.path) or 'index.html'
            filename = re.sub(r'[^\w\-_\.]', '_', filename)
            
            # Ensure filename has extension
            if '.' not in filename:
                filename += self._get_extension_for_type(file_type)
            
            # Create subdir path
            subdir = self._get_subdir_for_type(file_type)
            file_path = os.path.join(page_folder, subdir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                return
            
            # Download the resource
            content = await self.fetch_with_retry(absolute_url)
            if content:
                async with aiofiles.open(file_path, 'wb') as file:
                    await file.write(content)
                
                # Update the element's attribute to point to local file
                local_path = os.path.join(subdir, filename)
                if attr == 'style':
                    # Update inline style
                    style = element.get('style')
                    updated_style = style.replace(resource_url, local_path)
                    element['style'] = updated_style
                else:
                    element[attr] = local_path
                    
        except Exception as e:
            logger.error(f"Failed to download resource {resource_url}: {str(e)}")

    def _get_extension_for_type(self, file_type: str) -> str:
        """Get default extension for file type"""
        extensions = {
            'css': '.css',
            'js': '.js',
            'img': '.jpg',
            'font': '.woff2',
            'video': '.mp4',
            'audio': '.mp3'
        }
        return extensions.get(file_type, '.txt')

    async def _create_metadata_file(self, url: str, page_folder: str):
        """Create metadata file with scraping information"""
        metadata = {
            "url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "img_flag": self.config.img_flag,
                "css_flag": self.config.css_flag,
                "js_flag": self.config.js_flag,
                "font_flag": self.config.font_flag,
                "use_js_rendering": self.config.use_js_rendering
            },
            "stats": await self._get_scraping_stats(page_folder)
        }
        
        metadata_path = os.path.join(page_folder, 'metadata.json')
        async with aiofiles.open(metadata_path, 'w') as file:
            await file.write(json.dumps(metadata, indent=2))

    async def _get_scraping_stats(self, page_folder: str) -> Dict:
        """Get statistics about scraped content"""
        stats = {
            "total_files": 0,
            "file_types": {},
            "total_size": 0
        }
        
        for root, dirs, files in os.walk(page_folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    stats["total_files"] += 1
                    stats["total_size"] += file_size
                    stats["file_types"][file_ext] = stats["file_types"].get(file_ext, 0) + 1
        
        return stats

    def _create_zip_file(self, folder_path: str, url: str) -> str:
        """Create zip file from the scraped content"""
        sanitized_url = re.sub(r'[^\w\-_\.]', '_', urlparse(url).netloc)
        timestamp = int(time.time())
        zip_name = f"scraped_{sanitized_url}_{timestamp}.zip"
        zip_path = os.path.join(DOWNLOAD_DIRECTORY, zip_name)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=folder_path)
                    zipf.write(file_path, arcname)
        
        return zip_path

    def cleanup_folder(self, folder_path: str):
        """Clean up temporary folder"""
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
        except Exception as e:
            logger.error(f"Failed to cleanup folder {folder_path}: {str(e)}")

# ThreadPoolExecutor instance for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=5)


async def advanced_download_web_source(client: Client, message: Message):
    """Advanced web source download with professional features"""
    command_parts = message.text.split()

    if len(command_parts) <= 1:
        await message.reply_text(
            "**❌ Provide at least one URL.**\n\n"
            "**Usage Examples:**\n"
            "`/ws https://example.com` - Basic scraping\n"
            "`/ws https://example.com --js` - Enable JS rendering\n"
            "`/ws https://example.com --no-images` - Skip images\n"
            "`/ws https://example.com --full` - Download everything",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return

    url = command_parts[1]
    
    # Parse additional flags
    config = ScrapingConfig()
    
    if "--js" in command_parts:
        config.use_js_rendering = True
    if "--no-images" in command_parts:
        config.img_flag = False
    if "--no-css" in command_parts:
        config.css_flag = False
    if "--no-js" in command_parts:
        config.js_flag = False
    if "--full" in command_parts:
        config.video_flag = True
        config.audio_flag = True
    if "--proxy" in command_parts:
        config.use_proxy = True

    # Enhanced progress message
    progress_msg = await message.reply_text(
        "**🚀 Advanced Web Scraper Initiated**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "**📊 Status:** Analyzing website...\n"
        "**🔍 Engine:** Multi-engine scraper\n"
        "**⚡️ Mode:** Production ready\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

    try:
        # Update progress
        await progress_msg.edit_text(
            "**🚀 Advanced Web Scraper Initiated**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "**📊 Status:** Downloading resources...\n"
            "**🔍 Engine:** Multi-engine scraper\n"
            "**⚡️ Mode:** Production ready\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

        # Create scraper instance
        scraper = AdvancedWebScraper(config)
        page_folder = os.path.join(TEMP_DIRECTORY, f"scraped_{int(time.time())}")
        
        # Download the webpage
        zip_path = await scraper.save_page(url, page_folder)

        if zip_path and os.path.exists(zip_path):
            # Update progress
            await progress_msg.edit_text(
                "**🚀 Advanced Web Scraper Initiated**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "**📊 Status:** Packaging results...\n"
                "**🔍 Engine:** Multi-engine scraper\n"
                "**⚡️ Mode:** Production ready\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

            # Get file stats
            file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
            
            # Create enhanced caption
            if message.chat.type in [ChatType.SUPERGROUP, ChatType.GROUP]:
                user_info = f"[{message.chat.title}](https://t.me/{message.chat.username})" if message.chat.username else message.chat.title
            else:
                user_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
                user_info = f"[{user_name}](https://t.me/{message.from_user.username})" if message.from_user.username else user_name

            caption = (
                f"**🌐 Advanced Website Source Code**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"**🔗 Website:** `{url}`\n"
                f"**📦 Package Size:** {file_size:.2f} MB\n"
                f"**🛠️ Engine:** Multi-method scraper\n"
                f"**📂 Contents:** HTML, CSS, JS, Images, Fonts\n"
                f"**⚙️ Features:** Anti-detection, Retry logic\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"**👤 Requested by:** {user_info}\n"
                f"**⏰ Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Send the file
            await client.send_document(
                chat_id=message.chat.id,
                document=zip_path,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )

            # Cleanup
            try:
                os.remove(zip_path)
                scraper.cleanup_folder(page_folder)
            except Exception as cleanup_error:
                logger.error(f"Cleanup failed: {str(cleanup_error)}")

        else:
            await message.reply_text(
                "**❌ Scraping Failed**\n\n"
                "The website might be:\n"
                "• Protected by anti-bot measures\n"
                "• Requiring authentication\n"
                "• Temporarily unavailable\n"
                "• Using advanced protection\n\n"
                "Try using different flags or contact support.",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

    except Exception as e:
        error_msg = (
            f"**❌ Scraping Error Encountered**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"**Error:** {str(e)[:100]}...\n"
            f"**Suggestion:** Try with different parameters\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        logger.error(f"Scraping failed for {url}: {str(e)}")

    finally:
        # Delete progress message
        try:
            await progress_msg.delete()
        except:
            pass


@app.on_message(filters.command(["ws", "scrape"], prefixes=["/", "."]) & (filters.private | filters.group))
async def ws_command(client: Client, message: Message):
    """Handle web scraping command with advanced features"""
    asyncio.create_task(advanced_download_web_source(client, message))

@app.on_message(filters.command(["start"], prefixes=["/", "."]) & filters.private)
async def start_command(client: Client, message: Message):
    """Enhanced start command with detailed bot information"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Update Channel", url="https://t.me/BillaSpace"), 
         InlineKeyboardButton("🤚🏻 Backup Channel", url="https://t.me/Billa_Space")],
        [InlineKeyboardButton("👮🏻‍♂️ Proof Channel", url="https://t.me/Proofchannelch"), 
         InlineKeyboardButton("My Dev👨‍💻", user_id=5960968099)]
    ])
    
    await message.reply_text(
        text="**🚀 Professional Website Scraper Bot**\n\n"
             "**🔥 Advanced Features:**\n"
             "• Multi-engine scraping (HTTP, JS, Selenium)\n"
             "• Anti-detection mechanisms\n"
             "• Proxy support & user-agent rotation\n"
             "• Concurrent downloads\n"
             "• Retry logic with exponential backoff\n"
             "• Complete resource extraction\n\n"
             "**📖 Usage Examples:**\n"
             "`/ws https://example.com` - Basic scraping\n"
             "`/ws https://example.com --js` - Enable JS rendering\n"
             "`/ws https://example.com --no-images` - Skip images\n"
             "`/ws https://example.com --full` - Download everything\n"
             "`/ws https://example.com --proxy` - Use proxy\n\n"
             "**🛡️ Production Ready Features:**\n"
             "• Rate limiting protection\n"
             "• Comprehensive error handling\n"
             "• Resource optimization\n"
             "• Metadata generation\n\n"
             "Stay updated with our channels:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@app.on_message(filters.command(["help", "commands"], prefixes=["/", "."]))
async def help_command(client: Client, message: Message):
    """Help command with detailed usage instructions"""
    help_text = (
        "**🔧 Advanced Scraper Commands & Flags**\n\n"
        "**Basic Usage:**\n"
        "`/ws <url>` - Scrape website with default settings\n\n"
        "**Available Flags:**\n"
        "• `--js` - Enable JavaScript rendering\n"
        "• `--no-images` - Skip image downloads\n"
        "• `--no-css` - Skip CSS files\n"
        "• `--no-js` - Skip JavaScript files\n"
        "• `--full` - Download videos & audio too\n"
        "• `--proxy` - Use proxy servers\n\n"
        "**Examples:**\n"
        "`/ws https://spa-website.com --js`\n"
        "`/ws https://blog.com --no-images`\n"
        "`/ws https://site.com --full --proxy`\n\n"
        "**Supported Resources:**\n"
        "✅ HTML, CSS, JavaScript\n"
        "✅ Images (JPG, PNG, SVG, WebP)\n"
        "✅ Fonts (WOFF, WOFF2, TTF)\n"
        "✅ Documents (PDF, JSON, XML)\n"
        "✅ Media files (with --full flag)\n\n"
        "**Bot Features:**\n"
        "🔄 Auto-retry on failures\n"
        "🛡️ Anti-detection measures\n"
        "⚡ Concurrent processing\n"
        "📊 Detailed metadata\n"
        "🗜️ Optimized compression"
    )
    
    await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

if __name__ == "__main__":
    print("🚀 Starting Professional Website Scraper Bot...")
    print("🔥 Features: Multi-engine, Anti-detection, Production Ready")
    app.run()

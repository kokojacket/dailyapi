from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
import aiohttp
import json
import random
import os
from urllib.parse import urlparse
from typing import Dict, Any, List

@register("dailyapi", "koko", "日常API服务插件", "1.0.0")
class DailyApiPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        # 使用AstrBot的配置系统
        self.config = config or {}
        logger.info(f"[配置] 配置内容: {self.config}")

    async def initialize(self):
        """初始化插件"""
        logger.info("[初始化] DailyApiPlugin初始化完成")
        
        # 获取配置
        morning_news_config = self.config.get("morning_news", {})
        command = morning_news_config.get("command", "早报")
        enabled = morning_news_config.get("enabled", True)
        
        logger.info(f"[初始化] 早报触发命令: {command}, 功能状态: {'启用' if enabled else '禁用'}")
    
    @filter.on_text_message()
    async def on_message(self, event: AstrMessageEvent):
        """处理文本消息"""
        # 获取配置
        morning_news_config = self.config.get("morning_news", {})
        command = morning_news_config.get("command", "早报")
        enabled = morning_news_config.get("enabled", True)
        
        if not enabled:
            return
        
        message = event.message_str.strip()
        
        # 检查是否匹配早报命令
        if message == command:
            logger.info("[早报] 收到早报请求")
            result = await self.get_morning_news()
            
            # 检查结果是否为URL
            if self.is_valid_url(result):
                logger.info("[早报] 获取到图片URL: {}", result)
                image_content = await self.download_image(result)
                if image_content:
                    # 使用Image消息组件发送图片
                    yield event.chain_result([Comp.Image.fromBytes(image_content)])
                    event.stop_event()  # 停止事件传播
                    return
                # 如果图片下载失败，发送文本消息
                yield event.plain_result("获取早报图片失败，请稍后再试")
                event.stop_event()  # 停止事件传播
            else:
                # 发送文本消息
                yield event.plain_result(result)
                event.stop_event()  # 停止事件传播

    async def get_morning_news(self) -> str:
        """获取早报信息"""
        url = "http://api.suxun.site/api/sixs"
        
        logger.info("[早报] 开始请求API: {}", url)
        
        # 随机选择User-Agent
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': 'https://api.vvhan.com/'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as response:
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'image' in content_type:
                        # 直接返回图片URL
                        logger.info("[早报] 获取到图片URL: {}", response.url)
                        return str(response.url)
                    
                    # 尝试解析JSON
                    try:
                        morning_news_info = await response.json()
                        if isinstance(morning_news_info, dict) and morning_news_info.get('code') == '200':
                            # 返回图片URL
                            img_url = morning_news_info['image']
                            logger.info("[早报] 成功获取图片URL: {}", img_url)
                            return img_url
                    except:
                        logger.error("[早报] JSON解析失败")
                    
                    # 解析失败时返回错误信息
                    return '早报信息获取失败，请稍后再试'
        except Exception as e:
            logger.error(f"[早报] 请求失败: {str(e)}")
            return "获取早报失败，请稍后再试"

    def is_valid_url(self, url: str) -> bool:
        """检查是否为有效的URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    async def download_image(self, url: str) -> bytes:
        """下载图片内容"""
        logger.info("[图片下载] 开始下载图片: {}", url)
        
        # 随机生成User-Agent
        user_agent = random.choice(self.user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Referer': 'https://api.vvhan.com/'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        # 简单验证图片内容
                        if len(content) > 1024 and (content.startswith(b'\xff\xd8') or content.startswith(b'\x89PNG')):
                            logger.info("[图片下载] 下载成功，大小: {} bytes", len(content))
                            return content
                        logger.warning("[图片下载] 图片内容验证失败")
            # 下载失败返回None
            return None
        except Exception as e:
            logger.error(f"[图片下载] 下载失败: {str(e)}")
            return None

    async def terminate(self):
        """插件卸载时执行的操作"""
        logger.info("[终止] DailyApiPlugin已停用")

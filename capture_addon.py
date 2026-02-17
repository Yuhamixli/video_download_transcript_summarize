"""
mitmproxy addon: 拦截微信课程平台的视频资源
参考 res-downloader 的 QqPlugin 和 DefaultPlugin 逻辑
"""

import json
import re
import os
import hashlib
import time
from datetime import datetime
from mitmproxy import http, ctx

# 视频相关的 Content-Type
VIDEO_CONTENT_TYPES = [
    "video/mp4", "video/webm", "video/ogg", "video/avi",
    "video/x-flv", "video/x-matroska", "video/quicktime",
    "application/vnd.apple.mpegurl",  # m3u8
    "application/x-mpegURL",  # m3u8
    "video/MP2T",  # ts segments
]

# 视频 URL 模式
VIDEO_URL_PATTERNS = [
    r"\.mp4", r"\.m3u8", r"\.flv", r"\.ts\b",
    r"encfilekey=", r"finder\.video",
    r"mp\.weixin\.qq\.com.*?/mp/videoplayer",
    r"video\.qq\.com", r"livep\.l\.qq\.com",
    r"vod.*?\.myqcloud\.com",
    r"mpvideo\.qpic\.cn",
]

# 可能包含课程列表/视频信息的 API 模式
API_PATTERNS = [
    r"course", r"lesson", r"chapter", r"video.*list",
    r"catalog", r"content.*list", r"play.*url",
    r"media.*info", r"resource.*list",
]

CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "captured")
os.makedirs(CAPTURE_DIR, exist_ok=True)


class WeChatCourseCapture:
    """拦截并记录微信课程平台的所有视频资源和 API 请求"""

    def __init__(self):
        self.captured_videos = []
        self.captured_apis = []
        self.captured_all = []
        self.seen_urls = set()
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        ctx.log.info("=" * 60)
        ctx.log.info(" 微信课程视频捕获器已启动")
        ctx.log.info(" 请在微信中打开课程视频播放...")
        ctx.log.info("=" * 60)

    def _md5(self, s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()

    def _is_video_content_type(self, content_type: str) -> bool:
        if not content_type:
            return False
        ct = content_type.lower()
        return any(vt in ct for vt in VIDEO_CONTENT_TYPES)

    def _is_video_url(self, url: str) -> bool:
        return any(re.search(p, url, re.IGNORECASE) for p in VIDEO_URL_PATTERNS)

    def _is_api_url(self, url: str) -> bool:
        return any(re.search(p, url, re.IGNORECASE) for p in API_PATTERNS)

    def _save_capture(self):
        """保存捕获结果到 JSON 文件"""
        output = {
            "capture_time": self.start_time,
            "video_count": len(self.captured_videos),
            "api_count": len(self.captured_apis),
            "videos": self.captured_videos,
            "apis": self.captured_apis,
        }
        filepath = os.path.join(CAPTURE_DIR, f"capture_{self.start_time}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def _save_all_requests(self):
        """保存所有请求日志"""
        filepath = os.path.join(CAPTURE_DIR, f"all_requests_{self.start_time}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.captured_all, f, ensure_ascii=False, indent=2)

    def request(self, flow: http.HTTPFlow):
        """拦截请求阶段 - 参考 res-downloader 的 httpRequestEvent"""
        url = flow.request.pretty_url
        host = flow.request.pretty_host

        # 记录所有请求（用于调试分析）
        req_info = {
            "timestamp": time.time(),
            "method": flow.request.method,
            "url": url,
            "host": host,
            "path": flow.request.path,
            "content_type": flow.request.headers.get("content-type", ""),
        }

        # 检查是否是课程相关 API
        if self._is_api_url(url):
            req_info["type"] = "api"
            # 尝试捕获 POST body
            if flow.request.method == "POST" and flow.request.content:
                try:
                    body = flow.request.content.decode("utf-8", errors="replace")
                    req_info["request_body"] = body[:5000]
                except:
                    pass

        self.captured_all.append(req_info)

    def response(self, flow: http.HTTPFlow):
        """拦截响应阶段 - 参考 res-downloader 的 httpResponseEvent"""
        if not flow.response:
            return

        url = flow.request.pretty_url
        host = flow.request.pretty_host
        content_type = flow.response.headers.get("content-type", "")
        status = flow.response.status_code
        content_length = flow.response.headers.get("content-length", "0")

        # === 1. 检查视频 Content-Type ===
        if self._is_video_content_type(content_type):
            self._record_video(flow, "content-type", content_type)
            return

        # === 2. 检查 URL 模式是否匹配视频 ===
        if self._is_video_url(url):
            self._record_video(flow, "url-pattern", url)
            return

        # === 3. 检查 API 响应中的视频 URL ===
        if status == 200 and content_type and "json" in content_type.lower():
            self._check_api_response(flow)

        # === 4. 检查 HTML 响应中的视频元素 ===
        if status == 200 and content_type and "html" in content_type.lower():
            self._check_html_response(flow)

    def _record_video(self, flow: http.HTTPFlow, match_type: str, match_value: str):
        """记录发现的视频资源"""
        url = flow.request.pretty_url
        url_sign = self._md5(url)

        if url_sign in self.seen_urls:
            return
        self.seen_urls.add(url_sign)

        content_length = flow.response.headers.get("content-length", "unknown")
        content_type = flow.response.headers.get("content-type", "unknown")

        video_info = {
            "url": url,
            "url_sign": url_sign,
            "host": flow.request.pretty_host,
            "content_type": content_type,
            "content_length": content_length,
            "status": flow.response.status_code,
            "match_type": match_type,
            "match_value": match_value,
            "timestamp": time.time(),
            "request_headers": dict(flow.request.headers),
        }

        self.captured_videos.append(video_info)
        self._save_capture()

        # 醒目输出
        size_mb = "unknown"
        try:
            size_mb = f"{int(content_length) / 1024 / 1024:.2f}MB"
        except:
            pass

        ctx.log.info("=" * 60)
        ctx.log.info(f"[VIDEO #{len(self.captured_videos)}] 发现视频!")
        ctx.log.info(f"  URL: {url[:120]}...")
        ctx.log.info(f"  类型: {content_type}")
        ctx.log.info(f"  大小: {size_mb}")
        ctx.log.info(f"  匹配: {match_type}")
        ctx.log.info("=" * 60)

    def _check_api_response(self, flow: http.HTTPFlow):
        """检查 JSON API 响应中是否包含视频 URL"""
        url = flow.request.pretty_url
        try:
            body = flow.response.content
            if not body or len(body) > 5 * 1024 * 1024:
                return
            text = body.decode("utf-8", errors="replace")

            # 检查响应中是否包含视频相关信息
            has_video_ref = any(
                kw in text.lower()
                for kw in ["video_url", "videourl", "video_src", "play_url", "playurl",
                           "media_url", "mediaurl", ".mp4", ".m3u8", "mpvideo",
                           "finder.video", "encfilekey"]
            )

            if has_video_ref or self._is_api_url(url):
                api_info = {
                    "url": url,
                    "method": flow.request.method,
                    "status": flow.response.status_code,
                    "request_headers": dict(flow.request.headers),
                    "response_body": text[:10000],
                    "timestamp": time.time(),
                    "has_video_ref": has_video_ref,
                }

                # 捕获 POST body
                if flow.request.method == "POST" and flow.request.content:
                    try:
                        api_info["request_body"] = flow.request.content.decode(
                            "utf-8", errors="replace"
                        )[:5000]
                    except:
                        pass

                self.captured_apis.append(api_info)
                self._save_capture()

                ctx.log.info("=" * 60)
                ctx.log.info(f"[API #{len(self.captured_apis)}] 发现课程 API!")
                ctx.log.info(f"  URL: {url[:120]}")
                ctx.log.info(f"  方法: {flow.request.method}")
                ctx.log.info(f"  包含视频引用: {has_video_ref}")
                ctx.log.info("=" * 60)

        except Exception as e:
            pass

    def _check_html_response(self, flow: http.HTTPFlow):
        """检查 HTML 响应中是否包含视频元素"""
        try:
            body = flow.response.content
            if not body or len(body) > 2 * 1024 * 1024:
                return
            text = body.decode("utf-8", errors="replace")

            # 查找 <video> 标签、视频 src 属性等
            video_srcs = re.findall(
                r'(?:src|data-src|data-url)\s*=\s*["\']([^"\']*?(?:\.mp4|\.m3u8)[^"\']*)',
                text, re.IGNORECASE
            )

            if video_srcs:
                for src in video_srcs:
                    ctx.log.info(f"[HTML] 发现 HTML 中的视频源: {src[:100]}")
                    self.captured_apis.append({
                        "url": flow.request.pretty_url,
                        "type": "html_video_src",
                        "video_sources": video_srcs,
                        "timestamp": time.time(),
                    })
                self._save_capture()
        except:
            pass

    def done(self):
        """代理关闭时保存所有结果"""
        self._save_capture()
        self._save_all_requests()
        ctx.log.info(f"\n捕获完成: {len(self.captured_videos)} 个视频, "
                     f"{len(self.captured_apis)} 个 API")
        ctx.log.info(f"结果保存在: {CAPTURE_DIR}")


addons = [WeChatCourseCapture()]

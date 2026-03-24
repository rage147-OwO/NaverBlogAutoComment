import asyncio
import re
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Frame,
    Page,
    async_playwright,
)


class NaverBlog:
    """Playwright를 사용하여 네이버 블로그를 읽고 댓글을 달아줍니다."""

    def __init__(self, naver_id: str = None, naver_password: str = None):
        self.naver_id = naver_id
        self.naver_password = naver_password
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self, headless: bool = False):
        """브라우저를 시작합니다. 로그인 시 captcha/2FA 확인을 위해 기본값은 headless=False입니다."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self._context.new_page()

    async def login(self):
        """네이버 계정에 로그인합니다."""
        print("네이버 로그인 중...")
        await self.page.goto("https://nid.naver.com/nidlogin.login?mode=form")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)

        await self.page.fill("#id", self.naver_id)
        await asyncio.sleep(0.3)
        await self.page.fill("#pw", self.naver_password)
        await asyncio.sleep(0.3)
        await self.page.click(".btn_login")

        try:
            await self.page.wait_for_function(
                "!window.location.href.includes('nid.naver.com')",
                timeout=30000,
            )
            print("로그인 성공!")
        except Exception:
            if "nid.naver.com" in self.page.url:
                print("\n⚠️  추가 인증이 필요합니다 (캡챠 또는 2단계 인증).")
                print("브라우저에서 직접 인증을 완료해주세요.")
                input("인증 완료 후 Enter를 눌러주세요...")

    async def _get_frame(self) -> Frame:
        """mainFrame을 반환합니다. 없으면 기본 페이지를 반환합니다."""
        await asyncio.sleep(1)
        frame = self.page.frame("mainFrame")
        if frame:
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
        return frame or self.page

    async def get_posts(self, blog_id: str, count: int = 10) -> list[dict]:
        """블로그의 최근 포스트 목록을 가져옵니다."""
        print(f"포스트 목록 가져오는 중: blog.naver.com/{blog_id}")

        await self.page.goto(f"https://blog.naver.com/{blog_id}")
        await self.page.wait_for_load_state("networkidle", timeout=15000)

        frame = await self._get_frame()
        await asyncio.sleep(2)

        posts = []
        seen = set()
        pattern = re.compile(rf"(?:blog\.naver\.com)?/{re.escape(blog_id)}/(\d{{9,15}})")

        links = await frame.query_selector_all("a")
        for link in links:
            try:
                href = await link.get_attribute("href") or ""
                match = pattern.search(href)
                if not match:
                    continue

                log_no = match.group(1)
                if log_no in seen:
                    continue

                title = (await link.inner_text()).strip()
                if not title or len(title) < 2 or title.isdigit():
                    continue

                seen.add(log_no)
                posts.append({"log_no": log_no, "title": title})

                if len(posts) >= count:
                    break
            except Exception:
                continue

        # 링크에서 못 찾으면 페이지 소스에서 logNo 추출
        if not posts:
            posts = await self._extract_posts_from_source(blog_id, count)

        print(f"  → {len(posts)}개의 포스트를 찾았습니다.")
        return posts

    async def _extract_posts_from_source(self, blog_id: str, count: int) -> list[dict]:
        """페이지 HTML에서 logNo를 직접 추출합니다."""
        posts = []
        seen = set()

        for page_num in range(1, 4):
            url = (
                f"https://blog.naver.com/PostList.naver"
                f"?blogId={blog_id}&currentPage={page_num}"
            )
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle", timeout=10000)

            content = await self.page.content()
            log_nos = re.findall(r'logNo["\s]*[:=]["\s]*[\'"]?(\d{9,15})', content)

            for log_no in dict.fromkeys(log_nos):  # 순서 유지하면서 중복 제거
                if log_no not in seen:
                    seen.add(log_no)
                    posts.append({"log_no": log_no, "title": f"포스트 #{log_no}"})
                    if len(posts) >= count:
                        return posts

        return posts

    async def get_post_content(self, blog_id: str, log_no: str) -> dict:
        """특정 포스트의 제목과 본문을 가져옵니다."""
        url = f"https://blog.naver.com/{blog_id}/{log_no}"
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle", timeout=15000)

        frame = await self._get_frame()
        await asyncio.sleep(2)

        # 제목 추출 (여러 셀렉터 시도)
        title = ""
        for selector in [
            ".se-title-text",
            ".tit_h3",
            "h3.title",
            ".post_title",
            ".title",
            "h2",
            "h1",
        ]:
            try:
                el = await frame.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text:
                        title = text
                        break
            except Exception:
                continue

        # 본문 추출 (여러 셀렉터 시도)
        content = ""
        for selector in [
            ".se-main-container",
            ".post_ct",
            ".post-content",
            ".contents_style",
            ".post_body",
            "#postViewArea",
            "article",
        ]:
            try:
                el = await frame.query_selector(selector)
                if el:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 10:
                        content = text
                        break
            except Exception:
                continue

        # Claude API 입력 길이 제한
        if len(content) > 2000:
            content = content[:2000] + "..."

        return {
            "title": title,
            "content": content,
            "url": url,
            "log_no": log_no,
        }

    async def _find_in_all_frames(self, selectors: list[str]):
        """페이지의 모든 프레임에서 보이는 요소를 찾아 (frame, element) 튜플을 반환합니다."""
        for frame in self.page.frames:
            for selector in selectors:
                try:
                    el = await frame.query_selector(selector)
                    if el and await el.is_visible():
                        return frame, el
                except Exception:
                    continue
        return None

    async def post_comment(self, blog_id: str, log_no: str, comment: str) -> bool:
        """블로그 포스트에 댓글을 달아줍니다."""
        url = f"https://blog.naver.com/{blog_id}/{log_no}"
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(3)

        # 페이지 하단으로 스크롤하여 댓글 영역 로드
        frame = self.page.frame("mainFrame") or self.page
        await frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        # 댓글 입력창 찾기
        comment_input_result = await self._find_in_all_frames([
            ".u_cbox_write_txt",
            ".u_cbox_input",
            "textarea[placeholder*='댓글']",
            "textarea[placeholder*='comment']",
            ".comment_write textarea",
            "#commentBox textarea",
            ".reply_input textarea",
        ])

        if not comment_input_result:
            print("  [WARNING] 댓글 입력창을 찾을 수 없습니다.")
            print("           (댓글이 비공개이거나 이웃 공개로 설정되어 있을 수 있습니다)")
            return False

        comment_frame, comment_input = comment_input_result

        # 댓글 입력 (자연스러운 타이핑 시뮬레이션)
        await comment_input.click()
        await asyncio.sleep(0.5)
        await comment_input.fill("")
        await comment_input.type(comment, delay=30)
        await asyncio.sleep(1)

        # 제출 버튼 찾기
        submit_result = await self._find_in_all_frames([
            ".u_cbox_btn_upload",
            "button.comment_submit",
            "button[type='submit']",
            ".btn_comment_post",
            ".comment_btn_submit",
            "button[aria-label*='등록']",
            ".btn_write",
        ])

        if not submit_result:
            print("  [WARNING] 댓글 제출 버튼을 찾을 수 없습니다.")
            return False

        _, submit_btn = submit_result
        await submit_btn.click()
        await asyncio.sleep(3)

        return True

    async def close(self):
        """브라우저를 닫습니다."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

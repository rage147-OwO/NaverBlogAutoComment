import asyncio
import json
import random
import re
import requests
from typing import Optional
from urllib.parse import unquote

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
        """브라우저를 시작합니다. 최소 크기 창으로 실행합니다."""
        self._playwright = await async_playwright().start()

        # 창 위치 랜덤화 (매번 다른 위치에서 시작 - 자동화 감지 피하기)
        x_pos = random.randint(0, 800)
        y_pos = random.randint(0, 200)

        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=360,640",  # 매우 최소화된 창 크기 (표준 모바일)
                f"--window-position={x_pos},{y_pos}",  # 랜덤 위치
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 375, "height": 667},  # 모바일 크기로 최소화
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/14.1.2 Mobile/15E148 Safari/604.1"
            ),
        )
        self.page = await self._context.new_page()

    async def login(self):
        """네이버 계정에 로그인합니다."""
        print("네이버 로그인 중...")
        await self.page.goto("https://nid.naver.com/nidlogin.login?mode=form")
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        await self.page.fill("#id", self.naver_id)
        await asyncio.sleep(0.5)
        await self.page.fill("#pw", self.naver_password)
        await asyncio.sleep(0.5)
        await self.page.click(".btn_login")
        await asyncio.sleep(2)  # 로그인 버튼 클릭 후 대기

        try:
            await self.page.wait_for_function(
                "!window.location.href.includes('nid.naver.com')",
                timeout=60000,
            )
            print("로그인 성공!")
            print(f"현재 URL: {self.page.url}")
            await asyncio.sleep(5)  # 로그인 후 추가 대기
        except Exception as e:
            print(f"로그인 대기 중 예외 발생: {e}")
            print(f"현재 URL: {self.page.url}")
            if "nid.naver.com" in self.page.url:
                print("\n⚠️  추가 인증이 필요합니다 (캡챠 또는 2단계 인증).")
                print("브라우저에서 직접 인증을 완료해주세요.")
                input("인증 완료 후 Enter를 눌러주세요...")
                await asyncio.sleep(2)
                print(f"인증 후 URL: {self.page.url}")

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

    async def _natural_wait(self, min_sec: float = 1, max_sec: float = 3):
        """자연스러운 변동이 있는 대기 (자동화 감지 피하기)."""
        wait_time = random.uniform(min_sec, max_sec)
        await asyncio.sleep(wait_time)

    async def _move_mouse_randomly(self):
        """마우스를 랜덤하게 움직여서 자동화 신호 감소."""
        try:
            x = random.randint(100, 300)
            y = random.randint(100, 400)
            await self.page.mouse.move(x, y)
        except:
            pass

    async def get_posts(self, blog_id: str, count: int = 10) -> list[dict]:
        """Naver API를 사용하여 블로그의 모든 포스트 목록을 가져옵니다."""
        print(f"포스트 목록 가져오는 중: blog.naver.com/{blog_id} (API 방식)")

        posts = []
        curr_page = 1
        count_per_page = 30
        total_count = None

        try:
            while total_count is None or curr_page * count_per_page <= total_count:
                # Naver PostTitleListAsync API 호출
                api_url = (
                    f"https://blog.naver.com/PostTitleListAsync.naver"
                    f"?blogId={blog_id}&currentPage={curr_page}&countPerPage={count_per_page}"
                )

                response = requests.get(api_url, timeout=10).text
                # JSON 파싱 전에 escape 제거
                response = response.replace('\\', '\\\\')
                data = json.loads(response)

                post_list = data.get("postList", [])
                total_count = int(data.get("totalCount", 0))

                for post in post_list:
                    log_no = post.get("logNo")
                    title = post.get("title", f"포스트 #{log_no}").strip()
                    # URL 인코딩된 제목 디코딩
                    title = unquote(title)

                    if log_no and title:
                        posts.append({"log_no": log_no, "title": title})

                        if len(posts) >= count:
                            break

                if len(posts) >= count:
                    break

                curr_page += 1

        except Exception as e:
            print(f"  [WARNING] API 호출 실패: {e}")
            return []

        print(f"  → {len(posts)}개의 포스트를 찾았습니다.")
        return posts

    async def get_post_content(self, blog_id: str, log_no: str) -> dict:
        """특정 포스트의 제목과 본문을 가져옵니다 (모바일 버전)."""
        # 모바일 URL 사용
        url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
        # 현재 URL 확인 - 이미 이 포스트 페이지에 있으면 navigate하지 않음
        if self.page.url != url:
            await self.page.goto(url, timeout=30000)
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
            "[class*='post'][class*='content']",
            "main",
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

        # 위의 방법이 실패하면 JavaScript로 가장 큰 텍스트 블록 찾기
        if not content:
            try:
                content = await frame.evaluate("""
                    () => {
                        const divs = document.querySelectorAll('div');
                        let maxDiv = null;
                        let maxLength = 0;

                        for (const div of divs) {
                            const text = div.innerText.length;
                            if (text > maxLength && text > 100 && !div.querySelector('header') && !div.querySelector('nav')) {
                                maxLength = text;
                                maxDiv = div;
                            }
                        }

                        return maxDiv ? maxDiv.innerText : '';
                    }
                """)
                content = content.strip()
            except Exception:
                pass

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
                    if el:
                        # 가시성 확인하지 않고 찾은 것 반환 (숨겨진 요소도 포함)
                        return frame, el
                except Exception:
                    continue
        return None

    async def post_comment(self, blog_id: str, log_no: str, comment: str) -> bool:
        """블로그 포스트에 댓글을 달아줍니다 (모바일 버전)."""
        # 모바일 버전 URL 사용
        url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
        if self.page.url != url:
            await self.page.goto(url, timeout=30000, wait_until="load")
            await asyncio.sleep(3)

        # 1. 댓글 버튼 클릭 (comment_btn__TUucZ)
        try:
            btn = await self.page.query_selector("button.comment_btn__TUucZ")
            if not btn:
                print("  > 댓글 버튼 못 찾음")
                return False

            await self._move_mouse_randomly()  # 마우스 움직임
            await btn.click()
            print("  > 댓글 버튼 클릭")
            await self._natural_wait(3.5, 4.5)  # 변동 있는 대기
        except Exception as e:
            print(f"  > 버튼 클릭 실패: {e}")
            return False

        # 2. 입력 필드 찾기 (.u_cbox_text[contenteditable])
        try:
            inp = await self.page.query_selector(".u_cbox_text[contenteditable]")
            if not inp:
                print("  > 입력 필드 못 찾음")
                return False
            print("  > 입력 필드 찾음")
            await self._natural_wait(0.5, 1.5)
        except Exception as e:
            print(f"  > 입력 필드 검색 실패: {e}")
            return False

        # 3. 댓글 입력
        try:
            await self._move_mouse_randomly()  # 마우스 움직임
            await inp.focus()  # 명시적으로 포커스 설정
            await self._natural_wait(1, 2)
            await inp.type(comment, delay=50)  # 각 글자마다 50ms 딜레이
            print("  > 댓글 입력 완료")
            await self._natural_wait(4.5, 6)  # 변동 있는 대기
        except Exception as e:
            print(f"  > 입력 실패: {e}")
            return False

        # 4. 제출 버튼 클릭 (.u_cbox_btn_upload)
        try:
            submit = await self.page.query_selector("button.u_cbox_btn_upload")
            if not submit:
                print("  > 제출 버튼 못 찾음")
                return False

            await self._move_mouse_randomly()  # 마우스 움직임
            await submit.click()
            print("  > 제출 버튼 클릭")
            await self._natural_wait(5.5, 7.5)  # 변동 있는 대기 (서버 처리 시간)
            return True
        except Exception as e:
            print(f"  > 제출 버튼 클릭 실패: {e}")
            return False

    async def close(self):
        """브라우저를 닫습니다."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

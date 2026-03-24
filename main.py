import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

"""
네이버 블로그 자동 위로 댓글 서비스
블로그의 일기 포스트를 읽고 Claude AI로 따뜻한 위로 댓글을 자동으로 달아줍니다.

사용법:
  python main.py                  # 일반 실행 (댓글 달기)
  python main.py --dry-run        # 테스트 모드 (댓글을 실제로 달지 않음)
  python main.py --count 3        # 최근 3개 포스트만 처리
  python main.py --headless       # 브라우저 창 없이 실행
  python main.py --reset          # 기록 초기화 후 전체 재처리
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from comment_generator import CommentGenerator
from naver_blog import NaverBlog

# .env 파일 명시적으로 로드
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

BLOG_ID = "rage147-owo"
COMMENTED_POSTS_FILE = "commented_posts.json"


def load_commented_posts() -> list:
    if Path(COMMENTED_POSTS_FILE).exists():
        with open(COMMENTED_POSTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_commented_posts(posts: list):
    with open(COMMENTED_POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


async def run(args):
    naver_id = os.getenv("NAVER_ID")
    naver_password = os.getenv("NAVER_PASSWORD")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_api_key:
        print("[ERROR] ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 API 키를 입력해주세요.")
        return

    if not args.dry_run and (not naver_id or not naver_password):
        print("[ERROR] NAVER_ID 또는 NAVER_PASSWORD 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 네이버 아이디와 비밀번호를 입력해주세요.")
        return

    if args.reset:
        save_commented_posts([])
        print("[OK] 댓글 기록이 초기화되었습니다.")

    commented_posts = load_commented_posts()
    generator = CommentGenerator(api_key=anthropic_api_key)
    blog = NaverBlog(naver_id=naver_id, naver_password=naver_password)

    try:
        await blog.start(headless=args.headless)

        if not args.dry_run:
            await blog.login()

        print(f"\n{'=' * 50}")
        print(f"  블로그: blog.naver.com/{BLOG_ID}")
        print(f"  처리할 포스트 수: {args.count}개")
        print(f"  모드: {'테스트 (댓글 미작성)' if args.dry_run else '실제 댓글 작성'}")
        print(f"{'=' * 50}\n")

        # 포스트 목록 가져오기
        posts = await blog.get_posts(BLOG_ID, count=args.count)

        if not posts:
            print("❌ 포스트를 찾을 수 없습니다.")
            return

        new_count = 0
        skip_count = 0

        for i, post in enumerate(posts, 1):
            log_no = post["log_no"]
            print(f"\n[{i}/{len(posts)}] {post['title'][:50]}")

            if log_no in commented_posts:
                print("  > 이미 댓글을 달았습니다. 건너뜀.")
                skip_count += 1
                continue

            # 포스트 내용 읽기
            print("  > 포스트 내용 읽는 중...")
            post_data = await blog.get_post_content(BLOG_ID, log_no)

            if not post_data.get("content"):
                print("  [WARNING] 내용을 가져올 수 없습니다. 건너뜀.")
                continue

            title = post_data.get("title") or post["title"]
            content = post_data["content"]

            print(f"  제목: {title[:60]}")
            print(f"  내용 미리보기: {content[:80].strip()}...")

            # Claude로 댓글 생성
            print("  > 댓글 생성 중 (Claude AI)...")
            comment = generator.generate_comment(title, content)
            print(f"  [COMMENT] {comment}")

            if args.dry_run:
                print("  > [테스트 모드] 실제 댓글은 달지 않습니다.")
                new_count += 1
                continue

            # 댓글 달기
            print("  > 댓글 달기 시도 중...")
            success = await blog.post_comment(BLOG_ID, log_no, comment)

            if success:
                commented_posts.append(log_no)
                save_commented_posts(commented_posts)
                new_count += 1
                print("  [OK] 댓글 작성 완료!")
            else:
                print("  [FAILED] 댓글 달기에 실패했습니다.")

            # 포스트 간 대기 (너무 빠른 자동화 방지)
            if i < len(posts):
                await asyncio.sleep(5)

        print(f"\n{'=' * 50}")
        print(f"  완료! 새 댓글: {new_count}개 | 건너뜀: {skip_count}개")
        print(f"{'=' * 50}")

    finally:
        await blog.close()


def main():
    parser = argparse.ArgumentParser(
        description="네이버 블로그 자동 위로 댓글 서비스",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 모드: 댓글을 실제로 달지 않고 내용만 확인합니다",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="처리할 최근 포스트 수 (기본값: 5)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="브라우저 창을 숨기고 실행합니다 (로그인 captcha 대응 불가)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="댓글 기록을 초기화하고 전체 포스트를 다시 처리합니다",
    )

    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

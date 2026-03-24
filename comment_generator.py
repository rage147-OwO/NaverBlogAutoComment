import anthropic


class CommentGenerator:
    """Claude API를 사용하여 따뜻한 위로의 댓글을 생성합니다."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_comment(self, title: str, content: str) -> str:
        """블로그 일기를 읽고 짧고 분석적인 댓글을 생성합니다."""

        system_prompt = (
            "당신은 통찰력 있는 분석자입니다. "
            "블로그 일기의 핵심 패턴이나 심리를 간결하게 포착하는 댓글을 작성합니다.\n\n"
            "댓글 작성 원칙:\n"
            "1. 글쓴이의 경험에서 숨은 패턴이나 심리를 분석적으로 지적\n"
            "2. 신선한 관점이나 재해석 제시\n"
            "3. 이모지, 특수문자, Markdown, 강조(**) 금지\n"
            "4. 댓글은 100자 이내로 간결하게 작성"
        )

        user_message = (
            "다음 글을 분석해주세요.\n\n"
            f"제목: {title}\n\n"
            f"내용:\n{content}"
        )

        try:
            with self.client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=350,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                final = stream.get_final_message()

            for block in final.content:
                if block.type == "text":
                    comment = block.text.strip()
                    # "(GPT자동댓글)"이 없으면 추가
                    if "(GPT자동댓글)" not in comment:
                        comment = f"(GPT자동댓글) {comment}"
                    return comment
        except Exception as e:
            # API 크레딧 부족 시 기본 댓글 반환
            if "credit balance is too low" in str(e):
                print("[INFO] API 크레딧이 부족합니다. 테스트용 댓글을 사용합니다.")
                # 제목과 내용을 기반으로 간단한 분석 댓글 생성
                keywords = self._extract_keywords(title, content)
                return self._generate_mock_comment(title, keywords)
            raise

        return "글에 담긴 통찰을 마주할 수 있어 감사합니다. 당신의 성장 과정이 의미 있습니다."

    def _extract_keywords(self, title: str, content: str) -> list:
        """간단한 키워드 추출"""
        import re
        text = (title + " " + content).lower()
        # 감정 관련 키워드
        emotions = ["힘들", "어렵", "외로", "답답", "불안", "슬픔", "기쁨", "설렘", "감사", "희망"]
        return [e for e in emotions if e in text]

    def _generate_mock_comment(self, title: str, keywords: list) -> str:
        """테스트용 고급스러운 댓글 생성"""
        base_comments = {
            "힘들": "당신의 글에서 느껴지는 것은 단순한 어려움이 아니라, 그 과정 속에서 자기 성찰을 멈추지 않는 성숙함입니다. 심리학에서 말하는 '포스트트라우마틱 그로스(역경을 통한 성장)'의 초기 단계를 보는 것 같습니다.",
            "외로": "고독함이 때로는 가장 정직한 감정이라는 점을 당신의 글에서 느꼈습니다. 그것을 마주하고 표현하는 용기 자체가 이미 연결의 첫걸음이 되어 있습니다.",
            "기쁨": "순간의 기쁨을 포착하고 글로 남기는 행위 자체가 삶의 본질을 이해하는 과정입니다. 그 세밀함이 정말 아름답습니다.",
            "희망": "절망 속에서도 희망을 찾으려는 시도는, 단순한 긍정이 아니라 인간의 회복탄력성을 증명하는 것입니다. 당신의 성장 궤적이 의미 있습니다.",
        }

        # 키워드에 맞는 댓글 선택
        for keyword in keywords:
            if keyword in base_comments:
                return base_comments[keyword]

        # 기본 댓글
        return "글의 깊이 있는 관찰이 인상적입니다. 당신의 경험이 누군가에게 큰 위로와 영감이 될 수 있을 것 같습니다. 계속해서 그 목소리를 유지해주길 바랍니다."

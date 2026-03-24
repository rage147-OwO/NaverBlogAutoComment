import anthropic


class CommentGenerator:
    """Claude API를 사용하여 따뜻한 위로의 댓글을 생성합니다."""

    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_comment(self, title: str, content: str) -> str:
        """블로그 일기를 읽고 기술적이고 고급스러운 공감 댓글을 생성합니다."""

        system_prompt = (
            "당신은 깊이 있는 통찰력을 가진 철학적 사고가들입니다. "
            "단순한 위로가 아니라, 인간의 심리, 삶의 패턴, 그리고 성장의 본질에 대해 "
            "깊은 이해와 함께 고급스러운 댓글을 달아줍니다.\n\n"
            "댓글 작성 원칙:\n"
            "1. 글쓴이의 경험을 단순 감정을 넘어 그 본질을 포착하세요\n"
            "2. 심리학, 인지과학, 철학적 관점에서 통찰력 있는 코멘트를 제시하세요\n"
            "3. 글쓴이의 상황을 재정의하거나 새로운 관점을 제공하세요\n"
            "4. 고급스럽고 정교한 표현을 사용하되, 자연스럽고 친근하게 써주세요\n"
            "5. 존댓말 사용, 3~5문장 분량의 밀도 있는 글로 작성하세요\n"
            "6. 글쓴이가 '우와' 하며 감탄할 정도의 깊이 있는 관찰과 제안을 해주세요"
        )

        user_message = (
            "다음 블로그 일기를 깊이 있게 분석하고, 기술적이고 고급스러운 공감 댓글을 작성해주세요.\n"
            "단순한 위로가 아니라, 글쓴이의 경험에 숨어있는 패턴, 심리, 또는 성장의 기회를 "
            "지적하는 댓글을 원합니다. 댓글 내용만 작성해주세요.\n\n"
            f"제목: {title}\n\n"
            f"내용:\n{content}"
        )

        try:
            with self.client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                final = stream.get_final_message()

            for block in final.content:
                if block.type == "text":
                    return block.text.strip()
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

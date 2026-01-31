"""TelegramMessenger - Telegram Bot을 통한 추천 메시지 발송"""
from typing import Optional, Dict, List
import logging
import asyncio
from datetime import datetime

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    Bot = None
    TelegramError = Exception

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, THEME_IDS

logger = logging.getLogger(__name__)


class TelegramMessenger:
    """Telegram Bot 메시징 시스템

    Telegram Bot API를 활용한 실시간 알림 발송
    - python-telegram-bot 라이브러리 사용
    - 비동기 발송
    - 완전 무료, 제한 없음

    Features:
    - 일일 추천 메시지 발송
    - 실시간 알림 (피드백 기반 등)
    - HTML 포맷팅 지원
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        """초기화

        Args:
            bot_token: Telegram Bot Token (기본값: settings.TELEGRAM_BOT_TOKEN)
            chat_id: 메시지 수신 Chat ID (기본값: settings.TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot credentials not configured")
            self.bot = None
        elif Bot is None:
            logger.error("python-telegram-bot library not installed")
            self.bot = None
        else:
            self.bot = Bot(token=self.bot_token)
            logger.info("Telegram messenger initialized")

    async def send_message(
        self,
        message: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False
    ) -> bool:
        """메시지 발송

        Args:
            message: 발송할 메시지
            parse_mode: 파싱 모드 (HTML, Markdown, None)
            disable_web_page_preview: 링크 미리보기 비활성화

        Returns:
            발송 성공 여부
        """
        if self.bot is None:
            logger.error("Telegram bot not initialized")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.info("Telegram message sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def format_recommendation_message(
        self,
        theme_id: int,
        theme_name: str,
        regions: List[Dict]
    ) -> str:
        """추천 메시지 포맷팅

        Args:
            theme_id: 테마 ID
            theme_name: 테마명
            regions: 추천 지역 리스트
                [{region_name, score, curation, lat, lng}, ...]

        Returns:
            포맷팅된 메시지 (HTML)
        """
        if not regions:
            return f"<b>{theme_name}</b>\n추천 지역이 없습니다."

        # 메시지 헤더
        message = f"<b>📸 {theme_name} 추천</b>\n"
        message += f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>\n\n"

        # 지역별 정보
        for idx, region in enumerate(regions, 1):
            region_name = region.get("region_name", "N/A")
            score = region.get("score", 0)
            curation = region.get("curation", "")
            lat = region.get("lat", 0)
            lng = region.get("lng", 0)

            # 순위 이모지
            rank_emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."

            message += f"{rank_emoji} <b>{region_name}</b> ({score:.1f}점)\n"

            # 큐레이션 문구
            if curation:
                message += f"{curation}\n"

            # 지도 링크 (Google Maps)
            map_url = f"https://www.google.com/maps?q={lat},{lng}"
            message += f"📍 <a href='{map_url}'>지도 보기</a>\n\n"

        # 푸터
        message += "━━━━━━━━━━━━━━━\n"
        message += "<i>Weather Lens - 풍경사진 출사지 큐레이션</i>"

        return message

    async def send_daily_recommendations(
        self,
        recommendations: Dict[int, List[Dict]]
    ) -> Dict[int, bool]:
        """일일 추천 메시지 발송

        Args:
            recommendations: 테마별 추천 결과
                {theme_id: [{region_name, score, curation, ...}, ...], ...}

        Returns:
            테마별 발송 성공 여부
            {theme_id: success, ...}
        """
        results = {}

        for theme_id, regions in recommendations.items():
            theme_name = THEME_IDS.get(theme_id, f"Theme {theme_id}")

            # 메시지 포맷팅
            message = self.format_recommendation_message(
                theme_id=theme_id,
                theme_name=theme_name,
                regions=regions
            )

            # 발송
            success = await self.send_message(message)
            results[theme_id] = success

            # 과도한 API 호출 방지 (텔레그램 봇 API 제한: 초당 30개)
            if success:
                await asyncio.sleep(0.5)

        return results

    async def send_alert(
        self,
        message: str,
        priority: str = "info"
    ) -> bool:
        """실시간 알림 발송 (피드백 기반 등)

        Args:
            message: 알림 메시지
            priority: 우선순위 (info, warning, error)

        Returns:
            발송 성공 여부
        """
        # 우선순위 이모지
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
        }
        emoji = emoji_map.get(priority, "📢")

        # 메시지 포맷팅
        formatted_message = f"{emoji} <b>Alert</b>\n\n{message}\n\n"
        formatted_message += f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"

        return await self.send_message(formatted_message)

    async def send_feedback_report(
        self,
        region_name: str,
        theme_name: str,
        fail_count: int,
        penalty_score: int
    ) -> bool:
        """피드백 기반 실시간 페널티 알림

        Args:
            region_name: 지역명
            theme_name: 테마명
            fail_count: 실패 제보 건수
            penalty_score: 페널티 점수

        Returns:
            발송 성공 여부
        """
        message = (
            f"<b>User Report Alert</b>\n\n"
            f"지역: {region_name}\n"
            f"테마: {theme_name}\n"
            f"실패 제보: {fail_count}건\n"
            f"페널티: {penalty_score}점 감점\n\n"
            f"해당 지역의 점수가 일시적으로 하향 조정되었습니다."
        )

        return await self.send_alert(message, priority="warning")

    async def send_system_status(
        self,
        status: Dict
    ) -> bool:
        """시스템 상태 리포트 발송

        Args:
            status: 시스템 상태 정보
                {data_updated, score_calculated, regions_count, ...}

        Returns:
            발송 성공 여부
        """
        message = "<b>📊 System Status Report</b>\n\n"

        for key, value in status.items():
            message += f"• {key}: {value}\n"

        return await self.send_message(message)

    def format_compact_summary(
        self,
        all_recommendations: Dict[int, List[Dict]],
        max_regions_per_theme: int = 3
    ) -> str:
        """전체 테마 요약 메시지 (간략형)

        Args:
            all_recommendations: 전체 테마별 추천
            max_regions_per_theme: 테마당 표시할 최대 지역 수

        Returns:
            포맷팅된 요약 메시지
        """
        message = "<b>🌅 오늘의 출사지 추천</b>\n"
        message += f"<i>{datetime.now().strftime('%Y년 %m월 %d일')}</i>\n\n"

        for theme_id, regions in all_recommendations.items():
            theme_name = THEME_IDS.get(theme_id, f"Theme {theme_id}")
            message += f"<b>{theme_name}</b>\n"

            if not regions:
                message += "추천 지역 없음\n\n"
                continue

            for idx, region in enumerate(regions[:max_regions_per_theme], 1):
                region_name = region.get("region_name", "N/A")
                score = region.get("score", 0)
                message += f"  {idx}. {region_name} ({score:.1f}점)\n"

            message += "\n"

        message += "━━━━━━━━━━━━━━━\n"
        message += "<i>자세한 정보는 웹사이트에서 확인하세요</i>"

        return message

    async def send_daily_summary(
        self,
        all_recommendations: Dict[int, List[Dict]]
    ) -> bool:
        """일일 요약 메시지 발송

        Args:
            all_recommendations: 전체 테마별 추천

        Returns:
            발송 성공 여부
        """
        message = self.format_compact_summary(all_recommendations)
        return await self.send_message(message)

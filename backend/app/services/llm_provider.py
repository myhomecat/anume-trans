"""LLM 호출 경로 추상화.

두 경로를 둔다.
- SDKProvider : anthropic 공식 SDK. tool use(structured output) 지원. 배포 가능.
- CLIProvider : `claude` CLI subprocess. 로컬 프로토타입용 폴백. 스키마 강제 불가.

ANTHROPIC_API_KEY 가 있으면 SDK, 없으면 CLI 로 떨어진다.
어느 경로로 도는지는 기동 시 로그로 남긴다 — 폴백이 조용히 일어나면
"SDK 인 줄 알았는데 CLI" 가 되기 때문이다(ADR-001).
"""
import asyncio
import logging
import os
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)

# 단계별 모델 티어링. 번역은 짧은 구어체라 Haiku 로 충분하고,
# 이미지 분석(Vision + bbox)만 상위 모델을 쓴다.
MODEL_TRANSLATE = os.getenv("MODEL_TRANSLATE", "claude-haiku-4-5")
MODEL_VISION = os.getenv("MODEL_VISION", "claude-sonnet-5")


class LLMProvider(Protocol):
    name: str

    async def complete(self, prompt: str, *, model: str, max_tokens: int) -> str:
        """자유 텍스트 응답."""
        ...

    async def complete_tool(
        self, prompt: str, *, tool: dict, model: str, max_tokens: int
    ) -> Optional[dict]:
        """스키마를 강제해 dict 로 받는다. 지원하지 않으면 None."""
        ...


class SDKProvider:
    """anthropic 공식 SDK 경로."""

    name = "sdk"

    def __init__(self, api_key: str, timeout: float = 120.0):
        from anthropic import AsyncAnthropic  # 지연 import — CLI 경로만 쓸 때 의존성 불요

        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=3)
        self.last_usage: dict[str, int] = {}

    def _track(self, resp: Any) -> None:
        u = getattr(resp, "usage", None)
        if u is None:
            return
        self.last_usage = {
            "input_tokens": getattr(u, "input_tokens", 0),
            "output_tokens": getattr(u, "output_tokens", 0),
        }

    async def complete(self, prompt: str, *, model: str, max_tokens: int = 2048) -> str:
        resp = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        self._track(resp)
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    async def complete_tool(
        self, prompt: str, *, tool: dict, model: str, max_tokens: int = 4096
    ) -> Optional[dict]:
        resp = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=[tool],
            # 이 도구를 반드시 부르게 강제한다. 실행할 함수는 없고,
            # 전달된 인자 자체가 우리가 원하는 결과다(ADR-002).
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": prompt}],
        )
        self._track(resp)
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input
        logger.warning("tool_use 블록이 없다: stop_reason=%s", resp.stop_reason)
        return None


class CLIProvider:
    """`claude` CLI subprocess 경로. 스키마 강제는 불가하다."""

    name = "cli"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout

    async def complete(self, prompt: str, *, model: str = "", max_tokens: int = 0) -> str:
        # 셸을 거치지 않고 인자로 직접 넘긴다 — 이스케이프 파손·주입 여지를 없앤다.
        process = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt, "--output-format", "text",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
        if process.returncode != 0:
            raise RuntimeError(f"Claude CLI error: {stderr.decode()}")
        return stdout.decode().strip()

    async def complete_tool(self, prompt: str, **_: Any) -> Optional[dict]:
        return None  # 미지원 — 호출부가 문자열 파싱으로 폴백한다


def build_provider(timeout: int = 60) -> LLMProvider:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        logger.info("[LLM] provider=sdk translate=%s vision=%s", MODEL_TRANSLATE, MODEL_VISION)
        return SDKProvider(api_key)
    logger.warning(
        "[LLM] provider=cli — ANTHROPIC_API_KEY 가 없어 CLI 로 폴백한다. "
        "structured output 을 쓸 수 없어 배치 번역은 문자열 파싱으로 동작한다."
    )
    return CLIProvider(timeout)

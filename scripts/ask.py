"""3단계: 에이전트 루프를 실제로 돌려보는 CLI.

실행:
    python scripts/ask.py "평택시 인구는 최근 3년간 어떻게 변했어?"
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from stat_agent.agent import run_agent  # noqa: E402


def main() -> None:
    load_dotenv()
    question = sys.argv[1] if len(sys.argv) > 1 else "주민등록인구가 가장 최근에 어떻게 변했어?"
    print(f"질문: {question}\n")
    result = run_agent(question)
    print(f"\n답변:\n{result['answer']}")


if __name__ == "__main__":
    main()

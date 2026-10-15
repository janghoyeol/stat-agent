"""4단계: 에이전트가 실제로 맞는 답을 내는지 점수로 확인.

정답은 에이전트가 아니라 tools.py를 직접 호출해 구한 값으로 미리 고정했다
(평택/수원/성남/화성시, 전국의 2022~2024년 인구와 전국 고용률).
"최근"이 아니라 과거 확정 연도를 써서, 다음 달에 데이터가 갱신돼도
정답이 흔들리지 않게 했다.

실행:
    python scripts/run_eval.py
"""

from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from stat_agent.agent import run_agent  # noqa: E402


@dataclass
class EvalCase:
    id: str
    question: str
    # 정답으로 인정하려면: must_contain_all은 전부, must_contain_any는 하나 이상 포함돼야 함
    must_contain_all: list[str] = field(default_factory=list)
    must_contain_any: list[str] = field(default_factory=list)
    # 출처를 밝혔다고 볼 만한 단서(참고용 지표, 정답 여부에는 영향 없음)
    source_hints: list[str] = field(default_factory=list)


CASES = [
    EvalCase("pop_lookup_1", "2024년 화성시 총인구는 몇 명이야?",
             must_contain_all=["968821"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("pop_lookup_2", "2024년 수원시 인구는 얼마였어?",
             must_contain_all=["1193005"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("pop_lookup_3", "2022년 성남시 인구는 얼마였어?",
             must_contain_all=["922518"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("emp_lookup", "2023년 전국 고용률은 몇 %였어?",
             must_contain_all=["62.6"], source_hints=["DT_1DA7001S", "국가데이터처", "kosis"]),
    EvalCase("pop_change_1", "평택시 인구는 2022년에서 2023년 사이 얼마나 늘었어?",
             must_contain_all=["12493"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("pop_change_2", "수원시 인구는 2022년부터 2023년까지 얼마나 변했어?",
             must_contain_all=["6293"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("pop_change_3", "전국 인구는 2023년에서 2024년 사이 얼마나 줄었어?",
             must_contain_all=["108108"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
    EvalCase("nonexistent_region", "삼성시 인구는 어떻게 변했어?",
             must_contain_any=["못 찾", "찾지 못", "찾을 수 없", "존재하지 않", "확인되지 않"]),
    # v2: 더 어려운 케이스 — 6단계에서 추가. 지역명이 여러 도시에 걸쳐 있는 경우
    # (중구: 서울/부산/대구/인천/대전/울산에 전부 있음, 8개 코드 중복) 와,
    # 두 지역을 비교 판단까지 해야 하는 질문.
    EvalCase("ambiguous_region", "중구 인구는 2023년에 얼마였어?",
             must_contain_any=["어느", "어떤", "여러", "여섯", "구체적", "확인해", "말씀해주시",
                                "말씀해 주시", "다릅니다", "후보", "지역에 따라"]),
    EvalCase("compare_regions", "화성시랑 성남시 중 2022년에서 2024년 사이 인구가 더 많이 늘어난 곳은 어디야?",
             must_contain_all=["화성"], source_hints=["DT_1B04006", "행정안전부", "kosis"]),
]


def _norm(text: str) -> str:
    return text.replace(",", "").replace(" ", "").lower()


def is_correct(answer: str, case: EvalCase) -> bool:
    norm = _norm(answer)
    if case.must_contain_all and not all(_norm(t) in norm for t in case.must_contain_all):
        return False
    if case.must_contain_any and not any(_norm(t) in norm for t in case.must_contain_any):
        return False
    return True


def has_source(answer: str, case: EvalCase) -> bool | None:
    if not case.source_hints:
        return None
    norm = _norm(answer)
    return any(_norm(h) in norm for h in case.source_hints)


def main() -> None:
    load_dotenv()
    passed = 0
    sourced = 0
    sourced_total = 0

    for case in CASES:
        print(f"\n[{case.id}] {case.question}")
        try:
            answer = run_agent(case.question, verbose=False)["answer"]
        except Exception:  # noqa: BLE001 — 에이전트 자체가 터져도 다음 케이스는 계속 돌린다
            print("  ERROR:", traceback.format_exc(limit=1))
            continue

        correct = is_correct(answer, case)
        src = has_source(answer, case)
        passed += correct
        if src is not None:
            sourced_total += 1
            sourced += src

        print(f"  정답: {'O' if correct else 'X'}" + (f" / 출처: {'O' if src else 'X'}" if src is not None else ""))
        if not correct:
            print(f"  답변: {answer[:300]}")

    print(f"\n{'=' * 40}\n정답률: {passed}/{len(CASES)}")
    if sourced_total:
        print(f"출처 명시율: {sourced}/{sourced_total}")


if __name__ == "__main__":
    main()

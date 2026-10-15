"""Claude tool-use 에이전트 루프.

Anthropic API는 "모델이 끝날 때까지 자동으로 도는" 게 아니라, 모델이
tool_use를 요청하면 우리가 직접 함수를 실행하고 결과를 다시 넣어줘야
루프가 이어진다. 이 모듈이 그 루프를 담당한다.
"""

from __future__ import annotations

import json
import os

from anthropic import Anthropic

from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

MODEL = "claude-haiku-5-5"

SYSTEM_PROMPT = """\
너는 국가통계포털(KOSIS) 데이터를 조회해 질문에 답하는 통계 에이전트다.

규칙:
1. 모든 숫자 답변에는 반드시 출처(통계표명, 시점, 가능하면 링크)를 함께 밝힌다.
2. 통계표나 코드를 찾지 못했으면 지어내지 말고 못 찾았다고 말한다.
3. 증감률/증감량 계산은 절대 암산하지 말고 calculate_change 도구를 호출해서 계산한다.
4. get_table_info에서 분류 코드가 truncated=true로 나오면 전체를 못 본 것이니,
   name_filter를 바꿔 다시 조회해서 정확한 코드를 찾아라.
5. "앞으로 조회하겠다", "확인해보겠다"처럼 **할 일을 말로 선언만 하고 도구를
   호출하지 않은 채로 답변을 끝내지 마라.** 실제로 도구를 호출해서 값을 확인한
   뒤에만 답변을 끝낸다.
6. 지역명이 여러 시/도에 걸쳐 있을 수 있으면(예: "중구"는 서울/부산/대구/인천/
   대전/울산에 전부 있다), 짐작으로 하나를 고르지 말고 사용자에게 어느 지역인지
   되묻거나, 가능한 후보 전부를 실제로 조회해서 비교해 보여준다.
7. 같은 통계(예: 인구)를 여러 기관 표가 서로 다른 정의로 발표하는 경우가 있다.
   사용자가 특정 기관/표를 지정하지 않았다면, 비교 가능성과 일관성을 위해
   행정안전부의 "주민등록인구" 계열 표를 기본값으로 우선 사용한다.
"""


def run_agent(question: str, verbose: bool = True) -> dict:
    """사용자 질문 하나를 받아 도구를 호출해가며 최종 답변과 호출 기록을 돌려준다.

    반환값: {"answer": str, "trace": [{"tool": str, "input": dict, "output": Any, "is_error": bool}, ...]}
    trace는 화면(웹 UI)에 "에이전트가 뭘 어떤 순서로 호출했는지" 보여주기 위한 것.
    """
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    messages: list[dict] = [{"role": "user", "content": question}]
    trace: list[dict] = []

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = "".join(block.text for block in response.content if block.type == "text")
            return {"answer": answer, "trace": trace}

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if verbose:
                print(f"  [tool] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
            output, is_error = _run_tool(block.name, block.input)
            trace.append({"tool": block.name, "input": block.input, "output": output, "is_error": is_error})
            tool_results.append(_to_tool_result(block.id, output, is_error))

        messages.append({"role": "user", "content": tool_results})


def _run_tool(name: str, tool_input: dict) -> tuple[object, bool]:
    """도구 함수 하나를 실행한다. 예외가 나면 (에러 메시지, True)를 돌려준다.

    에러를 숨기지 않고 모델에게 그대로 알려줘서, 실패를 인지하고 다른 방법
    (다른 코드, 다른 표)을 시도할 수 있게 한다.
    """
    try:
        return TOOL_FUNCTIONS[name](**tool_input), False
    except Exception as e:  # noqa: BLE001 — 도구 실패를 모델에게 그대로 알려주기 위한 포괄 처리
        return f"에러: {e}", True


def _to_tool_result(tool_use_id: str, output: object, is_error: bool) -> dict:
    content = output if is_error else json.dumps(output, ensure_ascii=False)
    result = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        result["is_error"] = True
    return result

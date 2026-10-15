"""2단계: tools.py의 도구 4개가 실제 KOSIS 응답에 대해 잘 동작하는지 확인.

search → (필터 없이) meta → (name_filter로 좁힌) meta → data → calculate
순서로 호출해보고, 중간 결과를 눈으로 확인한다.

실행:
    python scripts/try_tools.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from stat_agent import tools  # noqa: E402
from stat_agent.kosis_client import KosisClient, KosisError  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    load_dotenv()
    client = KosisClient()

    section("1) search_tables('주민등록인구')")
    results = tools.search_tables("주민등록인구", limit=5, client=client)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    top = results[0]
    org_id, tbl_id = top["org_id"], top["tbl_id"]
    print(f"\n→ 사용할 표: {top['title']} ({org_id}/{tbl_id})")

    section("2) get_table_info() — name_filter 없이")
    info = tools.get_table_info(org_id, tbl_id, client=client)
    print(f"items: {info['items']}")
    for c in info["classifications"]:
        print(f"- {c['name']} (obj_id={c['obj_id']}): total={c['total_codes']} truncated={c['truncated']}")
        print(f"    예시: {c['codes'][:3]}")

    section("3) get_table_info(name_filter='평택') — 코드 좁히기")
    info_filtered = tools.get_table_info(org_id, tbl_id, name_filter="평택", client=client)
    for c in info_filtered["classifications"]:
        if c["codes"]:
            print(f"- {c['name']}: {c['codes']}")

    # 평택시에 해당하는 분류 코드를 찾는다. 못 찾으면 전국(첫 분류의 첫 코드)으로 대체.
    region_class = info_filtered["classifications"][0]
    region_code = region_class["codes"][0]["code"] if region_class["codes"] else info["classifications"][0]["codes"][0]["code"]
    other_codes = [c["codes"][0]["code"] for c in info["classifications"][1:]]
    itm_id = info["items"][0]["itm_id"]
    prd_se = info["periods"][0]["prd_se"]

    section("4) get_data()")
    print(f"itm_id={itm_id}, obj_codes={[region_code] + other_codes}, prd_se={prd_se}")
    data = tools.get_data(org_id, tbl_id, itm_id, [region_code] + other_codes, prd_se, recent=5, client=client)
    print(json.dumps(data, ensure_ascii=False, indent=2))

    section("5) calculate_change()")
    first, last = data[0], data[-1]
    result = tools.calculate_change(first["period"], first["value"], last["period"], last["value"])
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n완료! calculate_change 결과를 KOSIS 웹사이트 수치와 비교해 맞는지 확인해보세요.")


if __name__ == "__main__":
    try:
        main()
    except KosisError as e:
        print(f"\n[KOSIS 에러] {e}")
        sys.exit(1)

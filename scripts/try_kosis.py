"""1단계: KOSIS API를 직접 손으로 호출해보는 탐색 스크립트.

에이전트를 만들기 전에 '사람이 직접' 검색 → 메타 확인 → 수치 조회를 해본다.
여기서 막히는 지점이 곧 에이전트가 막힐 지점이고, 시스템 프롬프트와
도구 설명에 무엇을 써야 할지 알려준다.

실행:
    python scripts/try_kosis.py                # 기본 키워드 '주민등록인구'
    python scripts/try_kosis.py "고용률"
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# Windows 콘솔은 기본 코드페이지(cp949 등)로 stdout을 열어, 터미널이 UTF-8을
# 기대하면 한글이 깨진다. 실행 환경과 무관하게 항상 UTF-8로 출력하도록 강제.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from stat_agent.kosis_client import KosisClient, KosisError, PRD_MAP  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    load_dotenv()
    keyword = sys.argv[1] if len(sys.argv) > 1 else "주민등록인구"
    client = KosisClient()

    # 1) 검색 ---------------------------------------------------------
    section(f"1) 통합검색: '{keyword}'")
    results = client.search_tables(keyword, limit=5)
    for i, r in enumerate(results):
        print(f"[{i}] {r.get('TBL_NM')}  ({r.get('ORG_NM')})")
        print(f"     orgId={r.get('ORG_ID')} tblId={r.get('TBL_ID')} "
              f"기간={r.get('STRT_PRD_DE')}~{r.get('END_PRD_DE')}")
    if not results:
        print("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
        return

    top = results[0]
    org_id, tbl_id = top["ORG_ID"], top["TBL_ID"]
    print(f"\n→ 첫 번째 통계표로 진행: {top.get('TBL_NM')}")

    # 2) 항목/분류 메타 -------------------------------------------------
    section("2) 항목·분류 메타 (type=ITM)")
    meta = client.get_table_meta(org_id, tbl_id, "ITM")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in meta:
        groups[row.get("OBJ_ID", "?")].append(row)

    for obj_id, rows in groups.items():
        print(f"\n- OBJ_ID={obj_id} ({rows[0].get('OBJ_NM')}) : {len(rows)}개, "
              f"OBJ_ID_SN={rows[0].get('OBJ_ID_SN')}")
        for row in rows[:5]:
            print(f"    {row.get('ITM_ID'):>12}  {row.get('ITM_NM')}  {row.get('UNIT_NM') or ''}")
        if len(rows) > 5:
            print("    ...")

    # 항목(ITEM)과 분류(그 외)를 나눈다. 분류는 OBJ_ID_SN 순서가 objL1, objL2...
    item_rows = groups.pop("ITEM", None)
    if item_rows is None:
        print("\n[!] OBJ_ID='ITEM' 그룹이 없습니다. 위 출력을 보고 어떤 게 항목인지 확인해주세요.")
        return
    classes = sorted(groups.items(), key=lambda kv: int(kv[1][0].get("OBJ_ID_SN") or 0))

    # 3) 수록주기 -------------------------------------------------------
    section("3) 수록주기 (type=PRD)")
    prd = client.get_table_meta(org_id, tbl_id, "PRD")
    print(json.dumps(prd[:3], ensure_ascii=False, indent=2))
    raw_se = prd[0].get("PRD_SE", "Y") if prd else "Y"
    prd_se = PRD_MAP.get(raw_se, raw_se)

    # 4) 수치 조회 ------------------------------------------------------
    itm_id = item_rows[0]["ITM_ID"]
    obj_codes = [rows[0]["ITM_ID"] for _, rows in classes]
    section("4) 수치 조회 (최근 3개 시점)")
    print(f"itmId={itm_id} ({item_rows[0].get('ITM_NM')}), objL={obj_codes}, prdSe={prd_se}")
    data = client.get_data(org_id, tbl_id, itm_id, obj_codes, prd_se, recent=3)
    for row in data:
        labels = " / ".join(row.get(f"C{i}_NM", "") for i in range(1, 9) if row.get(f"C{i}_NM"))
        print(f"  {row.get('PRD_DE')}  {labels}  {row.get('ITM_NM')} = {row.get('DT')} {row.get('UNIT_NM') or ''}")

    print("\n완료! 위 숫자를 KOSIS 웹사이트의 같은 통계표와 비교해서 맞는지 확인해보세요.")
    print(f"통계표 링크: {top.get('LINK_URL') or top.get('TBL_VIEW_URL')}")


if __name__ == "__main__":
    try:
        main()
    except KosisError as e:
        print(f"\n[KOSIS 에러] {e}")
        sys.exit(1)

"""把选定语料转成多页文本型 PDF，用于验证 PDF 解析与页码来源。

两个刻意的取舍：
1. **纯标准库实现**：项目环境没有 reportlab/fpdf/fontTools，而沙箱不能写入 conda 环境；
   与其为一个辅助格式引入依赖，不如直接生成最小的合法 PDF。
2. **只用 ASCII（WinAnsi）编码**：内置标准字体不含 CJK 字形，嵌入中文字体又会显著增大仓库体积。
   因此 PDF 附录写成中英混排文档：正文用英文，但**事实项（锁定阈值、端口、配额、SLA）与 Markdown
   版本完全一致**，这样中文知识库里的跨格式一致性问题依然被真实覆盖。

PDF 为多页，因此 `chunks.page` 会得到真实的 1/2/3，可用来验证页码溯源。

用法：
    python evals/tools/build_pdfs.py
"""

from __future__ import annotations

import hashlib
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
LINES_PER_PAGE = 30
CHARS_PER_LINE = 88

#: 每个知识库各生成 2 份 PDF 附录，写明 base 基准文件与 3 项必须一致的已标注事实项。
APPENDIX = {
    "it": [
        {
            "slug": "it-vpn-lockout-policy",
            "title": "Xingqiao Tech - VPN Access Policy (Field Reference)",
            "base": "VPN 使用指南（北京）.md",
            "facts": [
                "XQ-IT-2026-011 V2.3, effective 2026-04-01",
                "Access granted within 1 business day; grant valid for 12 months",
            ],
        },
        {
            "slug": "it-exit-account-revocation",
            "title": "Xingqiao Tech - Offboarding Account Revocation (Field Reference)",
            "base": "离职与转岗账号回收流程.md",
            "facts": [
                "XQ-IT-2025-021 V3.4, effective 2025-11-01",
                "Account disabled, token revoked and VPN access reclaimed by 18:00 on the last day",
                "HR publishes the offboarding list 3 business days in advance",
            ],
        },
    ],
    "hr": [
        {
            "slug": "hr-travel-reimbursement-card",
            "title": "Xingqiao Tech - Travel Reimbursement Quick Card",
            "base": "差旅报销标准（一线城市）.md",
            "facts": [
                "XQ-FIN-010 V4.0, effective 2026-01-01",
                "Previous 2024 edition (XQ-FIN-010-V3) and its 500 CNY hotel cap are void",
                "Tier-1 standard must not be mixed with XQ-FIN-011 (other cities)",
            ],
        },
        {
            "slug": "hr-leave-quota-card",
            "title": "Xingqiao Tech - Leave Quota Quick Card",
            "base": "请假类型与假期额度对照表.md",
            "facts": [
                "XQ-HR-005 V3.0, numeric appendix to XQ-HR-004",
                "Annual leave: 5 days at 1 year, 10 at 3 years, 15 at 5 years, 20 at 10 years",
                "Paid sick leave: 5 days per year, first 5 days paid at 100%",
            ],
        },
    ],
    "product": [
        {
            "slug": "pd-clouddrive-quota-limits",
            "title": "Xingqiao CloudDrive - Plan Quota Reference",
            "base": "星桥云盘套餐与配额对照表.md",
            "facts": [
                "XQ-DRIVE-PLAN-004 v1.9, published 2026-08-05, for CloudDrive 3.4.x",
                "See the plan table in the Markdown version for per-plan storage and upload limits",
            ],
        },
        {
            "slug": "pd-sla-response-tiers",
            "title": "Xingqiao Ticket - SLA Response Tiers",
            "base": "星桥工单 SLA 分级与响应时限.md",
            "facts": [
                "XQ-TICKET-SLA-104 v3.1, published 2026-08-06, for Ticket 4.2.x",
                "P0 means total business outage with no workaround",
                "See the Markdown version for first-response targets per tier",
            ],
        },
    ],
}


def escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def content_stream(lines: list[tuple[str, int]]) -> bytes:
    parts = ["BT", "/F1 10 Tf", "14 TL", "54 760 Td"]
    for text, size in lines:
        if size != 10:
            parts.append(f"/F1 {size} Tf")
        parts.append(f"({escape(text)}) Tj")
        parts.append("T*")
        if size != 10:
            parts.append("/F1 10 Tf")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def build_pdf(path: Path, title: str, pages: list[list[str]]) -> dict:
    """显式编号，避免 "/Pages 自引用" 这类循环页码树错误。

    编号约定：1=Font，2=Pages，3..2+2n 为每页的 Content/Page 交替，最后是 Info 与 Catalog。
    """
    font_id = 1
    pages_id = 2
    objects: dict[int, bytes] = {
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    }
    page_ids: list[int] = []
    next_id = 3
    for lines in pages:
        stream = zlib.compress(content_stream(lines))
        content_id = next_id
        page_id = next_id + 1
        next_id += 2
        objects[content_id] = (
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        page_ids.append(page_id)
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode()
    info_id = next_id
    objects[info_id] = (
        f"<< /Title ({escape(title)}) /Producer (KnowOps synthetic dataset builder) >>".encode()
    )
    catalog_id = next_id + 1
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
    size = catalog_id + 1

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n".encode() + objects[object_id] + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {size}\n".encode()
    out += b"0000000000 65535 f \n"
    for object_id in range(1, size):
        out += f"{offsets[object_id]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {size} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))
    return {
        "file": path.name,
        "format": "pdf",
        "pages": len(pages),
        "bytes": len(out),
        "sha256": hashlib.sha256(bytes(out)).hexdigest(),
    }


def paginate(paragraphs: list[str]) -> list[list[str]]:
    pages, current = [], []
    for paragraph in paragraphs:
        wrapped = [paragraph[i : i + CHARS_PER_LINE] for i in range(0, max(len(paragraph), 1), CHARS_PER_LINE)]
        for line in wrapped:
            if len(current) >= LINES_PER_PAGE:
                pages.append(current)
                current = []
            current.append(line)
    if current:
        pages.append(current)
    return pages


def main() -> int:
    import json

    manifest = {}
    missing = []
    for domain, items in APPENDIX.items():
        manifest[domain] = []
        for item in items:
            source = EVALS / "corpus" / domain / item["base"]
            if not source.exists():
                missing.append(str(source))
                continue
            lines = [
                (item["title"], 12),
                ("", 10),
                (f"Fictional company: Xingqiao Tech. Source document: {item['base']}", 10),
                ("This appendix mirrors facts already labelled in the Markdown version.", 10),
                ("", 10),
                ("1. Scope", 11),
                ("Applies to all active accounts and services managed by the platform team.", 10),
                ("Field staff must follow the Markdown policy when the two disagree.", 10),
                ("", 10),
                ("2. Confirmed values (must match the Markdown wording)", 11),
            ]
            for fact in item["facts"]:
                lines += [(f"  - {fact}", 10)]
            lines += [
                ("", 10),
                ("3. Operator checklist", 11),
                ("  1) Confirm the requester identity and ticket id in the service desk system.", 10),
                ("  2) Record the exact timestamp before and after the change.", 10),
                ("  3) Escalate to the platform on-call when a value conflicts with policy.", 10),
                ("  4) Attach the approval thread to the ticket before closing it.", 10),
                ("  5) Re-check the value against this appendix after any policy revision.", 10),
                ("", 10),
                ("4. Escalation and contacts", 11),
                ("Service desk extension 6001, weekdays 09:00-18:30 Asia/Shanghai.", 10),
                ("Platform on-call pager is reachable through the service desk only.", 10),
                ("Security incidents must be reported within one hour of detection.", 10),
                ("", 10),
                ("5. Common questions", 11),
                ("Q: Which document wins when this card and the Markdown policy disagree?", 10),
                ("A: The Markdown policy is authoritative; treat this card as a field summary.", 10),
                ("Q: Can a value be changed locally by a site administrator?", 10),
                ("A: No. Local overrides are not permitted for the values listed above.", 10),
                ("Q: How often is this card revised?", 10),
                ("A: At least once per quarter, or immediately after a policy revision.", 10),
                ("", 10),
                ("6. Related documents", 11),
                (f"  - {item['base']} (authoritative Markdown version)", 10),
                ("  - Identity and Access Management Standard, revision V1.1 or later", 10),
                ("  - Service Desk Operating Procedure, revision V2.0 or later", 10),
                ("", 10),
                ("7. Revision history", 11),
                ("  V1.0 2026-03-02 initial field reference for the synthetic dataset.", 10),
                ("  V1.1 2026-06-11 clarified escalation path and page-level traceability.", 10),
                ("  V1.2 2026-09-08 added common questions and related document list.", 10),
                ("", 10),
                ("Note: page numbers in this PDF are used by KnowOps to verify PDF page tracing.", 10),
                ("Printed copies are for reference only; the Markdown version remains authoritative.", 10),
            ]
            pages = paginate(lines)
            target = EVALS / "corpus" / domain / f"{item['slug']}.pdf"
            manifest[domain].append(build_pdf(target, item["title"], pages))
            print(f"生成 {target.relative_to(ROOT)} ｜ {len(pages)} 页 ｜ {manifest[domain][-1]['bytes']} 字节")
    if missing:
        print(f"跳过 {len(missing)} 份基准文件尚未生成的附录：{[Path(m).name for m in missing]}")
    if not any(manifest.values()):
        print("没有生成任何 PDF（基准文件都不存在）", file=sys.stderr)
        return 1
    (EVALS / "pdf_appendix.json").write_text(
        json.dumps(
            {
                "purpose": "验证 PDF 解析、分页与 chunks.page 溯源；正文为 ASCII，事实项与 Markdown 一致。",
                "limitations": "内置标准字体不含 CJK 字形，因此 PDF 附录正文为英文；不能代表中文 PDF 版式。",
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("写入 evals/pdf_appendix.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build submission/deck/pitch.pdf from deck/outline.md (8 slides, 5-min pitch).

Usage:  python submission/deck/build_pdf.py
Output: submission/deck/pitch.pdf
Requires: reportlab (already in env, v5.0.1+).
Design: 1 idea/slide, 24pt+ titles, dark-on-light. Speaker notes = PITCH.md beats.
"""
from pathlib import Path

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                PageBreak, Table, TableStyle)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT

HERE = Path(__file__).resolve().parent
OUT = HERE / "pitch.pdf"

PAGE_W, PAGE_H = landscape(A4)
INK = HexColor("#111111")
ACCENT = HexColor("#1a56db")
MUTED = HexColor("#555555")
CARD = HexColor("#eef2ff")

title_style = ParagraphStyle("title", fontSize=30, leading=34, textColor=INK,
                             spaceAfter=0.4 * cm, fontName="Helvetica-Bold")
h2_style = ParagraphStyle("h2", fontSize=20, leading=24, textColor=ACCENT,
                          spaceAfter=0.3 * cm, fontName="Helvetica-Bold")
body_style = ParagraphStyle("body", fontSize=15, leading=20, textColor=INK,
                            spaceAfter=0.2 * cm, fontName="Helvetica",
                            alignment=TA_LEFT)
note_style = ParagraphStyle("note", fontSize=11, leading=14, textColor=MUTED,
                            spaceBefore=0.4 * cm, fontName="Helvetica-Oblique")
foot_style = ParagraphStyle("foot", fontSize=10, leading=12, textColor=MUTED,
                            fontName="Helvetica")

SLIDES = [
    ("1 · Title",
     "Onboard Copilot",
     ["HR + IT copilot that closes onboarding exceptions live · Track 3",
      "QR: live demo + repo (paste at freeze) · Tagline: \u201c8 tools deleted. 1 decision.\u201d"],
     "Face intro 5s. End-card QR must scan from 3m."),
    ("2 · Problem",
     "Priya starts Monday — five systems, zero join",
     ["SSO, laptop, payroll ID, training live in 5 disconnected systems",
      "Today: 11 open tickets, 4 owners, 0 accountability",
      "Stat: Day-1 blockers hit every company + pain quote"],
     "Hook 0–8s verbatim (PITCH.md). Candidate card CAND-002 on screen."),
    ("3 · Solution",
     "Exception queue \u2192 staged preview \u2192 APPROVE \u2192 receipt",
     ["Staged preview with citations (OFFER \u00a72.1, BG-CLEAR #881, INV-HOLD LT-1005)",
      "One explicit APPROVE <hash> flips staged \u2192 active at midnight",
      "Audit row appended: who / what / diff / rollback"],
     "Stage 8–20s. confirm=False watermark visible on preview pane."),
    ("4 · Demo (live moment)",
     "One new endpoint, rescan, reroute — same server ID",
     ["GET /it/oncall-coverage (L1) added on stage",
      "synapse build --discover \u2192 it_oncall_coverage, no client re-config",
      "Agent re-routes breaching tickets to on-call"],
     "QR + 3 steps (Stage \u2192 Approve \u2192 Activate). Inspector Reconnect re-lists in 3s."),
    ("5 · Architecture",
     "Two FastAPIs \u2192 two MCP servers \u2192 one copilot",
     ["Read live HR/IT state \u2192 stage reversible draft + preview_hash",
      "CHECK scope/hash/approval \u2192 ACT \u2192 RECORD hash-chained audit",
      "Same SYNAPSE_SERVER_ID across discover; SQLite WAL, offline-first"],
     "Mermaid PNG (assets/arch.png) + synapse build output on this slide."),
    ("6 · Benchmarks + quota-proof",
     "1.3s boot · ~10.6ms p50 · guarded 97.5% / 0% FP · \u20b90",
     ["Cold start 1.3s (target <15s) · breaches p50 10.6ms / p95 11.6ms",
      "Safety: 96.8% block / 0% FP, 40 cases (MOCK ~11ms) · TTFT local 0.24s",
      "Guards: cache + rate limit + cached-JSON fallback · screenshots in assets/quota-proof/"],
     "Full table: BENCHMARKS.md. \u20b90 badge big. Quota tripwire T8: <40% \u2192 freeze hosted builds."),
    ("7 · Roadmap",
     "Freeze \u2192 harden \u2192 expand",
     ["Now (freeze D12): 10 dry runs, record golden.mp4, publish repo",
      "Next: Frappe HRMS backend, second breach scenario",
      "Later: payroll-rails read-only, multi-tenant isolation"],
     "Show restraint: no-go paths declared (BG_PENDING\u2192block, visa<90d\u2192warn+ticket)."),
    ("8 · Team + Ask",
     "Solo builder — try it live",
     ["APIs + Synapse + safety/evals + demo/video: one owner, full slice",
      "Contact + repo link + CTA: \u201cTry it live at the link below\u201d",
      "MIT license · Repro: run.bat (3 cmds, <60s warm)"],
     "End card: links + QR + synapse info quota + \u20b90. Thank you."),
]


def slide_table(items):
    rows = [[Paragraph(f"\u2022 {b}", body_style)] for b in items]
    t = Table(rows, colWidths=[PAGE_W - 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("BOX", (0, 0), (-1, -1), 1, ACCENT),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#c7d2fe")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=landscape(A4),
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.4 * cm,
                            title="Onboard Copilot — pitch deck",
                            author="VIBE_CODE")
    story = []
    for i, (kicker, title, bullets, note) in enumerate(SLIDES):
        story.append(Paragraph(kicker, h2_style))
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3 * cm))
        story.append(slide_table(bullets))
        story.append(Paragraph("Speaker note: " + note, note_style))
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph("Onboard Copilot · Track 3 · submission/deck/pitch.pdf",
                               foot_style))
        if i < len(SLIDES) - 1:
            story.append(PageBreak())
    doc.build(story)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(SLIDES)} slides)")


if __name__ == "__main__":
    build()

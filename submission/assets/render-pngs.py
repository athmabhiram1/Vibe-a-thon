"""Render submission/assets/arch.png (matplotlib fallback of ARCHITECTURE.md
mermaid flowchart LR) + quota-proof/ollama-ps.png (PIL text rendering)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
import textwrap

# ---------------- arch.png ----------------
fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

def box(x, y, w, h, lines, face="#EAF2FF", edge="#2B6CB0", dashed=False):
    style = "round,pad=0.08" if not dashed else "round,pad=0.08"
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, facecolor=face,
                       edgecolor=edge, linewidth=1.6,
                       linestyle=(0, (5, 4)) if dashed else "-")
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center",
            fontsize=8.5, color="#1A202C", family="sans-serif", weight="bold")

def arrow(x1, y1, x2, y2, label=None, dashed=False, ly=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color="#2D3748", lw=1.5,
                                linestyle=(0, (5, 4)) if dashed else "-"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + ly, label, ha="center",
                va="center", fontsize=6.5, color="#4A5568", family="sans-serif",
                bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

ax.text(8, 8.45, "Track 3 Onboard Copilot — architecture (render of ARCHITECTURE.md mermaid)",
        ha="center", fontsize=11, weight="bold", color="#1A202C")

# Row 1: sources -> MCP servers
box(0.4, 6.2, 2.6, 1.3, ["HR Directory", "FastAPI :8001", "H1-H5"])
box(0.4, 4.3, 2.6, 1.3, ["Ticketing SLA", "FastAPI :8002", "I1-I6 + L1"])
box(4.6, 6.2, 3.0, 1.3, ["MCP server hr-api", "13-tool baseline"])
box(4.6, 4.3, 3.0, 1.3, ["MCP server it-api", "shares allowlist (13 total)"])
# Agent center-right
box(9.2, 5.2, 3.0, 1.4, ["Onboard Copilot agent", "Inspector Web UI", "Cite-Before-Act gate"],
    face="#EBF8FF", edge="#2B6CB0")
# Human loop
box(9.2, 3.2, 3.0, 1.2, ["Human", "APPROVE hash"], face="#F0FFF4", edge="#276749")
# Ledger + DB
box(12.9, 5.4, 2.5, 1.2, ["Audit ledger", "hash chain"], face="#FFFAF0", edge="#975A16")
box(12.9, 3.4, 2.5, 1.2, ["SQLite WAL", "79 rows seed"], face="#FFFAF0", edge="#975A16")

arrow(3.0, 6.85, 4.6, 6.85, "synapse build --auto", ly=0.28)
arrow(3.0, 4.95, 4.6, 4.95, "synapse build --auto --new", ly=0.28)
arrow(7.6, 6.85, 9.2, 6.0)
arrow(7.6, 4.95, 9.2, 5.6)
arrow(10.0, 5.2, 10.0, 4.4, "CITE preview+hash", ly=0.0)
arrow(11.2, 3.8, 11.2, 5.2, "CHECK + ACT", ly=0.0)
arrow(12.2, 6.0, 12.9, 6.0, "RECORD audit.jsonl", ly=0.28)
arrow(12.2, 5.4, 12.9, 4.0)

# Live discover dashed box
box(4.6, 1.2, 7.6, 1.4,
    ["LIVE discover: GET /it/oncall-coverage (it_oncall_coverage) added on stage",
     "synapse build --discover -> expanded allowlist, same server ID (13 -> 14 tools)"],
    face="#FFFFFF", edge="#9C4221", dashed=True)
arrow(8.4, 2.6, 6.1, 4.3, dashed=True)

ax.text(8, 0.35, "Fallback: cache -> canned JSON | P0 video -> P1 live -> P2 --local Ollama -> P3 Inspector/curl",
        ha="center", fontsize=7.5, color="#4A5568")
fig.tight_layout()
fig.savefig("submission/assets/arch.png", bbox_inches="tight")
print("arch.png saved")

# ---------------- ollama-ps.png ----------------
from PIL import Image, ImageDraw, ImageFont
try:
    font = ImageFont.truetype("consola.ttf", 20)
    bold = ImageFont.truetype("consola.ttf", 22)
except OSError:
    font = ImageFont.load_default()
    bold = font

lines = [
    "$ ollama ps",
    "NAME    ID    SIZE    PROCESSOR    CONTEXT    RUNNER    UNTIL",
    "(no resident models loaded at capture time)",
    "",
    "$ ollama list",
    "NAME                    ID              SIZE      MODIFIED",
    "qwen2.5-coder:7b        dae161e27b0e    4.7 GB    12 minutes ago",
    "tev1:4b                 7954dce22bc6    4.6 GB    7 days ago",
    "llama3.1:8b             46e0c10c039e    4.9 GB    2 months ago",
    "llama3.2:3b             a80c4f17acd5    2.0 GB    3 months ago",
    "qwen3:8b                500a1f067a9f    5.2 GB    3 months ago",
    "qwen3-embedding:0.6b    ac6da0dfba84    639 MB    3 months ago",
]
header = "ollama quota proof 2026-11-24 - see ollama-ps.txt"
tmp = Image.new("RGB", (10, 10))
d0 = ImageDraw.Draw(tmp)
lh = d0.textbbox((0, 0), "Ag", font=font)[3] + 10
W = int(max(d0.textlength(t, font=font) for t in lines + [header])) + 80
H = 60 + len(lines) * lh + 70
img = Image.new("RGB", (W, H), (12, 18, 32))
d = ImageDraw.Draw(img)
d.text((30, 14), header, font=bold, fill=(125, 211, 252))
y = 56
for t in lines:
    fill = (34, 197, 94) if t.startswith("$") else (226, 232, 240)
    d.text((30, y), t, font=font, fill=fill)
    y += lh
d.text((30, H - 40), "qwen2.5-coder:7b pulled (4.7 GB) | spend Rs.0 (local)",
       font=font, fill=(148, 163, 184))
img.save("submission/assets/quota-proof/ollama-ps.png")
print("ollama-ps.png saved")

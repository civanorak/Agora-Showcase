import logging
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def _generate_report_html(
    site_name: str,
    total_count: int,
    verdict_counts: dict[str, int],
    top_paths: list[dict],
    top_uas: list[dict],
    generated_at: str,
) -> str:
    # Calculations
    ai_verdicts = [
        "assistant_browse",
        "crawler_search",
        "crawler_training",
        "shopping_agent",
        "automation_other",
    ]
    ai_count = sum(verdict_counts.get(v, 0) for v in ai_verdicts)
    human_count = verdict_counts.get("human", 0)
    unknown_count = verdict_counts.get("unknown", 0)

    ai_pct = round((ai_count / total_count * 100), 1) if total_count > 0 else 0.0
    human_pct = round((human_count / total_count * 100), 1) if total_count > 0 else 0.0
    round((unknown_count / total_count * 100), 1) if total_count > 0 else 0.0

    assistant_count = verdict_counts.get("assistant_browse", 0)
    shopping_count = verdict_counts.get("shopping_agent", 0)
    crawler_search_count = verdict_counts.get("crawler_search", 0)
    crawler_training_count = verdict_counts.get("crawler_training", 0)
    verdict_counts.get("automation_other", 0)

    # UI display labels and styles
    styles = {
        "assistant_browse": {"label": "Assistant Browse", "color": "#166534", "bg": "#f0fdf4"},
        "crawler_search": {"label": "Search Crawler", "color": "#1e40af", "bg": "#eff6ff"},
        "crawler_training": {"label": "Training Crawler", "color": "#6b21a8", "bg": "#faf5ff"},
        "shopping_agent": {"label": "Shopping Agent", "color": "#b45309", "bg": "#fffbeb"},
        "automation_other": {"label": "Automation Other", "color": "#991b1b", "bg": "#fef2f2"},
        "human": {"label": "Human Traffic", "color": "#3f3f46", "bg": "#f4f4f5"},
        "unknown": {"label": "Unknown", "color": "#71717a", "bg": "#fafafa"},
    }

    # Build the breakdown segments for the HTML progress bar
    breakdown_html = ""
    for v, count in verdict_counts.items():
        if count == 0:
            continue
        pct = (count / total_count * 100) if total_count > 0 else 0
        style = styles.get(v, styles["unknown"])
        breakdown_html += f'<div style="width: {pct}%; background-color: {style["color"]};" title="{style["label"]}: {count} ({round(pct, 1)}%)"></div>'

    # Build the legend list
    legend_html = ""
    for v in [
        "assistant_browse",
        "shopping_agent",
        "crawler_search",
        "crawler_training",
        "automation_other",
        "human",
        "unknown",
    ]:
        count = verdict_counts.get(v, 0)
        if count == 0:
            continue
        pct = (count / total_count * 100) if total_count > 0 else 0
        style = styles.get(v, styles["unknown"])
        legend_html += f"""
        <div class="legend-item">
            <span class="legend-color" style="background-color: {style["color"]};"></span>
            <span class="legend-label">{style["label"]}</span>
            <span class="legend-value">{count} ({round(pct, 1)}%)</span>
        </div>
        """

    # Build the paths table rows
    paths_rows_html = ""
    if not top_paths:
        paths_rows_html = '<tr><td colspan="2" class="text-muted text-center">No AI agent path hits recorded.</td></tr>'
    for idx, item in enumerate(top_paths, 1):
        paths_rows_html += f"""
        <tr>
            <td class="font-mono" style="font-size: 12px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{item["path"]}</td>
            <td class="text-right font-mono font-bold" style="width: 80px;">{item["count"]}</td>
        </tr>
        """

    # Build the user agents table rows
    uas_rows_html = ""
    if not top_uas:
        uas_rows_html = '<tr><td colspan="2" class="text-muted text-center">No AI agent user agents recorded.</td></tr>'
    for idx, item in enumerate(top_uas, 1):
        uas_rows_html += f"""
        <tr>
            <td class="font-mono" style="font-size: 11px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{item["ua"]}</td>
            <td class="text-right font-mono font-bold" style="width: 80px;">{item["count"]}</td>
        </tr>
        """

    # Executive Insight
    insight_text = ""
    if ai_count > 0:
        if assistant_count + shopping_count > (crawler_training_count + crawler_search_count):
            insight_text = (
                f"Your store has a high concentration of **commercial shopping and search assistants** ({round((assistant_count + shopping_count) / ai_count * 100)}% of AI traffic). "
                "These agents are actively browsing products or searching on behalf of buyers, representing high purchase intent."
            )
        else:
            insight_text = (
                f"Most of your agent traffic is driven by **search & training bots** ({round((crawler_training_count + crawler_search_count) / ai_count * 100)}% of AI traffic). "
                "These bots are indexing your content for LLM training or web search, with lower immediate commercial intent but high relevance for future AI-driven search visibility."
            )
    else:
        insight_text = "No AI agent traffic was detected in the last 7 days. Your store traffic consists entirely of humans or unclassified automation."

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AGORA Weekly AI Traffic Report — {site_name}</title>
    <style>
        @page {{
            size: A4;
            margin: 20mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #09090b;
            line-height: 1.5;
            font-size: 13.5px;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
        }}
        .report-container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 2px solid #e4e4e7;
            padding-bottom: 18px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .logo-area h1 {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin: 0;
            color: #09090b;
        }}
        .logo-area span {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #71717a;
        }}
        .meta-area {{
            text-align: right;
        }}
        .meta-area div {{
            font-size: 12px;
            color: #71717a;
        }}
        .meta-area .title {{
            font-size: 15px;
            font-weight: 700;
            color: #09090b;
            margin-bottom: 4px;
        }}
        .kpi-row {{
            display: flex;
            gap: 12px;
            margin-bottom: 28px;
        }}
        .kpi-card {{
            flex: 1;
            border: 1px solid #e4e4e7;
            border-radius: 8px;
            padding: 16px 20px;
            background-color: #fafafa;
        }}
        .kpi-label {{
            font-size: 10px;
            font-weight: 600;
            color: #a1a1aa;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .kpi-value {{
            font-size: 26px;
            font-weight: 700;
            color: #09090b;
            margin-top: 4px;
            letter-spacing: -0.02em;
        }}
        .kpi-note {{
            font-size: 11px;
            color: #71717a;
            margin-top: 4px;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: 700;
            color: #09090b;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-top: 28px;
            margin-bottom: 12px;
            border-bottom: 1px solid #f4f4f5;
            padding-bottom: 6px;
        }}
        .bar-chart-container {{
            margin-bottom: 24px;
        }}
        .bar-chart {{
            display: flex;
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
            background-color: #f4f4f5;
            margin-bottom: 14px;
        }}
        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            font-size: 11.5px;
        }}
        .legend-color {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
            display: inline-block;
        }}
        .legend-label {{
            color: #52525b;
            flex-grow: 1;
        }}
        .legend-value {{
            font-weight: 600;
            color: #09090b;
            margin-left: 8px;
        }}
        .grid-2 {{
            display: flex;
            gap: 20px;
            margin-top: 24px;
        }}
        .grid-col {{
            flex: 1;
            min-width: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}
        th {{
            text-align: left;
            padding: 6px 12px;
            background-color: #fafafa;
            border-bottom: 1px solid #e4e4e7;
            font-weight: 600;
            color: #71717a;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.05em;
        }}
        td {{
            padding: 8px 12px;
            border-bottom: 1px solid #f4f4f5;
            color: #27272a;
        }}
        .text-right {{
            text-align: right;
        }}
        .text-center {{
            text-align: center;
        }}
        .text-muted {{
            color: #a1a1aa;
        }}
        .font-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .font-bold {{
            font-weight: 700;
        }}
        .insight-card {{
            border: 1px dashed #e4e4e7;
            border-radius: 8px;
            padding: 16px 20px;
            background-color: #fafafa;
            margin-top: 28px;
        }}
        .insight-title {{
            font-size: 12.5px;
            font-weight: 700;
            color: #09090b;
            margin-bottom: 6px;
        }}
        .insight-body {{
            font-size: 12px;
            color: #52525b;
        }}
        footer {{
            border-top: 1px solid #e4e4e7;
            margin-top: 40px;
            padding-top: 12px;
            font-size: 11px;
            color: #a1a1aa;
            display: flex;
            justify-content: space-between;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <header>
            <div class="logo-area">
                <h1>AGORA</h1>
                <span>Agent Storefront Analytics</span>
            </div>
            <div class="meta-area">
                <div class="title">Weekly Traffic Report</div>
                <div>Store: <strong>{site_name}</strong></div>
                <div>Generated: {generated_at}</div>
            </div>
        </header>

        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">Total Requests</div>
                <div class="kpi-value">{total_count}</div>
                <div class="kpi-note">Last 7 days total traffic</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">AI Agent Share</div>
                <div class="kpi-value">{ai_pct}%</div>
                <div class="kpi-note">{ai_count} agent interactions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Human Traffic</div>
                <div class="kpi-value">{human_pct}%</div>
                <div class="kpi-note">{human_count} requests</div>
            </div>
        </div>

        <div class="section-title">Traffic Breakdown</div>
        <div class="bar-chart-container">
            <div class="bar-chart">
                {breakdown_html}
            </div>
            <div class="legend-grid">
                {legend_html}
            </div>
        </div>

        <div class="grid-2">
            <div class="grid-col">
                <div class="section-title">Top AI Agent Target Paths</div>
                <table>
                    <thead>
                        <tr>
                            <th>Path</th>
                            <th class="text-right">Hits</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paths_rows_html}
                    </tbody>
                </table>
            </div>
            <div class="grid-col">
                <div class="section-title">Top AI User Agents</div>
                <table>
                    <thead>
                        <tr>
                            <th>User Agent</th>
                            <th class="text-right">Hits</th>
                        </tr>
                    </thead>
                    <tbody>
                        {uas_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="insight-card">
            <div class="insight-title">AGORA Traffic Analysis & Insights</div>
            <div class="insight-body">
                {insight_text}
            </div>
        </div>

        <footer>
            <div>Agora Weekly AI Traffic Report &copy; {datetime.now().year}</div>
            <div>Confidential &middot; Internal Store Analytics</div>
        </footer>
    </div>
</body>
</html>
"""
    return html_content


async def _fetch_report_data(site_id: str) -> dict:
    db = await get_db()

    # Verify site exists
    site_cursor = await db.execute("SELECT name FROM sites WHERE id = ?", (site_id,))
    site_row = await site_cursor.fetchone()
    if not site_row:
        raise HTTPException(status_code=404, detail="Site not found")
    site_name = site_row["name"]

    # 1. Total count
    total_cursor = await db.execute(
        "SELECT COUNT(*) AS count FROM events WHERE site_id = ? AND ts >= datetime('now', '-7 days')",
        (site_id,),
    )
    total_count = (await total_cursor.fetchone())["count"]

    # 2. Verdict breakdown
    verdict_cursor = await db.execute(
        """
        SELECT c.verdict, COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ? AND e.ts >= datetime('now', '-7 days')
        GROUP BY c.verdict
        """,
        (site_id,),
    )
    verdict_rows = await verdict_cursor.fetchall()
    verdict_counts = {
        "assistant_browse": 0,
        "crawler_search": 0,
        "crawler_training": 0,
        "shopping_agent": 0,
        "automation_other": 0,
        "human": 0,
        "unknown": 0,
    }
    for r in verdict_rows:
        if r["verdict"] in verdict_counts:
            verdict_counts[r["verdict"]] = r["count"]
        else:
            verdict_counts["unknown"] += r["count"]

    # 3. Top paths visited by bots
    ai_verdicts = (
        "assistant_browse",
        "crawler_search",
        "crawler_training",
        "shopping_agent",
        "automation_other",
    )
    path_cursor = await db.execute(
        f"""
        SELECT e.path, COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ? AND e.ts >= datetime('now', '-7 days')
          AND c.verdict IN {tuple(ai_verdicts)}
        GROUP BY e.path
        ORDER BY count DESC
        LIMIT 5
        """,
        (site_id,),
    )
    path_rows = await path_cursor.fetchall()
    top_paths = [{"path": r["path"], "count": r["count"]} for r in path_rows]

    # 4. Top user agents for bots
    ua_cursor = await db.execute(
        f"""
        SELECT e.ua, COUNT(*) AS count
        FROM events e
        JOIN classifications c ON c.event_id = e.id
        WHERE e.site_id = ? AND e.ts >= datetime('now', '-7 days')
          AND c.verdict IN {tuple(ai_verdicts)}
        GROUP BY e.ua
        ORDER BY count DESC
        LIMIT 5
        """,
        (site_id,),
    )
    ua_rows = await ua_cursor.fetchall()
    top_uas = [{"ua": r["ua"], "count": r["count"]} for r in ua_rows]

    return {
        "site_name": site_name,
        "total_count": total_count,
        "verdict_counts": verdict_counts,
        "top_paths": top_paths,
        "top_uas": top_uas,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


@router.get("/report/preview", response_class=HTMLResponse)
async def get_report_preview(site_id: str = Query(...)):
    """Serve the HTML version of the weekly traffic report."""
    data = await _fetch_report_data(site_id)
    html_content = _generate_report_html(
        site_name=data["site_name"],
        total_count=data["total_count"],
        verdict_counts=data["verdict_counts"],
        top_paths=data["top_paths"],
        top_uas=data["top_uas"],
        generated_at=data["generated_at"],
    )
    return HTMLResponse(content=html_content)


@router.get("/report/pdf")
async def get_report_pdf(site_id: str = Query(...)):
    """Deprecated (D005): HTML is the canonical report format.

    The WeasyPrint PDF path was removed — it required GTK system libraries that
    could not be provisioned reliably (never worked on Windows dev). This route
    now permanently redirects to the HTML report so any external link keeps
    working.
    """
    return RedirectResponse(
        url=f"/report/preview?site_id={quote(site_id, safe='')}",
        status_code=308,
    )

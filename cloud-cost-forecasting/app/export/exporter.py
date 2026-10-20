"""Export helpers for the Download Analysis feature.

Provides :class:`AnalysisExporter`, which accepts analysis results produced by
the Streamlit application and serializes them to CSV, Excel (XLSX), PDF, or JSON
without re-running any forecasting or anomaly-detection computation.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import xml.sax.saxutils
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Excel support via openpyxl (already a transitive dependency of pandas/streamlit
# in the project environment).
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

# ReportLab is used for PDF generation.  It is declared in requirements.txt.
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

logger = __import__("logging").getLogger(__name__)


def compute_input_hash(file_contents: dict[str, bytes], config: dict) -> str:
    """Compute a stable SHA-256 digest of analysis inputs.

    Parameters
    ----------
    file_contents:
        Mapping of file name to raw file bytes.  Order-independent: keys are
        sorted before hashing so that reordering files does not change the
        digest.
    config:
        Mapping of hyperparameter name to value.  Keys and values are both
        hashed so that any parameter change invalidates the digest.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.  Identical inputs always produce the same
        digest across processes and Python versions.
    """
    h = hashlib.sha256()
    for name in sorted(file_contents.keys()):
        h.update(name.encode("utf-8"))
        h.update(file_contents[name])
    for key in sorted(config.keys()):
        h.update(str(key).encode("utf-8"))
        h.update(str(config[key]).encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_cell(value: Any) -> str:
    """Sanitize a cell value for CSV/Excel to prevent formula injection.

    Spreadsheet applications interpret cells beginning with ``=``, ``+``,
    ``-`` or ``@`` as formulas.  Prefixing such values with a tab character
    neutralizes the interpretation while keeping the text readable.
    Numeric values are returned unchanged.
    """
    if isinstance(value, (int, float, np.integer, np.floating)):
        if np.isnan(value) or np.isinf(value):
            return ""
        return value
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    if text and text[0] in "=+-@":
        return "\t" + text
    return text


def _json_safe(value: Any) -> Any:
    """Convert a Python/pandas/NumPy value into a JSON-safe primitive."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    if isinstance(value, pd.Series):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _escape_pdf_text(text: Any) -> str:
    """Escape text for safe inclusion in ReportLab Paragraph markup.

    ReportLab Paragraph uses XML-like markup, so ``&``, ``<`` and ``>`` in
    user-provided text must be escaped to avoid breaking the document or
    injecting markup.
    """
    if text is None:
        return ""
    return xml.sax.saxutils.escape(str(text))


def _safe_filename(name: str) -> str:
    """Return a filesystem-safe filename derived from *name*."""
    if not name:
        return "billing_analysis"
    # Keep only alphanumerics, dots, underscores and hyphens.
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    safe = safe.strip("._") or "billing_analysis"
    return safe


def _df_to_json_safe(df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    """Convert a DataFrame to a JSON-safe list of records."""
    if df is None or df.empty:
        return []
    df2 = df.copy()
    # Normalize datetime columns to ISO strings.
    for col in df2.columns:
        if pd.api.types.is_datetime64_any_dtype(df2[col]):
            df2[col] = df2[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
    records = df2.to_dict(orient="records")
    return [_json_safe(r) for r in records]


class AnalysisExporter:
    """Serialize analysis results produced by the Streamlit app.

    Parameters
    ----------
    results:
        Dictionary containing any subset of the following keys:

        * ``source_file`` (str) — sanitized uploaded filename
        * ``generated_at`` (datetime) — report generation timestamp
        * ``config`` (dict) — analysis configuration
        * ``raw_data`` (pd.DataFrame or None) — ingested billing data
        * ``daily_data`` (pd.DataFrame or None) — daily aggregated spend
        * ``forecast_data`` (pd.DataFrame or None) — forecast with CI bands
        * ``eval_metrics`` (dict or None) — forecasting evaluation metrics
        * ``ranked_results`` (pd.DataFrame or None) — anomaly cost-impact ranking
        * ``explanations`` (list of dict or None) — anomaly explanations
        * ``anomaly_count`` (int) — number of detected anomalies

    Only keys that are present and non-empty are exported.  Missing keys are
    treated as "no data available for this section" and are omitted honestly
    rather than fabricated.
    """

    def __init__(self, results: Dict[str, Any]):
        self.results = results or {}

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------
    def to_csv(self) -> bytes:
        """Export a single CSV with the best available tabular results.

        Priority order:
        1. Ranked anomaly results (the core analysis output).
        2. Forecast data (if no anomaly results).
        3. Daily aggregated spend (if no forecast).
        4. Empty CSV with a header row (if nothing is available).
        """
        ranked = self.results.get("ranked_results")
        if ranked is not None and not ranked.empty:
            out = ranked.copy()
        else:
            forecast = self.results.get("forecast_data")
            if forecast is not None and not forecast.empty:
                out = forecast.copy()
            else:
                daily = self.results.get("daily_data")
                if daily is not None and not daily.empty:
                    out = daily.copy()
                else:
                    out = pd.DataFrame(
                        {
                            "message": [
                                "No analysis results available. "
                                "Run the analysis in the Streamlit app first."
                            ]
                        }
                    )

        out = out.copy()
        for col in out.columns:
            out[col] = out[col].apply(_sanitize_cell)

        buf = io.StringIO()
        out.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------
    def to_excel(self) -> bytes:
        """Export a multi-sheet XLSX workbook with available results."""
        wb = Workbook()

        # Remove default sheet and add our own in a sensible order.
        wb.remove(wb.active)

        # ---- Summary sheet ----
        ws = wb.create_sheet("Summary")
        ws.append(["FinOps — Cloud Cost Analysis Report"])
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([])
        ws.append(["Generated at", self.results.get("generated_at", datetime.now()).isoformat()])
        ws.append(["Source file", self.results.get("source_file", "—")])
        ws.append([])

        metrics = self.results.get("eval_metrics") or {}
        if metrics:
            ws.append(["Forecast evaluation metrics"])
            ws["A" + str(ws.max_row)].font = Font(bold=True)
            for key in ("mape", "rmse", "mae"):
                if key in metrics and metrics[key] is not None:
                    ws.append([key.upper(), metrics[key]])
        ws.append([])

        cfg = self.results.get("config") or {}
        if cfg:
            ws.append(["Analysis configuration"])
            ws["A" + str(ws.max_row)].font = Font(bold=True)
            for key in sorted(cfg.keys()):
                ws.append([key, cfg[key]])
        ws.append([])

        anomaly_count = self.results.get("anomaly_count", 0)
        ws.append(["Anomalies detected", anomaly_count])
        total_excess = self.results.get("total_excess_cost", 0)
        if total_excess:
            ws.append(["Total excess cost (USD)", total_excess])

        # Auto-size columns roughly.
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    v = str(cell.value) if cell.value is not None else ""
                    max_len = max(max_len, len(v))
                except Exception:
                    pass
            ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 60)

        # ---- Processed Data sheet ----
        raw = self.results.get("raw_data")
        if raw is not None and not raw.empty:
            ws2 = wb.create_sheet("Processed Data")
            self._write_df_to_sheet(ws2, raw)

        # ---- Forecast sheet ----
        forecast = self.results.get("forecast_data")
        if forecast is not None and not forecast.empty:
            ws3 = wb.create_sheet("Forecast")
            self._write_df_to_sheet(ws3, forecast)

        # ---- Anomalies sheet ----
        ranked = self.results.get("ranked_results")
        if ranked is not None and not ranked.empty:
            ws4 = wb.create_sheet("Anomalies")
            # Only keep actual anomaly rows if any are flagged.
            anomaly_rows = ranked[ranked.get("is_anomaly", False) == True]  # noqa: E712
            if anomaly_rows.empty:
                anomaly_rows = ranked
            self._write_df_to_sheet(ws4, anomaly_rows)

        # ---- Configuration sheet ----
        cfg = self.results.get("config")
        if cfg:
            ws5 = wb.create_sheet("Configuration")
            ws5.append(["Key", "Value"])
            for k, v in sorted(cfg.items()):
                ws5.append([k, v])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def _write_df_to_sheet(ws, df: pd.DataFrame) -> None:
        """Write a DataFrame into an openpyxl worksheet with header styling."""
        df2 = df.copy()
        # Normalize datetimes to strings for openpyxl.
        for col in df2.columns:
            if pd.api.types.is_datetime64_any_dtype(df2[col]):
                df2[col] = df2[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
        headers = [_sanitize_cell(c) for c in df2.columns]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for _, row in df2.iterrows():
            ws.append([_sanitize_cell(v) for v in row.tolist()])

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def to_pdf(self) -> bytes:
        """Export a readable PDF report with available results."""
        from reportlab.lib import colors
        from reportlab.platypus import Table as RLTable

        styles = getSampleStyleSheet()
        story: List[Any] = []

        title = "FinOps — Cloud Cost Analysis Report"
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))

        gen_at = self.results.get("generated_at", datetime.now())
        if isinstance(gen_at, datetime):
            gen_at = gen_at.isoformat()
        story.append(Paragraph(f"Generated: {_escape_pdf_text(gen_at)}", styles["Normal"]))
        story.append(
            Paragraph(
                f"Source file: {_escape_pdf_text(self.results.get('source_file', '—'))}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # ---- Executive summary metrics ----
        metrics = self.results.get("eval_metrics") or {}
        if metrics:
            story.append(Paragraph("Forecast Evaluation", styles["Heading2"]))
            data = [["Metric", "Value"]]
            for key in ("mape", "rmse", "mae"):
                if key in metrics and metrics[key] is not None:
                    v = metrics[key]
                    if key == "mape":
                        data.append([key.upper(), f"{v:.2%}"])
                    else:
                        data.append([key.upper(), f"${v:,.2f}"])
            t = RLTable(data)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ]
                )
            )
            story.append(t)
            story.append(Spacer(1, 0.2 * inch))

        # ---- Forecast highlights ----
        forecast = self.results.get("forecast_data")
        if forecast is not None and not forecast.empty:
            story.append(Paragraph("Forecast Summary", styles["Heading2"]))
            first = forecast.iloc[0]
            last = forecast.iloc[-1]
            story.append(
                Paragraph(
                    f"Forecast horizon: {len(forecast)} days "
                    f"({_escape_pdf_text(str(first['date']))} to "
                    f"{_escape_pdf_text(str(last['date']))})",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"First forecasted cost: ${first['forecast_cost_usd']:,.2f}",
                    styles["Normal"],
                )
            )
            story.append(
                Paragraph(
                    f"Last forecasted cost: ${last['forecast_cost_usd']:,.2f}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.2 * inch))

        # ---- Anomaly highlights ----
        ranked = self.results.get("ranked_results")
        anomaly_count = self.results.get("anomaly_count", 0)
        story.append(Paragraph("Anomaly Detection Summary", styles["Heading2"]))
        story.append(Paragraph(f"Anomalies detected: {anomaly_count}", styles["Normal"]))
        if ranked is not None and not ranked.empty:
            anomaly_rows = ranked[ranked.get("is_anomaly", False) == True]  # noqa: E712
            if not anomaly_rows.empty:
                top = anomaly_rows.iloc[0]
                story.append(
                    Paragraph(
                        f"Top anomaly: {_escape_pdf_text(str(top['date']))} — "
                        f"${top['observed_cost']:,.2f} observed vs "
                        f"${top['expected_cost']:,.2f} expected "
                        f"(${top['excess_cost']:,.2f} excess)",
                        styles["Normal"],
                    )
                )
        story.append(Spacer(1, 0.2 * inch))

        # ---- Results table ----
        story.append(Paragraph("Top Anomalies by Cost Impact", styles["Heading2"]))
        if ranked is not None and not ranked.empty:
            display = ranked.copy()
            # Keep only anomaly rows if available; otherwise show all ranked rows.
            anomaly_rows = display[display.get("is_anomaly", False) == True]  # noqa: E712
            if not anomaly_rows.empty:
                display = anomaly_rows
            display = display.head(10)
            table_data = [
                [
                    "Rank",
                    "Date",
                    "Observed (USD)",
                    "Expected (USD)",
                    "Excess (USD)",
                    "Cost Impact",
                ]
            ]
            for _, r in display.iterrows():
                table_data.append(
                    [
                        str(r.get("cost_impact_rank", "")),
                        _escape_pdf_text(str(r.get("date", ""))),
                        f"${r.get('observed_cost', 0):,.2f}",
                        f"${r.get('expected_cost', 0):,.2f}",
                        f"${r.get('excess_cost', 0):,.2f}",
                        f"{r.get('cost_impact_score', 0):.3f}",
                    ]
                )
            t = RLTable(table_data)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(t)
        else:
            story.append(Paragraph("No anomaly data available.", styles["Normal"]))

        buf = io.BytesIO()
        from reportlab.platypus import SimpleDocTemplate

        doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        """Export all available results as a UTF-8 JSON string."""
        out: Dict[str, Any] = {
            "generated_at": _json_safe(self.results.get("generated_at", datetime.now())),
            "source_file": self.results.get("source_file"),
            "config": _json_safe(self.results.get("config")),
        }

        summary = {}
        metrics = self.results.get("eval_metrics") or {}
        if metrics:
            summary["forecast_metrics"] = _json_safe(metrics)
        summary["anomaly_count"] = _json_safe(self.results.get("anomaly_count", 0))
        total_excess = _json_safe(self.results.get("total_excess_cost"))
        if total_excess is not None:
            summary["total_excess_cost_usd"] = total_excess
        out["summary"] = summary

        raw = self.results.get("raw_data")
        if raw is not None and not raw.empty:
            out["raw_data"] = _df_to_json_safe(raw)

        daily = self.results.get("daily_data")
        if daily is not None and not daily.empty:
            out["daily_data"] = _df_to_json_safe(daily)

        forecast = self.results.get("forecast_data")
        if forecast is not None and not forecast.empty:
            out["forecast_data"] = _df_to_json_safe(forecast)

        ranked = self.results.get("ranked_results")
        if ranked is not None and not ranked.empty:
            out["ranked_results"] = _df_to_json_safe(ranked)

        explanations = self.results.get("explanations")
        if explanations:
            out["explanations"] = _json_safe(explanations)

        return json.dumps(out, indent=2, ensure_ascii=False)


def export_results(results: Dict[str, Any]) -> AnalysisExporter:
    """Factory convenience returning an :class:`AnalysisExporter` for *results*."""
    return AnalysisExporter(results)

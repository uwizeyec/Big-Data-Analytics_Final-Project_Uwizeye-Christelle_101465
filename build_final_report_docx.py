"""Create an editable Word version of the final technical report.

Run: python build_final_report_docx.py
"""

from __future__ import annotations

import zipfile
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.shared import Inches, Pt


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT = PROJECT_DIR / "docs" / "final_technical_report.docx"
FIGURES = PROJECT_DIR / "data" / "visualizations"
ARCHITECTURE_FIGURE = FIGURES / "00_system_architecture.png"
APPENDIX_SOURCE = PROJECT_DIR / "IMPLEMENTATION REQUIREMENTS_Screenshort_Report.docx"
APPENDIX_IMAGE_DIR = PROJECT_DIR / "data" / "appendix_screenshots"
FIGURE_NUMBER = 0


def heading(document: Document, text: str, level: int = 1) -> None:
    document.add_heading(text, level=level)


def paragraph(document: Document, text: str, bold_start: str | None = None) -> None:
    p = document.add_paragraph()
    if bold_start and text.startswith(bold_start):
        p.add_run(bold_start).bold = True
        p.add_run(text[len(bold_start):])
    else:
        p.add_run(text)
    p.paragraph_format.space_after = Pt(6)


def add_field(paragraph, instruction: str) -> None:
    """Insert a Word field; Word can update it with Ctrl+A then F9."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction_node = OxmlElement("w:instrText")
    instruction_node.set(qn("xml:space"), "preserve")
    instruction_node.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "0"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    paragraph._p.append(begin)
    paragraph._p.append(instruction_node)
    paragraph._p.append(separate)
    paragraph._p.append(placeholder)
    paragraph._p.append(end)


def caption(document: Document, text: str) -> None:
    """Add a simple Word-compatible caption (no dynamic Word field codes)."""
    global FIGURE_NUMBER
    FIGURE_NUMBER += 1
    p = document.add_paragraph()
    p.style = "Caption"
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Figure {FIGURE_NUMBER}. {text}")
    for run in p.runs:
        run.italic = True
        run.font.size = Pt(9)


def add_table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for values in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = value


def add_figure(document: Document, filename: str, caption_text: str) -> None:
    path = FIGURES / filename
    if not path.exists():
        document.add_paragraph(f"[Figure not found: {path.name}. Run create_part4_visualizations.py.]")
        return
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(6.25))
    caption(document, caption_text)


def create_architecture_diagram() -> Path:
    """Create a compact architecture image for the technical report."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(10, 4.2))
    axis.set_xlim(0, 10)
    axis.set_ylim(0, 5)
    axis.axis("off")

    boxes = [
        (0.4, 2.0, 1.65, 1.0, "Synthetic JSON\nGenerator", "#dceefb"),
        (3.0, 3.35, 1.8, 0.9, "MongoDB\nCatalog • Users • Transactions", "#d9f0d3"),
        (3.0, 0.75, 1.8, 0.9, "HBase\nTime-series Sessions", "#fee8c8"),
        (6.1, 2.0, 1.75, 1.0, "Apache Spark\nClean • SQL • Join", "#e6d8f0"),
        (8.55, 2.0, 1.1, 1.0, "Insights\nCSV • PNG\nReport", "#fddde6"),
    ]
    for x, y, width, height, label, color in boxes:
        rectangle = plt.Rectangle((x, y), width, height, facecolor=color, edgecolor="#264653", linewidth=1.5)
        axis.add_patch(rectangle)
        axis.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=9, weight="bold")

    arrows = [
        ((2.05, 2.65), (3.0, 3.8)), ((2.05, 2.35), (3.0, 1.2)),
        ((4.8, 3.8), (6.1, 2.65)), ((4.8, 1.2), (6.1, 2.35)),
        ((7.85, 2.5), (8.55, 2.5)),
    ]
    for start, end in arrows:
        axis.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.6, "color": "#264653"})

    axis.text(5.0, 4.8, "E-Commerce Big Data Analytics Architecture", ha="center", fontsize=14, weight="bold")
    plt.tight_layout()
    plt.savefig(ARCHITECTURE_FIGURE, dpi=220, bbox_inches="tight")
    plt.close()
    return ARCHITECTURE_FIGURE


def extract_appendix_screenshots() -> list[Path]:
    """Extract embedded screenshot images from the supplied evidence document."""
    if not APPENDIX_SOURCE.exists():
        return []
    APPENDIX_IMAGE_DIR.mkdir(parents=True)
    image_paths: list[Path] = []
    with zipfile.ZipFile(APPENDIX_SOURCE) as archive:
        media_names = sorted(
            name for name in archive.namelist()
            if name.startswith("word/media/") and not name.endswith("/")
        )
        for number, media_name in enumerate(media_names, start=1):
            extension = Path(media_name).suffix.lower()
            destination = APPENDIX_IMAGE_DIR / f"appendix_screenshot_{number:02d}{extension}"
            destination.write_bytes(archive.read(media_name))
            image_paths.append(destination)
    return image_paths


def add_toc(document: Document, title: str, instruction: str) -> None:
    heading(document, title)
    p = document.add_paragraph()
    add_field(p, instruction)
    note = document.add_paragraph("In Microsoft Word, click this table and press F9 (or Ctrl+A, then F9) to update it.")
    note.runs[0].italic = True


def main() -> None:
    # The compact report is retained as a separate file on request, so the
    # complete appendix version is never overwritten.
    global FIGURE_NUMBER
    FIGURE_NUMBER = 0
    compact = "--previous-version" in sys.argv
    output = (
        PROJECT_DIR / "docs" / "final_technical_report_simple.docx"
        if compact else OUTPUT
    )
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    normal = document.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)

    title = document.add_heading("E-Commerce Big Data Analytics Platform", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("Technical Report\n").bold = True
    subtitle.add_run("Student: [Your name]    Student ID: [Your student ID]\n")
    subtitle.add_run("Course: Big Data Analytics    Submission date: [Date]")

    if not compact:
        add_toc(document, "Table of Contents", 'TOC \\o "1-3" \\h \\z \\u')
        add_toc(document, "Table of Figures", 'TOC \\h \\z \\c "Figure"')
        document.add_page_break()

    heading(document, "1. Introduction and system architecture")
    paragraph(document, "This project implements an e-commerce analytics platform over a synthetic 90-day dataset containing 10,000 users, 5,000 products, 25 categories, 50,000 transactions, and 200,000 browsing sessions. It demonstrates how MongoDB, HBase, and Apache Spark support complementary analytical workloads.")
    paragraph(document, "MongoDB stores business documents including product catalog records, user profiles, and transactions with embedded line items. HBase stores time-oriented browsing sessions for efficient retrieval of one user's activity. Spark cleans the raw JSON, creates typed Parquet datasets, runs SQL analytics, and joins the logical HBase and MongoDB sources for an integrated funnel analysis.")
    add_table(document, ["Component", "Primary responsibility"], [
        ["MongoDB", "Nested catalog, user, and transaction documents; document aggregations."],
        ["HBase", "Time-series browsing sessions retrieved by user/time prefix."],
        ["Spark", "Cleaning, transformation, SQL analytics, joins, and static visualizations."],
    ])
    create_architecture_diagram()
    add_figure(document, "00_system_architecture.png", "System architecture and flow of data from generation to reporting.")

    heading(document, "2. Data modelling and storage decisions")
    heading(document, "2.1 MongoDB", 2)
    paragraph(document, "MongoDB database ecommerce_analytics contains category documents with embedded subcategories, product documents with price history, user documents with a summarized purchase history, and transaction documents with embedded item lines. Embedding is appropriate because the related fields are usually created and read together. Indexes were created for category, user/time, transaction time, and item product/category analytical filters.")
    add_table(document, ["Collection", "Key modelling decision"], [
        ["categories", "Small category hierarchy embedded in each category document."],
        ["products", "Product details, stock, category snapshot, and bounded price history."],
        ["users", "Profile plus embedded order/spend/preferred-category summary."],
        ["transactions", "Header and historical item lines embedded in one purchase document."],
    ])
    paragraph(document, "All 25 categories, 5,000 products, 10,000 users, and 50,000 transactions were loaded. The two implemented aggregation pipelines identify top products by recognized revenue and segment customers by purchase behavior. The load and index operation took 3.413 seconds.")

    heading(document, "2.2 HBase", 2)
    paragraph(document, "The user_sessions HBase row key is user_id|ISO-8601-start_time|session_id. It co-locates one user's sessions and preserves chronological order for an efficient prefix scan. Column families meta, device, geo, and activity group related attributes. The product_daily_metrics table uses product_id|YYYY-MM-DD for future daily performance facts.")
    paragraph(document, "A deterministic 10,000-session representative subset was loaded and verified. The example prefix scan for user_005955 returned the user's stored session data, including device, referrer, browsing counts, and conversion status.")

    heading(document, "3. Spark batch processing and SQL analytics")
    paragraph(document, "The Spark batch application standardizes IDs, parses timestamps, casts numerical fields, filters invalid records, explodes nested transaction items, and joins items to known products. The resulting Parquet datasets contain 10,000 cleaned users, 5,000 products, and 109,863 transaction-item rows; 92,216 transaction items have recognized statuses (completed, shipped, or delivered).")
    paragraph(document, "A co-purchase recommendation indicator self-joins recognized transaction items on transaction_id. The condition product A < product B prevents mirrored pairs. Spark produced 68,565 unique pairs. Since the generated catalog is large and baskets are mostly random, the top observed count of two represents a weak demonstration signal rather than a production-quality recommendation.")
    paragraph(document, "Spark SQL registers logical MongoDB user/product/transaction views and HBase session/page-view views. Query one joins engagement measures to purchase value by state and value segment. Query two calculates category product-detail views, recognized purchases, units, revenue, and purchases per 100 views. The sales numerator is restricted to the HBase session cohort, maintaining a valid shared denominator.")

    heading(document, "4. Integrated analytics workflow")
    paragraph(document, "Business question: Which device type and acquisition channel create the strongest progression from browsing, through cart activity, to a recognized purchase?")
    paragraph(document, "Spark reads the reproducible JSON sample loaded into HBase and cleaned MongoDB-shaped transaction/product Parquet records. It derives browsing and cart stages from HBase conversion status, filters MongoDB records to recognized statuses, and joins both sources by session_id. A left join preserves non-purchasing browsing sessions. The final aggregation returns funnel counts, conversion rates, orders, units, revenue, and revenue per purchasing session by device type and referrer.")
    paragraph(document, "The integrated result contains 10,000 browsing sessions, 6,517 cart sessions, and 2,031 sessions matched to recognized purchases. HBase is appropriate for session-event evidence, MongoDB for flexible purchase documents, and Spark for the cross-system join and aggregate computation.")

    heading(document, "5. Visualizations and business insights")
    add_figure(document, "01_monthly_sales_performance.png", "Monthly recognized item revenue and recognized order volume.")
    paragraph(document, "Revenue and order volume should be interpreted together. A change in revenue without the same change in order volume may indicate a change in average basket value rather than customer volume.")
    add_figure(document, "02_top_category_revenue.png", "Top ten product categories by recognized item revenue.")
    paragraph(document, "High-revenue categories are candidates for inventory monitoring and marketing attention. The measure is revenue, not profit, because product cost, returns, delivery cost, and all discount effects are outside this simplified model.")
    add_figure(document, "03_customer_purchase_segments.png", "Customer segmentation by recognized purchase frequency.")
    paragraph(document, "The frequency distribution distinguishes one-time buyers from repeat customers. This can support retention and re-engagement analysis, although the synthetic data does not establish the causes of repeat purchasing.")
    add_figure(document, "04_cross_system_conversion_funnel.png", "Cross-system funnel from HBase browsing evidence to MongoDB recognized purchases.")
    paragraph(document, "The funnel shows substantial drop-off after cart activity. It identifies the checkout stage as a worthwhile investigation point, but it does not prove why users abandoned a cart.")

    heading(document, "6. Scalability, limitations, and future work")
    paragraph(document, "The laptop implementation uses Spark local[2] with eight shuffle partitions. Typed Parquet avoids repeated JSON parsing; early recognized-status filtering reduces join input; and deduplication plus product A < product B reduces recommendation self-join output. Production deployment would scale executors and partitions, partition transaction Parquet by date, use time-bounded HBase scans, and possibly add native Spark connectors.")
    paragraph(document, "The records are synthetic and largely random, so results show method demonstrations and associations rather than causal business conclusions. Only a 10,000-session HBase subset was loaded. Future work could load the full stream, incorporate refunds and product costs, create daily HBase product metrics, and use richer behavioral features in a recommendation model.")

    heading(document, "7. Reproducibility")
    paragraph(document, "The repository README provides the commands required to regenerate the raw data, start MongoDB/HBase, load both systems, run Spark processing, run the integrated funnel, and create all visualizations. Key outputs and full query details are retained in JSON summary files. Screenshots of MongoDB, HBase, Spark SQL, integration, and visualization completion should be included as appendices or selected evidence if required by the course instructions.")

    heading(document, "8. Conclusion")
    paragraph(document, "This project demonstrates that an e-commerce analytics platform benefits from using different big-data technologies for the tasks they handle best. MongoDB provided a flexible document model for catalog, user, and transaction data; HBase provided an efficient key-oriented design for time-series browsing sessions; and Apache Spark provided scalable-style batch processing, SQL analysis, and cross-system integration.")
    paragraph(document, "The completed analysis produced cleaned Parquet facts, MongoDB aggregation results, HBase session retrieval, recommendation indicators, category and customer analytics, and an integrated funnel from browsing to recognized purchase. In particular, the shared 10,000-session cohort made it possible to calculate a consistent cross-system funnel of 10,000 browsing sessions, 6,517 cart sessions, and 2,031 recognized-purchase sessions.")
    paragraph(document, "Although the data is synthetic and the local execution is not a production cluster, the solution establishes a reproducible architecture and a clear path to scale: distributed storage, larger HBase scans, Spark connectors, incremental aggregates, and richer behavioural models. The results illustrate how combining document, wide-column, and distributed-processing technologies can turn operational e-commerce records into actionable analytical evidence.")

    if not compact:
        document.add_page_break()
        heading(document, "Appendix A — Implementation Evidence Screenshots")
        paragraph(document, "The following screenshots document the execution evidence collected while implementing MongoDB, HBase, Spark, integration, and visualization tasks.")
        screenshots = extract_appendix_screenshots()
        if not screenshots:
            paragraph(document, "No screenshot source document was found. Add screenshots manually if required.")
        for index, screenshot in enumerate(screenshots, start=1):
            p = document.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                p.add_run().add_picture(str(screenshot), width=Inches(6.25))
                caption(document, f"Appendix implementation evidence screenshot {index}.")
            except Exception:
                paragraph(document, f"[Could not embed appendix screenshot {index}: {screenshot.name}]")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)
    print(f"Created Word report: {output}")


if __name__ == "__main__":
    main()

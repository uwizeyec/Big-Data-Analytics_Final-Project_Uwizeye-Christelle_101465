"""Create a 10-minute defence presentation for the e-commerce analytics project."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

ROOT = Path(r"D:\P.D\AUCA\Masters Big Data\Courses\Semester 3\Big Data Analytics\E-Commerce_Final Project_Uwizeye Christelle_101465")
OUT = ROOT / "docs" / "E-Commerce_Defense_Presentation_101465.pptx"
NOTES = ROOT / "docs" / "defense_speaker_notes_101465.md"
VIZ = ROOT / "data" / "visualizations"

NAVY = RGBColor(20, 47, 82); BLUE = RGBColor(38, 111, 182); TEAL = RGBColor(0, 142, 138)
ORANGE = RGBColor(236, 132, 35); WHITE = RGBColor(255, 255, 255); DARK = RGBColor(34, 42, 52); GRAY = RGBColor(97, 107, 118)


def title(slide, text, time_label):
    t = slide.shapes.add_textbox(Inches(.55), Inches(.28), Inches(10.4), Inches(.55))
    p = t.text_frame.paragraphs[0]; p.text = text; p.font.size = Pt(27); p.font.bold = True; p.font.color.rgb = NAVY
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.25), Inches(.28), Inches(1.45), Inches(.42))
    badge.fill.solid(); badge.fill.fore_color.rgb = TEAL; badge.line.fill.background()
    p = badge.text_frame.paragraphs[0]; p.text = time_label; p.font.size = Pt(11); p.font.bold = True; p.font.color.rgb = WHITE; p.alignment = PP_ALIGN.CENTER
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.55), Inches(1.05), Inches(12.15), Inches(.05))
    line.fill.solid(); line.fill.fore_color.rgb = TEAL; line.line.fill.background()


def footer(slide, n):
    b = slide.shapes.add_textbox(Inches(.55), Inches(7.16), Inches(12.1), Inches(.16))
    p = b.text_frame.paragraphs[0]; p.text = f"AUCA Big Data Analytics Final Project  |  Uwizeye Christelle  |  ID: 101465  |  {n}"
    p.font.size = Pt(8); p.font.color.rgb = GRAY; p.alignment = PP_ALIGN.RIGHT


def bullet_slide(prs, heading, time_label, points, number):
    s = prs.slides.add_slide(prs.slide_layouts[6]); title(s, heading, time_label)
    box=s.shapes.add_textbox(Inches(.85), Inches(1.45), Inches(11.6), Inches(5.45)); tf=box.text_frame; tf.word_wrap=True
    for i, point in enumerate(points):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.text=point; p.font.size=Pt(19); p.font.color.rgb=DARK; p.space_after=Pt(12)
    footer(s, number); return s


def code_box(slide, x, y, w, h, heading, code):
    shape=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb=RGBColor(244,247,250); shape.line.color.rgb=RGBColor(204,216,228)
    tx=slide.shapes.add_textbox(Inches(x+.18), Inches(y+.12), Inches(w-.36), Inches(.28)); p=tx.text_frame.paragraphs[0]; p.text=heading; p.font.bold=True; p.font.size=Pt(13); p.font.color.rgb=NAVY
    body=slide.shapes.add_textbox(Inches(x+.18), Inches(y+.52), Inches(w-.36), Inches(h-.65)); tf=body.text_frame; tf.word_wrap=True
    p=tf.paragraphs[0]; p.text=code; p.font.name='Consolas'; p.font.size=Pt(12); p.font.color.rgb=DARK


def image_slide(prs, heading, time_label, name, caption, number):
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,heading,time_label)
    s.shapes.add_picture(str(VIZ/name), Inches(.92), Inches(1.35), width=Inches(11.5), height=Inches(5.45))
    c=s.shapes.add_textbox(Inches(.95), Inches(6.82), Inches(11.5), Inches(.2)); p=c.text_frame.paragraphs[0]; p.text=caption; p.font.size=Pt(10); p.font.italic=True; p.font.color.rgb=GRAY
    footer(s,number)


def build():
    prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
    # 1
    s=prs.slides.add_slide(prs.slide_layouts[6]); bg=s.background.fill; bg.solid(); bg.fore_color.rgb=NAVY
    t=s.shapes.add_textbox(Inches(.8),Inches(1.05),Inches(11.7),Inches(1.1)); p=t.text_frame.paragraphs[0]; p.text='Distributed Multi-Model Analytics\nfor E-Commerce Data'; p.font.size=Pt(34); p.font.bold=True; p.font.color.rgb=WHITE; p.alignment=PP_ALIGN.CENTER
    st=s.shapes.add_textbox(Inches(1),Inches(3.15),Inches(11.3),Inches(.55)); p=st.text_frame.paragraphs[0]; p.text='Final Project Defence'; p.font.size=Pt(22); p.font.color.rgb=RGBColor(205,228,246); p.alignment=PP_ALIGN.CENTER
    inf=s.shapes.add_textbox(Inches(1),Inches(5.65),Inches(11.3),Inches(.6)); p=inf.text_frame.paragraphs[0]; p.text='Uwizeye Christelle  |  Student ID: 101465  |  AUCA Big Data Analytics'; p.font.size=Pt(17); p.font.color.rgb=WHITE; p.alignment=PP_ALIGN.CENTER
    # 2
    image_slide(prs,'1. Architecture and dataset','0:00–1:00','00_system_architecture.png','Generated JSON data is stored according to the strongest access pattern, then analysed using Spark.',2)
    # 3
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,'2. Data modelling decisions','1:00–2:30')
    code_box(s,.75,1.5,5.85,4.55,'MongoDB transaction document (simplified)','''{\n  "transaction_id": "txn_...",\n  "user_id": "user_005955",\n  "status": "recognised",\n  "items": [{"product_id": "prod_01748",\n             "quantity": 2, "price": 111.33}]\n}''')
    code_box(s,6.75,1.5,5.85,4.55,'HBase browsing-session row key','''Row key\nuser_005955|2026-09-25T00:48:37|sess_e69952bc68\n\nColumn families\nmeta  → session ID, times, status\ndevice → type, browser, OS\ngeo   → country, city, IP\nactivity → views, cart, products\n\nWhy: sessions for one user are stored together.''')
    x=s.shapes.add_textbox(Inches(.9),Inches(6.35),Inches(11.7),Inches(.4)); p=x.text_frame.paragraphs[0]; p.text='MongoDB supports flexible business documents; HBase supports fast time-ordered retrieval of one user’s events.'; p.font.size=Pt(14); p.font.bold=True; p.font.color.rgb=TEAL; p.alignment=PP_ALIGN.CENTER; footer(s,3)
    # 4
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,'3. Query demonstration: MongoDB and HBase','2:30–5:30')
    code_box(s,.75,1.42,5.85,4.7,'MongoDB aggregation — product popularity','''transactions.aggregate([\n  {$match: {status: "recognised"}},\n  {$unwind: "$items"},\n  {$group: {_id: "$items.product_id",\n    units: {$sum: "$items.quantity"},\n    revenue: {$sum: {$multiply:\n      ["$items.quantity", "$items.price"]}}}},\n  {$sort: {revenue: -1}}, {$limit: 10}\n])\n\nReturns: top products by recognised\nitem revenue and units sold.''')
    code_box(s,6.75,1.42,5.85,4.7,'HBase query — one user’s session activity','''# user prefix scan\nscan 'user_sessions', {\n  STARTROW => 'user_005955|',\n  STOPROW  => 'user_005955}',\n  LIMIT => 20\n}\n\nReturns session metadata, device,\nview counts and cart behaviour.\n\nEfficient because the row key starts\nwith user_id.''')
    q=s.shapes.add_textbox(Inches(.85),Inches(6.35),Inches(11.7),Inches(.35)); p=q.text_frame.paragraphs[0]; p.text='Live-demo preparation: have MongoDB analytics and the HBase shell query result already open.'; p.font.size=Pt(13);p.font.bold=True;p.font.color.rgb=ORANGE;p.alignment=PP_ALIGN.CENTER;footer(s,4)
    # 5
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,'4. Spark cleaning and recommendation indicator','5:30–6:40')
    code_box(s,.75,1.5,7.05,4.7,'PySpark processing logic','''# normalize records and explode transaction line items\nclean_items = transactions.filter("status = 'recognised'") \\\n    .select('transaction_id', 'user_id',\n            explode('items').alias('item'))\n\n# products bought in the same transaction\npairs = clean_items.alias('a').join(clean_items.alias('b'),\n    (col('a.transaction_id') == col('b.transaction_id')) &\n    (col('a.item.product_id') < col('b.item.product_id')))\n\n# count co-purchases as recommendation indicators''')
    code_box(s,8.0,1.5,4.6,4.7,'Batch output','''10,000 users cleaned\n5,000 products cleaned\n109,863 transaction items\n92,216 recognised items\n68,565 unique product pairs\n\nInterpretation:\nPairs indicate possible\nrecommendations; counts are\nweak in synthetic random data.''')
    footer(s,5)
    # 6
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,'5. Spark SQL analytics','6:40–7:30')
    code_box(s,.8,1.45,11.7,4.8,'Category view-to-purchase funnel (simplified Spark SQL)','''SELECT p.category_id,\n       COUNT(*) AS product_detail_views,\n       COUNT(DISTINCT t.transaction_id) AS purchasing_transactions,\n       ROUND(100.0 * COUNT(DISTINCT t.transaction_id) / COUNT(*), 2)\n         AS purchases_per_100_product_views\nFROM hbase_page_views v\nJOIN mongo_products p ON v.product_id = p.product_id\nLEFT JOIN mongo_transaction_items t ON v.session_id = t.session_id\nWHERE t.status = 'recognised'\nGROUP BY p.category_id\nORDER BY purchases_per_100_product_views DESC;\n\nThis demonstrates SQL logic over DataFrames representing data that could reside in HBase and MongoDB.''')
    footer(s,6)
    # 7
    s=prs.slides.add_slide(prs.slide_layouts[6]); title(s,'6. Integrated business question and workflow','7:30–8:15')
    box=s.shapes.add_textbox(Inches(.9),Inches(1.5),Inches(11.5),Inches(.65)); p=box.text_frame.paragraphs[0];p.text='Business question: Which browsing journeys turn into recognised purchases?';p.font.size=Pt(23);p.font.bold=True;p.font.color.rgb=NAVY;p.alignment=PP_ALIGN.CENTER
    steps=[('HBase','Browsing sessions\nviews, carts, device, referrer',TEAL),('Spark','Join and aggregate\nusing session_id',ORANGE),('MongoDB','Recognised orders\nitems and revenue',BLUE)]
    for i,(name,desc,color) in enumerate(steps):
        x=1.0+i*4.1; sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(3),Inches(3.1),Inches(1.35));sh.fill.solid();sh.fill.fore_color.rgb=color;sh.line.fill.background();tf=sh.text_frame;tf.clear();p=tf.paragraphs[0];p.text=name;p.font.size=Pt(20);p.font.bold=True;p.font.color.rgb=WHITE;p.alignment=PP_ALIGN.CENTER;p=tf.add_paragraph();p.text=desc;p.font.size=Pt(11);p.font.color.rgb=WHITE;p.alignment=PP_ALIGN.CENTER
        if i<2:
            a=s.shapes.add_textbox(Inches(x+3.2),Inches(3.42),Inches(.6),Inches(.3));p=a.text_frame.paragraphs[0];p.text='→';p.font.size=Pt(28);p.font.color.rgb=GRAY;p.alignment=PP_ALIGN.CENTER
    out=s.shapes.add_textbox(Inches(1),Inches(5.25),Inches(11.2),Inches(.6));p=out.text_frame.paragraphs[0];p.text='Outcome: conversion rates and revenue can be compared by device type and referral source.';p.font.size=Pt(19);p.font.color.rgb=DARK;p.alignment=PP_ALIGN.CENTER;footer(s,7)
    # 8 funnel
    image_slide(prs,'7. Integrated funnel result','8:15–9:00','04_cross_system_conversion_funnel.png','Result: 10,000 browsing sessions → 6,517 cart sessions → 2,031 recognised purchases.',8)
    # 9 visuals
    image_slide(prs,'8. Visual insight: category revenue','9:00–9:30','02_top_category_revenue.png','The chart helps prioritize product categories for merchandising and marketing analysis.',9)
    # 10 limits
    bullet_slide(prs,'9. Reflection, scalability and conclusion','9:30–10:00',[
        'MongoDB: indexes support document and aggregation queries; embed line items to retrieve an order in one read.',
        'HBase: user-prefixed row keys provide locality for session-history retrieval.',
        'Spark: Parquet and distributed DataFrame operations support larger-scale transformations and joins.',
        'Honest limitation: data is synthetic and only a representative 10,000-session HBase sample was loaded.',
        'Conclusion: each technology was selected for the workload it performs best.'
    ],10)
    # 11 Q&A
    s=prs.slides.add_slide(prs.slide_layouts[6]); bg=s.background.fill;bg.solid();bg.fore_color.rgb=NAVY
    b=s.shapes.add_textbox(Inches(1),Inches(2.3),Inches(11.3),Inches(1));p=b.text_frame.paragraphs[0];p.text='Thank you — Questions?';p.font.size=Pt(37);p.font.bold=True;p.font.color.rgb=WHITE;p.alignment=PP_ALIGN.CENTER
    q=s.shapes.add_textbox(Inches(1.4),Inches(4.0),Inches(10.5),Inches(1.1));p=q.text_frame.paragraphs[0];p.text='Be ready to explain: data-model trade-offs, row-key design, Spark joins, scalability, and the limitation of synthetic data.';p.font.size=Pt(19);p.font.color.rgb=RGBColor(205,228,246);p.alignment=PP_ALIGN.CENTER
    return prs


NOTES_TEXT = '''# Defence speaker notes — 18-minute format\n\n## Before your name is called\nOpen this presentation, your GitHub repository, and Command Prompt windows with these outputs ready. The first 10 minutes are your presentation; the remaining 8 minutes are questions. Do not spend time starting Docker, HBase, MongoDB, or Spark during the presentation.\n\n## Slide 1 — 0:00–0:15\nSay your name, ID, project title and technologies: MongoDB, HBase and Spark.\n\n## Slide 2 — 0:15–1:00\nFollow the architecture arrows. Explain that one system is not ideal for all data patterns.\n\n## Slide 3 — 1:00–2:30\nPoint to MongoDB's embedded transaction items. Then explain that the HBase key begins with user ID, allowing a prefix scan to retrieve that user's sessions efficiently.\n\n## Slide 4 — 2:30–5:30 (live demo)\nRun or show saved output from:\n```cmd\npython mongodb_analytics.py\ndocker exec final-hbase hbase shell /tmp/hbase_query_user_sessions.rb user_005955\n```\nExplain aggregation stages: filter recognised orders, unwind items, group and sort. For HBase, explain prefix scan efficiency.\n\n## Slide 5 — 5:30–6:40\nShow saved Spark output from `python spark_batch_recommendations.py`. Explain cleaning, explode, self-join and count. State clearly that recommendation pairs are indicators, not proof of preference.\n\n## Slide 6 — 6:40–7:30\nShow `python spark_sql_analytics.py`. Explain that the SQL joins browsing/page-view rows with product and transaction data.\n\n## Slides 7–8 — 7:30–9:00\nState the integrated question, inputs and result. Key result: 10,000 browsing, 6,517 cart and 2,031 recognised purchase sessions.\n\n## Slides 9–10 — 9:00–10:00\nShow the category chart. Give the limitation: synthetic data and 10,000-session HBase sample. Close with the technology-fit conclusion.\n\n## Q&A — 10:00–18:00\nLikely questions: Why MongoDB instead of HBase for orders? Why a user-first HBase row key? What happens at larger scale? Why is the recommendation evidence weak? How does Spark join data sources?\n'''

if __name__=='__main__':
    prs=build(); OUT.parent.mkdir(parents=True,exist_ok=True); prs.save(OUT); NOTES.write_text(NOTES_TEXT,encoding='utf-8')
    print(f'Created {OUT} ({len(prs.slides)} slides)')
    print(f'Created {NOTES}')

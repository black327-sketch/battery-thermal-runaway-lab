# Report Consistency Report

## What Changed
- Report preview still uses `report_ctx` plus `generate_formal_report(report_ctx)`.
- Markdown download uses the same `formal_md` string shown in preview.
- HTML download now uses `generate_formal_report_html(formal_md)` and `mime="text/html"`; it is no longer Markdown served as HTML.
- Word export now renders the same shared Markdown report into docx tables/paragraphs, reducing divergence from preview.
- The page stores the last generated `ctx`, Markdown, and HTML in `st.session_state["formal_report_last"]` for inspection.

## Verified Structure
- Markdown starts from the shared generated report.
- HTML starts with a true `<!doctype html>` document and includes converted tables.
- docx generation returns non-empty bytes from the same shared report content.

## Tests
- `tests/test_report_generator.py` includes `test_formal_report_html_and_docx_share_markdown_source`.
- Full test suite with backup ignored: `221 passed`.
- Screenshot: `artifacts/screenshots/report-preview.png`.

## Remaining Limitations
- The docx exporter now prioritizes content consistency over the previous handcrafted rich layout. Tables and headings are preserved; embedded figure handling from the old exporter is no longer the primary path.

from pathlib import Path
import markdown
src = Path('Be_An_Earth_System_Trend_Detective_Reference_AR.md').read_text(encoding='utf-8-sig')
body = markdown.markdown(src, extensions=['tables','fenced_code','sane_lists'])
html = '''<!doctype html><html lang="ar"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 14mm 15mm 15mm; }
* { box-sizing:border-box; }
body { direction:rtl; unicode-bidi:plaintext; font-family:"Segoe UI",Tahoma,Arial,sans-serif; font-size:10.5pt; line-height:1.55; color:#182334; }
h1 { color:#0a5b70; font-size:23pt; line-height:1.25; border-bottom:2px solid #42a9aa; padding-bottom:8px; margin:0 0 12px; }
h2 { color:#0a5b70; font-size:16pt; border-bottom:1px solid #d6e5e8; padding-bottom:4px; margin-top:20px; }
h3 { color:#155f71; font-size:12pt; margin:14px 0 6px; }
p { margin:6px 0 9px; }
li { margin:3px 0; }
table { direction:rtl; border-collapse:collapse; width:100%; font-size:9pt; margin:9px 0 14px; page-break-inside:avoid; }
th { background:#e7f2f3; color:#143c4d; }
th,td { border:1px solid #c5d4da; padding:6px 7px; vertical-align:top; }
blockquote { border-right:3px solid #42a9aa; padding:6px 12px; margin:10px 0; background:#f2f8f8; }
code { direction:ltr; unicode-bidi:embed; font-family:Consolas,monospace; font-size:9pt; color:#8b3d19; }
pre { direction:ltr; text-align:left; white-space:pre-wrap; overflow-wrap:anywhere; background:#f3f6f9; border:1px solid #d8e0e5; padding:9px 12px; border-radius:4px; page-break-inside:avoid; }
a { color:#075985; text-decoration:underline; overflow-wrap:anywhere; }
hr { border:0; border-top:1px solid #ccd7dd; margin:15px 0; }
strong { color:#102a43; }
</style></head><body>''' + body + '</body></html>'
Path('reference_print.html').write_text(html, encoding='utf-8')

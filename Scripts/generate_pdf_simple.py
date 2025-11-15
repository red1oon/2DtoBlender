#!/usr/bin/env python3
"""
Generate PDF from Executive Summary markdown via HTML intermediate
"""

import subprocess
import sys
from pathlib import Path

def markdown_to_html(md_path, html_path):
    """Convert markdown to HTML with styling"""

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Simple markdown to HTML conversion
    html_lines = []
    html_lines.append('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #0066cc;
            font-size: 28px;
            text-align: center;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        h2 {
            color: #0066cc;
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
        }
        h3 {
            color: #0066cc;
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 12px;
        }
        h4 {
            color: #333;
            font-size: 14px;
            margin-top: 15px;
            margin-bottom: 10px;
        }
        p {
            margin: 10px 0;
            text-align: justify;
        }
        ul, ol {
            margin: 10px 0;
            padding-left: 30px;
        }
        li {
            margin: 5px 0;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 90%;
            color: #d63384;
        }
        pre {
            background-color: #f8f9fa;
            border-left: 4px solid #0066cc;
            padding: 15px;
            overflow-x: auto;
            font-size: 85%;
            line-height: 1.4;
        }
        .metadata {
            color: #666;
            font-size: 90%;
            font-style: italic;
        }
        hr {
            border: none;
            border-top: 2px solid #0066cc;
            margin: 30px 0;
        }
        .checkmark {
            color: #28a745;
            font-weight: bold;
        }
        .pending {
            color: #ffc107;
            font-weight: bold;
        }
        strong {
            color: #0066cc;
        }
    </style>
</head>
<body>
''')

    in_code_block = False
    in_list = False

    for line in md_content.split('\n'):
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre><code>')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # Horizontal rules
        if line.strip() == '---':
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<hr>')
            continue

        # Headings
        if line.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h1>{line[2:].strip()}</h1>')
        elif line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line[3:].strip()}</h2>')
        elif line.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{line[4:].strip()}</h3>')
        elif line.startswith('#### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h4>{line[5:].strip()}</h4>')

        # Lists
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            text = line.strip()[2:].strip()
            # Convert markdown formatting
            text = text.replace('**', '<strong>').replace('**', '</strong>')
            text = text.replace('✅', '<span class="checkmark">✓</span>')
            text = text.replace('⏸️', '<span class="pending">⏸</span>')
            html_lines.append(f'<li>{text}</li>')

        # Empty lines
        elif not line.strip():
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            continue

        # Regular paragraphs
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            text = line.strip()
            # Convert markdown formatting
            text = text.replace('**', '<strong>').replace('**', '</strong>')
            text = text.replace('`', '<code>').replace('`', '</code>')
            text = text.replace('✅', '<span class="checkmark">✓</span>')
            text = text.replace('⏸️', '<span class="pending">⏸</span>')

            # Metadata lines
            if ':' in text and len(text) < 100:
                html_lines.append(f'<p class="metadata">{text}</p>')
            else:
                html_lines.append(f'<p>{text}</p>')

    if in_list:
        html_lines.append('</ul>')

    html_lines.append('''
</body>
</html>
''')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))

    print(f"✓ HTML generated: {html_path}")


def html_to_pdf_chrome(html_path, pdf_path):
    """Convert HTML to PDF using Chrome/Chromium headless"""

    # Try google-chrome first, then chromium
    browsers = ['google-chrome', 'chromium-browser', 'chromium']

    for browser in browsers:
        try:
            result = subprocess.run(
                [browser, '--headless', '--disable-gpu', '--print-to-pdf=' + str(pdf_path), str(html_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"✓ PDF generated using {browser}: {pdf_path}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return False


def html_to_pdf_firefox(html_path, pdf_path):
    """Convert HTML to PDF using Firefox headless"""
    try:
        result = subprocess.run(
            ['firefox', '--headless', '--print-to-pdf=' + str(pdf_path), str(html_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"✓ PDF generated using Firefox: {pdf_path}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False


if __name__ == '__main__':
    base_path = Path(__file__).parent
    md_path = base_path / 'DWG_to_Database_EXECUTIVE_SUMMARY.md'
    html_path = base_path / 'DWG_to_Database_EXECUTIVE_SUMMARY.html'
    pdf_path = base_path / 'DWG_to_Database_EXECUTIVE_SUMMARY.pdf'

    if not md_path.exists():
        print(f"Error: Input file not found: {md_path}")
        sys.exit(1)

    print(f"Converting {md_path.name} to PDF...")

    # Step 1: Markdown to HTML
    markdown_to_html(md_path, html_path)

    # Step 2: HTML to PDF
    if html_to_pdf_chrome(html_path, pdf_path):
        print(f"\n✓ Success! PDF created: {pdf_path}")
    elif html_to_pdf_firefox(html_path, pdf_path):
        print(f"\n✓ Success! PDF created: {pdf_path}")
    else:
        print(f"\n⚠ Could not generate PDF automatically.")
        print(f"HTML file created: {html_path}")
        print(f"\nManual conversion options:")
        print(f"1. Open {html_path} in Chrome/Firefox")
        print(f"2. Press Ctrl+P (Print)")
        print(f"3. Select 'Save as PDF'")
        print(f"4. Save to: {pdf_path}")

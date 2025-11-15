#!/usr/bin/env python3
"""
Generate PDF from Executive Summary markdown file
Uses markdown2 for parsing and reportlab for PDF generation
"""

import sys
import re
from pathlib import Path

try:
    import markdown
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
except ImportError as e:
    print(f"Error: Missing required module: {e}")
    print("Installing required packages...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "markdown", "reportlab"], check=True)
    # Re-import after installation
    import markdown
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def markdown_to_pdf(md_path, pdf_path):
    """Convert markdown file to PDF with formatting"""

    # Read markdown content
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Container for PDF elements
    story = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )

    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['Code'],
        fontSize=9,
        fontName='Courier',
        textColor=colors.HexColor('#d63384'),
        backColor=colors.HexColor('#f8f9fa'),
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['BodyText'],
        fontSize=10,
        leftIndent=30,
        bulletIndent=15,
        spaceAfter=6
    )

    # Parse markdown line by line
    lines = md_content.split('\n')
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        # Handle code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                if code_lines:
                    code_text = '\n'.join(code_lines)
                    # Wrap long lines
                    wrapped_lines = []
                    for cl in code_lines:
                        if len(cl) > 80:
                            wrapped_lines.append(cl[:80] + '...')
                        else:
                            wrapped_lines.append(cl)
                    code_text = '\n'.join(wrapped_lines)
                    story.append(Paragraph(f'<font name="Courier" size="8">{code_text}</font>', code_style))
                    story.append(Spacer(1, 10))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            i += 1
            continue

        # Skip empty lines
        if not line.strip():
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Handle horizontal rules
        if line.strip() == '---':
            story.append(Spacer(1, 10))
            story.append(Table([['']], colWidths=[6.5*inch], style=TableStyle([
                ('LINEABOVE', (0,0), (-1,-1), 2, colors.HexColor('#0066cc'))
            ])))
            story.append(Spacer(1, 10))
            i += 1
            continue

        # Handle headings
        if line.startswith('# '):
            # Main title
            text = line[2:].strip()
            story.append(Paragraph(text, title_style))
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, h1_style))
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, h2_style))
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, h3_style))

        # Handle bullet lists
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:].strip()
            # Handle bold and checkmarks
            text = text.replace('**', '<b>').replace('**', '</b>')
            text = text.replace('✅', '&#10004;')
            text = text.replace('⏸️', '&#9208;')
            story.append(Paragraph(f'• {text}', bullet_style))

        # Handle bold metadata lines
        elif line.startswith('**') and '**' in line[2:]:
            text = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
            story.append(Paragraph(text, body_style))

        # Handle regular paragraphs
        elif line.strip():
            text = line.strip()
            # Convert markdown bold
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            # Convert inline code
            text = re.sub(r'`(.*?)`', r'<font name="Courier" color="#d63384">\1</font>', text)
            # Handle checkmarks
            text = text.replace('✅', '&#10004;')
            text = text.replace('⏸️', '&#9208;')
            story.append(Paragraph(text, body_style))

        i += 1

    # Build PDF
    doc.build(story)
    print(f"✓ PDF generated successfully: {pdf_path}")


if __name__ == '__main__':
    input_md = Path(__file__).parent / 'DWG_to_Database_EXECUTIVE_SUMMARY.md'
    output_pdf = Path(__file__).parent / 'DWG_to_Database_EXECUTIVE_SUMMARY.pdf'

    if not input_md.exists():
        print(f"Error: Input file not found: {input_md}")
        sys.exit(1)

    print(f"Converting {input_md.name} to PDF...")
    markdown_to_pdf(str(input_md), str(output_pdf))
    print(f"Output: {output_pdf}")

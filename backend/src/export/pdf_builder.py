import os
import datetime
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from loguru import logger
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import PROCESSED_DIR

def add_header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    
    # Header
    canvas_obj.setFont("Helvetica-Bold", 10)
    canvas_obj.drawString(doc.leftMargin, doc.height + doc.topMargin + 10, "SimulReport - Engineering Analysis")
    
    # Footer
    canvas_obj.setFont("Helvetica", 9)
    page_num = canvas_obj.getPageNumber()
    text = f"Page {page_num}"
    canvas_obj.drawRightString(doc.width + doc.leftMargin, doc.bottomMargin - 20, text)
    
    canvas_obj.restoreState()

class PDFBuilder:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Custom Styles
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=10,
            textColor='#444444'
        ))

        self.styles.add(ParagraphStyle(
            name='JustifiedBody',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=12,
            leading=18,
            spaceAfter=14
        ))
        
        self.styles.add(ParagraphStyle(
            name='BulletItem',
            parent=self.styles['Normal'],
            alignment=TA_JUSTIFY,
            fontSize=11,
            leading=16,
            leftIndent=20,
            spaceAfter=6
        ))
        
        self.heading_style = self.styles['Heading1']
        
    def _sanitize(self, text: str) -> str:
        """Strip any HTML tags the AI might emit that ReportLab can't handle,
        then re-apply only the safe inline tags we control."""
        # Remove ALL HTML tags first (sub, sup, u, s, span, etc.)
        text = re.sub(r'<(?!/?b>|/?i>|/?br/?>)[^>]+>', '', text)
        # Escape bare & characters that aren't already an entity
        text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|bull);)', '&amp;', text)
        # Strip LaTeX-style fragments that can confuse the parser
        text = re.sub(r'\$[^$]*\$', '', text)
        return text

    def _safe_paragraph(self, text: str, style) -> Paragraph:
        """Try to build a Paragraph, fall back to plain-escaped text on failure."""
        try:
            return Paragraph(text, style)
        except Exception:
            # Strip all markup and try again as completely plain text
            plain = re.sub(r'<[^>]+>', '', text)
            try:
                return Paragraph(plain, style)
            except Exception:
                return Paragraph("(content rendering error)", style)

    def _parse_markdown(self, text: str, story: list):
        """Parse LLM markdown to ReportLab Paragraphs"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
            
            # Apply inline bold/italic BEFORE sanitizing so we keep them
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', line)
            
            # Now sanitize to remove any AI-generated HTML we can't handle
            line = self._sanitize(line)

            # Block formatting
            if line.startswith('#### '):
                story.append(self._safe_paragraph(line[5:], self.styles['Heading4'] if 'Heading4' in self.styles else self.styles['Heading3']))
            elif line.startswith('### '):
                story.append(self._safe_paragraph(line[4:], self.styles['Heading3']))
            elif line.startswith('## '):
                story.append(self._safe_paragraph(line[3:], self.styles['Heading2']))
            elif line.startswith('# '):
                story.append(self._safe_paragraph(line[2:], self.styles['Heading1']))
            elif line.startswith('* ') or line.startswith('- '):
                story.append(self._safe_paragraph(f"&bull; {line[2:]}", self.styles['BulletItem']))
            elif line.startswith('---') or line.startswith('==='):
                story.append(Spacer(1, 8))
            else:
                story.append(self._safe_paragraph(line, self.styles['JustifiedBody']))
        
    def build_report(self, content: dict, viz_files: dict, params: dict, output_dir: Path = PROCESSED_DIR) -> str:
        project_name = params.get("project_name", "Untitled_Report").replace(" ", "_")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = output_dir / f"{project_name}_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            str(output_filename), 
            pagesize=letter,
            rightMargin=72, leftMargin=72,
            topMargin=72, bottomMargin=72
        )
        
        story = []
        
        # --- COVER PAGE ---
        story.append(Spacer(1, 2 * inch))
        # Use service-appropriate title
        service_upper = params.get('service', '').upper()
        if service_upper == 'EFD':
            cover_title = "EFD Report: Operational Production &amp; Economic Efficiency Analysis"
        else:
            cover_title = "Engineering Simulation Report"
        story.append(Paragraph(cover_title, self.styles['CoverTitle']))
        story.append(Paragraph(f"Project: {params.get('project_name', 'N/A')}", self.styles['CoverSubtitle']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"Industry: {params.get('industry', 'N/A')}", self.styles['CoverSubtitle']))
        story.append(Paragraph(f"Service: {params.get('service', 'N/A')}", self.styles['CoverSubtitle']))
        story.append(Spacer(1, 1 * inch))
        story.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%B %d, %Y')}", self.styles['CoverSubtitle']))
        story.append(PageBreak())
        
        # --- CONTENT ---
        if "full_text" in content:
            self._parse_markdown(content["full_text"], story)
            story.append(Spacer(1, 24))
            
        # --- VISUALIZATIONS (Dashboard + page-by-page plots) ---
        valid_viz = {name: path for name, path in viz_files.items() if os.path.exists(path)}
        
        if valid_viz:
            from reportlab.platypus import Table, TableStyle
            
            # Determine dashboard images based on service
            service = params.get("service", "").upper()
            dashboard_stats = params.get("dashboard_stats", {})
            
            dash_p1, dash_p2 = None, None
            dash_title = "Executive Summary Dashboard"
            table_rows = []
            
            if service == "CFD":
                dash_p1 = valid_viz.get("cfd_scalar_pressure")
                dash_p2 = valid_viz.get("cfd_scalar_velocity")
                max_p = dashboard_stats.get("max_pressure")
                min_p = dashboard_stats.get("min_pressure")
                max_v = dashboard_stats.get("max_velocity")
                table_rows = [
                    ["Metric / Flow Parameter", "Minimum Value", "Maximum Value"],
                    ["Pressure (p)", f"{min_p:.4f}" if min_p is not None else "N/A", f"{max_p:.4f}" if max_p is not None else "N/A"],
                    ["Velocity Magnitude (v_mag)", "0.0000", f"{max_v:.4f}" if max_v is not None else "N/A"]
                ]
            elif service == "FEA":
                dash_p1 = valid_viz.get("fea_stress")
                dash_p2 = valid_viz.get("fea_displacement")
                max_stress = dashboard_stats.get("max_stress")
                max_disp = dashboard_stats.get("max_displacement")
                min_fos = dashboard_stats.get("min_fos")
                table_rows = [
                    ["Metric / Structural Parameter", "Minimum Value", "Maximum Value"],
                    ["Von Mises Stress", "-", f"{max_stress:.4f}" if max_stress is not None else "N/A"],
                    ["Displacement / Deflection", "0.0000", f"{max_disp:.4f}" if max_disp is not None else "N/A"],
                    ["Factor of Safety (FOS)", f"{min_fos:.2f}" if min_fos is not None else "N/A", "-"]
                ]
            elif service == "DEM":
                dash_p1 = valid_viz.get("dem_elevation")
                dash_p2 = valid_viz.get("dem_slope")
                max_elev = dashboard_stats.get("max_elevation")
                min_elev = dashboard_stats.get("min_elevation")
                max_slope = dashboard_stats.get("max_slope")
                table_rows = [
                    ["Metric / Terrain Parameter", "Minimum Value", "Maximum Value"],
                    ["Elevation (z)", f"{min_elev:.2f}" if min_elev is not None else "N/A", f"{max_elev:.2f}" if max_elev is not None else "N/A"],
                    ["Slope Gradient (deg)", "0.00", f"{max_slope:.2f}" if max_slope is not None else "N/A"]
                ]
            elif service == "EFD":
                dash_p1 = valid_viz.get("efd_production_trend")
                dash_p2 = valid_viz.get("efd_commodity_comparison")
                total_prod = dashboard_stats.get("total_production")
                gas_share = dashboard_stats.get("gas_share_pct")
                onshore = dashboard_stats.get("onshore_pct")
                sales_eff = dashboard_stats.get("sales_efficiency_pct")

                # Format total production
                if total_prod is not None:
                    if total_prod >= 1e12:
                        prod_str = f"{total_prod/1e12:.1f} Trillion Units"
                    elif total_prod >= 1e9:
                        prod_str = f"{total_prod/1e9:.1f} Billion Units"
                    elif total_prod >= 1e6:
                        prod_str = f"{total_prod/1e6:.1f} Million Units"
                    else:
                        prod_str = f"{total_prod:,.0f} Units"
                else:
                    prod_str = "N/A"

                table_rows = [
                    ["KPI", "Value (Aggregated)", "Status"],
                    ["Total Production Volume", prod_str, "Stable"],
                    ["Gas Commodity Share", f"{gas_share:.1f}%" if gas_share is not None else "N/A", "Major Driver"],
                    ["Onshore Contribution", f"{onshore:.1f}%" if onshore is not None else "N/A", "Primary Base"],
                    ["Sales Efficiency", f"~{sales_eff:.0f}%" if sales_eff is not None else "N/A", "Healthy"],
                ]
            
            dashboard_added = False
            if dash_p1 and dash_p2 and os.path.exists(dash_p1) and os.path.exists(dash_p2):
                story.append(PageBreak())
                story.append(Paragraph(dash_title, self.heading_style))
                story.append(Spacer(1, 8))
                story.append(Paragraph(
                    f"Combined performance overview showing critical visual fields and analytical metrics for the {service} service.",
                    self.styles['JustifiedBody']
                ))
                story.append(Spacer(1, 10))
                
                # Side-by-side images (fit within margins of letter page - 6.5 inch printable width)
                img_w = 3.15 * inch
                img_h = 1.95 * inch
                img1 = Image(dash_p1, width=img_w, height=img_h)
                img2 = Image(dash_p2, width=img_w, height=img_h)
                
                img_table = Table([[img1, img2]], colWidths=[3.25*inch, 3.25*inch])
                img_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
                
                cap1_text = "Pressure Contour Map" if service == "CFD" else ("Stress Contour" if service == "FEA" else ("Elevation Map" if service == "DEM" else "Total Production Volume Over Time"))
                cap2_text = "Velocity Magnitude Contour" if service == "CFD" else ("Displacement / Deflection" if service == "FEA" else ("Slope Gradient Map" if service == "DEM" else "Total Production by Commodity"))
                
                cap_table = Table([[
                    Paragraph(f"<b>{cap1_text}</b>", self.styles['CoverSubtitle']),
                    Paragraph(f"<b>{cap2_text}</b>", self.styles['CoverSubtitle'])
                ]], colWidths=[3.25*inch, 3.25*inch])
                cap_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                
                story.append(KeepTogether([img_table, Spacer(1, 4), cap_table]))
                story.append(Spacer(1, 14))
                
                if table_rows:
                    col_w = [2.5*inch, 2.0*inch, 2.0*inch] if len(table_rows[0]) == 3 else [3.25*inch, 3.25*inch]
                    t = Table(table_rows, colWidths=col_w)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), '#ede9fe'),
                        ('TEXTCOLOR', (0,0), (-1,0), '#4c1d95'),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('ALIGN', (0,1), (0,-1), 'LEFT'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,0), 9),
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('TOPPADDING', (0,0), (-1,0), 6),
                        ('GRID', (0,0), (-1,-1), 0.5, '#e2e8f0'),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), ['#ffffff', '#fafafa']),
                        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                        ('FONTSIZE', (0,1), (-1,-1), 8),
                        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
                        ('TOPPADDING', (0,1), (-1,-1), 5),
                    ]))
                    story.append(KeepTogether([
                        Paragraph("<b>Key Performance Indicators</b>" if service == "EFD" else "<b>Key Engineering Metrics</b>", self.styles['CoverSubtitle']),
                        Spacer(1, 4),
                        t
                    ]))
                
                story.append(PageBreak())
                dashboard_added = True

            # Subsequent Supplemental Figures
            dash_names = []
            if service == "CFD":
                dash_names = ["cfd_scalar_pressure", "cfd_scalar_velocity"]
            elif service == "FEA":
                dash_names = ["fea_stress", "fea_displacement"]
            elif service == "DEM":
                dash_names = ["dem_elevation", "dem_slope"]
            elif service == "EFD":
                dash_names = ["efd_production_trend", "efd_commodity_comparison"]
                
            other_viz = {k: v for k, v in valid_viz.items() if k not in dash_names}
            
            if dashboard_added:
                if other_viz:
                    story.append(Paragraph("Supplemental Technical Figures", self.heading_style))
                    story.append(Spacer(1, 8))
                    story.append(Paragraph(
                        "The following detailed plots and diagnostics support the analysis above:",
                        self.styles['JustifiedBody']
                    ))
                    story.append(Spacer(1, 12))
                    chart_items = list(other_viz.items())
                else:
                    chart_items = []
            else:
                story.append(PageBreak())
                story.append(Paragraph("Visualizations &amp; Diagrams", self.heading_style))
                story.append(Spacer(1, 8))
                story.append(Paragraph(
                    "The following plots and diagrams were generated from the analysis of your uploaded data:",
                    self.styles['JustifiedBody']
                ))
                story.append(Spacer(1, 12))
                chart_items = list(valid_viz.items())

            for idx, (name, path) in enumerate(chart_items):
                try:
                    img = Image(path, width=6*inch, height=3.75*inch)
                    caption_text = f"Figure {idx+1}: {name.replace('_', ' ').title()}"
                    caption = Paragraph(f"<b>{caption_text}</b>", self.styles['CoverSubtitle'])
                    # Each chart on its own page for a clean professional look
                    story.append(KeepTogether([img, Spacer(1, 10), caption]))
                    story.append(PageBreak())
                except Exception as e:
                    logger.error(f"Could not embed chart {name}: {e}")
            
        doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
        logger.info(f"Built PDF report: {output_filename}")

        return str(output_filename)

    def _enforce_page_count(self, pdf_path: str, viz_files: dict, target_pages: int = 10):
        """Ensures exactly 10 pages by truncating overflow or padding with additional charts."""
        import PyPDF2

        reader = PyPDF2.PdfReader(pdf_path)
        num_pages = len(reader.pages)
        logger.info(f"PDF has {num_pages} pages, target is {target_pages}")

        if num_pages == target_pages:
            return

        writer = PyPDF2.PdfWriter()

        # Take at most target_pages from the existing doc
        for i in range(min(num_pages, target_pages)):
            writer.add_page(reader.pages[i])

        # If short, generate supplemental pages with charts or notes
        if num_pages < target_pages:
            pages_needed = target_pages - num_pages
            plots = [p for p in viz_files.values() if os.path.exists(p)]

            supp_path = pdf_path + ".supp.pdf"
            supp_doc = SimpleDocTemplate(
                supp_path, pagesize=letter,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )

            supp_story = []
            plot_idx = 0

            for p in range(pages_needed):
                if plots:
                    # Put 2 charts per page, cycling through available images
                    supp_story.append(Paragraph(f"<b>Supplemental Visualizations (continued)</b>", self.styles['Heading2']))
                    supp_story.append(Spacer(1, 12))
                    for _ in range(2):
                        plot_path = plots[plot_idx % len(plots)]
                        plot_idx += 1
                        img = Image(plot_path, width=6*inch, height=3.25*inch)
                        supp_story.append(img)
                        supp_story.append(Spacer(1, 16))
                else:
                    # Absolute fallback — appendix notes
                    supp_story.append(Paragraph("Appendix — Additional Notes", self.styles['Heading1']))
                    supp_story.append(Spacer(1, 24))
                    for _ in range(15):
                        supp_story.append(Paragraph(
                            "___________________________________________________________________",
                            self.styles['Normal']
                        ))
                        supp_story.append(Spacer(1, 18))

                supp_story.append(PageBreak())

            supp_doc.build(supp_story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

            supp_reader = PyPDF2.PdfReader(supp_path)
            for i in range(min(pages_needed, len(supp_reader.pages))):
                writer.add_page(supp_reader.pages[i])

            # Clean up supplemental file
            try:
                os.remove(supp_path)
            except:
                pass

        # Write back
        temp_path = pdf_path + ".temp.pdf"
        with open(temp_path, "wb") as f:
            writer.write(f)
        os.replace(temp_path, pdf_path)

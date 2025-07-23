"""
Markdown to ReportLab conversion service.
Converts markdown text to ReportLab Paragraph objects for PDF generation.
"""
import re
import markdown
from markdown.extensions import codehilite, tables
from reportlab.platypus import Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import cm
from bs4 import BeautifulSoup


class MarkdownToPDFParser:
    """
    Convert markdown text to ReportLab flowables (Paragraphs, Spacers, etc.).
    Supports basic markdown formatting for medical documents.
    """
    
    def __init__(self, styles):
        """
        Initialize parser with ReportLab styles.
        
        Args:
            styles: ReportLab StyleSheet with custom styles
        """
        self.styles = styles
        self.md = markdown.Markdown(
            extensions=['extra', 'codehilite', 'toc'],
            extension_configs={
                'codehilite': {'css_class': 'highlight'},
                'extra': {},
                'toc': {'anchorlink': True}
            }
        )
    
    def parse(self, markdown_text):
        """
        Parse markdown text and return list of ReportLab flowables.
        
        Args:
            markdown_text: String containing markdown content
            
        Returns:
            List of ReportLab flowables (Paragraph, Spacer objects)
        """
        if not markdown_text or not markdown_text.strip():
            return []
        
        # Convert markdown to HTML
        html_content = self.md.convert(markdown_text)
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Convert HTML elements to ReportLab flowables
        flowables = []
        for element in soup.find_all(recursive=False):
            flowable = self._convert_element(element)
            if flowable:
                if isinstance(flowable, list):
                    flowables.extend(flowable)
                else:
                    flowables.append(flowable)
        
        return flowables
    
    def _convert_element(self, element):
        """Convert a single HTML element to ReportLab flowable(s)"""
        tag = element.name.lower() if element.name else None
        
        if tag == 'h1':
            return self._create_heading(element.get_text(), level=1)
        elif tag == 'h2':
            return self._create_heading(element.get_text(), level=2)
        elif tag == 'h3':
            return self._create_heading(element.get_text(), level=3)
        elif tag == 'h4':
            return self._create_heading(element.get_text(), level=4)
        elif tag == 'p':
            return self._create_paragraph(element)
        elif tag == 'ul':
            return self._create_list(element, ordered=False)
        elif tag == 'ol':
            return self._create_list(element, ordered=True)
        elif tag == 'blockquote':
            return self._create_blockquote(element)
        elif tag == 'hr':
            return self._create_separator()
        elif tag == 'br':
            return Spacer(1, 6)
        else:
            # For unhandled tags, try to extract text content
            text = element.get_text().strip()
            if text:
                return self._create_simple_paragraph(text)
        
        return None
    
    def _create_heading(self, text, level=1):
        """Create heading paragraph"""
        if level == 1:
            style_name = 'DocumentTitle'
        elif level == 2:
            style_name = 'MedicalContentBold'
        else:
            style_name = 'MedicalContentBold'
        
        # Create bold version for headings
        formatted_text = f"<b>{self._escape_html(text)}</b>"
        
        return [
            Spacer(1, 12 if level <= 2 else 6),
            Paragraph(formatted_text, self.styles[style_name]),
            Spacer(1, 6)
        ]
    
    def _create_paragraph(self, element):
        """Create paragraph from HTML p element"""
        formatted_text = self._format_inline_elements(element)
        
        if not formatted_text.strip():
            return Spacer(1, 6)
        
        return [
            Paragraph(formatted_text, self.styles['MedicalContent']),
            Spacer(1, 6)
        ]
    
    def _create_simple_paragraph(self, text):
        """Create simple paragraph from plain text"""
        if not text.strip():
            return Spacer(1, 6)
        
        return [
            Paragraph(self._escape_html(text), self.styles['MedicalContent']),
            Spacer(1, 6)
        ]
    
    def _create_list(self, element, ordered=False):
        """Create list from ul/ol elements"""
        items = []
        counter = 1
        
        for li in element.find_all('li', recursive=False):
            text = self._format_inline_elements(li)
            
            if ordered:
                bullet = f"{counter}. "
                counter += 1
            else:
                bullet = "• "
            
            list_text = f"{bullet}{text}"
            items.append(Paragraph(list_text, self.styles['MedicalContent']))
            items.append(Spacer(1, 3))
        
        # Remove last spacer
        if items and isinstance(items[-1], Spacer):
            items.pop()
        
        # Add spacing around the list
        result = [Spacer(1, 6)]
        result.extend(items)
        result.append(Spacer(1, 6))
        
        return result
    
    def _create_blockquote(self, element):
        """Create blockquote with indentation"""
        text = self._format_inline_elements(element)
        
        # Create indented style
        quote_style = ParagraphStyle(
            name='Blockquote',
            parent=self.styles['MedicalContent'],
            leftIndent=1*cm,
            rightIndent=0.5*cm,
            fontName='Times-Italic',
            spaceBefore=6,
            spaceAfter=6
        )
        
        return [
            Spacer(1, 6),
            Paragraph(f'"{text}"', quote_style),
            Spacer(1, 6)
        ]
    
    def _create_separator(self):
        """Create horizontal rule"""
        return [
            Spacer(1, 12),
            Paragraph("_" * 50, self.styles['MedicalContent']),
            Spacer(1, 12)
        ]
    
    def _format_inline_elements(self, element):
        """Format inline HTML elements (bold, italic, links, etc.)"""
        # Handle nested elements
        formatted_text = ""
        
        for content in element.contents:
            if hasattr(content, 'name') and content.name:  # Tag element
                tag = content.name.lower()
                text = content.get_text()
                
                if tag == 'strong' or tag == 'b':
                    formatted_text += f"<b>{self._escape_html(text)}</b>"
                elif tag == 'em' or tag == 'i':
                    formatted_text += f"<i>{self._escape_html(text)}</i>"
                elif tag == 'u':
                    formatted_text += f"<u>{self._escape_html(text)}</u>"
                elif tag == 'code':
                    formatted_text += f"<font name='Courier'>{self._escape_html(text)}</font>"
                elif tag == 'a':
                    # For links, just show the text (or add URL in parentheses)
                    href = content.get('href', '')
                    if href and href != text:
                        formatted_text += f"{self._escape_html(text)} ({href})"
                    else:
                        formatted_text += self._escape_html(text)
                elif tag == 'br':
                    formatted_text += "<br/>"
                else:
                    formatted_text += self._escape_html(text)
            else:  # Text content
                formatted_text += self._escape_html(str(content))
        
        return formatted_text.strip()
    
    def _escape_html(self, text):
        """Escape HTML characters for ReportLab"""
        if not text:
            return ""
        
        # ReportLab HTML escape
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')
        
        return text
    
    def parse_medical_content(self, markdown_text, title=None):
        """
        Parse medical markdown content with specific formatting.
        
        Args:
            markdown_text: Medical content in markdown format
            title: Optional title for the content
            
        Returns:
            List of ReportLab flowables formatted for medical documents
        """
        flowables = []
        
        # Add title if provided
        if title:
            flowables.append(Paragraph(f"<b>{self._escape_html(title)}</b>", 
                                     self.styles['MedicalContentBold']))
            flowables.append(Spacer(1, 12))
        
        # Parse markdown content
        content_flowables = self.parse(markdown_text)
        flowables.extend(content_flowables)
        
        return flowables
    
    def parse_prescription_instructions(self, instructions):
        """
        Parse prescription instructions with medical formatting.
        
        Args:
            instructions: Prescription instructions in markdown format
            
        Returns:
            List of ReportLab flowables for prescription instructions
        """
        if not instructions or not instructions.strip():
            return []
        
        flowables = []
        flowables.append(Paragraph("<b>INSTRUÇÕES GERAIS:</b>", 
                                 self.styles['MedicalContentBold']))
        flowables.append(Spacer(1, 6))
        
        # Parse instructions
        instruction_flowables = self.parse(instructions)
        flowables.extend(instruction_flowables)
        
        return flowables
import os
import uuid
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone

try:
    import pypdf
    from pypdf import PdfReader, PdfWriter

    PDF_LIBRARY_AVAILABLE = True
except ImportError:
    PDF_LIBRARY_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import black
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFFormOverlay:
    """
    Service for filling PDF forms with submitted data using coordinate-based overlay.
    Creates precise text overlays using ReportLab and merges them with original PDFs.
    """

    def __init__(self):
        if not PDF_LIBRARY_AVAILABLE:
            raise ImportError("pypdf library is required for PDF form processing")
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab library is required for PDF overlay generation"
            )
        
        # Cache for template information to improve performance
        self._template_cache = {}

    def fill_form(
        self, template_path, form_data, field_config=None, output_filename=None
    ):
        """
        Fill PDF form fields with submitted data using coordinate-based overlay.

        Args:
            template_path (str): Path to blank PDF form template
            form_data (dict): Form data to fill
            field_config (dict): Field configuration with coordinates
            output_filename (str): Optional output filename

        Returns:
            HttpResponse: Filled PDF as streaming HTTP response
        """
        return self.generate_pdf_response(template_path, form_data, field_config, output_filename)

    def generate_pdf_response(self, template_path, form_data, field_config, filename=None):
        """
        Generate PDF and return as HttpResponse for direct download.
        
        Args:
            template_path (str): Path to blank PDF form template
            form_data (dict): Form data to fill
            field_config (dict): Field configuration with coordinates
            filename (str): Optional output filename
            
        Returns:
            HttpResponse: Streaming PDF response with proper headers
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"PDF template not found: {template_path}")

        if not field_config:
            raise ValueError(
                "Field configuration is required for coordinate-based overlay"
            )

        try:
            # Get cached template information or read from file
            template_info = self._get_template_info(template_path)
            page_width = template_info['page_width']
            page_height = template_info['page_height']

            # Create overlay PDF with form data
            overlay_buffer = self._create_overlay_pdf(
                form_data, field_config, page_width, page_height
            )

            # Merge overlay with original PDF
            filled_pdf_buffer = self._merge_pdfs(template_path, overlay_buffer)

            # Generate output filename if not provided
            if not filename:
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                filename = f"filled_form_{timestamp}.pdf"

            # Create HTTP response with PDF content
            response = HttpResponse(
                filled_pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            
            # Set proper headers for download
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(filled_pdf_buffer.getvalue())
            
            # Ensure proper cleanup of buffers
            filled_pdf_buffer.close()
            overlay_buffer.close()
            
            return response

        except Exception as e:
            raise Exception(f"Error generating PDF response: {str(e)}")

    def _get_template_info(self, template_path):
        """
        Get cached template information or read from file.
        
        Args:
            template_path (str): Path to PDF template
            
        Returns:
            dict: Template information with page dimensions
        """
        # Check cache first
        template_mtime = os.path.getmtime(template_path)
        cache_key = f"{template_path}:{template_mtime}"
        
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]
        
        # Read template and cache information
        reader = PdfReader(template_path)
        if not reader.pages:
            raise ValueError("PDF template has no pages")

        # Get first page dimensions (assuming single page form)
        first_page = reader.pages[0]
        mediabox = first_page.mediabox
        page_width = float(mediabox.width)
        page_height = float(mediabox.height)
        
        template_info = {
            'page_width': page_width,
            'page_height': page_height,
        }
        
        # Cache the information
        self._template_cache[cache_key] = template_info
        
        # Limit cache size to prevent memory issues
        if len(self._template_cache) > 10:
            # Remove oldest entries
            oldest_key = next(iter(self._template_cache))
            del self._template_cache[oldest_key]
        
        return template_info

    def fill_form_legacy(self, template_path, form_data, field_config=None, output_filename=None):
        """
        Legacy method that returns ContentFile for backward compatibility.
        
        Args:
            template_path (str): Path to blank PDF form template
            form_data (dict): Form data to fill
            field_config (dict): Field configuration with coordinates
            output_filename (str): Optional output filename

        Returns:
            ContentFile: Filled PDF as Django ContentFile
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"PDF template not found: {template_path}")

        if not field_config:
            raise ValueError(
                "Field configuration is required for coordinate-based overlay"
            )

        try:
            # Get cached template information or read from file
            template_info = self._get_template_info(template_path)
            page_width = template_info['page_width']
            page_height = template_info['page_height']

            # Create overlay PDF with form data
            overlay_buffer = self._create_overlay_pdf(
                form_data, field_config, page_width, page_height
            )

            # Merge overlay with original PDF
            filled_pdf_buffer = self._merge_pdfs(template_path, overlay_buffer)

            # Generate output filename if not provided
            if not output_filename:
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"filled_form_{timestamp}.pdf"

            # Return as ContentFile for legacy compatibility
            content_file = ContentFile(filled_pdf_buffer.getvalue(), name=output_filename)
            
            # Cleanup buffers
            filled_pdf_buffer.close()
            overlay_buffer.close()
            
            return content_file

        except Exception as e:
            raise Exception(f"Error filling PDF form: {str(e)}")

    def _create_overlay_pdf(self, form_data, field_config, page_width, page_height):
        """
        Create PDF overlay with form data using ReportLab.

        Args:
            form_data (dict): Form data to render
            field_config (dict): Field configuration with coordinates
            page_width (float): PDF page width in points
            page_height (float): PDF page height in points

        Returns:
            BytesIO: PDF overlay buffer
        """
        buffer = BytesIO()

        # Create PDF canvas with same dimensions as original
        pdf_canvas = canvas.Canvas(buffer, pagesize=(page_width, page_height))

        # Process each field in the configuration
        for field_name, config in field_config.items():
            if field_name in form_data:
                field_value = form_data[field_name]
                if field_value is not None and str(field_value).strip():
                    self._draw_field_on_canvas(
                        pdf_canvas, field_name, field_value, config, page_height
                    )

        # Save the canvas
        pdf_canvas.save()
        buffer.seek(0)
        return buffer

    def _draw_field_on_canvas(
        self, pdf_canvas, field_name, field_value, config, page_height
    ):
        """
        Draw a single field on the PDF canvas.

        Args:
            pdf_canvas: ReportLab canvas object
            field_name (str): Name of the field
            field_value: Value to render
            config (dict): Field configuration
            page_height (float): Page height for coordinate conversion
        """
        # Get field configuration
        field_type = config.get("type", "text")
        x_cm = config.get("x", 0)
        y_cm = config.get("y", 0)
        font_size = config.get("font_size", 12)
        font_family = config.get("font_family", "Helvetica")

        # Convert cm to points (1 cm = 28.35 points)
        # Add horizontal padding from left edge
        left_padding = font_size * 0.1  # 10% of font size as left padding
        x_points = x_cm * cm + left_padding

        # Convert y coordinate (PDF origin is bottom-left, config uses top-left)
        # fieldConfig.y is the TOP edge of the field box
        # We need to position text baseline within the field box
        field_height = config.get('height', 0.7) * cm  # Field height in points
        
        # Position text baseline at approximately 75% down from field top
        # This centers text nicely within the field box
        baseline_offset = field_height * 0.75
        y_points = page_height - (y_cm * cm) - baseline_offset

        # Set font
        try:
            pdf_canvas.setFont(font_family, font_size)
        except:
            # Fallback to Helvetica if font not available
            pdf_canvas.setFont("Helvetica", font_size)

        # Set text color
        pdf_canvas.setFillColor(black)

        # Render based on field type
        if field_type == "boolean":
            # Render checkbox
            if field_value:
                self._draw_checkbox(pdf_canvas, x_points, y_points, config)
        elif field_type == "choice":
            # Render selected choice
            pdf_canvas.drawString(x_points, y_points, str(field_value))
        elif field_type == "date":
            # Format date value
            if hasattr(field_value, "strftime"):
                formatted_date = field_value.strftime("%d/%m/%Y")
            else:
                formatted_date = str(field_value)
            pdf_canvas.drawString(x_points, y_points, formatted_date)
        elif field_type in ["text", "textarea"]:
            # Handle multi-line text
            text_value = str(field_value)
            max_width = config.get("width", 10) * cm

            if field_type == "textarea" or len(text_value) > 50:
                self._draw_multiline_text(
                    pdf_canvas, text_value, x_points, y_points, max_width, font_size
                )
            else:
                pdf_canvas.drawString(x_points, y_points, text_value)
        else:
            # Default: render as string
            pdf_canvas.drawString(x_points, y_points, str(field_value))

    def _draw_checkbox(self, pdf_canvas, x_points, y_points, config):
        """Draw a checked checkbox."""
        size = config.get("width", 0.5) * cm

        # Draw checkbox border - x_points and y_points already include padding
        # Adjust y position to align checkbox properly within field
        checkbox_y = y_points + (
            config.get("font_size", 12) * 0.2
        )  # Slight upward adjustment
        pdf_canvas.rect(x_points, checkbox_y, size, size)

        # Draw check mark using the adjusted checkbox_y position
        pdf_canvas.line(
            x_points + size * 0.2,
            checkbox_y + size * 0.4,
            x_points + size * 0.4,
            checkbox_y + size * 0.2,
        )
        pdf_canvas.line(
            x_points + size * 0.4,
            checkbox_y + size * 0.2,
            x_points + size * 0.8,
            checkbox_y + size * 0.7,
        )

    def _draw_multiline_text(
        self, pdf_canvas, text, x_points, y_points, max_width, font_size
    ):
        """Draw multiline text with word wrapping."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            text_width = pdf_canvas.stringWidth(test_line, "Helvetica", font_size)

            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, break it
                    lines.append(word)

        if current_line:
            lines.append(" ".join(current_line))

        # Draw each line
        line_height = font_size + 2
        for i, line in enumerate(lines):
            # y_points is already adjusted for baseline in _draw_field_on_canvas
            pdf_canvas.drawString(x_points, y_points - (i * line_height), line)

    def _merge_pdfs(self, template_path, overlay_buffer):
        """
        Merge overlay PDF with original template.

        Args:
            template_path (str): Path to original PDF
            overlay_buffer (BytesIO): Overlay PDF buffer

        Returns:
            BytesIO: Merged PDF buffer
        """
        # Read original PDF
        original_reader = PdfReader(template_path)

        # Read overlay PDF
        overlay_reader = PdfReader(overlay_buffer)

        # Create writer
        writer = PdfWriter()

        # Merge pages (assuming single page for now)
        if original_reader.pages and overlay_reader.pages:
            original_page = original_reader.pages[0]
            overlay_page = overlay_reader.pages[0]

            # Merge overlay onto original
            original_page.merge_page(overlay_page)
            writer.add_page(original_page)

            # Add any additional pages from original
            for page_num in range(1, len(original_reader.pages)):
                writer.add_page(original_reader.pages[page_num])

        # Write to buffer
        output_buffer = BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        return output_buffer

    def extract_form_fields(self, pdf_path):
        """
        Extract fillable fields from PDF form (for reference/debugging).

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            dict: Dictionary of field names and their properties
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            reader = PdfReader(pdf_path)
            fields = {}

            if reader.is_encrypted:
                return fields

            for page_num, page in enumerate(reader.pages):
                if "/Annots" in page:
                    annotations = page["/Annots"]
                    if annotations:
                        page_fields = self._extract_page_fields(page, page_num)
                        fields.update(page_fields)

            return fields

        except Exception as e:
            raise Exception(f"Error extracting PDF fields: {str(e)}")

    def _extract_page_fields(self, page, page_num):
        """Extract fields from a specific page."""
        fields = {}

        try:
            if "/Annots" in page:
                annotations = page["/Annots"]
                for annotation in annotations:
                    if hasattr(annotation, "get_object"):
                        ann_obj = annotation.get_object()
                        if "/T" in ann_obj:  # Field name
                            field_name = ann_obj["/T"]
                            field_type = ann_obj.get("/FT", "Unknown")

                            fields[f"{field_name}_page_{page_num}"] = {
                                "name": field_name,
                                "type": str(field_type),
                                "page": page_num,
                            }
        except Exception:
            # Skip problematic annotations
            pass

        return fields

    def validate_pdf_form(self, pdf_path):
        """
        Validate that PDF can be processed.

        Args:
            pdf_path (str): Path to PDF file

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if not os.path.exists(pdf_path):
                return False, "PDF file does not exist"

            reader = PdfReader(pdf_path)

            if not reader.pages:
                return False, "PDF has no pages"

            if reader.is_encrypted:
                return False, "PDF is encrypted and cannot be processed"

            # Check if PDF is readable
            first_page = reader.pages[0]
            mediabox = first_page.mediabox

            if not mediabox:
                return False, "PDF page dimensions cannot be determined"

            return True, None

        except Exception as e:
            return False, str(e)


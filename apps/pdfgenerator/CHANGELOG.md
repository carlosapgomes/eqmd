# PDF Generator Changelog

All notable changes to the PDF Generator app will be documented in this file.

## [Unreleased]

### Added

- Comprehensive documentation suite (README.md, DEVELOPER_GUIDE.md, QUICK_REFERENCE.md)
- Developer guide for adding new document types
- Quick reference guide for common tasks
- This changelog file

## [0.1.0] - 2025-01-20

### Initial Release

### Features

- **Core PDF Generation Service**

  - HospitalLetterheadGenerator class with ReportLab
  - A4 portrait letterhead template
  - Automatic header/footer with hospital branding
  - Patient name displayed on every page
  - Page numbers (X/Y format)
  - Medical signature section with auto-filled date

- **Document Types**

  - Prescription PDF generation (`create_prescription_pdf()`)
  - Generic PDF generation (`generate_pdf()`)
  - Support for custom document types

- **Markdown Parser**

  - MarkdownToPDFParser class
  - Support for headers (h1-h4)
  - Bold, italic, underline formatting
  - Ordered and unordered lists
  - Blockquotes
  - Horizontal rules
  - HTML escaping for security

- **Web Endpoints**

  - `/pdf/prescription/` - Generate prescription PDFs
  - `/pdf/discharge-report/` - Generate discharge reports
  - `/pdf/exam-request/` - Generate exam requests
  - All endpoints require authentication
  - Patient access validation

- **Integration with Existing Apps**
  - OutpatientPrescriptionPDFView in outpatientprescriptions app
  - URL route: `/outpatientprescriptions/<uuid:pk>/pdf/`
  - Permission checks via `can_access_patient()`

### Technical Details

#### Stack

- ReportLab for PDF generation
- Python-Markdown for markdown parsing
- BeautifulSoup for HTML processing

#### Configuration

- Hospital configuration from `settings.HOSPITAL_CONFIG`
- PDF configuration from `settings.PDF_CONFIG`
- Configurable margins, fonts, page size

#### Architecture

- Service layer: `services/pdf_generator.py`, `services/markdown_parser.py`
- View layer: Base class for common functionality, specific views per document type
- No models required (PDFs generated on-demand)

### Security

- Authentication required for all endpoints
- Patient access validation
- HTML escaping in markdown parser
- No persistent PDF storage
- Logo path validation (local files only)

### Testing

- Unit tests in `tests/test_pdf_generation.py`
- Tests for PDF generator initialization
- Tests for markdown parsing
- Tests for PDF generation
- Tests for HTML escaping
- Tests for empty content handling

### Known Limitations

- No digital signature support
- No batch PDF generation
- No email delivery
- Logo URL downloads not implemented (security)
- Limited markdown support (no tables, no code blocks)

## Future Plans

### Planned Features

- [ ] Digital signature integration
- [ ] Batch PDF generation
- [ ] Email PDF delivery
- [ ] Advanced markdown support (tables, code blocks)
- [ ] Custom fonts support
- [ ] PDF storage and archiving
- [ ] Multi-language support
- [ ] Template customization UI

### Potential Enhancements

- [ ] Performance optimization for high volume
- [ ] PDF preview before download
- [ ] PDF watermarking
- [ ] Multiple hospital configurations
- [ ] Custom signature templates
- [ ] PDF versioning

## Migration Notes

### From HTML Print Templates

The PDF generator replaces HTML print templates. To migrate:

1. Identify print views using HTML templates
2. Extract data structures used in templates
3. Create PDF generation view
4. Map template content to markdown
5. Update URLs from `/print/` to `/pdf/`
6. Update frontend buttons to call new endpoints

Example:

```python
# Before (HTML print)
path('<uuid:pk>/print/', OutpatientPrescriptionPrintView.as_view())

# After (PDF generation)
path('<uuid:pk>/pdf/', OutpatientPrescriptionPDFView.as_view())
```

## Version History

### 0.1.0 (2025-01-20)

- Initial release
- Core PDF generation functionality
- Three document types supported
- Full integration with outpatient prescriptions

## Contributors

- Initial implementation based on `prompts/pdfgenerator/pdf_implementation_plan.md`

## Support

For issues or questions:

1. Check `README.md` for full documentation
2. See `DEVELOPER_GUIDE.md` for adding new document types
3. See `QUICK_REFERENCE.md` for common tasks
4. Review `tests/test_pdf_generation.py` for examples
5. Enable debug logging for troubleshooting

## Related Documentation

- **Main Documentation**: `apps/pdfgenerator/README.md`
- **Developer Guide**: `apps/pdfgenerator/DEVELOPER_GUIDE.md`
- **Quick Reference**: `apps/pdfgenerator/QUICK_REFERENCE.md`
- **Implementation Plan**: `prompts/pdfgenerator/pdf_implementation_plan.md`
- **Outpatient Prescriptions**: `apps/outpatientprescriptions/views.py`

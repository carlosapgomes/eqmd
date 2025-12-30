# Poppler Installation and Troubleshooting Guide

## Overview

Poppler is a PDF rendering library required for the visual PDF field configurator in the PDF Forms app. This guide provides comprehensive installation instructions and troubleshooting steps for all platforms.

## What is Poppler?

Poppler is a PDF rendering library based on the xpdf-3.0 code base. It provides utilities for:

- Converting PDF pages to images (`pdftoppm`)
- Extracting PDF information (`pdfinfo`)
- Converting PDF to text (`pdftotext`)

The PDF Forms app uses `pdf2image` Python library, which depends on Poppler to convert PDF pages into images for the visual field configuration interface.

## Installation Instructions

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install poppler utilities
sudo apt install poppler-utils

# Verify installation
pdftoppm -h
```

**Package Details:**

- Package name: `poppler-utils`
- Includes: pdftoppm, pdfinfo, pdftotext, pdftocairo, and other utilities
- Typical installation size: ~15MB

### CentOS/RHEL/Fedora

**CentOS/RHEL 7:**

```bash
sudo yum install poppler-utils
```

**CentOS/RHEL 8+ and Fedora:**

```bash
sudo dnf install poppler-utils
```

**Verification:**

```bash
pdftoppm -h
pdfinfo -h
```

### macOS

**Using Homebrew (Recommended):**

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install poppler
brew install poppler

# Verify installation
pdftoppm -h
```

**Using MacPorts:**

```bash
sudo port install poppler
```

### Windows

**Manual Installation:**

1. **Download Poppler for Windows:**
   - Visit: <https://blog.alivate.com.au/poppler-windows/>
   - Download the latest release (e.g., `poppler-23.08.0-0.zip`)

2. **Extract Files:**

   ```cmd
   # Extract to a permanent location
   C:\Program Files\poppler\
   ```

3. **Add to PATH:**
   - Open System Properties → Environment Variables
   - Edit System PATH variable
   - Add: `C:\Program Files\poppler\bin`
   - Restart Command Prompt/PowerShell

4. **Verify Installation:**

   ```cmd
   pdftoppm -h
   ```

**Using Chocolatey (Alternative):**

```cmd
# Install Chocolatey package manager if not installed
# Then install poppler
choco install poppler
```

### Docker Environments

**Dockerfile:**

```dockerfile
# Ubuntu/Debian base
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y poppler-utils

# Alpine base
FROM alpine:latest
RUN apk add --no-cache poppler-utils

# CentOS base
FROM centos:8
RUN dnf install -y poppler-utils
```

**Docker Compose:**

```yaml
services:
  web:
    build: .
    volumes:
      - .:/app
    depends_on:
      - db
    # Poppler will be available inside container
```

## Verification Steps

### Basic Verification

```bash
# Check if poppler is installed
which pdftoppm
which pdfinfo

# Display help (should show command options)
pdftoppm -h
pdfinfo -h

# Check version
pdftoppm -v
```

### Advanced Testing

```bash
# Create a test PDF (if you have one)
echo "Test PDF content" | ps2pdf - test.pdf

# Convert PDF to image
pdftoppm -png -f 1 -l 1 test.pdf test_output

# Should create test_output-1.png file
ls test_output-*.png
```

### Python Integration Test

```python
# Test from Django shell
python manage.py shell

# Test pdf2image integration
from pdf2image import convert_from_path
import os

# Test with a sample PDF
pdf_path = 'path/to/sample.pdf'
if os.path.exists(pdf_path):
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    print(f"Successfully converted PDF to {len(images)} images")
else:
    print("Please provide a valid PDF path for testing")
```

## Common Issues and Solutions

### Issue 1: "Command not found" - Poppler not in PATH

**Symptoms:**

```bash
pdftoppm -h
# bash: pdftoppm: command not found
```

**Solutions:**

**Linux:**

```bash
# Check if poppler is actually installed
dpkg -l | grep poppler  # Ubuntu/Debian
rpm -qa | grep poppler   # CentOS/RHEL

# If not installed, install it
sudo apt install poppler-utils  # Ubuntu/Debian
sudo dnf install poppler-utils  # CentOS/RHEL 8+
```

**macOS:**

```bash
# Check Homebrew installation
brew list | grep poppler

# If not installed
brew install poppler

# Check PATH
echo $PATH | grep -o '/usr/local/bin'
```

**Windows:**

1. Verify extraction location: `C:\Program Files\poppler\bin\pdftoppm.exe`
2. Check PATH environment variable
3. Restart Command Prompt after PATH changes
4. Use full path as test: `"C:\Program Files\poppler\bin\pdftoppm.exe" -h`

### Issue 2: "Permission denied" - Execution permissions

**Symptoms:**

```bash
pdftoppm -h
# Permission denied
```

**Solution:**

```bash
# Check permissions
ls -la $(which pdftoppm)

# Fix permissions if needed
sudo chmod +x $(which pdftoppm)

# For web server deployment
sudo chown www-data:www-data $(which pdftoppm)  # Ubuntu
sudo chown apache:apache $(which pdftoppm)      # CentOS
```

### Issue 3: pdf2image errors - "Unable to get page count"

**Symptoms:**

```python
from pdf2image import convert_from_path
convert_from_path('test.pdf')
# PDFPageCountError: Unable to get page count. Is poppler installed and in PATH?
```

**Solutions:**

1. **Verify Poppler Installation:**

   ```bash
   pdftoppm -h  # Should work without errors
   ```

2. **Check PDF File:**

   ```bash
   pdfinfo test.pdf  # Should display PDF information
   ```

3. **Test with Different PDF:**
   - Try with a different PDF file
   - Ensure PDF is not corrupted
   - Check file permissions

4. **Python Environment Issues:**

   ```python
   import subprocess
   result = subprocess.run(['pdftoppm', '-h'], capture_output=True, text=True)
   print(result.returncode)  # Should be 0
   print(result.stdout)      # Should show help text
   ```

### Issue 4: Docker container issues

**Symptoms:**

```bash
# Inside Docker container
pdftoppm -h
# Command not found
```

**Solutions:**

1. **Update Dockerfile:**

   ```dockerfile
   RUN apt-get update && apt-get install -y poppler-utils
   ```

2. **Rebuild container:**

   ```bash
   docker build --no-cache -t myapp .
   ```

3. **Verify in running container:**

   ```bash
   docker exec -it container_name bash
   pdftoppm -h
   ```

### Issue 5: Web server permission issues

**Symptoms:**

- Visual configurator shows "Poppler not found" error
- Command line `pdftoppm` works fine
- Django app can't access poppler

**Solutions:**

1. **Check web server user:**

   ```bash
   # Test as web server user
   sudo -u www-data pdftoppm -h  # Ubuntu
   sudo -u apache pdftoppm -h    # CentOS
   ```

2. **Fix PATH for web server:**

   ```bash
   # Add to /etc/environment or web server config
   PATH="/usr/local/bin:/usr/bin:/bin"
   ```

3. **Django shell testing:**

   ```python
   python manage.py shell
   
   import subprocess
   import os
   
   # Check PATH from Django
   print(os.environ.get('PATH'))
   
   # Test poppler access
   result = subprocess.run(['which', 'pdftoppm'], capture_output=True, text=True)
   print(f"pdftoppm location: {result.stdout.strip()}")
   ```

## Performance Considerations

### Memory Usage

- PDF to image conversion is memory-intensive
- Large PDFs may require significant RAM
- Consider implementing timeouts for conversion

### Optimization Settings

```python
# Optimize pdf2image performance
from pdf2image import convert_from_path

images = convert_from_path(
    pdf_path,
    dpi=150,        # Lower DPI for faster conversion
    first_page=1,   # Convert only first page
    last_page=1,
    fmt='png',      # PNG format for better quality
    thread_count=1  # Single thread for stability
)
```

## Alternative Solutions

### If Poppler Cannot Be Installed

The PDF Forms app provides automatic fallback when Poppler is not available:

1. **Manual JSON Editor**: Full-featured JSON editor with validation
2. **Template System**: Pre-built field configuration templates  
3. **Import/Export**: Copy configurations between systems
4. **No Functionality Loss**: All field configuration features available

### Cloud Deployment Options

**AWS Lambda Layers:**

- Use pre-built Poppler layer for Lambda functions
- Search AWS Lambda Layers marketplace for "poppler"

**Google Cloud Run:**

```dockerfile
FROM gcr.io/google-appengine/python
RUN apt-get update && apt-get install -y poppler-utils
```

**Heroku:**

```
# Add to requirements.txt or use buildpack
https://github.com/heroku/heroku-buildpack-poppler
```

## Support and Resources

### Official Documentation

- Poppler Project: <https://poppler.freedesktop.org/>
- pdf2image Documentation: <https://pypi.org/project/pdf2image/>

### Community Resources

- Stack Overflow: Search "poppler installation"
- GitHub Issues: pdf2image repository issues
- Docker Hub: Pre-built images with Poppler included

### Getting Help

If you continue to experience issues:

1. **Check System Logs:**

   ```bash
   # Linux
   journalctl -u your-django-app
   
   # Check Django logs
   tail -f /var/log/django/debug.log
   ```

2. **Create Minimal Test Case:**

   ```python
   # test_poppler.py
   try:
       from pdf2image import convert_from_path
       print("pdf2image imported successfully")
       
       # Test with a simple PDF
       images = convert_from_path('sample.pdf', first_page=1, last_page=1)
       print(f"Successfully converted PDF: {len(images)} images")
       
   except Exception as e:
       print(f"Error: {e}")
   ```

3. **Provide Environment Details:**
   - Operating System and version
   - Python version
   - Django version
   - Poppler version (`pdftoppm -v`)
   - pdf2image version (`pip show pdf2image`)

---

**Last Updated**: 2025-07-25  
**Tested Platforms**: Ubuntu 20.04/22.04, CentOS 8, macOS 12+, Windows 10/11  
**PDF Forms App Version**: Latest

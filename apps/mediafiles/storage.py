import os
import uuid
from pathlib import Path
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils import timezone


class SecureVideoStorage(FileSystemStorage):
    """
    Custom storage backend for FilePond that maintains our UUID naming convention
    and secure directory structure.
    """

    def __init__(self):
        # Use our existing media structure
        super().__init__(location=settings.MEDIA_ROOT)

    def _save(self, name, content):
        """
        Save file with UUID naming in structured directory.
        """
        # Generate UUID-based filename
        file_uuid = uuid.uuid4()
        original_ext = Path(name).suffix.lower()

        # Create date-based directory structure: videos/YYYY/MM/originals/
        date_path = timezone.now().strftime('%Y/%m')
        directory = f"videos/{date_path}/originals"

        # Ensure directory exists
        full_dir = os.path.join(self.location, directory)
        os.makedirs(full_dir, exist_ok=True)

        # Generate secure filename
        secure_filename = f"{file_uuid}{original_ext}"
        secure_path = os.path.join(directory, secure_filename)

        # Save the file
        return super()._save(secure_path, content)

    def url(self, name):
        """
        Return secure URL for file access through our view system.
        """
        # Extract UUID from filename for secure URL generation
        filename = Path(name).name
        file_uuid = filename.split('.')[0]  # Get UUID part before extension

        from django.urls import reverse
        return reverse('mediafiles:serve_file', kwargs={'file_id': file_uuid})
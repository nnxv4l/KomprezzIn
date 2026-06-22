import os
import shutil
import tempfile
import zipfile
from io import BytesIO

def create_temp_dir():
    return tempfile.mkdtemp()

def cleanup_temp_dir(temp_dir):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

def format_size(size_in_bytes):
    size_in_mb = size_in_bytes / (1024 * 1024)
    return f"{size_in_mb:.1f} MB".replace('.', ',')

def get_file_size(file_path):
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0

def create_zip_from_bytes(file_results):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data in file_results:
            zip_file.writestr(filename, data)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

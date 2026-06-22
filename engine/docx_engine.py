import os
import shutil
import tempfile
import zipfile
from io import BytesIO

from PIL import Image

def process_images_in_memory(image_bytes, ext, iteration):
    """
    Memproses byte gambar (resize dan optimasi/kompresi).
    """
    # Parameter berdasarkan iterasi (1, 2, 3)
    qualities = {1: 80, 2: 60, 3: 40}
    max_sizes = {1: 1920, 2: 1280, 3: 800}
    
    quality = qualities.get(iteration, 40)
    max_size = max_sizes.get(iteration, 800)
    
    try:
        img = Image.open(BytesIO(image_bytes))
        original_format = img.format
        
        # Resize jika diperlukan (mempertahankan rasio aspek)
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        output_buffer = BytesIO()
        
        if img.mode in ('RGBA', 'LA') or (original_format == 'PNG' and 'transparency' in img.info):
            # Pertahankan transparansi PNG: kuantisasi palet untuk memperkecil ukuran
            # Tidak menggunakan parameter quality karena ini PNG
            img_quantized = img.quantize(colors=256, method=2)
            img_quantized.save(output_buffer, format='PNG', optimize=True)
        else:
            # Konversi ke RGB jika bukan agar aman saat disimpan sebagai JPEG
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # Gunakan format asli atau JPEG sebagai fallback
            save_format = original_format if original_format in ['JPEG', 'JPG'] else 'JPEG'
            img.save(output_buffer, format=save_format, quality=quality, optimize=True)
            
        return output_buffer.getvalue()
    except Exception:
        # Jika gagal memproses gambar, kembalikan bytes aslinya
        return image_bytes

def compress_archive(input_path, output_path, iteration, media_folder_prefix):
    """
    Fungsi generik untuk DOCX dan PPTX (karena keduanya berbasis ZIP).
    Mengekstrak, mencari gambar di media_folder_prefix, memprosesnya, dan me-repack.
    """
    # Cek apakah file adalah ZIP yang valid (dan bukan protected/encrypted OLE)
    if not zipfile.is_zipfile(input_path):
        raise ValueError("File dilindungi password atau bukan format arsip yang valid.")
        
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Cari dan proses gambar
        media_path = os.path.join(temp_dir, media_folder_prefix, 'media')
        if os.path.exists(media_path):
            for filename in os.listdir(media_path):
                file_path = os.path.join(media_path, filename)
                ext = filename.split('.')[-1].lower()
                
                # Proses gambar berukuran besar
                if ext in ['jpeg', 'jpg', 'png', 'bmp'] and os.path.getsize(file_path) > 50 * 1024:
                    with open(file_path, 'rb') as f:
                        img_bytes = f.read()
                        
                    compressed_bytes = process_images_in_memory(img_bytes, ext, iteration)
                    
                    # Simpan hasil kompresi jika lebih kecil
                    if len(compressed_bytes) < len(img_bytes):
                        with open(file_path, 'wb') as f:
                            f.write(compressed_bytes)
                            
        # Repack ke output_path
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_out.write(file_path, arcname)
                    
        return True
    except zipfile.BadZipFile:
        raise ValueError("File arsip rusak atau dilindungi password.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

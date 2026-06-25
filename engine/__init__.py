import os
import logging

from .pdf_engine import compress_pdf
from .pptx_engine import compress_pptx, compress_docx
from .xlsx_engine import compress_xlsx

logger = logging.getLogger(__name__)

def process_file(temp_dir, file_name, input_path, target_size=2097152):
    """
    Memproses satu file:
    1. Cek apakah ukurannya sudah < target_size (jika ya, langsung kembalikan)
    2. Eksekusi kompresi maksimal 3 iterasi
    3. Mengembalikan hasil kompresi terbaik
    """
    # Validasi ekstensi DULU sebelum cek size, agar file aneh tidak by-pass
    if '.' not in file_name:
        logger.warning(f"File ditolak: {file_name} (Tanpa ekstensi)")
        return {
            "success": False,
            "filename": file_name,
            "error": "Format file tidak diketahui (tanpa ekstensi)"
        }

    ext = file_name.rsplit('.', 1)[-1].lower()
    if ext not in ['pdf', 'docx', 'pptx', 'xlsx']:
        logger.warning(f"Format tidak didukung: {file_name} (Ext: {ext})")
        return {
            "success": False,
            "filename": file_name,
            "error": "Format tidak didukung"
        }

    original_size = os.path.getsize(input_path)

    # Jika sudah di bawah target, kembalikan langsung
    if original_size <= target_size:
        with open(input_path, 'rb') as f:
            best_bytes = f.read()
        return {
            "success": True,
            "filename": file_name,
            "bytes": best_bytes,
            "original_size": original_size,
            "final_size": original_size,
            "status": "ok",
            "message": "Ukuran sudah di bawah target"
        }

    best_path = input_path
    best_size = original_size
    best_bytes = None
    
    error_message = None
    
    # Maksimal 3 iterasi kompresi
    tolerance_size = target_size * 1.05
    for iteration in range(1, 4):
        output_path = os.path.join(temp_dir, f"out_{iteration}_{file_name}")
        
        try:
            if ext == 'pdf':
                compress_pdf(best_path, output_path, iteration)
            elif ext == 'docx':
                compress_docx(best_path, output_path, iteration)
            elif ext == 'pptx':
                compress_pptx(best_path, output_path, iteration)
            elif ext == 'xlsx':
                compress_xlsx(best_path, output_path, iteration)

            if os.path.exists(output_path):
                current_size = os.path.getsize(output_path)
                # Pastikan ukurannya mengecil
                size_difference_pct = ((best_size - current_size) / best_size) * 100
                
                if current_size < best_size:
                    best_size = current_size
                    best_path = output_path
                    
                # Hentikan jika sudah mencapai target
                # OPTIMASI 1: Hentikan jika sudah masuk dalam batas toleransi target (misal 1.04MB untuk target 1MB)
                if best_size <= tolerance_size:
                    logger.info(f"Target tercapai untuk {file_name} pada iterasi {iteration}.")
                    break

                # OPTIMASI 2: Hentikan jika penurunan ukuran sangat kecil (< 3%), tidak efisien lanjut iterasi
                if size_difference_pct < 3.0:
                    logger.info(f"Kompresi {file_name} stagnan di iterasi {iteration}. Menghentikan proses.")
                    break
        except ValueError as ve:
             # Biasanya terkait file ber-password
             error_message = str(ve)
             logger.warning(f"Validasi gagal untuk {file_name}: {error_message}")
             break
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error kompresi {file_name} (iterasi {iteration}): {error_message}")
            # Lanjut ke iterasi berikutnya jika bukan error fatal
            continue

    if error_message and best_size == original_size:
        logger.error(f"Kompresi gagal total untuk {file_name}. Mengembalikan error ke UI.")
        return {
            "success": False,
            "filename": file_name,
            "error": error_message
        }

    # Baca byte terbaik
    with open(best_path, 'rb') as f:
        best_bytes = f.read()

    status = "ok" if best_size <= target_size else "warn"
    
    return {
        "success": True,
        "filename": file_name,
        "bytes": best_bytes,
        "original_size": original_size,
        "final_size": best_size,
        "status": status,
        "message": ""
    }

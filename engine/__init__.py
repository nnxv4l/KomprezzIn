import os

from .pdf_engine import compress_pdf
from .pptx_engine import compress_pptx, compress_docx

TARGET_SIZE = 2 * 1024 * 1024  # 2 MB

def process_file(temp_dir, file_name, input_path):
    """
    Memproses satu file:
    1. Cek apakah ukurannya sudah < 2MB (jika ya, langsung kembalikan)
    2. Eksekusi kompresi maksimal 3 iterasi
    3. Mengembalikan hasil kompresi terbaik
    """
    original_size = os.path.getsize(input_path)

    # Jika sudah di bawah target, kembalikan langsung
    if original_size <= TARGET_SIZE:
        with open(input_path, 'rb') as f:
            best_bytes = f.read()
        return {
            "success": True,
            "filename": file_name,
            "bytes": best_bytes,
            "original_size": original_size,
            "final_size": original_size,
            "status": "ok",
            "message": "Ukuran sudah di bawah 2MB"
        }

    ext = file_name.split('.')[-1].lower()
    best_path = input_path
    best_size = original_size
    best_bytes = None
    
    error_message = None
    
    # Maksimal 3 iterasi kompresi
    for iteration in range(1, 4):
        output_path = os.path.join(temp_dir, f"out_{iteration}_{file_name}")
        
        try:
            if ext == 'pdf':
                compress_pdf(best_path, output_path, iteration)
            elif ext in ['docx']:
                compress_docx(best_path, output_path, iteration)
            elif ext in ['pptx']:
                compress_pptx(best_path, output_path, iteration)
            else:
                return {
                    "success": False,
                    "filename": file_name,
                    "error": "Format tidak didukung"
                }
                
            if os.path.exists(output_path):
                current_size = os.path.getsize(output_path)
                # Pastikan ukurannya mengecil
                if current_size < best_size:
                    best_size = current_size
                    best_path = output_path
                    
                # Hentikan jika sudah mencapai target
                if best_size <= TARGET_SIZE:
                    break
        except ValueError as ve:
             # Biasanya terkait file ber-password
             error_message = str(ve)
             break
        except Exception as e:
            error_message = str(e)
            # Lanjut ke iterasi berikutnya jika bukan error fatal
            continue

    if error_message and best_size == original_size:
        return {
            "success": False,
            "filename": file_name,
            "error": error_message
        }

    # Baca byte terbaik
    with open(best_path, 'rb') as f:
        best_bytes = f.read()

    status = "ok" if best_size <= TARGET_SIZE else "warn"
    
    return {
        "success": True,
        "filename": file_name,
        "bytes": best_bytes,
        "original_size": original_size,
        "final_size": best_size,
        "status": status,
        "message": ""
    }

import os
import subprocess
import pikepdf
import platform

def compress_pdf(input_path, output_path, iteration=1):
    """
    Kompresi PDF menggunakan Ghostscript.
    Iterasi 1: /ebook (150 dpi)
    Iterasi 2: /screen (72 dpi)
    Iterasi 3: /screen + image downsampling paksa (72 dpi)
    """
    
    # Cek apakah file dilindungi password menggunakan pikepdf (akan error jika di-password)
    try:
        with pikepdf.open(input_path):
            pass
    except pikepdf.PasswordError:
        raise ValueError("File PDF dilindungi password")
    except Exception:
        pass

    settings = {
        1: "/ebook",
        2: "/screen",
        3: "/screen"
    }
    
    pdf_setting = settings.get(iteration, "/screen")
    
    # Deteksi binary gs berdasarkan OS
    gs_executable = "gswin64c" if platform.system() == "Windows" else "gs"
    
    gs_cmd = [
        gs_executable,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_setting}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]
    
    if iteration == 3:
        gs_cmd.insert(-1, "-dDownsampleColorImages=true")
        gs_cmd.insert(-1, "-dColorImageResolution=72")
        gs_cmd.insert(-1, "-dDownsampleGrayImages=true")
        gs_cmd.insert(-1, "-dGrayImageResolution=72")
        gs_cmd.insert(-1, "-dDownsampleMonoImages=true")
        gs_cmd.insert(-1, "-dMonoImageResolution=72")

    try:
        result = subprocess.run(gs_cmd, capture_output=True, text=True, check=False)

        # Mengabaikan error bawaan GS, selama output ada dan > 0 byte
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            error_msg = result.stderr.strip() if result.stderr else "Ghostscript gagal menghasilkan file keluaran tanpa error spesifik."
            raise Exception(error_msg)

        return True
    except FileNotFoundError:
         # Jika gswin64c tidak ditemukan di Windows, coba fallback ke gswin32c atau gs
         if platform.system() == "Windows":
             try:
                 gs_cmd[0] = "gswin32c"
                 subprocess.run(gs_cmd, capture_output=True, text=True, check=False)
                 if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                     return True
             except FileNotFoundError:
                 try:
                     gs_cmd[0] = "gs"
                     subprocess.run(gs_cmd, capture_output=True, text=True, check=False)
                     if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                         return True
                 except Exception:
                     pass
         raise Exception("Ghostscript (gs/gswin64c/gs) tidak ditemukan di sistem. Harap install Ghostscript.")
    except Exception as e:
        raise Exception(str(e))

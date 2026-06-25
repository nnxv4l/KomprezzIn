from .docx_engine import compress_archive

def compress_xlsx(input_path, output_path, iteration=1):
    """
    Kompresi XLSX dengan memanfaatkan engine generik untuk ZIP.
    XLSX menyimpan gambar di 'xl/media/'.
    """
    return compress_archive(input_path, output_path, iteration, "xl")

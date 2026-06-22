from .docx_engine import compress_archive

def compress_pptx(input_path, output_path, iteration=1):
    """
    Kompresi PPTX dengan memanfaatkan engine generik untuk ZIP.
    PPTX menyimpan gambar di 'ppt/media/'.
    """
    return compress_archive(input_path, output_path, iteration, "ppt")

def compress_docx(input_path, output_path, iteration=1):
    """
    Kompresi DOCX dengan memanfaatkan engine generik untuk ZIP.
    DOCX menyimpan gambar di 'word/media/'.
    """
    return compress_archive(input_path, output_path, iteration, "word")

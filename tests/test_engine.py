import pytest
import os
from engine import process_file
from engine.utils import create_temp_dir, cleanup_temp_dir

@pytest.fixture
def temp_environment():
    """Fixture untuk menyediakan direktori sementara dan membersihkannya setelah testing"""
    temp_dir = create_temp_dir()
    yield temp_dir
    cleanup_temp_dir(temp_dir)

def test_process_file_no_extension(temp_environment):
    """Memastikan file tanpa ekstensi akan ditolak dengan error yang benar"""
    dummy_input = os.path.join(temp_environment, "rahasia")
    
    # Buat file dummy
    with open(dummy_input, "wb") as f:
        f.write(b"ini adalah file rahasia")
        
    result = process_file(temp_environment, "rahasia", dummy_input)
    
    assert result["success"] is False
    assert "tanpa ekstensi" in result["error"].lower()

def test_process_file_unsupported_format(temp_environment):
    """Memastikan format yang tidak didukung (contoh: .txt) akan ditolak"""
    dummy_input = os.path.join(temp_environment, "catatan.txt")
    
    with open(dummy_input, "wb") as f:
        f.write(b"halo dunia")
        
    result = process_file(temp_environment, "catatan.txt", dummy_input)
    
    assert result["success"] is False
    assert "tidak didukung" in result["error"].lower()

def test_process_file_already_small(temp_environment):
    """Memastikan file yang ukurannya sudah kecil akan langsung dikembalikan tanpa proses Ghostscript/ZIP"""
    dummy_input = os.path.join(temp_environment, "kecil.pdf")
    
    with open(dummy_input, "wb") as f:
        f.write(b"file sangat kecil")
        
    # Target 2MB, file asli hanya beberapa byte
    result = process_file(temp_environment, "kecil.pdf", dummy_input, target_size=2000000)
    
    assert result["success"] is True
    assert result["original_size"] == result["final_size"]
    assert result["status"] == "ok"

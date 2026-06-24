import textwrap

def render_results_header(total_files: int, success_files: int) -> str:
    """Merender header container hasil kompresi"""
    return f'<div id="results"><div class="reshead" style="margin-top: 2rem;"><div class="label" style="margin:0">// Hasil kompres</div><div class="meta">{total_files} file &bull; {success_files} diproses</div></div>'

def render_error_card(fname: str, icon_cls: str, icon_text: str, err_msg: str) -> str:
    """Merender HTML card untuk file yang gagal diproses"""
    return textwrap.dedent(f"""
    <div class="fcard">
        <div class="fcard-top"><div class="ficon {icon_cls}">{icon_text}</div>
        <div><div class="fname">{fname}</div><div class="fmeta">Gagal diproses</div></div>
        <span class="tag warn">Error</span></div>
        <div class="hint">{err_msg}</div>
    </div>""")

def render_file_card(fname: str, orig_str: str, final_str: str, saving_pct: int, 
                     status: str, hint_html: str, icon_cls: str, icon_text: str) -> str:
    """Merender HTML card untuk file yang berhasil diproses (OK atau Warn)"""
    tag_cls = "ok" if status == "ok" else "warn"
    bar_cls = "" if status == "ok" else " warnbar"
    
    return textwrap.dedent(f"""
    <div class="fcard">
        <div class="fcard-top"><div class="ficon {icon_cls}">{icon_text}</div>
        <div><div class="fname">{fname}</div><div class="fmeta">{orig_str} &rarr; {final_str}</div></div>
        <span class="tag {tag_cls}">{final_str}</span></div>
        <div class="bar{bar_cls}"><span style="width: {saving_pct}%;"></span></div>
        <div class="barlabel"><span>penghematan</span><b class="cnt">{saving_pct}%</b></div>
        {hint_html}
    </div>""")

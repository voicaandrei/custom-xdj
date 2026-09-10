"""Stock binding for final 16: removes only the attempted 160px layout hooks."""
from index_beta15_contract import inspect as previous

def inspect():
    r=previous()
    r['C_static']['row_output_bytes']=4480
    r['C_static']['browse_width']=80
    r['C_static']['stock_layout_literals_retained']=['0x152e8f4','0x152c524','0x152c2b8']
    r['I']=['The reported overlap came from the enlarged layout; restore the earlier 80px layout.']
    r['U']=['Final 16 installation and owner check','Long duration stress and every LINK source mode']
    return r

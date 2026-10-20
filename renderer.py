import pymupdf as pmf

def load_pdf(filepath):
    doc = pmf.open(filepath)
    return doc

def render_page(doc, page_number, zoom =2.0):
    mat = pmf.Matrix(zoom, zoom)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(matrix= mat)

    return pix.tobytes("ppm")
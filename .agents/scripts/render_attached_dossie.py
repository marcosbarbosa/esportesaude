from pathlib import Path

import fitz


pdf_path = Path(
    "attached_assets/Dossie_Completo_MARIA_INOCENCIA_2_1787308403527.pdf"
)
output_dir = Path(".agents/outputs/dossie_attached_pages")
output_dir.mkdir(parents=True, exist_ok=True)

document = fitz.open(pdf_path)
print(f"pages={document.page_count}")
print(f"metadata={document.metadata}")

for index, page in enumerate(document):
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    output_path = output_dir / f"page-{index + 1:02d}.png"
    pixmap.save(output_path)
    print(f"rendered={output_path} size={page.rect.width}x{page.rect.height}")
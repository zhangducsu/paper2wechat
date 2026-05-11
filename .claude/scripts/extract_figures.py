#!/usr/bin/env python3
"""
PDF Figure Extractor
从PDF中提取所有大于200x200px的图片，按Figure编号命名
"""

import fitz  # PyMuPDF
import os
import sys
import json
import re


def extract_figures(pdf_path, output_dir):
    """Extract figures from PDF"""
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    # Track extracted figures
    figures = []
    fig_counter = 0
    
    # Common figure caption patterns
    fig_pattern = re.compile(r'Fig\.\s*(\d+)|Figure\s*(\d+)', re.IGNORECASE)
    
    for page_idx in range(total_pages):
        page = doc[page_idx]
        images = page.get_images(full=True)
        page_text = page.get_text()
        
        # Find figure numbers mentioned on this page
        fig_numbers_on_page = set()
        for match in fig_pattern.finditer(page_text):
            num = match.group(1) or match.group(2)
            fig_numbers_on_page.add(int(num))
        
        for img_idx, img in enumerate(images):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                w = base_image["width"]
                h = base_image["height"]
                
                # Only save reasonably large images
                if w > 200 and h > 200:
                    fig_counter += 1
                    
                    # Try to match with figure number
                    fig_num = None
                    for fn in sorted(fig_numbers_on_page):
                        fname = f"fig{fn}.{image_ext}"
                        fpath = os.path.join(output_dir, fname)
                        if not os.path.exists(fpath):
                            fig_num = fn
                            break
                    
                    if fig_num is None:
                        fname = f"fig{fig_counter}.{image_ext}"
                    else:
                        fname = f"fig{fig_num}.{image_ext}"
                    
                    fpath = os.path.join(output_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(image_bytes)
                    
                    figures.append({
                        "file": fname,
                        "page": page_idx + 1,
                        "size": f"{w}x{h}",
                        "fig_num": fig_num
                    })
                    
                    print(f"  Extracted: {fname} ({w}x{h}) from page {page_idx + 1}")
                    
            except Exception as e:
                print(f"  Warning: Failed to extract image {img_idx} from page {page_idx + 1}: {e}")
    
    doc.close()
    
    # Save figure metadata
    meta_path = os.path.join(output_dir, "figures_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(figures, f, ensure_ascii=False, indent=2)
    
    print(f"\nTotal: {len(figures)} figures extracted to {output_dir}")
    print(f"Metadata saved to {meta_path}")
    
    return figures


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_figures.py <pdf_path> <output_dir>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    extract_figures(pdf_path, output_dir)

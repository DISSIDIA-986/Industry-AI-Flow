#!/usr/bin/env python3
"""
Generate high-resolution image from CAPSTONE_POSTER.html for printing.
Uses Playwright to render the HTML and capture as PNG/PDF.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def generate_poster_image(
    html_path: str,
    output_png: str | None = None,
    output_pdf: str | None = None,
    scale: float = 2.0,
) -> None:
    """
    Render HTML poster and save as high-resolution image/PDF.
    
    Args:
        html_path: Path to the HTML file
        output_png: Output PNG path (optional)
        output_pdf: Output PDF path (optional)
        scale: Scale factor for higher resolution (default 2x)
    """
    html_file = Path(html_path).resolve()
    if not html_file.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")
    
    file_url = f"file://{html_file}"
    
    async with async_playwright() as p:
        # Launch Chromium
        browser = await p.chromium.launch(headless=True)
        
        # Create page with proper viewport for 24x36 inch poster
        # At 72 DPI base: 24*72=1728, 36*72=2592
        # With scale=2: 3456 x 5184 pixels
        page = await browser.new_page(
            viewport={"width": int(1728 * scale), "height": int(2592 * scale)}
        )
        
        # Navigate to HTML file
        await page.goto(file_url, wait_until="networkidle")
        
        # Wait for fonts to load
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)  # Allow CSS/fonts to fully render
        
        # Generate outputs
        if output_png:
            output_png_path = Path(output_png).resolve()
            await page.screenshot(
                path=str(output_png_path),
                full_page=True,
                type="png",
                scale="device" if scale > 1 else "css",
            )
            print(f"✓ PNG saved: {output_png_path}")
        
        if output_pdf:
            output_pdf_path = Path(output_pdf).resolve()
            # Generate PDF with exact 24x36 inch size as defined in CSS @page
            await page.pdf(
                path=str(output_pdf_path),
                width="24in",  # 24 inches
                height="36in",  # 36 inches
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            print(f"✓ PDF saved: {output_pdf_path}")
        
        await browser.close()


async def main():
    script_dir = Path(__file__).parent
    html_path = script_dir / "CAPSTONE_POSTER.html"
    
    print("🎨 Generating poster images for printing...")
    print(f"Source: {html_path}")
    
    # Generate both PNG and PDF
    await generate_poster_image(
        html_path=str(html_path),
        output_png=str(script_dir / "CAPSTONE_POSTER.png"),
        output_pdf=str(script_dir / "CAPSTONE_POSTER.pdf"),
        scale=2.0,  # 2x scale for high resolution
    )
    
    print("\n✅ Done! Files ready for printing.")
    print("\nPrinting tips:")
    print("- Use the PDF for best print quality")
    print("- Print size: 24×36 inches (61×91.5 cm)")
    print("- Ensure 'Actual Size' or '100%' scaling in print dialog")


if __name__ == "__main__":
    asyncio.run(main())

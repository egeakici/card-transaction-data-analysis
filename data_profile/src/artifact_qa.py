"""Render publication PDFs and verify figure pairs and generated links."""
import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image,ImageDraw

from .common import OUT,DERIVED,json_save


def run():
    render_dir=DERIVED/'figure_qa';render_dir.mkdir(exist_ok=True)
    checks=[];tiles=[]
    for path in sorted((OUT/'figures').glob('*.pdf')):
        png=path.with_suffix('.png');assert png.exists()
        with Image.open(png) as image:
            dpi=image.info.get('dpi',(0,0));assert all(abs(v-300)<1 for v in dpi),path.name
            assert image.width>=1000 and image.height>=600
        with pdfplumber.open(path) as doc:
            assert len(doc.pages)==1
            text=doc.pages[0].extract_text() or ''
            assert len(text)>20,path.name
        document=pdfium.PdfDocument(path);page=document[0]
        rendered=page.render(scale=1.5).to_pil().convert('RGB')
        rendered.save(render_dir/f'{path.stem}.png')
        thumb=rendered.copy();thumb.thumbnail((900,500))
        tile=Image.new('RGB',(950,550),'white');tile.paste(thumb,((950-thumb.width)//2,35))
        ImageDraw.Draw(tile).text((12,8),path.stem,fill='black');tiles.append(tile)
        page.close();document.close()
        checks.append({'figure':path.stem,'png_dpi':dpi,'pdf_text_verified':True,'pdf_rendered':True})
    assert len(checks)==11,f'Expected eleven figure pairs, got {len(checks)}'
    contact=Image.new('RGB',(1900,550*((len(tiles)+1)//2)),'#eeeeee')
    for i,tile in enumerate(tiles):contact.paste(tile,((i%2)*950,(i//2)*550))
    contact.save(DERIVED/'all_figures_contact_sheet.png')
    broken=[]
    for path in OUT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            target=target.split('#')[0]
            if target and not (path.parent/target).exists():broken.append({'file':path.relative_to(OUT).as_posix(),'target':target})
    assert not broken,broken
    result={'figure_pairs':len(checks),'png_resolution':'300 dpi','pdf_rendering':'passed','broken_relative_links':broken,'figures':checks}
    json_save(OUT/'artifact_checks.json',result)
    return result


if __name__=='__main__':run()

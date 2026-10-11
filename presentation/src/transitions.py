"""Inject slide transitions (Morph + fades) into a pptxgenjs-built deck.

PowerPoint stores Morph as an mc:AlternateContent block so that older
renderers fall back to a cross-fade. Transitions live between
<p:clrMapOvr> and </p:sld> in CT_Slide.
"""
import json, re, shutil, sys, zipfile
from defusedxml import minidom

MORPH = (
    '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
    '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
    '<p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"'
    ' spd="slow" p14:dur="{dur}" advClick="1"><p159:morph option="byObject"/></p:transition>'
    '</mc:Choice>'
    '<mc:Fallback>'
    '<p:transition spd="slow" advClick="1"><p:fade/></p:transition>'
    '</mc:Fallback>'
    '</mc:AlternateContent>'
)
FADE = '<p:transition spd="slow" advClick="1"><p:fade/></p:transition>'
FADE_BLACK = '<p:transition spd="slow" advClick="1"><p:fade thruBlk="1"/></p:transition>'

BLOCK = {
    'morph': MORPH.format(dur=1100),
    'morph_slow': MORPH.format(dur=1500),
    'fade': FADE,
    'fadeBlack': FADE_BLACK,
}


def slide_order(zf):
    """Return slide part names in presentation order."""
    pres = minidom.parseString(zf.read('ppt/presentation.xml'))
    rels = minidom.parseString(zf.read('ppt/_rels/presentation.xml.rels'))
    rid2target = {r.getAttribute('Id'): r.getAttribute('Target')
                  for r in rels.getElementsByTagName('Relationship')}
    out = []
    for sld in pres.getElementsByTagName('p:sldId'):
        rid = sld.getAttribute('r:id')
        target = rid2target[rid].replace('../', '').lstrip('/')
        out.append(target if target.startswith('ppt/') else 'ppt/' + target)
    return out


def main(pptx, plan_file):
    plan = json.load(open(plan_file))
    src = pptx + '.orig'
    shutil.copy(pptx, src)
    with zipfile.ZipFile(src) as zin:
        order = slide_order(zin)
        if len(order) != len(plan):
            sys.exit('plan has %d entries but deck has %d slides' % (len(plan), len(order)))
        trans = dict(zip(order, plan))
        with zipfile.ZipFile(pptx, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename in trans:
                    xml = data.decode('utf-8')
                    if '<p:transition' in xml or 'p159:morph' in xml:
                        sys.exit('slide already carries a transition: ' + item.filename)
                    block = BLOCK[trans[item.filename]]
                    new, n = re.subn(r'</p:sld>\s*$', block + '</p:sld>', xml)
                    if n != 1:
                        sys.exit('could not locate </p:sld> in ' + item.filename)
                    data = new.encode('utf-8')
                zout.writestr(item, data)
    counts = {}
    for v in plan:
        counts[v] = counts.get(v, 0) + 1
    print('transitions applied:', ', '.join('%s x%d' % kv for kv in sorted(counts.items())))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

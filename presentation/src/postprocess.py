"""Inject slide transitions and object animations into a pptxgenjs-built deck.

pptxgenjs writes neither, so both go straight into the slide XML. In CT_Slide the
order is <p:cSld>, <p:clrMapOvr>, <p:transition>, <p:timing>, so both parts are
appended just before </p:sld>, transition first.
"""
import json, re, shutil, sys, zipfile
from defusedxml import minidom

# ----------------------------------------------------------------- transitions
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
BLOCK = {
    'morph': MORPH.format(dur=1100),
    'morph_slow': MORPH.format(dur=1500),
    'fade': '<p:transition spd="slow" advClick="1"><p:fade/></p:transition>',
    'fadeBlack': '<p:transition spd="slow" advClick="1"><p:fade thruBlk="1"/></p:transition>',
}

# ------------------------------------------------------------------ animations
PRESET = {'fade': (10, 0), 'floatUp': (10, 0), 'zoom': (23, 0), 'wipeUp': (22, 4)}


class Ids:
    def __init__(self, start=3):
        self.n = start

    def __call__(self):
        self.n += 1
        return self.n


def _set_visible(spid, ids):
    return ('<p:set><p:cBhvr><p:cTn id="%d" dur="1" fill="hold">'
            '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            '<p:tgtEl><p:spTgt spid="%s"/></p:tgtEl>'
            '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
            '</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>' % (ids(), spid))


def _fade_in(spid, dur, ids):
    return ('<p:animEffect transition="in" filter="fade"><p:cBhvr>'
            '<p:cTn id="%d" dur="%d"/><p:tgtEl><p:spTgt spid="%s"/></p:tgtEl>'
            '</p:cBhvr></p:animEffect>' % (ids(), dur, spid))


def _anim_attr(spid, attr, frm, to, dur, ids):
    return ('<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base">'
            '<p:cTn id="%d" dur="%d" fill="hold"/>'
            '<p:tgtEl><p:spTgt spid="%s"/></p:tgtEl>'
            '<p:attrNameLst><p:attrName>%s</p:attrName></p:attrNameLst></p:cBhvr>'
            '<p:tavLst><p:tav tm="0"><p:val><p:strVal val="%s"/></p:val></p:tav>'
            '<p:tav tm="100000"><p:val><p:strVal val="%s"/></p:val></p:tav></p:tavLst>'
            '</p:anim>' % (ids(), dur, spid, attr, frm, to))


def effect_xml(kind, spid, dur, delay, ids):
    pid, sub = PRESET[kind]
    body = _set_visible(spid, ids)
    if kind == 'wipeUp':
        body += ('<p:animEffect transition="in" filter="wipe(up)"><p:cBhvr>'
                 '<p:cTn id="%d" dur="%d"/><p:tgtEl><p:spTgt spid="%s"/></p:tgtEl>'
                 '</p:cBhvr></p:animEffect>' % (ids(), dur, spid))
    else:
        body += _fade_in(spid, dur, ids)
    if kind == 'floatUp':
        body += _anim_attr(spid, 'ppt_y', '#ppt_y+0.055', '#ppt_y', dur, ids)
    elif kind == 'zoom':
        body += _anim_attr(spid, 'ppt_w', '#ppt_w*0.6', '#ppt_w', dur, ids)
        body += _anim_attr(spid, 'ppt_h', '#ppt_h*0.6', '#ppt_h', dur, ids)
    return ('<p:par><p:cTn id="%d" presetID="%d" presetClass="entr" presetSubtype="%d"'
            ' fill="hold" grpId="0" nodeType="withEffect">'
            '<p:stCondLst><p:cond delay="%d"/></p:stCondLst>'
            '<p:childTnLst>%s</p:childTnLst></p:cTn></p:par>'
            % (ids(), pid, sub, delay, body))


def timing_xml(steps, name2id, where):
    """steps: [{shapes, effect, dur, delay}] — all start automatically, delays absolute."""
    ids = Ids()
    inner = []
    for st in steps:
        for nm in st['shapes']:
            if nm not in name2id:
                raise SystemExit('%s: no shape named %r (have %d names)'
                                 % (where, nm, len(name2id)))
            inner.append(effect_xml(st['effect'], name2id[nm], st['dur'], st['delay'], ids))
    if not inner:
        return ''
    return (
        '<p:timing><p:tnLst><p:par>'
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        '<p:par><p:cTn id="3" fill="hold">'
        '<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        + ''.join(inner) +
        '</p:childTnLst></p:cTn></p:par>'
        '</p:childTnLst></p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        '</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')


NAME_RE = re.compile(r'<p:cNvPr[^>]*\bid="(\d+)"[^>]*\bname="([^"]*)"')
SP_RE = re.compile(r'<p:sp>.*?</p:sp>', re.S)
PH_RE = re.compile(r'<p:ph\b[^/>]*\bidx="(\d+)"', re.S)


def shape_ids(xml):
    """name -> shape id, plus 'ph:<idx>' for placeholders (pptxgenjs drops their
    objectName, but the layout-assigned idx is stable)."""
    ids = {m.group(2): m.group(1) for m in NAME_RE.finditer(xml)}
    for blk in SP_RE.finditer(xml):
        b = blk.group(0)
        cn = NAME_RE.search(b)
        ph = PH_RE.search(b)
        if cn and ph:
            ids['ph:' + ph.group(1)] = cn.group(1)
    return ids


def slide_order(zf):
    pres = minidom.parseString(zf.read('ppt/presentation.xml'))
    rels = minidom.parseString(zf.read('ppt/_rels/presentation.xml.rels'))
    rid2t = {r.getAttribute('Id'): r.getAttribute('Target')
             for r in rels.getElementsByTagName('Relationship')}
    out = []
    for sld in pres.getElementsByTagName('p:sldId'):
        t = rid2t[sld.getAttribute('r:id')].replace('../', '').lstrip('/')
        out.append(t if t.startswith('ppt/') else 'ppt/' + t)
    return out


def main(pptx, trans_file, fx_file=None):
    plan = json.load(open(trans_file))
    fx = {int(k): v for k, v in json.load(open(fx_file)).items()} if fx_file else {}
    src = pptx + '.orig'
    shutil.copy(pptx, src)
    tmp = pptx + '.tmp'
    n_fx = 0
    with zipfile.ZipFile(src) as zin:
        order = slide_order(zin)
        if len(order) != len(plan):
            sys.exit('plan has %d entries, deck has %d slides' % (len(plan), len(order)))
        by_part = {part: (i + 1, plan[i]) for i, part in enumerate(order)}
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename in by_part:
                    num, trans = by_part[item.filename]
                    xml = data.decode('utf-8')
                    if '<p:transition' in xml or '<p:timing>' in xml:
                        sys.exit('slide already has timing/transition: ' + item.filename)
                    add = BLOCK[trans]
                    if num in fx:
                        name2id = shape_ids(xml)
                        add += timing_xml(fx[num], name2id, 'slide %d' % num)
                        n_fx += sum(len(s['shapes']) for s in fx[num])
                    xml, k = re.subn(r'</p:sld>\s*$', add + '</p:sld>', xml)
                    if k != 1:
                        sys.exit('no </p:sld> in ' + item.filename)
                    data = xml.encode('utf-8')
                zout.writestr(item, data)
    shutil.move(tmp, pptx)          # only replace the deck once the rewrite succeeded
    counts = {}
    for v in plan:
        counts[v] = counts.get(v, 0) + 1
    print('transitions:', ', '.join('%s x%d' % kv for kv in sorted(counts.items())))
    print('animations: %d effects across slides %s'
          % (n_fx, ', '.join(str(k) for k in sorted(fx))))


if __name__ == '__main__':
    main(*sys.argv[1:])

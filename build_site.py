#!/usr/bin/env python3
"""
Halal Market Ledger — static site builder.

Regenerates index.html from data/history.json + the report pages in reports/.
Run after dropping a new reports/YYYY-MM-DD.html and appending to history.json:

    python3 build_site.py
"""
import json, os, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

def e(s): return html.escape(str(s))

def load_history():
    p = os.path.join(ROOT, 'data', 'history.json')
    if not os.path.exists(p): return []
    with open(p) as f:
        try: return json.load(f) or []
        except json.JSONDecodeError: return []

def money(v, c='$'):
    try: return c + format(float(v), ',.2f')
    except (TypeError, ValueError): return 'n/a'

def sgn(v, d=2):
    if v is None: return '<span class="na">n/a</span>'
    try: v = float(v)
    except (TypeError, ValueError): return '<span class="na">n/a</span>'
    cls = 'up' if v > 0 else ('down' if v < 0 else 'flat')
    return '<span class="%s">%+.*f%%</span>' % (cls, d, v)

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="Daily Shariah-screened equity review — 112 securities scored every trading day.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%%22http://www.w3.org/2000/svg%%22 viewBox=%%220 0 100 100%%22><text y=%%22.9em%%22 font-size=%%2290%%22>🌙</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,700&family=JetBrains+Mono:wght@400;500;700&display=swap">
<link rel="stylesheet" href="%(base)sassets/style.css">
</head>
<body>
<script>(function(){try{var t=localStorage.getItem('hml-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
'''

THEME_BTN = '''<button class="themebtn" id="themebtn" type="button" aria-label="Switch colour theme">Theme</button>
<script>
(function(){
  var b=document.getElementById('themebtn'); if(!b) return;
  b.addEventListener('click',function(){
    var de=document.documentElement, cur=de.getAttribute('data-theme');
    if(!cur){ cur = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light'; }
    var next = cur==='dark' ? 'light':'dark';
    de.setAttribute('data-theme',next);
    try{ localStorage.setItem('hml-theme',next); }catch(e){}
  });
})();
</script>'''

def build_index(hist):
    runs = sorted(hist, key=lambda r: r.get('date',''), reverse=True)
    latest = runs[0] if runs else None
    P = [HEAD % {'title':'Halal Market Ledger', 'base':''}]
    A = P.append

    A('<div class="hero"><canvas id="stars"></canvas><div class="hero-in">')
    A('<div class="brand"><span class="eyebrow">Daily Shariah-Screened Equity Review</span>'
      '<h1>Halal Market Ledger</h1>'
      '<p class="sub">112 Shariah-screened securities &mdash; 50 US stocks, 50 TSX listings and 12 halal funds &mdash; '
      'ranked on a single 105-point value-and-quality model. A new report every trading day, all of them kept here.</p></div>')
    A('<div class="stamp">')
    if latest:
        A('<span class="big">%s</span>' % e(latest.get('label', latest.get('date',''))))
        A('<span class="sm">latest report &middot; %d in the archive</span>' % len(runs))
    A(THEME_BTN)
    A('</div></div></div>')

    A('<div class="wrap">')

    if not runs:
        A('<div class="empty"><h2>No reports yet</h2><p>The first scheduled run will publish here.</p></div>')
    else:
        # ---- latest highlights ----
        A('<section><div class="sec-head"><h2>Latest run</h2>'
          '<span class="sec-note">%s &middot; %s</span></div>' %
          (e(latest.get('label','')), e(latest.get('session',''))))
        A('<div class="strip">')
        for i, p in enumerate(latest.get('top_us', [])[:3], 1):
            A('<div class="sc"><span class="l">US pick %d</span><span class="v">%s</span>'
              '<span class="m">%s &middot; %s</span><span class="m">score %s</span></div>'
              % (i, e(p['t']), money(p['p']), sgn(p.get('c')), p.get('s','')))
        bc = latest.get('best_ca')
        if bc:
            A('<div class="sc"><span class="l">Canada</span><span class="v">%s</span>'
              '<span class="m">%s &middot; %s</span><span class="m">score %s</span></div>'
              % (e(bc['t']), money(bc['p'],'C$'), sgn(bc.get('c')), bc.get('s','')))
        te = latest.get('top_etf')
        if te:
            A('<div class="sc"><span class="l">Top fund</span><span class="v">%s</span>'
              '<span class="m">%s &middot; %s</span></div>'
              % (e(te['t']), money(te['p']), sgn(te.get('c'))))
        A('<div class="sc"><span class="l">US avg move</span><span class="v">%s</span>'
          '<span class="m">50 names</span></div>' % sgn(latest.get('us_avg')))
        A('</div>')
        if latest.get('note'):
            A('<p class="note">%s</p>' % e(latest['note']))
        A('<p style="margin-top:16px"><a class="cta" href="reports/%s.html">Read the full report &rarr;</a></p>'
          % e(latest['date']))
        A('</section>')

        # ---- archive ----
        A('<section><div class="sec-head"><h2>Archive</h2>'
          '<span class="sec-note">%d report%s</span></div>' % (len(runs), '' if len(runs)==1 else 's'))
        A('<div class="tw"><table><thead><tr><th>Date</th><th class="num">US avg</th>'
          '<th>Top 3 US</th><th>Canada</th><th class="num">Strong Buy</th><th class="num">Buy</th><th></th>'
          '</tr></thead><tbody>')
        for r in runs:
            picks = ' &middot; '.join('%s <span class="mut">%s</span>' % (e(p['t']), p.get('s',''))
                                      for p in r.get('top_us', [])[:3])
            ca = r.get('best_ca') or {}
            c = r.get('counts') or {}
            A('<tr><td class="nm"><a href="reports/%s.html">%s</a></td>'
              '<td class="num">%s</td><td class="picks">%s</td>'
              '<td class="mono">%s</td><td class="num">%s</td><td class="num">%s</td>'
              '<td class="num"><a class="mini" href="reports/%s.html">open</a></td></tr>'
              % (e(r['date']), e(r.get('label', r['date'])), sgn(r.get('us_avg')), picks,
                 e(ca.get('t','')), c.get('Strong Buy',''), c.get('Buy',''), e(r['date'])))
        A('</tbody></table></div></section>')

        # ---- score trend ----
        if len(runs) > 1:
            A('<section><div class="sec-head"><h2>Score trend</h2>'
              '<span class="sec-note">top names across %d runs</span></div>' % len(runs))
            A('<div id="trend" class="tgrid"></div></section>')

    A('<div class="disc"><b>Not investment advice.</b> This is an automated daily screen, not a recommendation to buy or '
      'sell anything. The scores are the output of a fixed formula applied to publicly reported ratios. Analyst targets are '
      'opinions with a poor forecasting record. Shariah compliance is a personal religious obligation &mdash; index screens '
      'disagree with each other, and none substitutes for your own scholarship or a qualified advisor. Do your own research.</div>')
    A('<footer><span>Halal Market Ledger</span><span>Built %s &middot; %d report%s archived</span></footer>'
      % (datetime.date.today().isoformat(), len(runs), '' if len(runs)==1 else 's'))
    A('</div>')

    A('<script id="hist" type="application/json">%s</script>' % json.dumps(
        [{'d': r['date'], 'us': r.get('us', [])} for r in runs]))
    A(TREND_JS)
    A(STARS_JS)
    A('</body></html>')
    return '\n'.join(P)

TREND_JS = '''<script>
(function(){
  var box=document.getElementById('trend'); if(!box) return;
  var H=[]; try{H=JSON.parse(document.getElementById('hist').textContent)||[];}catch(e){return;}
  if(H.length<2) return;
  var chron=H.slice().reverse(), map={};
  chron.forEach(function(r){ (r.us||[]).forEach(function(x){ (map[x.t]=map[x.t]||[]).push(x.s); }); });
  var latest=(chron[chron.length-1].us||[]).slice().sort(function(a,b){return b.s-a.s;}).slice(0,12);
  var out=[];
  latest.forEach(function(x){
    var v=map[x.t]||[]; if(v.length<2) return;
    var mn=Math.min.apply(null,v), mx=Math.max.apply(null,v), rg=(mx-mn)||1, W=100, Hh=30;
    var pts=v.map(function(s,i){return [(i/(v.length-1))*W, Hh-((s-mn)/rg)*Hh];});
    var d=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);}).join(' ');
    var dl=v[v.length-1]-v[0], col=dl>0?'var(--jade)':(dl<0?'var(--clay)':'var(--ink-3)');
    out.push('<div class="tc"><div class="th"><span>'+x.t+'</span><span class="tv">'+v[v.length-1].toFixed(1)+'</span></div>'+
      '<div class="th mut2"><span>'+v.length+' runs</span><span style="color:'+col+'">'+(dl>0?'+':'')+dl.toFixed(1)+'</span></div>'+
      '<svg viewBox="0 0 '+W+' '+Hh+'" preserveAspectRatio="none" aria-hidden="true">'+
      '<path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="1.6" vector-effect="non-scaling-stroke"/>'+
      '<circle cx="'+pts[pts.length-1][0].toFixed(1)+'" cy="'+pts[pts.length-1][1].toFixed(1)+'" r="2" fill="'+col+'"/></svg></div>');
  });
  box.innerHTML=out.join('');
})();
</script>'''

STARS_JS = '''<script>
(function(){
  var c=document.getElementById('stars'); if(!c) return;
  var x=c.getContext('2d'), dpr=Math.min(window.devicePixelRatio||1,2);
  function col(){ return getComputedStyle(document.documentElement).getPropertyValue('--star').trim()||'#1a6b57'; }
  function star8(cx,cy,R){
    var r=R*0.414, p=[];
    for(var i=0;i<16;i++){ var a=(Math.PI/8)*i-Math.PI/2, rad=(i%2===0)?R:r;
      p.push([cx+Math.cos(a)*rad, cy+Math.sin(a)*rad]); }
    x.beginPath(); x.moveTo(p[0][0],p[0][1]);
    for(var j=1;j<16;j++) x.lineTo(p[j][0],p[j][1]);
    x.closePath(); x.stroke();
  }
  function draw(){
    var w=c.clientWidth,h=c.clientHeight; if(!w||!h) return;
    c.width=w*dpr; c.height=h*dpr; x.setTransform(dpr,0,0,dpr,0,0);
    x.clearRect(0,0,w,h); x.strokeStyle=col(); x.lineWidth=1; x.lineJoin='round';
    var S=64,R=S*0.52;
    for(var row=-1,yy=-S; yy<h+S; row++, yy+=S){
      var off=(row%2===0)?0:S/2;
      for(var xx=-S+off; xx<w+S; xx+=S){
        star8(xx,yy,R);
        x.beginPath(); var q=S*0.5*0.30;
        x.moveTo(xx+S/2,yy+S/2-q); x.lineTo(xx+S/2+q,yy+S/2);
        x.lineTo(xx+S/2,yy+S/2+q); x.lineTo(xx+S/2-q,yy+S/2);
        x.closePath(); x.stroke();
      }
    }
  }
  draw();
  var t; addEventListener('resize',function(){clearTimeout(t);t=setTimeout(draw,120);});
  if(window.matchMedia){var mq=matchMedia('(prefers-color-scheme: dark)');
    (mq.addEventListener?mq.addEventListener.bind(mq,'change'):mq.addListener.bind(mq))(draw);}
  new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(draw);
})();
</script>'''

if __name__ == '__main__':
    hist = load_history()
    with open(os.path.join(ROOT,'index.html'),'w',encoding='utf-8') as f:
        f.write(build_index(hist))
    print('index.html rebuilt — %d report(s) in archive' % len(hist))

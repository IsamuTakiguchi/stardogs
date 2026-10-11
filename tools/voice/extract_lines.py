import re,json,sys,os
s=open(os.path.join(os.path.dirname(__file__),'..','..','public','index.html'),encoding='utf-8').read()
L=[]
def add(w,t):
    if (w,t) not in L: L.append((w,t))
for w,t in re.findall(r"radio\('(\w+)','([^']+)'",s): add(w,t)
for w,a,b in re.findall(r"radio\('(\w+)',[^?']+\?'([^']+)':'([^']+)'\)",s): add(w,a); add(w,b)
# chase lines
ch=s[s.index('const CHASE={'):s.index('function chaseEvent')]
for who,body in re.findall(r"\n  (\w+):\{(.*?)\},?(?=\n)",ch):
    for k,v in re.findall(r"(start|ff|fail):'([^']+)'",body): add(who,v)
    m=re.search(r"saved:\[(.*?)\]",body); [add(who,v) for v in re.findall(r"'([^']+)'",m.group(1))]
    m=re.search(r"reply:'([^']+)'",body); add('kotetsu',m.group(1))
# stage clear lines
for blk in re.findall(r"clear:(\[\[.*)",s):
    for w,t in re.findall(r"\['(\w+)','([^']+)'\]",blk): add(w,t)
# map briefings
for t in re.findall(r"brief:'([^']+)'",s): add('kotetsu',t)
json.dump([{'who':w,'text':t} for w,t in L],open(sys.argv[1],'w'),ensure_ascii=False,indent=0)
from collections import Counter; print(len(L),Counter(w for w,_ in L))

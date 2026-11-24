"""Dibuja la plantilla del mesonoto (una pieza, pinzas en V, pestañas, huecos de la esfera)
y la guía de ranuras para el chasis. Correr después de plantilla_meso.py."""
import os
AQUI = os.path.dirname(os.path.abspath(__file__))
import json, numpy as np
d=json.load(open(os.path.join(AQUI, "mesonoto.json")))
S=np.load(os.path.join(AQUI, "S.npy")); fl=np.load(os.path.join(AQUI, "flat.npy"))   # fl[j,0]=A (S[:,j]), fl[j,1]=B (S[:,j+1])
nJ=fl.shape[0]; nI=fl.shape[2]
TAB_W, TAB_L, SOLAPA = 6.0, 12.0, 5.0
HOLGURA, RANURA = 0.6, 1.0
# esfera (subida 2.5 mm a lo largo del eje) y radio del hueco
E=np.array(d["Eje_L"]["mat"]); ez=E[:3,2]; c0=np.array(d["Eje_L"]["loc"])
cL=c0+2.5*ez; cR=cL*np.array([1,-1,1]); R_HUECO=11.5
print("centro esfera L:",np.round(cL,2))

def normal_afuera(a,b,interior):
    u=(b-a)/np.linalg.norm(b-a); n=np.array([-u[1],u[0]])
    if np.dot(interior-a,n)>0: n=-n
    return u,n

def borde_con_pestanas(P, interior_pts, nseg_con_tab):
    """P: puntos del borde (en orden). Inserta pestañas en los segmentos indicados."""
    out=[P[0]]; dobleces=[]
    for i in range(len(P)-1):
        a,b=P[i],P[i+1]
        if i in nseg_con_tab:
            m=(a+b)/2; u,n=normal_afuera(a,b,interior_pts[i])
            p1=m-u*TAB_W/2; p4=m+u*TAB_W/2
            out+= [p1, p1+n*TAB_L, p4+n*TAB_L, p4]
            dobleces.append((p1+n*(TAB_L-SOLAPA), p4+n*(TAB_L-SOLAPA)))
        out.append(b)
    return out, dobleces

A=lambda j: fl[j,0]; B=lambda j: fl[j,1]
contorno=[]; dobleces=[]
# 1) pared del lado y- (franja 0, borde A) de atrás (i=0) hacia adelante (i=5), con pestañas en bandas 0..3
pts,dob=borde_con_pestanas([A(0)[i] for i in range(nI)], [B(0)[i] for i in range(nI)], {0,1,2,3})
contorno+=pts; dobleces+=dob
# 2) borde de adelante (i=5) de j=0 a j=nJ-1, con pinzas
for j in range(nJ):
    contorno.append(B(j)[5])
    if j<nJ-1:
        ap=((B(j)[3]+B(j)[4])/2+(A(j+1)[3]+A(j+1)[4])/2)/2   # punta de la pinza en x≈44
        contorno += [B(j)[4], ap, A(j+1)[4], A(j+1)[5]]
# 3) pared del lado y+ (última franja, borde B), de adelante hacia atrás
P=[B(nJ-1)[i] for i in range(nI-1,-1,-1)]
I=[A(nJ-1)[i] for i in range(nI-1,-1,-1)]
pts,dob=borde_con_pestanas(P, I, {1,2,3,4})   # segmentos 5-4..1-0 -> bandas 3..0
contorno+=pts[1:]; dobleces+=dob
# 4) borde de atrás (i=0) de j=nJ-1 a 0, con pinzas
for j in range(nJ-1,-1,-1):
    contorno.append(A(j)[0])
    if j>0:
        ap=((A(j)[1]+A(j)[2])/2+(B(j-1)[1]+B(j-1)[2])/2)/2   # punta de la pinza en x≈20
        contorno += [A(j)[1], ap, B(j-1)[1], B(j-1)[0]]
contorno=np.array(contorno)

# 5) perforaciones: corte de la esfera con la superficie, llevado al plano
def huecos(c):
    segs=[]
    for j in range(nJ):
        for i in range(nI-1):
            for tri3,tri2 in (((S[i,j],S[i,j+1],S[i+1,j]),(A(j)[i],B(j)[i],A(j)[i+1])),
                              ((S[i,j+1],S[i+1,j+1],S[i+1,j]),(B(j)[i],B(j)[i+1],A(j)[i+1]))):
                T3=np.array(tri3); T2=np.array(tri2); n=40
                f=lambda w: np.linalg.norm(w@T3-c)-R_HUECO
                for a in range(n):
                    for b in range(n-a):
                        for sub in (((a,b),(a+1,b),(a,b+1)),) + ((((a+1,b),(a+1,b+1),(a,b+1)),) if a+b<n-1 else ()):
                            W=[np.array([1-(p[0]+p[1])/n,p[0]/n,p[1]/n]) for p in sub]
                            F=[f(w) for w in W]
                            cr=[]
                            for k in range(3):
                                f1,f2=F[k],F[(k+1)%3]
                                if (f1<0)!=(f2<0):
                                    t=f1/(f1-f2); w=W[k]+(W[(k+1)%3]-W[k])*t; cr.append(w@T2)
                            if len(cr)==2: segs.append(cr)
    return segs
hL=huecos(cL); hR=huecos(cR)
print("segmentos hueco L,R:",len(hL),len(hR))

# 6) SVG carta horizontal
allp=np.vstack([contorno]+[np.array(s) for s in hL+hR] if hL+hR else [contorno])
mn=contorno.min(0); mx=contorno.max(0)
W,H=279.4,215.9
off=np.array([(W-(mx-mn)[0])/2, 22]) - mn
T=lambda p: (round(p[0]+off[0],2), round(p[1]+off[1],2))
L=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">']
L.append('<polygon points="'+" ".join("%s,%s"%T(p) for p in contorno)+'" fill="none" stroke="#000" stroke-width="0.25"/>')
for s in hL+hR:
    (x1,y1),(x2,y2)=T(s[0]),T(s[1]); L.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="0.25"/>')
for a,b in dobleces:
    (x1,y1),(x2,y2)=T(a),T(b); L.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#d0451b" stroke-width="0.3" stroke-dasharray="2,1.5"/>')
L.append(f'<text x="15" y="10" font-family="Helvetica" font-size="4" fill="#333">Mesonoto · una pieza · cartulina 200 g · escala real</text>')
L.append(f'<text x="15" y="15" font-family="Helvetica" font-size="3" fill="#333">Pinzas en V: atrás ~2 mm (borde que toca la banda 1), adelante ≤1 mm (queda bajo el pronoto). Los dos huecos son para la esfera del hombro.</text>')
L.append(f'<rect x="15" y="{H-20}" width="10" height="10" fill="none" stroke="#000" stroke-width="0.25"/><text x="27" y="{H-13}" font-family="Helvetica" font-size="3" fill="#333">1 cm — medir antes de cortar · imprimir al 100 %</text>')
L.append(f'<line x1="150" y1="{H-14}" x2="158" y2="{H-14}" stroke="#000" stroke-width="0.25"/><text x="160" y="{H-13}" font-family="Helvetica" font-size="3" fill="#333">cortar</text>')
L.append(f'<line x1="180" y1="{H-14}" x2="188" y2="{H-14}" stroke="#d0451b" stroke-width="0.3" stroke-dasharray="2,1.5"/><text x="190" y="{H-13}" font-family="Helvetica" font-size="3" fill="#333">doblar</text>')
L.append("</svg>")
open(os.path.join(AQUI, "mesonoto_plantilla_carta.svg"),"w").write("\n".join(L))

# 7) guía de ranuras sobre el chasis (vista desde arriba, cabeza hacia arriba)
ch=d["H_Chasis"]; CV=np.array(ch["verts"]); CF=ch["faces"]
zt=CV[:,2].max(); top=[f for f in CF if all(abs(CV[v,2]-zt)<0.05 for v in f)]
from collections import Counter
ed=Counter()
for f in top:
    for k in range(len(f)): ed[tuple(sorted((f[k],f[(k+1)%len(f)])))]+=1
bord=[e for e,c in ed.items() if c==1]
print("chasis: caras arriba",len(top),"aristas borde",len(bord))
V2=lambda p: np.array([-p[1], -p[0]])   # x (cabeza) hacia arriba, vista desde arriba
ranuras=[]
for jcol,lado in ((0,-1),(S.shape[1]-1,1)):
    for i in range(4):
        a,b=S[i,jcol],S[i+1,jcol]; m=(a+b)/2
        ranuras.append((m, b-a))
allc=np.array([V2(CV[v]) for e in bord for v in e]); mnc=allc.min(0); mxc=allc.max(0)
W2,H2=215.9,279.4
offc=np.array([(W2-(mxc-mnc)[0])/2, 25])-mnc
T2=lambda p: (round(p[0]+offc[0],2), round(p[1]+offc[1],2))
L=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W2}mm" height="{H2}mm" viewBox="0 0 {W2} {H2}">']
for a,b in bord:
    (x1,y1),(x2,y2)=T2(V2(CV[a])),T2(V2(CV[b])); L.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#888" stroke-width="0.25"/>')
# huella del mesonoto (borde de las paredes) punteada
for jcol in (0,S.shape[1]-1):
    pts=" ".join("%s,%s"%T2(V2(S[i,jcol])) for i in range(S.shape[0]))
    L.append(f'<polyline points="{pts}" fill="none" stroke="#2a7" stroke-width="0.3" stroke-dasharray="1.5,1"/>')
for m,dv in ranuras:
    d2=V2(dv); ang=np.degrees(np.arctan2(d2[1],d2[0])); cx,cy=T2(V2(m)); w=TAB_W+HOLGURA
    L.append(f'<rect x="{cx-w/2:.2f}" y="{cy-RANURA/2:.2f}" width="{w:.2f}" height="{RANURA}" transform="rotate({ang:.1f} {cx} {cy})" fill="none" stroke="#000" stroke-width="0.25"/>')
L.append(f'<text x="15" y="12" font-family="Helvetica" font-size="4" fill="#333">Guía: ranuras del mesonoto en el chasis (vista desde arriba, cabeza hacia arriba)</text>')
L.append(f'<text x="15" y="17" font-family="Helvetica" font-size="3" fill="#333">Gris = contorno del chasis (alinear con tu pieza). Negro = 8 ranuras de {TAB_W+HOLGURA:.1f} × {RANURA} mm. Verde punteado = dónde apoyan las paredes.</text>')
L.append(f'<rect x="15" y="{H2-20}" width="10" height="10" fill="none" stroke="#000" stroke-width="0.25"/><text x="27" y="{H2-13}" font-family="Helvetica" font-size="3" fill="#333">1 cm — imprimir al 100 %</text>')
L.append("</svg>")
open(os.path.join(AQUI, "mesonoto_guia_chasis_carta.svg"),"w").write("\n".join(L))
print("contorno pts",len(contorno),"tamaño",np.round(mx-mn,1))

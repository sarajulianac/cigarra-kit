"""Plantilla del mesonoto: una pieza, franjas longitudinales unidas por el centro, pinzas en V."""
import json, os, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(AQUI, "desarrollo_meso.py")).read().split('F=[desarrollar')[0])   # carga S, tercer, desarrollar
def rigido(P,Q):
    cp,cq=P.mean(0),Q.mean(0); H=(P-cp).T@(Q-cq); U,_,Vt=np.linalg.svd(H)
    D=np.eye(2); D[1,1]=np.sign(np.linalg.det(Vt.T@U.T)); R=Vt.T@D@U.T
    return lambda X:(X-cp)@R.T+cq
nI,nJ=S.shape[0],S.shape[1]
POR_PANEL=1
# 1. cada franja j (entre S[:,j] y S[:,j+1]) desarrollada
FR=[desarrollar(S[:,j],S[:,j+1]) for j in range(nJ-1)]
# 2. colocar: dentro del panel se pegan a lo largo de todo el borde; entre paneles, solo en el centro
flat=[None]*(nJ-1); mism=[]
CENTRO=[2,3]
for j in range(nJ-1):
    FA,FB,_=FR[j]
    if j==0:
        flat[j]=(FA,FB); continue
    pA,pB=flat[j-1]
    mismo_panel = (j % POR_PANEL)!=0
    idx = list(range(nI)) if mismo_panel else CENTRO
    T=rigido(FA[idx],pB[idx])
    A2,B2=T(FA),T(FB)
    if mismo_panel:
        mism.append(np.abs(np.linalg.norm(A2-pB,axis=1)).max())
        A2=pB.copy()        # el borde común es uno solo
    flat[j]=(A2,B2)
print("desajuste máx dentro de paneles (mm):",round(max(mism or [0]),2))
# 3. pinzas: en cada frontera de panel, el borde de la izquierda (pB) y el de la derecha (A)
pinzas=[]
for j in range(POR_PANEL, nJ-1, POR_PANEL):
    pB=flat[j-1][1]; A=flat[j][0]
    pinzas.append((j, np.linalg.norm(pB-A,axis=1)))
print("pinzas (ancho por x):", [(j,np.round(g[[0,1,4,5]],1).tolist()) for j,g in pinzas])
np.save(os.path.join(AQUI, "flat.npy"),np.array([np.stack([a,b]) for a,b in flat]))

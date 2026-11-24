"""Mesonoto: lee su malla (mesonoto.json, exportada de Mecanismo_Alas.blend) y la desarrolla.
Prueba dos formas de cortarlo y mide el tamaño de las pinzas que haría falta en cada una."""
import os
AQUI = os.path.dirname(os.path.abspath(__file__))
import json, numpy as np
d=json.load(open(os.path.join(AQUI, "mesonoto.json")))
V=np.array(d["verts"])
xs=sorted(set(np.round(V[:,0],1)))
# secciones: puntos ordenados por el arco (de y- a y+ pasando por arriba)
S=[]
for x in xs:
    s=V[np.abs(V[:,0]-x)<0.05]
    # ordenar por ángulo alrededor de (y=0,z=0)
    ang=np.arctan2(s[:,2], -s[:,1])   # y- -> 0 rad, arriba pi/2, y+ -> pi
    S.append(s[np.argsort(ang)])
S=np.array(S)   # (6,27,3)
def tercer(a,b,da,db,lado):
    L=np.linalg.norm(b-a); x=(da**2-db**2+L**2)/(2*L); h=np.sqrt(max(da**2-x**2,0))
    u=(b-a)/L; n=np.array([-u[1],u[0]]); return a+u*x+lado*n*h
def desarrollar(A,B):
    """A,B (27,3): bordes. Devuelve coords planas FA,FB y error (diagonales no usadas)."""
    n=len(A); FA=np.zeros((n,2)); FB=np.zeros((n,2))
    FA[0]=[0,0]; FB[0]=[np.linalg.norm(B[0]-A[0]),0]
    err=0
    for j in range(n-1):
        # tri (A_j,B_j,A_j+1)
        FA[j+1]=tercer(FA[j],FB[j],np.linalg.norm(A[j+1]-A[j]),np.linalg.norm(A[j+1]-B[j]),+1)
        FB[j+1]=tercer(FB[j],FA[j+1],np.linalg.norm(B[j+1]-B[j]),np.linalg.norm(B[j+1]-A[j+1]),-1)
        e=abs(np.linalg.norm(FB[j+1]-FA[j])-np.linalg.norm(B[j+1]-A[j])); err=max(err,e)
    return FA,FB,err
F=[desarrollar(S[i],S[i+1]) for i in range(len(S)-1)]
for i,(FA,FB,e) in enumerate(F): print("banda",i,"x",xs[i],xs[i+1],"error diag",round(e,3))
def rigido(P,Q):  # mapea P->Q
    cp,cq=P.mean(0),Q.mean(0); H=(P-cp).T@(Q-cq); U,_,Vt=np.linalg.svd(H); R=(U@Vt).T
    if np.linalg.det(R)<0: Vt[-1]*=-1; R=(U@Vt).T
    return lambda X:(X-cp)@R.T+cq
top=slice(12,15)
for i in range(len(F)-1):
    FA1,FB1,_=F[i+1]; FA0,FB0,_=F[i]
    T=rigido(FA1[top],FB0[top])
    g=np.linalg.norm(T(FA1)-FB0,axis=1)
    print("pinza entre banda",i,i+1,"separación por j:",np.round(g[[0,4,8,11,13,15,18,22,26]],2))
np.save(os.path.join(AQUI, "S.npy"), S)

print("\n--- franjas longitudinales (entre líneas j), unidas por la sección del medio ---")
# franja j: bordes A = S[:,j], B = S[:,j+1] (6 puntos a lo largo de x)
G=[desarrollar(S[:,j],S[:,j+1]) for j in range(S.shape[1]-1)]
print("error max franjas", round(max(g[2] for g in G),3))
mid=slice(2,4)
for j in range(S.shape[1]-2):
    FA1,FB1,_=G[j+1]; FA0,FB0,_=G[j]
    T=rigido(FA1[mid],FB0[mid])
    gap=np.linalg.norm(T(FA1)-FB0,axis=1)
    print(j, "huecos en x=",xs, np.round(gap,2))

import matplotlib
matplotlib.use('Agg')
import os
import json
import numpy as np
from scipy.spatial.distance import pdist, squareform
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.sparse as ss
# from MVGCN.graph import distance_scipy_spatial as dss

def build_A(nodes,maindir,kNN):
    all_nodes = dict.fromkeys(sorted(set([int(v) for vols in [list(nodes[sub][run].keys()) for sub in nodes.keys() for run in nodes[sub].keys()] for v in vols])))
    #print(sorted(set([int(v) for vols in [list(nodes[sub][run].keys()) for sub in nodes.keys() for run in nodes[sub].keys()] for v in vols])))
    #for sub in nodes.keys():
    #    print(sub)
    #    for run in nodes[sub].keys():
    #        print('\t',run)
    #        print('\t',list(nodes[sub][run].keys()))
    print(len(all_nodes.keys()))
    for vol in all_nodes.keys():
        all_nodes[vol] = np.mean(np.array([float(c) for cntr in [(nodes[sub][run][str(vol)]).strip('[]').split() for sub in nodes.keys() for run in nodes[sub].keys() if str(vol) in nodes[sub][run].keys()] for c in cntr]).reshape((-1,3)), axis=0)
    cntrs=[]
    vols=[]
    idx=0
    for k,v in all_nodes.items():
        print(idx,k)
        idx+=1
        cntrs.append(v)
        vols.append(k)
    np.savetxt(os.path.join(maindir,'vols.txt'),vols)
    np.savetxt(os.path.join(maindir,'centers.txt'),cntrs)
    
    
    dists = squareform(pdist(cntrs,metric='euclidean'))
    # dists = dists + np.eye(len(all_nodes))*np.mean(dists,axis=1)

    # kdists =  dists / np.amax(dists, axis=1)[:,np.newaxis]
    kdists = np.divide(dists,np.amax(dists))
    # print(kdists.shape)
    # print(kdists)
    idx = np.argsort(dists)[:,1:kNN]

    # kdists = np.array([[dists[n][i] for i in idx[n]] for n in range(idx.shape[0])])
    # # wt_kdists = kdists / np.amax(kdists,axis=1)[:,np.newaxis]

    A = np.zeros(dists.shape)
    for n in range(idx.shape[0]):
        for i in idx[n]:
            A[n][i] = kdists[n][i]
    # print(A)
    for r in range(A.shape[0]):
        for c in range(A.shape[1]):
            if A[r][c]>0 and A[r][c]!=A[c][r]:
                A[c][r]=A[r][c]

    A = A + np.eye(len(all_nodes))*np.mean(kdists[idx],axis=1) # add self-connections

    for r in range(A.shape[0]):
        for c in range(A.shape[1]):
            if A[r][c]!=A[c][r]:
                print(f'assymetry at row {r}, col {c}')
    return A



if __name__ == "__main__":

    #main_dir='/Volumes/ElementsExternal/mridti_test2'
    #main_dir = '/data/brain/mridti_small'
    #main_dir = '/data/brain/preproc_outputs'
    main_dir = '/data/brain/preproc2_features'
    
    with open(os.path.join(main_dir,'center_vxls.json'),'r') as n:
        nodes_dict = json.load(n)

    kNN = 20
    A = build_A(nodes_dict, main_dir,kNN)

    np.save(os.path.join(main_dir,f'adj_mtrx{kNN}.npy'), A)

    ax = sns.heatmap(A)
    fig = ax.get_figure()
    #plt.savefig(os.path.join(main_dir,f'adj_mtrx{kNN}.png'))
    fig.savefig(os.path.join(main_dir,f'adj_mtrx{kNN}.png'))

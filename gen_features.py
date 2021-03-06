import sys
import os
import subprocess
import nibabel as nib
import numpy as np
import json
from dipy.tracking import utils
from scipy.io import loadmat
from joblib import Parallel, delayed
import time
import datetime
import shutil

def bash_command(string_cmd):
    process = subprocess.Popen(string_cmd.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output

def gen_hshtbl(trk):
    hshtbl = []
    for sl in trk:
        hshtbl.append(sum([256**2*c[0]+256*c[1]+c[2] for c in sl]))
    if len(trk) != len(np.unique(np.array(hshtbl))): print("Streamline hashing generated equivalent hashes")
    return hshtbl


def gen_masks(fs_dir,subrun,vols,subject,maindir):
    diff = 100
    anatr=''
    #print('gen masks sub_run: ',subrun)
    for anatf in os.listdir(os.path.join(maindir,subject,'anat','freesurfer')):
        if os.path.exists(os.path.join(maindir,subject,'anat','freesurfer',
                    anatf,'mri','aparc+aseg.mgz')) and 'fsaverage' not in anatf:
            #print('anatfile: ',anatf)
            try:
                d = abs(int(subrun.split('_')[1].split('-')[1]) -
                                        int(anatf.split('_')[1].split('-')[1]))
            except:
                print('THIS: ', subrun, anatf)
            if d<diff:
                diff=d
                anatr = anatf
            if d==diff:
                if int(anatf.split('_')[1].split('-')[1]) <
                                        int(anatr.split('_')[1].split('-')[1]):
                    anatr = anatf
    anatr='_'.join(anatr.split('_')[:2])
    parcseg = os.path.join(fs_dir,anatr,'mri','aparc+aseg.mgz')
    anat = nib.load(parcseg)
    anat_img = anat.get_fdata().astype(int)
    anat_aff = anat.affine
    mask_dir = os.path.join(fs_dir,anatr,'seg_masks')
    if not os.path.exists(mask_dir): bash_command(f'mkdir {mask_dir}')
    labels=np.unique(anat_img)
    try:
        v_ids = np.loadtxt(vols)
    except FileNotFoundError:
        print("ERROR: Run gen_nodes.py AND adj_mtx.py first to generate the 'master list' of Volume IDs")
    for label in v_ids:
        if not os.path.exists(os.path.join(mask_dir,f'{int(label)}_msk.npz')):
            mask = np.ma.array(anat_img, mask = anat_img !=
                                                label, fill_value=0).filled()
            np.savez(os.path.join(mask_dir,f'{int(label)}_msk'), mask)
            # msk_nii = nib.Nifti1Image(mask,anat_aff)
            # nib.save(msk_nii,os.path.join(mask_dir,f'{int(label)}_msk.nii'))
    return mask_dir,parcseg

def read_trkfile(run):
    extra_calc=False
    trkfile = nib.streamlines.load(run)
    trk_img = trkfile.tractogram.streamlines
    trk_aff = trkfile.affine
    ht = gen_hshtbl(trk_img)
    return trk_img,trk_aff,ht

def get_trks(subject, maindir,dtk_path,vol_ids):
    if subject.split('-')[0]=='sub':
        print(subject)
        sub = os.path.join(maindir,subject)
        trkdir = os.path.join(sub,'dwi','tracks')
        fsdir = os.path.join(sub,'anat','freesurfer')
        if os.path.exists(trkdir):
            for run in os.listdir(trkdir):
                trkrun = os.path.join(trkdir,run)
                if not os.path.exists(os.path.join(trkrun,
                            "algo_vol-trk_map.json")) and os.path.isdir(trkrun):
                    #if os.path.isdir(trkrun): # and run in os.listdir(fsdir):
                    print(run)
                    maskdir,mgz = gen_masks(fsdir,run,vol_ids,subject,maindir)
                    nii = mgz.split('.')[0]+'.nii'
                    bash_command(f'mri_convert --in_type mgz --out_type nii {mgz} {nii}')
                    bash_command(f'flirt -in {os.path.join(sub,"dwi","dtk",run)}_dwi.nii -ref {nii} -omat {os.path.join(sub,"dwi",run)}_reg.mtx -out {os.path.join(sub,"dwi",run)}_reg')
                    #if not os.path.exists(os.path.join(trkrun,"algo_vol-trk_map.json")):
                    algo_vxl_sl={}

                    for algo in os.listdir(trkrun):
                        if algo.endswith('.trk') and 'fltr' in algo and
                                                            'reg' not in algo:
                            print(algo)
                            bash_command(f'{dtk_path}track_transform {os.path.join(trkrun,algo)} {os.path.join(trkrun,algo.split(".")[0])}_reg.trk -src {os.path.join(sub,"dwi","dtk",run)}_dwi.nii -ref {nii} -reg {os.path.join(sub,"dwi",run)}_reg.mtx -reg_type flirt')
                            algo_trks,algo_aff,hshtbl = read_trkfile(f'{os.path.join(trkrun,algo.split(".")[0])}_reg.trk')
                            np.savetxt(f'{os.path.join(trkrun,algo.split(".")[0])}_sl.txt',np.array(hshtbl))
                            vxl_sl={}
                            if os.path.exists(maskdir):
                                for maskf in os.listdir(maskdir):
                                    if maskf.endswith('npz'):
                                        try:
                                            mask = np.load(os.path.join(maskdir,
                                                                maskf))['arr_0']
                                            vxl_sl[maskf.split("_")[0]] =
                                                gen_hshtbl(list(utils.target(
                                                algo_trks,mask,algo_aff)))
                                        except:
                                            print(f'Could not load mask {maskf} for {run} {algo}')
                                sl_vxl={}
                                ks = sorted([int(k) for k in vxl_sl.keys()])
                                print(len(ks))
                                for kE in ks:
                                    sl_vxl[str(kE)]=vxl_sl[str(kE)]
                                algo_vxl_sl[algo.split('.')[0]]=sl_vxl
                    if os.path.exists(maskdir): shutil.rmtree(maskdir)
                    with open(os.path.join(trkrun,"algo_vol-trk_map.json"),'w') as t:
                        json.dump(algo_vxl_sl,t)
    return


if __name__=="__main__":
    main_dir = sys.argv[1]
    dtk_home = sys.argv[2]
    vols=os.path.join(main_dir,'vols.txt')
    n_jobs = -2

    with open('times.txt','a') as tt:
        tt.write(f'\n<=============| BCG features Run |============>\n\nDate: {datetime.datetime.now()}\nFolder: {main_dir}\nn_jobs: {n_jobs}')

    with open('preproc_log.txt','a') as lt:
        lt.write(f'<=============| BCG features Run |=============>\n\nDate: {datetime.datetime.now()}\nFolder: {main_dir}\nn_jobs: {n_jobs}')

    main_start=time.time()
    Parallel(n_jobs=n_jobs,verbose=50)(delayed(get_trks)(subdir, main_dir, 
        dtk_home, vols) for subdir in os.listdir(main_dir) if
        os.path.isdir(os.path.join(main_dir,subdir)))
    main_dur = time.time() - main_start

    with open('times.txt','a') as tt:
        tt.write(f'Overall BCG features Duration:\t{main_dur}\n')
    with open('preproc_log.txt', 'a') as lt:
        lt.write('\n\n')

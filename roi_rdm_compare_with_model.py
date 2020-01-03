#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  1 20:44:25 2020

@author: rj299
"""

#%%
import warnings
import sys 
if not sys.warnoptions:
    warnings.simplefilter("ignore")

import os
import numpy as np
import pandas as pd
import scipy.io
from scipy import stats
import scipy.spatial.distance as sp_distance

import nibabel as nib

import matplotlib.pyplot as plt
import matplotlib.pylab as pylab

import seaborn as sns 
from sklearn.preprocessing import normalize

sns.set(style = 'white', context='poster', rc={"lines.linewidth": 2.5})

#%%
params = {
          'legend.fontsize': 10,
          'axes.labelsize': 12,
         'axes.titlesize': 12,
         'xtick.labelsize': 10,
         'ytick.labelsize': 10
         
         }
pylab.rcParams.update(params)

#%% calculate SV
def ambig_utility(sub_id, par, p, a, obj_val, domain, model):
    '''
    Calcualte subjective value based on model
    For a list of trials
    
    Input:
        sub_id: subject id
        par: panda data frame of all subjects' parameter fits
        p: probability of lotteries, vector
        a: ambiguity of lotteries, vector
        obj_val: objective value of lottery pary-offs, vector
        domain_idx: domian indes, 1-medical, 0-monetary
        model: named of the subjective value model
        
    Output:
        sv: subjective values of lotteries, vector
    '''
    
    if domain == 'Med':
        domain_idx = 1
    elif domain == 'Mon':
        domain_idx = 0
        
    par_sub = par[(par.id == sub_id) & (par.is_med == domain_idx)]
    
    beta = par_sub.iloc[0]['beta']
    val1 = par_sub.iloc[0]['val1']
    val2 = par_sub.iloc[0]['val2']
    val3 = par_sub.iloc[0]['val3']
    val4 = par_sub.iloc[0]['val4']
    
    val = np.zeros(obj_val.shape)
    val[obj_val == 5] = val1
    val[obj_val == 8] = val2
    val[obj_val == 12] = val3
    val[obj_val == 25] = val4
    
    
    if model == 'ambigSVPar':       
        sv = (p - beta * a/2) * val
        
    ref_sv = np.ones(obj_val.shape) * val1
        
    return sv, ref_sv

#%%
def half_matrix(matrix):
    ''' Take half of the correlation matrix, excluding diagnoal
    Input:
        matrix
    
    Output:
        half_matrix: matrix with the upper half and diagnal equals to nan
        vector: vector of the half matrix, without nan
    '''
    import copy
    
    half_matrix = copy.deepcopy(matrix)
    
    vector = []
    for i in range(half_matrix.shape[0]):
        for j in range(half_matrix.shape[1]):
            if i-j <= 0:
                half_matrix[i,j] = np.nan
            else:
                vector.append(half_matrix[i,j])
    
    return half_matrix, np.array(vector)

#%%
# calculate spearman correlation between rdm and model rdm
# for each model, each roi, each subject

def compare_with_model(subjects, roi_names, mod_rdm_vector, out_fig):
    
    mod_names = list(mod_rdm_vector.keys())
    
    spearman_r = {roi_name: {} for roi_name in roi_names} # each model is an entry in this dictionary
    spearman_p = {roi_name: {} for roi_name in roi_names}
        
#     spearman_r = {'domain': {}, 'uncertainty': {}, 'value': {}}
#     spearman_p = {'domain': {}, 'uncertainty': {}, 'value': {}}

    for (roi_idx, roi_name) in enumerate(roi_names):
        
        # each roi is an entry in the dictionary
        spearman_r_roi = {mod_name: [] for mod_name in mod_names} # spearman's rho
        spearman_p_roi = {mod_name: [] for mod_name in mod_names} # p values

    #     spearman_r_mod = {'vmpfc': [], 'vstr': []}
    #     spearman_p_mod = {'vmpfc': [], 'vstr': []}

        for sub in subjects:
            roi_rdm_obj = np.load('/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/rdm_new/_subject_id_%s/roi_rdm.npy' %sub,
                   allow_pickle = True)

            # get dictionary type
            roi_rdm = roi_rdm_obj.item()

    #         roi_names = list(roi_rdm.keys())

            for (mod_idx, mod_name) in enumerate(mod_names):
                # spearman bween model rdm and individual rdm, using only half of matrix
                rdm_half, rdm_vector = half_matrix(roi_rdm[roi_name])
                
                if mod_name == 'sv' or mod_name == 'rating':
                    # for these two models, model rdm is different for each individual
                    # thus, mode_rdm_vector[mod_name] is a dictionary, each subject in an item
                    rho, pvalue = stats.spearmanr(rdm_vector, mod_rdm_vector[mod_name][sub])
                else:
                    rho, pvalue = stats.spearmanr(rdm_vector, mod_rdm_vector[mod_name])

                spearman_r_roi[mod_name].append(rho)
                spearman_p_roi[mod_name].append(pvalue)

        spearman_r[roi_name] = spearman_r_roi
        spearman_p[roi_name] = spearman_p_roi
        
        np.save(os.path.join(out_fig, 'spearman_r_with_model_%s' %roi_name), spearman_r_roi)
        np.save(os.path.join(out_fig, 'spearman_p_with_model_%s' %roi_name), spearman_p_roi)
        
    return spearman_r, spearman_p

#%%
# plot spearman r distribution
def plot_r_hist(r, out_fig, save = False):
    
    roi_names = list(r.keys())
    mod_names = list(r[roi_names[0]].keys())
    
    plot_size = 5
    
    for (roi_idx, roi_name) in enumerate(roi_names):

        f, ax = plt.subplots(len(mod_names), 1, figsize = (plot_size,plot_size * len(mod_names)))
        
        for (mod_idx, mod_name) in enumerate(mod_names):    
            # plot distribution
            ax[mod_idx].hist(r[roi_name][mod_name], bins = 15)
            # plot median
            median = np.median(r[roi_name][mod_name])
            ax[mod_idx].vlines(median, ymin=0, ymax=ax[mod_idx].get_ylim()[1], 
                               colors = 'r', linestyles = 'dashed')
            ax[mod_idx].legend(['median = %s' %round(median,3)])
            ax[mod_idx].set_title('Spearman r, '+mod_name+', '+roi_name)
            
        if save:
            f.savefig(os.path.join(out_fig, 'r_with_model_hist_%s.eps' %roi_name), format = 'eps')
#%%            
# permutation test

# for each iteration (iter_num), select perm_num subjects, calculate median
# each permutation: calculate spearman correlation between rdm and model rdm
# do this for each model, each roi

def permutation_test(subjects, roi_names, mod_rdm_vector, out_fig,
                    iter_num = 1000, perm_num = 100):
    
    import numpy as np
#     iter_num number of iteration
#     perm_num number of subjects (permutation)
    
    mod_names = list(mod_rdm_vector.keys())
    
    r_perm = {roi_name: {} for roi_name in roi_names}

    # each model
    for (roi_idx, roi_name) in enumerate(roi_names):

        r_perm_roi = {mod_name: [] for mod_name in mod_names}

        # each ROI
        for (mod_idx, mod_name) in enumerate(mod_names):

            for iter_idx in range(iter_num): 

                rho_perm = []

                for perm_idx in range(perm_num):
                    # randomly select a subject
                    sub = np.random.choice(subjects)
                    roi_rdm_obj = np.load('/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/rdm_new/_subject_id_%s/roi_rdm.npy' %sub,
                                          allow_pickle = True)

                    # get dictionary type
                    roi_rdm = roi_rdm_obj.item()

                    rdm_perm = roi_rdm[roi_name]

                    # shuffle columns
                    np.random.shuffle(rdm_perm)

    #                 # permute columns of matrix
    #                 columns = list(range(roi_rdm[roi_name].shape(0)))

    #                 columns_perm = np.random.permutation(columns)

    #                 rdm_perm = np.argsort(columns_perm)

                    # spearman bween model rdm and individual rdm, half matrix
                    _, rdm_vector_perm = half_matrix(rdm_perm)

    #                 rdm_vector_perm = np.random.permutation(rdm_vector)
                    if mod_name == 'sv' or mod_name == 'rating':
                    # for these two models, model rdm is different for each individual
                    # thus, mode_rdm_vector[mod_name] is a dictionary, each subject in an item
                        rho_i, pvalue_i = stats.spearmanr(rdm_vector_perm, mod_rdm_vector[mod_name][sub])
                    else:
                        rho_i, pvalue_i = stats.spearmanr(rdm_vector_perm, mod_rdm_vector[mod_name])

                    rho_perm.append(rho_i)

                r_perm_roi[mod_name].append(np.median(rho_perm))
                
                print('Model %s, ROI %s, iteration %s finished' %(mod_name, roi_name, iter_idx+1))

        r_perm[roi_name] = r_perm_roi
        
        np.save(os.path.join(out_fig, 'perm_null_%s.npy' %roi_name), r_perm_roi)
    
    return r_perm


#%%
# plot permutation null distribution
def plot_permutation_null(r_perm, out_fig, sig_level = 0.05, save = False):
    
#     sig_level = 0.05
    roi_names = list(r_perm.keys())
    mod_names = list(r_perm[roi_names[0]].keys())
    
    for (roi_idx, roi_name) in enumerate(roi_names):
    

        f, ax = plt.subplots(len(mod_names), 1, figsize = (5,5 * len(mod_names)))
        for (mod_idx, mod_name) in enumerate(mod_names):
            # plot distribution
            ax[mod_idx].hist(r_perm[roi_name][mod_name], bins = 30)

            # plot critical value
            n_iter = len(r_perm[roi_name][mod_name])
            # two-tailed
            critical_up_idx = int(n_iter * (1-sig_level/2))
            critical_low_idx = int(n_iter * (sig_level/2))
            
            r_sorted = np.sort(r_perm[roi_name][mod_name])
            critical_up = r_sorted[critical_up_idx]
            critical_low = r_sorted[critical_low_idx]
            ax[mod_idx].vlines(critical_up, ymin=0, ymax=ax[mod_idx].get_ylim()[1], 
                               colors = 'r', linestyles = 'dashed')
            ax[mod_idx].vlines(critical_low, ymin=0, ymax=ax[mod_idx].get_ylim()[1], 
                               colors = 'r', linestyles = 'dashed')
            
            ax[mod_idx].legend(['critical_low = %s' %round(critical_low,3),
                                'critical_up = %s' %round(critical_up,3)],
                              loc = 'upper left')

            ax[mod_idx].set_title('Spearman r perm null, '+mod_name+', '+roi_name)   
            
        if save:    
            f.savefig(os.path.join(out_fig, 'r_with_model_hist_%s_perm_null.eps' %roi_name), format = 'eps')  
           
#%%
base_root = '/home/rj299/scratch60/mdm_analysis/'
data_root = '/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/1stLevel/'
data_behav_root = '/home/rj299/scratch60/mdm_analysis/data_behav'
out_root = '/home/rj299/scratch60/mdm_analysis/output/'
out_fig = os.path.join(out_root, 'imaging', 'Sink_resp_rsa_nosmooth', 'roi_compare_with_model')
anat_mean = nib.load(os.path.join(out_root, 'imaging', 'all_sub_average.nii.gz'))

stims = {'01': 'Med_amb_0', '02': 'Med_amb_1', '03': 'Med_amb_2', '04': 'Med_amb_3',
         '05': 'Med_risk_0', '06': 'Med_risk_1', '07': 'Med_risk_2', '08': 'Med_risk_3', 
         '09': 'Mon_amb_0', '10': 'Mon_amb_1', '11': 'Mon_amb_2', '12': 'Mon_amb_3',
         '13': 'Mon_risk_0', '14': 'Mon_risk_1', '15': 'Mon_risk_2', '16': 'Mon_risk_3'}

stim_num = len(stims)

subjects = [2073, 2550, 2582, 2583, 2584, 2585, 2588, 2592, 
            2593, 2594, 2596, 2597, 2598, 2599, 2600, 2624, 
            2650, 2651, 2652, 2653, 2654, 2655, 2656, 2657, 
            2658, 2659, 2660, 2661, 2662, 2663, 2664, 2665, 2666]

#%%
# all rois' names
sub = 2654
roi_rdm_obj = np.load('/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/rdm_new/_subject_id_%s/roi_rdm.npy' %sub,
              allow_pickle = True)
roi_rdm = roi_rdm_obj.item()
roi_names_all = list(roi_rdm.keys())

print('All names of ROIs:')
for roi_name in roi_names_all:
    print(roi_name)

    
#%% Model RDMs
def plot_model_rdm(mod_rdm, mod_name, out_fig, save = False):
    
    stim_cat = ['', 'Med_amb', '', 'Med_risk', '', 'Mon_amb', '', 'Mon_risk']
    edges = np.array([0,4,8,12,16])-0.5
#    
    f, ax = plt.subplots(1,1, figsize=(7, 5))
    im0 = ax.imshow(mod_rdm)
    ax.set_xticklabels([])
    ax.set_yticklabels(stim_cat)
    ax.set_title('%s model' %mod_name) 
    ax.set_ylabel('condition')
    ax.set_xlabel('condition')
    ax.vlines(edges,min(edges),max(edges))
    ax.hlines(edges,min(edges),max(edges))
    f.colorbar(im0, ax=ax, shrink = 0.8)
    
    f.savefig(os.path.join(out_fig, 'model_%s.eps' %mod_name), format = 'eps')
    
#%%    
def plot_sub_model_rdm(mod_rdm, mod_name, out_fig, save = False):
    
    '''
    Input
    mod_rdm: dictionary, each item is a subejct
    
    '''
    
    
    stim_cat = ['', 'Med_amb', '', 'Med_risk', '', 'Mon_amb', '', 'Mon_risk']
    edges = np.array([0,4,8,12,16])-0.5
    
    subs = list(mod_rdm.keys())
    
    f, ax = plt.subplots(len(subs),1, figsize=(7, len(subs)*5))
    
    for (sub_idx, sub) in enumerate(subs):
        im0 = ax[sub_idx].imshow(mod_rdm[sub])
        ax[sub_idx].set_xticklabels([])
        ax[sub_idx].set_yticklabels(stim_cat)
        ax[sub_idx].set_title('Sub_%s_%s model' %(sub, mod_name)) 
        ax[sub_idx].set_ylabel('condition')
        ax[sub_idx].set_xlabel('condition')
        ax[sub_idx].vlines(edges,min(edges),max(edges))
        ax[sub_idx].hlines(edges,min(edges),max(edges))
        f.colorbar(im0, ax=ax[sub_idx], shrink = 0.8)
    
    f.savefig(os.path.join(out_fig, 'model_%s.eps' %mod_name), format = 'eps')  
    
#%% Model RDM domain difference
mod_rdm_domain = np.ones([16,16])

med_id = list(range(8))
mon_id = list(range(8,16))

mon_mask = [(a,b) for a in mon_id for b in mon_id]
med_mask = [(a,b) for a in med_id for b in med_id]

for mon_mask_idx in mon_mask:  
    mod_rdm_domain[mon_mask_idx] = 0
for med_mask_idx in med_mask:  
    mod_rdm_domain[med_mask_idx] = 0

plot_model_rdm(mod_rdm_domain, 'domain', out_fig, True)


#%% Model RDM risk/ambig difference
mod_rdm_uncert = np.ones([16,16])

risk_id = [0,1,2,3,8,9,10,11]
amb_id = [4,5,6,7,12,13,14,15]

amb_mask = [(a,b) for a in risk_id for b in risk_id]
risk_mask = [(a,b) for a in amb_id for b in amb_id]

for risk_mask_idx in risk_mask:  
    mod_rdm_uncert[risk_mask_idx] = 0
for amb_mask_idx in amb_mask:  
    mod_rdm_uncert[amb_mask_idx] = 0

plot_model_rdm(mod_rdm_uncert, 'uncertainty', out_fig, True)


#%% Model RDM value (outcome magnitude) difference
mod_rdm_val = np.ones([16,16])

level = np.array([0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3])

for i in range(len(level)):
    for j in range(len(level)):
        mod_rdm_val[i, j] = abs(level[i] - level[j])/3
        
plot_model_rdm(mod_rdm_val, 'value', out_fig, True)


    
#%% Model RDM of value, taking individual specific subjective values

# read parameters to calculate SV, and post-scan ratings
par = pd.read_csv(os.path.join(data_behav_root, 'par_09300219.csv'))
rating = pd.read_csv(os.path.join(data_behav_root, 'rating_11082019.csv'))

# each subject's model rdm is an dictionary item
mod_rdm_sv = {}
mod_rdm_rating = {}

for sub in subjects:
    
    # read fitted values
    par_sub = par[par.id == sub]
    
    val1_med = par_sub[par_sub.is_med == 1].iloc[0]['val1']
    val2_med = par_sub[par_sub.is_med == 1].iloc[0]['val2']
    val3_med = par_sub[par_sub.is_med == 1].iloc[0]['val3']
    val4_med = par_sub[par_sub.is_med == 1].iloc[0]['val4']
        
    val1_mon = par_sub[par_sub.is_med == 0].iloc[0]['val1']
    val2_mon = par_sub[par_sub.is_med == 0].iloc[0]['val2']
    val3_mon = par_sub[par_sub.is_med == 0].iloc[0]['val3']
    val4_mon = par_sub[par_sub.is_med == 0].iloc[0]['val4']
    
    # read ratings
    rating_sub = rating[rating.id == sub]
    
    rating1_med = rating_sub[rating_sub.is_med == 1].iloc[0]['rating1']
    rating2_med = rating_sub[rating_sub.is_med == 1].iloc[0]['rating2']
    rating3_med = rating_sub[rating_sub.is_med == 1].iloc[0]['rating3']
    rating4_med = rating_sub[rating_sub.is_med == 1].iloc[0]['rating4']
        
    rating1_mon = rating_sub[rating_sub.is_med == 0].iloc[0]['rating1']
    rating2_mon = rating_sub[rating_sub.is_med == 0].iloc[0]['rating2']
    rating3_mon = rating_sub[rating_sub.is_med == 0].iloc[0]['rating3']
    rating4_mon = rating_sub[rating_sub.is_med == 0].iloc[0]['rating4']    
    
    # normalize (linear) values within domain
    val_med = np.array([val1_med, val2_med, val3_med, val4_med])
    val_mon = np.array([val1_mon, val2_mon, val3_mon, val4_mon])
    rating_med = np.array([rating1_med, rating2_med, rating3_med, rating4_med])
    rating_mon = np.array([rating1_mon, rating2_mon, rating3_mon, rating4_mon])
    
    val_med_norm = val_med/50 # because the range for fitting is 0-50, arbitrary
    val_mon_norm = val_mon/50
    rating_med_norm = rating_med/100 # because the range is 0-100
    rating_mon_norm = rating_mon/100
    
    
    # make vectors of value corresponding to stimulus
    val_vector = np.array([val_med_norm[0], val_med_norm[1], val_med_norm[2], val_med_norm[3],
                           val_med_norm[0], val_med_norm[1], val_med_norm[2], val_med_norm[3],
                           val_mon_norm[0], val_mon_norm[1], val_mon_norm[2], val_mon_norm[3],
                           val_mon_norm[0], val_mon_norm[1], val_mon_norm[2], val_mon_norm[3]])
    
    rating_vector = np.array([rating_med_norm[0], rating_med_norm[1], rating_med_norm[2], rating_med_norm[3],
                              rating_med_norm[0], rating_med_norm[1], rating_med_norm[2], rating_med_norm[3],
                              rating_mon_norm[0], rating_mon_norm[1], rating_mon_norm[2], rating_mon_norm[3],
                              rating_mon_norm[0], rating_mon_norm[1], rating_mon_norm[2], rating_mon_norm[3]])
    
    # calculate rdm
    mod_rdm_sv_sub = np.ones([16, 16])
    mod_rdm_rating_sub = np.ones([16, 16])
    
    for i in range(mod_rdm_sv_sub.shape[0]):
        for j in range(mod_rdm_sv_sub.shape[0]):
            
            mod_rdm_sv_sub[i, j] = np.absolute(val_vector[i] - val_vector[j])
            mod_rdm_rating_sub[i, j] = np.absolute(rating_vector[i] - rating_vector[j])
    
#    plot_model_rdm(mod_rdm_sv_sub, 'sv', out_fig, False)
#    plot_model_rdm(mod_rdm_rating_sub, 'rating', out_fig, False)
    
    mod_rdm_sv[sub] = mod_rdm_sv_sub
    mod_rdm_rating[sub] = mod_rdm_rating_sub

np.save(os.path.join(out_fig, 'model_sv.npy'), mod_rdm_sv)
np.save(os.path.join(out_fig, 'model_rating.npy'), mod_rdm_rating)

# plot all subjects
plot_sub_model_rdm(mod_rdm_sv, 'sv', out_fig, False)
plot_sub_model_rdm(mod_rdm_rating, 'rating', out_fig, False)

# vectorize
vector = [{}, {}]

for (mod_idx, mod_rdm) in enumerate([mod_rdm_sv, mod_rdm_rating]):
    
    mod_rdm_vector_mod = {}
    
    for sub in mod_rdm.keys():
        _, mod_rdm_vector_mod[sub] = half_matrix(mod_rdm[sub])
        
    vector[mod_idx] = mod_rdm_vector_mod            

mod_rdm_vector_individual = {}
mod_rdm_vector_individual['sv'] = vector[0]
mod_rdm_vector_individual['rating'] = vector[1]

#%% Make a dictionary of all models
# all models to compare
mod_rdm = {'domain': mod_rdm_domain, 'uncertainty': mod_rdm_uncert, 
          'value': mod_rdm_val}

# vectorize

# mod_rdm_vector = {mod_name: 
#                   mod_rdm[mod_name].reshape(mod_rdm[mod_name].shape[0]*mod_rdm[mod_name].shape[1],)
#                   for mod_name in list(mod_rdm.keys())} 

mod_rdm_vector = {}
for mod_name in mod_rdm.keys():
    _, mod_rdm_vector[mod_name] = half_matrix(mod_rdm[mod_name])

# add the models with indiviudal model RDMs    
mod_rdm_vector['sv'] = mod_rdm_vector_individual['sv']    
mod_rdm_vector['rating'] = mod_rdm_vector_individual['rating']

#%% plot ROI rdms correlation with model spearman rho distribution
#roi_names = ['vmpfc', 'vstr']
roi_names = roi_names_all

# plot correlation with model
spearman_r, spearman_p = compare_with_model(subjects, roi_names, mod_rdm_vector, out_fig)

plot_r_hist(spearman_r, out_fig, True)

#%%

# load saved 
#roi_name = 'zhang_sal_lcaudate'
#spearman_r_obj = np.load('/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/spearman_r_with_model_%s.npy' %roi_name,
#                                          allow_pickle = True)
#spearman_r_temp = spearman_r_obj.item()

#%%
# plot null distribution from permutation 
spearman_r_perm = permutation_test(subjects, roi_names, mod_rdm_vector, out_fig,
                                   iter_num = 2000, # default: 1000
#                                   perm_num = 50 # default: 100
                                  )

#%%
# load saved 


#spearman_r_perm = {}
#
#for roi_name in roi_names_all:
#    r_perm_obj = np.load('/home/rj299/scratch60/mdm_analysis/output/imaging/Sink_resp_rsa_nosmooth/perm_null_%s.npy' %roi_name,
#                                          allow_pickle = True)
#    r_perm = r_perm_obj.item()
#    spearman_r_perm[roi_name] = r_perm
    
plot_permutation_null(spearman_r_perm, out_fig, 0.05, True)
    
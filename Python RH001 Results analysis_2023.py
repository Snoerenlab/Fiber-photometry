# -*- coding: utf-8 -*-
"""
Created in 2022

Script to analyze the fiber photometry data with copulation test for RH001.
Based on Python 3.9, installed via anaconda.
NOTE -> Runs after the Python RH001 Data analysis script has run.

Steps to take:
    1) Make a folder that contains all recorded TDT data
    2) Make a folder for your experiment data, and save the TDT metafile and Noldus excel output of the raw data in it
    3) Save a copy of the python script in this folder as well (otherwise you loose your master script due to automatic saving when running)
    4) Fill in baseline correction times
    5) Check behaviors and behavioral parameters that were calculated
    6) Check whether your observer sheets have similar names (plus observation column)
    7) Fill in list with excluded animals, folder directories etc

Information on conditions built in:
    - Duration of behavior is from start behavior until M/I/E (thus excluded the time from M/IE to next behavior)
    - This is also implemented in the time-out durations


@author: Eelke Snoeren
"""

import tdt
import trompy as tp
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from itertools import chain
sns.set()
from PIL import Image
import glob
import os
from matplotlib.backends.backend_pdf import PdfPages
import multiprocessing as mp
from pandas import ExcelWriter
import openpyxl
from sklearn.metrics import auc
import scipy.stats as stats
pd.set_option('use_inf_as_na', True)
from pandas import option_context
from tdt import epoc_filter
from numpy import trapz
from numpy import NaN
import os.path
from os import path
from mpl_toolkits.axes_grid1 import make_axes_locatable
import math
from matplotlib import rcParams
import pickle
from itertools import zip_longest

# Fill in "exclude" or "include" on whether or not you want to take out (exclude) the behaviors before another relevant behavior happens or not (include)
status_excluding='exclude'
status_outliers=True
status_correction=True

# Set your baseline correction times before snips 
baseline_start=-20
baseline_end=-5

# Set your pre and post-sniptime
presnip=10
postsnip=10

# Set fontsize for figures
xaxis_fontsize=12
yaxis_fontsize=14
label_fontsize=16
subtitle_fontsize=16
title_fontsize=16

# Define the directory folders (use / instead of \)
directory= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA" # Of the metafile and behavioral data
directory_tdt="D:/RH001 POA/TDT_tanks_and_metafile/" # Of the TDT recordings
directory_output= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Output" # Of the output folder for your results
directory_results= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results tdt" # Of the output folder for your results
directory_results_cor= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results tdt cor" # Of the output folder for your results corrected for outliers
directory_results_beh= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results behavior" # Of the output folder for your results
directory_pickle = "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Pickle files"
directory_fullgraphs = "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA//Fullgraphs"


if not os.path.isdir(directory_output):
    os.mkdir(directory_output)

if not os.path.isdir(directory_fullgraphs):
    os.mkdir(directory_fullgraphs)

if not os.path.isdir(directory_results_cor):
    os.mkdir(directory_results_cor)

if not os.path.isdir(directory_results):
    os.mkdir(directory_results)

if not os.path.isdir(directory_results_beh):
    os.mkdir(directory_results_beh)

directory_results_perrat = "/Results per rat"
directory_results_total = "/Results total"
directory_results_parts = "/Results parts"
directory_AUC = "/AUC"
directory_AUC_parts = "/AUC parts"
directory_results_parameters = "/Results parameters"
directory_copgraphs = "/Copgraphs"
directory_heatmaps = "/Heatmaps"

    
# ################ ################ ################ ################  
# ################ OPEN PICKLE #####################
# ################ ################ ################ ################  

# Change directory to output folder
os.chdir(directory_pickle)

# to load
with open("my_dict_process.pickle", "rb") as file:
    my_dict_process= pickle.load(file)

with open("my_dict_behavior.pickle", "rb") as file:
    my_dict_behavior= pickle.load(file)

# Change directory back
os.chdir(directory)

print('dictionary loaded')

# Assign file names
file_TDT = 'Metafile TDT_RH001b_RH001c_python.xlsx' # Metafile
file_beh = 'RH001bc Raw data corrected_plus.xlsx' # Noldus raw data


# Define output file names
out_path1 = "%s/Output/RH001_results.xlsx" % directory # Final result filename & location
out_path2 = "%s/Output/RH001_test_load.xlsx" % directory # Filename & location file for load test
out_path3 = "%s/Output/RH001_test_dataprep.xlsx" % directory # Filename & location file for data prep test
out_path4 = "%s/Output/RH001_test_dataframe.xlsx" % directory # Filename & location file for dataframe results test

###########################################################################################################################
# # # Fill the list with rats that need to be excluded for analysis
# # Doubts stay in
# list_excl=['102','103','106','109','110','111','125']
# list_excltdt=[102,103,106,109,110,111,125]

# # Doubts go out as well
# list_excltdt=[102,103,104,105,106,109,110,111,112,113,116,125]
# list_excl=['102','103','104','105','106','109','110','111','112','113','116','125']

# Extra doubts go out as well
list_excltdt=[102,103,104,106,109,110,111,112,113,116, 119, 120, 123, 125]
list_excl=['102','103','104','106','109','110','111','112','113','116', '119', '120', '123','125']

# Fill in list with TestID that needs exclusion due to too many signal artifacts
list_signal_artifact_excl=['105COP1','115COP2','117COP2','118COP2','117COP3','118COP6']

############################################################################################################################

# Load in the Metafile sheet from the Metafile TDT
xlsx_TDT = pd.ExcelFile(file_TDT)
metafile = pd.read_excel(xlsx_TDT, "Metafile")

# Create a directory for the tank
metafile['directory_tank']= directory_tdt+metafile['tdtfolder']+'/'+metafile['tdtfile']

# Delete the excluded rats from the metafile
for i in list_excltdt:
    metafile=metafile[metafile.RatID != i]

# Create an identical rat-test-session code
metafile['ID']=metafile['RatID'].map(str)+metafile['Test']
metafile['ID']=metafile['ID']+metafile['Testsession'].map(str)
metafile['COPTEST']=metafile['Test']+metafile['Testsession'].map(str)

# Delete the rats-tests that have too many artifacts
for o in list_signal_artifact_excl:
    metafile=metafile[(metafile.ID != o)]

# Create a dictionary from the metafile
dict_metafile = metafile.to_dict()

# Create lists of the metafile
list_directory_tank=metafile['directory_tank'].tolist()
list_ratid=metafile['RatID'].tolist()
list_ID=metafile['ID'].tolist()
list_blue=metafile['blue'].tolist()
list_uv=metafile['uv'].tolist()
list_virus=metafile['Virus'].tolist()
list_test=metafile['Test'].tolist()
list_testsession=metafile['Testsession'].tolist()
list_coptest=metafile['COPTEST'].tolist()

# Make dictionary for virus and coptests
dict_virus = dict(zip(list_ratid,list_virus))
dict_id= dict(zip(list_ID,list_ratid))
dict_test=dict(zip(list_ID,list_test))
dict_testsession=dict(zip(list_ID,list_testsession))
dict_coptest=dict(zip(list_ID,list_coptest))

# Analysis of the behavioral part
# Load and clean up of the data file of the rawdata for DataFrames
xlsx_data = pd.ExcelFile(file_beh)
file_sheets_data = []
for sheet in xlsx_data.sheet_names:
    file_sheets_data.append(xlsx_data.parse(sheet))
dataraw = pd.concat(file_sheets_data)
dataraw = dataraw.dropna(axis=0, how='all')

# Fill out your short column names behind the definition a-z
A='Date_Time_Absolute_dmy_hmsf'
B='Date_dmy'
C='Time_Absolute_hms'
D='Time_Absolute_f'
E='Time_Relative_hmsf'
F='Time_Relative_hms'
G='Time_Relative_f'
H='Time_Relative_sf' # Time
I='Duration_sf'
J='Observation'
K='Event_Log'
L='Behavior'
M='Event_Type'
N='Comment'

# For the rest of the document we will use these new terms for the "important behaviors"
TIME='Time'
OBS='Observation'
BEH='Behavior'
EVENT='Event_Type'
RATID='RatID' # RatID number 
ID='ID' # RatID with experiment - unique identifyer
TREAT='Treatment'
VIRUS='Virus'
EXP='Experiment'

# Fill out your behavioral observations behind definition BA-BZ and BSA-BSZ
BA='Mount' # Defines the end of a mount, when detaching from female
BB='Intromission' # Defines the end of an intromission, after the end of the "jump"
BC='Ejaculation' # Defines the end of an ejaculation, the moment the female jumps away
BD='Attempt to mount'
BE='Anogenital sniffing'
BF='Chasing'
BG='Genital grooming'
BH='Sniffing bedding'
BI='Sniffing female'
BJ='Head away from female'
BK='Head to female'
BL='Other'
# BM='Selfgrooming'
BN='Intro female'
BO='Start fix'
BP='End fix'
BS='Start cop behavior' # Defined as the moment the male body attaches to the female body to start a copulation

# Fill in your extra behavioral calculations behind definition EA-EZ
EA='Copulations' # mounts, intromissions and ejaculations (BA,BB,BC)
EB='IR' # Intromission ratio - the number of intromissions divided by the sum of the number of intromissions and the number of mounts (BB/BA+BB)
EC='III' # Inter-intromission interval - the total test time divided by the number of intromissions, or the ejaculation latency divided by the number of intromissions
ED='CR' # Copulatory rate - the sum of the number of mounts and the number of intromissions divided by the time from first behavior to ejaculation
EE='PEI' # post-ejaculatory interval - Time from ejaculation to first mount/intromission
EF='IMBI' # Inter-mount-bout interval - Time from first mount of mountbout to first mount of next mountbout
EG='TO' # Time-out - Interval from the last mount of mountbout to the first mount of next mountbout
EH='Copulation_oriented behavior' # EA+BD+BE+BF+BG
EI='Female_oriented behavior' # EA+BI+BK
EJ='Non copulation_oriented behavior' # BJ+BH+BL+BM

Timetest = 1800

# Make a list of the standard behaviors and the to be calculated behaviors
list_sex=list((BA,BB,BC))
list_behaviors=list((BA,BB,BC,BD,BE,BF,BG,BH,BI,BJ,BK))
list_startcop=list(('Start Mount','Start Intromission','Start Ejaculation'))
list_other_behaviors=list((BD,BE,BF,BG,BH,BI,BJ,BK))
list_behaviors_extra=list((EA,EB,EC,ED,EE,EF,EG,EH,EI,EJ))
list_beh_tdt=list((BA,BB,BC,BD,BE,BF,BG,BH,BI,BJ,BK,BN))
list_sex_MB=list((BA,BB,BC,'Single Mount','Single Intromission','Single Ejaculation','Start MB Mount',
                  'Start MB Intromission','End MB Mount','End MB Intromission','End MB Ejaculation',
                  'MB Mount','MB Intromission'))
# Create list with the interesting copulation behaviors, including the mount bout elements
list_MB_behavior=['Single Mount','Single Intromission','Single Ejaculation','Start MB Mount',
                  'Start MB Intromission','End MB Mount','End MB Intromission','End MB Ejaculation',
                  'MB Mount','MB Intromission']

list_nosex=list((BD,BE,BF,BG,BH,BI))

list_relevant_behaviors=[BA,BB,BC,BD]

# Rename columns (add or remove letters according to number of columns)
dataraw.columns = [A,B,C,D,E,F,G,H,I,J,K,L,M,N]
dataraw.columns=[A,B,C,D,E,F,G,TIME,I,OBS,K,BEH,EVENT,N]

# Make a new datafile with selected columns
data_full=dataraw[[TIME,OBS,BEH,EVENT]]

# Make a column for the experiment and RatID
data_full=data_full.assign(Experiment =lambda x: data_full.Observation.str.split('_').str[0])
data_full=data_full.assign(RatID =lambda x: data_full.Observation.str.split('_').str[-1])

# Make a column for the diet and virus
data_full[VIRUS]=pd.to_numeric(data_full[RATID])
data_full[VIRUS]=data_full[VIRUS].map(dict_virus)

data_full[ID]=data_full[RATID]+data_full[EXP]

# Delete the rows that "end" a behavior
# Drop a row by condition
data_full=data_full[data_full.Event_Type != 'State stop']

# Delete the rows that are empty in behavior
data_full=data_full[data_full.Behavior != '']

# Delete the rows with the excluded animals
for i in list_excl:
    data_full=data_full[data_full.RatID != i]

# Clean up the file by selecting relevant columns and reorganize
data_full=data_full[[OBS,EXP,ID,RATID,VIRUS,TIME,BEH]]

data_full = data_full.sort_values(by=[OBS,TIME], ascending = True)

# Create a column with the start and times for behaviors
data_full['Time_cop'] = data_full.groupby(RATID)[TIME].shift()
data_full['Time_next'] = data_full.groupby(RATID)[TIME].shift(-1)
data_full['Beh_next'] = data_full.groupby(RATID)[BEH].shift(-1)
data_full['Beh_start'] = np.where((data_full[BEH]==BA)|(data_full[BEH]==BB)|(data_full[BEH]==BC), data_full['Time_cop'], data_full[TIME])
data_full['Beh_end'] = np.where((data_full[BEH]==BA)|(data_full[BEH]==BB)|(data_full[BEH]==BC), data_full[TIME],data_full['Time_next'])

# Sort the dataset for further analysis
data_full = data_full.sort_values(by=[OBS,TIME], ascending = True)
data_full = data_full.reset_index(drop=True)

# Clean up the data and replace "Start copulation" for "Start Mount, Start Intromission, or Start Ejaculation"
# Get a dataframe that only contains the copulation
df_cop=data_full.loc[(data_full[BEH]==BA)|(data_full[BEH]==BB)|(data_full[BEH]==BC)|(data_full[BEH]==BS)]
df_cop['Next_behavior']=df_cop.groupby(RATID)[BEH].shift(-1)

# Make column with Start copulation
df_cop['Start Copulation']=np.where(((df_cop[BEH]==BS) & (df_cop['Next_behavior']== BA)),'Start Mount','')
df_cop['Start Copulation']=np.where(((df_cop[BEH]==BS) & (df_cop['Next_behavior']== BB)),'Start Intromission',df_cop['Start Copulation'])
df_cop['Start Copulation']=np.where(((df_cop[BEH]==BS) & (df_cop['Next_behavior']== BC)),'Start Ejaculation',df_cop['Start Copulation'])

# Place the index numbers in lists
list_idx_mount=df_cop.index[(df_cop['Start Copulation']=='Start Mount')].tolist()
list_idx_intromission=df_cop.index[(df_cop['Start Copulation']=='Start Intromission')].tolist()
list_idx_ejaculation=df_cop.index[(df_cop['Start Copulation']=='Start Ejaculation')].tolist()

# Replace the "Start Copulation" for the actual behavior it was
for i in list_idx_mount:
    data_full.at[i,'Behavior']='Start Mount'
for j in list_idx_intromission:
    data_full.at[j,'Behavior']='Start Intromission'
for k in list_idx_ejaculation:
    data_full.at[k,'Behavior']='Start Ejaculation'

# Mark beginning per rat
data_full = data_full.sort_values(by=[OBS,TIME])
data_full['obs_num'] = data_full.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
data_full = data_full.sort_values(by=[OBS,TIME], ascending = False)
data_full['obs_num_back'] = data_full.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
data_full = data_full.sort_values(by=[OBS,TIME])

# Mark introduction female
data_full['fem_mark']=np.where((data_full[BEH]==BN),data_full[TIME], np.NaN)
data_full['fem_mark']=data_full.groupby(['ID'], sort=False)['fem_mark'].fillna(method="ffill")

# Correct Beh_end for the last behaviors
data_full['Beh_end']=np.where(data_full['obs_num_back']==1,(data_full['fem_mark']+1800),data_full['Beh_end'])

# Calculate the duration of the behaviors
data_full['durations'] = data_full['Beh_end']-data_full['Beh_start']

# Make a new column that makes an unique name for the behaviors per rat
data_full['beh_num_trick'] = data_full[BEH].map(str) + data_full[ID]

# Number the behaviors per behavior per rat
data_full['beh_num'] = data_full.groupby('beh_num_trick')[BEH].transform(lambda x: np.arange(1, len(x) + 1))

# Number the behaviors backwards
data_full = data_full.sort_values(by=[OBS,TIME], ascending = False)
data_full['beh_num_back'] = data_full.groupby('beh_num_trick')[BEH].transform(lambda x: np.arange(1, len(x) + 1))
data_full = data_full.sort_values(by=[OBS,TIME])
data_full = data_full.reset_index(drop=True)

# Mark the ejaculatory series with identifying numbers (up to 3 series)
data_full['Series_mark']=np.where((data_full[BEH]==BN),999,np.NaN)
data_full['Series_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==1)),111,data_full['Series_mark'])
data_full['Series_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==2)),222,data_full['Series_mark'])
data_full['Series_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==3)),333,data_full['Series_mark'])
data_full['Series_mark']=data_full.groupby(['ID'], sort=False)['Series_mark'].fillna(method="backfill")
data_full['Series_mark']=data_full.groupby(['ID'], sort=False)['Series_mark'].fillna(444)
data_full['Series_mark']=np.where((data_full[BEH]==BN),111,data_full['Series_mark'])

# Create a dictionary that matches the identifying numbers to the phases
dict_series={999:'BASELINE',111:'ejac_serie1',222:'ejac_serie2',333:'ejac_serie3',444:'ejac_serie_rest'}

# Code the phases with words
data_full['Series_mark']=data_full['Series_mark'].map(dict_series)

# # Mark the ejaculatory PEI with identifying numbers (up to 3 PEI) until 1st intromission
data_full['Series_mark_PEII']=np.where((data_full[BEH]==BN),999,np.NaN)
data_full['Series_mark_PEII']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==1)),111,data_full['Series_mark_PEII'])
data_full['Series_mark_PEII']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==2)),222,data_full['Series_mark_PEII'])
data_full['Series_mark_PEII']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==3)),333,data_full['Series_mark_PEII'])
data_full['Series_mark_PEII']=data_full.groupby(['ID'], sort=False)['Series_mark_PEII'].fillna(method="backfill")
data_full['Series_mark_PEII']=data_full.groupby(['ID'], sort=False)['Series_mark_PEII'].fillna(444)
data_full['Series_mark_PEII']=np.where((data_full[BEH]==BN),111,data_full['Series_mark_PEII'])

# Create a dictionary that matches the identifying numbers to the phases
dict_series_PEII={999:'BASELINE',111:'ejac_serie1',222:'ejac_serie2',333:'ejac_serie3',444:'ejac_serie_rest'}

# Code the phases with words
data_full['Series_mark_PEII']=data_full['Series_mark_PEII'].map(dict_series_PEII)

# Mark the ejaculatory PEI with identifying numbers (up to 3 PEI)
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==1)),111,np.nan)
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==2)),222,data_full['PEII_mark'])
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==3)),333,data_full['PEII_mark'])
data_full['PEII_mark']=data_full.groupby(['ID'], sort=False)['PEII_mark'].fillna(method="ffill")

# Create a dictionary that matches the identifying numbers to the phases
dict_PEI={111:'PEI1',222:'PEI2',333:'PEI3'}

# Code the phases with words
data_full['PEII_mark']=data_full['PEII_mark'].map(dict_PEI)

# Fix the 1st series if no ejaculation
data_full['Series_noejac_PEII']=data_full['Series_mark_PEII'].shift(-1)
data_full['Series_marknoejac_PEII']=np.where(((data_full['Series_mark_PEII']=='ejac_serie1') & (data_full['Series_noejac_PEII']=='ejac_serie_rest')),777,np.nan)
# data_full['Series_marknoejac']=np.where((data_full['beh_num_back']==1),999,data_full['Series_marknoejac'])
data_full['Series_marknoejac_PEII']=data_full.groupby(['ID'], sort=False)['Series_marknoejac_PEII'].fillna(method="ffill")
data_full['Series_mark_PEII']=np.where(((data_full['Series_mark_PEII']=='ejac_serie_rest') & (data_full['Series_marknoejac_PEII']==777)),'ejac_serie1',data_full['Series_mark_PEII'])

# Fix the the 2nd series if no 2nd ejaculation is reached -> then still call it 2nd series
data_full['Series_mark_PEII']=np.where(((data_full['Series_mark_PEII']=='ejac_serie_rest') & (data_full['PEII_mark']=='PEI1')),'ejac_serie2',data_full['Series_mark_PEII'])

# Get the 1st mount or intromission in PEI phase.
# Number the behaviors per behavior per rat
data_full['beh_num_trick_PEII'] = data_full['beh_num_trick']  + data_full['PEII_mark']
data_full['beh_num_trick_PEII'] = np.where((data_full[BEH]==BB),(data_full[ID]+data_full['Series_mark_PEII']+"COP"),data_full['beh_num_trick_PEII'])
data_full['beh_num_trick_PEII']=data_full.groupby(['ID'], sort=False)['beh_num_trick_PEII'].fillna('nothing')

data_full['beh_num_PEII'] = data_full.groupby('beh_num_trick_PEII')[BEH].transform(lambda x: np.arange(1, len(x) + 1))

data_full['PEII_mark_fix']=np.where(((data_full[BEH]==BB)&(data_full['beh_num_PEII']==1)),111,np.nan)
data_full['PEII_mark_fix']=np.where((data_full[BEH]==BC),222,data_full['PEII_mark_fix'])
data_full['PEII_mark_fix']=data_full.groupby(['ID'], sort=False)['PEII_mark_fix'].fillna(method="backfill")

data_full['PEII_mark']=np.where(((data_full['PEII_mark_fix']==111)&(data_full['Series_mark_PEII']=='ejac_serie2')&(data_full['PEII_mark']!=np.NaN)),'PEI1',"")
data_full['PEII_mark']=np.where(((data_full['PEII_mark_fix']==111)&(data_full['Series_mark_PEII']=='ejac_serie3')&(data_full['PEII_mark']!=np.NaN)),'PEI2',data_full['PEII_mark'])
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==1)),'PEI1',data_full['PEII_mark'])
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==2)),'PEI2',data_full['PEII_mark'])
data_full['PEII_mark']=np.where(((data_full[BEH]==BC)&(data_full['beh_num']==3)),'PEI3',data_full['PEII_mark'])

data_full['Series_mark_PEII']=np.where(((data_full['PEII_mark']==BS)&(data_full['beh_num']==1)),888,data_full['Series_mark_PEII'])

# # Make new dataframes for each phase
data_T = data_full.copy()
data_B = data_full[data_full['Series_mark'].isin(['BASELINE'])]
data_S1 = data_full[data_full['Series_mark'].isin(['ejac_serie1'])]
data_S2 = data_full[data_full['Series_mark'].isin(['ejac_serie2'])]
data_S3 = data_full[data_full['Series_mark'].isin(['ejac_serie3'])]
data_S1_PEII = data_full[data_full['PEII_mark'].isin(['PEI1'])]
data_S2_PEII = data_full[data_full['PEII_mark'].isin(['PEI2'])]
data_S3_PEII = data_full[data_full['PEII_mark'].isin(['PEI3'])]

# Print the rat numbers that did not have a "intro female" mark
for row in data_S1.itertuples():
    if row.obs_num == 1:
        if row.Behavior != BN:
            print(row.ID)

print("dataprep finished")    

# Create list and dictionaries with series
list_series = ['T','B','S1','S2','S3']
df_data={'T':data_T,'B':data_B,'S1':data_S1,'S2':data_S2,'S3':data_S3,'S1_PEII':data_S1_PEII,'S2_PEII':data_S2_PEII,'S3_PEII':data_S3_PEII}

df_data_tdt={'S1':data_S1,'S2':data_S2,'T':data_T}

def dataprep (data):
    """
    Parameters
    ----------
    data : DataFrame
        Add the dataframe for analysis
        e.g. data_T, data_B, data_S1, data_S2, data_S3, data_S1_PEII, data_S2_PEII, data_S3_PEII

    Returns
    -------
    data : DataFrame
        Returns a new dataframe with all columns needed later to retrieve the results
    """

    # Mark beginning per rat
    data = data.sort_values(by=[OBS,TIME])
    data['obs_num'] = data.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
    
    # Make a new column that makes an unique name for the behaviors per rat
    data['beh_num_trick'] = data[BEH].map(str) + data[ID]
    
    # Number the behaviors per behavior per rat
    data['beh_num'] = data.groupby('beh_num_trick')[BEH].transform(lambda x: np.arange(1, len(x) + 1))
    
    # Create a new dataframe with only the MB related behaviors
    df_MB=data.loc[(data[BEH]==BA)|(data[BEH]==BB)|(data[BEH]==BC)|(data[BEH]==BJ)|(data[BEH]==BL)]
    df_MB['obs_num'] = df_MB.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
    df_MB = df_MB.sort_values(by=[OBS,TIME], ascending = False)
    df_MB['obs_num_back'] = df_MB.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
    df_MB = df_MB.sort_values(by=[OBS,TIME])

    df_MB[BEH]=np.where((df_MB[BEH]==BL),BJ,df_MB[BEH])
    df_MB['MB_behavior']=np.where((df_MB['obs_num']==1),"fix",df_MB[BEH])
    df_MB['Next_behavior']=df_MB.groupby(RATID)['MB_behavior'].shift(-1)
    df_MB['Previous_behavior']=df_MB.groupby(RATID)[BEH].shift(1)
    df_MB['Previous_behavior']=np.where((df_MB['obs_num']==1),"fix",df_MB['Previous_behavior'])
    ################# IS RATID THE RIGHT ONE???#################
    #############################################################
    
    # Make a column with MB mark for start MB copulation, MB copulation, end MB, and single copulations
    df_MB['MB_mark']=np.where(((df_MB[BEH]==BA)|(df_MB[BEH]==BB)|(df_MB[BEH]==BC)),"MB","")
    df_MB['MB_mark']=np.where(((df_MB['MB_mark']=="MB")&(df_MB['Next_behavior']==BJ)&((df_MB['Previous_behavior']==BJ)|(df_MB['Previous_behavior']=='fix'))),"Single copulation",df_MB['MB_mark'])
    df_MB['MB_mark']=np.where(((df_MB['MB_mark']=="MB")&(df_MB['Next_behavior']!=BJ)&(df_MB['Previous_behavior']==BJ)),"Start MB",df_MB['MB_mark'])
    df_MB['MB_mark']=np.where(((df_MB['MB_mark']=="MB")&((df_MB['Next_behavior']==BJ)|(df_MB['Next_behavior']=='fix'))&(df_MB['Previous_behavior']!=BJ)),"End MB",df_MB['MB_mark'])
    df_MB['MB_mark']=np.where(((df_MB[BEH]==BA)|(df_MB[BEH]==BB)|(df_MB[BEH]==BC))&((df_MB['Next_behavior']=='fix')&(df_MB['Previous_behavior']==BJ)),"Single copulation",df_MB['MB_mark'])
    df_MB['MB_mark']=np.where(((df_MB[BEH]==BA)|(df_MB[BEH]==BB)|(df_MB[BEH]==BC))&((df_MB['Next_behavior']!=BJ)&(df_MB['Previous_behavior']=='fix')),"Start MB",df_MB['MB_mark'])
    
    # Fix MB_mark for ejaculations
    df_MB['MB_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='MB')),"End MB",df_MB['MB_mark'])
    df_MB['MB_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='Start MB')),"Single copulation",df_MB['MB_mark'])
   
    # Make a column to mark type of copulation in MB
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BA)&(df_MB['MB_mark']=='Single copulation')),'Single Mount','')
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BA)&(df_MB['MB_mark']=='Start MB')),'Start MB Mount',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BA)&(df_MB['MB_mark']=='End MB')),'End MB Mount',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BA)&(df_MB['MB_mark']=='MB')),'MB Mount',df_MB['MB_COP_mark'])
    
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BB)&(df_MB['MB_mark']=='Single copulation')),'Single Intromission',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BB)&(df_MB['MB_mark']=='Start MB')),'Start MB Intromission',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BB)&(df_MB['MB_mark']=='End MB')),'End MB Intromission',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BB)&(df_MB['MB_mark']=='MB')),'MB Intromission',df_MB['MB_COP_mark'])
    
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='Single copulation')),'Single Ejaculation',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='Start MB')),'Start MB Ejaculation',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='End MB')),'End MB Ejaculation',df_MB['MB_COP_mark'])
    df_MB['MB_COP_mark']=np.where(((df_MB[BEH]==BC)&(df_MB['MB_mark']=='MB')),'MB Ejaculation',df_MB['MB_COP_mark'])
    
    # Write the markers back in the real dataframe
    # Place the index numbers in lists
    list_idx_singlecopulation=df_MB.index[(df_MB['MB_mark']=='Single copulation')].tolist()
    list_idx_startMB=df_MB.index[(df_MB['MB_mark']=='Start MB')].tolist()
    list_idx_endMB=df_MB.index[(df_MB['MB_mark']=='End MB')].tolist()
    
    list_idx_singlemount=df_MB.index[(df_MB['MB_COP_mark']=='Single Mount')].tolist()
    list_idx_singleintro=df_MB.index[(df_MB['MB_COP_mark']=='Single Intromission')].tolist()
    list_idx_singleejac=df_MB.index[(df_MB['MB_COP_mark']=='Single Ejaculation')].tolist()
    
    list_idx_startMBmount=df_MB.index[(df_MB['MB_COP_mark']=='Start MB Mount')].tolist()
    list_idx_startMBintro=df_MB.index[(df_MB['MB_COP_mark']=='Start MB Intromission')].tolist()
    list_idx_startMBejac=df_MB.index[(df_MB['MB_COP_mark']=='Start MB Ejaculation')].tolist()
    
    list_idx_endMBmount=df_MB.index[(df_MB['MB_COP_mark']=='End MB Mount')].tolist()
    list_idx_endMBintro=df_MB.index[(df_MB['MB_COP_mark']=='End MB Intromission')].tolist()
    list_idx_endMBejac=df_MB.index[(df_MB['MB_COP_mark']=='End MB Ejaculation')].tolist()
    
    list_idx_MBmount=df_MB.index[(df_MB['MB_COP_mark']=='MB Mount')].tolist()
    list_idx_MBintro=df_MB.index[(df_MB['MB_COP_mark']=='MB Intromission')].tolist()
    list_idx_MBejac=df_MB.index[(df_MB['MB_COP_mark']=='MB Ejaculation')].tolist()
    
    # Replace the "Start Copulation" for the actual behavior it was
    for i in list_idx_singlecopulation:
        data.at[i,'MB_mark']='Single copulation'
    for j in list_idx_startMB:
        data.at[j,'MB_mark']='Start MB'
    for k in list_idx_endMB:
        data.at[k,'MB_mark']='End MB'

    for i in list_idx_singlemount:
        data.at[i,'MB_cop_mark']='Single Mount'
    for j in list_idx_singleintro:
        data.at[j,'MB_cop_mark']='Single Intromission'
    for k in list_idx_singleejac:
        data.at[k,'MB_cop_mark']='Single Ejaculation'
     
    for i in list_idx_startMBmount:
        data.at[i,'MB_cop_mark']='Start MB Mount'
    for j in list_idx_startMBintro:
        data.at[j,'MB_cop_mark']='Start MB Intromission'
    for k in list_idx_startMBejac:
        data.at[k,'MB_cop_mark']='Start MB Ejaculation'
    
    for i in list_idx_endMBmount:
        data.at[i,'MB_cop_mark']='End MB Mount'
    for j in list_idx_endMBintro:
        data.at[j,'MB_cop_mark']='End MB Intromission'
    for k in list_idx_endMBejac:
        data.at[k,'MB_cop_mark']='End MB Ejaculation'
    
    for i in list_idx_MBmount:
        data.at[i,'MB_cop_mark']='MB Mount'
    for j in list_idx_MBintro:
        data.at[j,'MB_cop_mark']='MB Intromission'
    for k in list_idx_MBejac:
        data.at[k,'MB_cop_mark']='MB Ejaculation'
    
    # Mark the time of the start and end of each mount bout
    data['Time_start_mount_bout']=np.where(((data['MB_mark']=='Start MB')|(data['MB_mark']=='Single copulation')),data['Beh_start'],np.NaN)
    data['Time_start_mount_bout']=data.groupby(['ID'], sort=False)['Time_start_mount_bout'].fillna(method="backfill")
    data['Time_end_mount_bout']=np.where(((data['MB_mark']=='End MB')|(data['MB_mark']=='Single copulation')),data['Beh_end'],np.NaN)
    data['Time_end_mount_bout']=data.groupby(['ID'], sort=False)['Time_end_mount_bout'].fillna(method="backfill")
       
    # Get the duration of the mount bout, marked next to the start of the mount bout
    data['Duration_mount_bout']=np.where((data['MB_mark']=="Start MB"),((data['Time_end_mount_bout'])-(data['Time_start_mount_bout'])),np.NaN)
    data['Duration_mount_bout']=np.where((data['MB_mark']=="Single copulation"),data['durations'],data['Duration_mount_bout'])
    
    # Get column with the start of next mount bout
    data['Start_next_MB']=data.groupby(['ID'], sort=False)['Time_start_mount_bout'].shift(-1)
    
    # Get the duration of the time out
    data['Duration_time_out']=np.where(((data['MB_mark']=="End MB")|(data['MB_mark']=="Single copulation")),
                                              (data['Start_next_MB']-(data['Time_end_mount_bout'])),np.NaN)
    
    # Count the mount bouts
    data['Mount_bout_count']=np.where(((data['MB_mark']=="Start MB")|(data['MB_mark']=="Single copulation")),1,np.NaN)
    data['OBS_MB_count'] = data['Mount_bout_count'].map(str) + data['ID'] 
    data['Mount_bout_num'] = data.groupby('OBS_MB_count')['Mount_bout_count'].transform(lambda x: np.arange(1, len(x) + 1))
    
    # Calculate the interval between the start of mount bouts
    data['Interval_MB']=np.where((data['Duration_mount_bout']>0),(data['Start_next_MB']-data['Time_start_mount_bout']),np.NaN)
    
    return data

data_T=dataprep(data_T)    
data_S1=dataprep(data_S1)
data_S2=dataprep(data_S2)
data_S3=dataprep(data_S3)
data_S1_PEII=dataprep(data_S1_PEII)
data_S2_PEII=dataprep(data_S2_PEII)
data_S3_PEII=dataprep(data_S3_PEII)

print("data ready for analysis")

# Create list with unique IDs that are in dataset
list_id=list(data_full[ID].unique())

###############################################################################################################
######################### ANALYSIS OF BEHAVIOR FOR TDT ########################################################
###############################################################################################################

# Create lists of coptest and statistics that needs to be calculated
list_cop=['COP1','COP2','COP3','COP4','COP5','COP6','COP7']
list_stat=['Mean','Median','Std','SEM','Q25','Q75','semedian','var']

# Create definitions to calculate group averages and statistical outcomes
def groupdict(dictionary):
    """
    Parameters
    ----------
    dictionary : string
        Add the dictionary of behavioral data results
        e.g. "dict_results_T", "dict_results_S1", "dict_results_S2"

    Returns
    -------
    dict_groups : dictionary
        Returns a new dictionary with the outcomes per coptest (for all rats) in a list
    """
    
    dict_beh=my_dict_behavior[dictionary]
    
    # Create an empty dictionary with ID and behaviors
    dict_groups={}

    for key,parameters in dict_beh.items():
        for parameter,value in parameters.items():
            dict_groups[parameter]={}
            for t in list_cop:
                dict_groups[parameter][t]=[]

    for key,parameters in dict_beh.items():
        for parameter,value in parameters.items():
            for t in list_cop:
                if t in key:
                    dict_groups[parameter][t].append(value)

    return dict_groups

def statsdict(dictionary_groups):
    """
    Parameters
    ----------
    dictionary : dictionary
        Add the dictionary with behavioral data results per coptest
        e.g. dict_group_T, dict_group_S1, dict_group_S2

    Returns
    -------
    dict_groups : dictionary
        Returns a new dictionary with the statistical data derived from the group_dictionary
    """
 
    # Create an empty dictionary with ID and behaviors
    dict_stats={}
    for parameter,cops in dictionary_groups.items():
        dict_stats[parameter]={}
        for cop,value in cops.items():
            dict_stats[parameter][cop]={}
            for cop in list_cop:
                dict_stats[parameter][cop]={}
                for i in list_stat:
                    dict_stats[parameter][cop][i]=[]

    # Fill dictionary with statistical measures
    for parameter,cops in dictionary_groups.items():
        for cop,values in cops.items():
            dict_stats[parameter][cop]['Mean']=np.nanmean(values)
            dict_stats[parameter][cop]['Median']=np.nanmedian(values)
            dict_stats[parameter][cop]['Std']=np.nanstd(values)
            dict_stats[parameter][cop]['SEM']=np.nanstd(values)/np.sqrt(np.size(values))
            dict_stats[parameter][cop]['Q25']=np.nanquantile(values,0.25)
            dict_stats[parameter][cop]['Q75']=np.nanquantile(values,0.75)
            dict_stats[parameter][cop]['semedian']=(dict_stats[parameter][cop]['Q75']-dict_stats[parameter][cop]['Q25'])/len(values)*1.34
            dict_stats[parameter][cop]['var']=np.nanvar(values)
            dict_stats[parameter][cop]['len']=len(values)
            dict_stats[parameter][cop]['max']=dict_stats[parameter][cop]['Mean']+dict_stats[parameter][cop]['Std']
            dict_stats[parameter][cop]['min']=dict_stats[parameter][cop]['Mean']-dict_stats[parameter][cop]['Std']

    return dict_stats

# Create groupdictionaries
dict_group_T=groupdict("dict_results_T")
dict_group_S1=groupdict("dict_results_S1")
dict_group_S2=groupdict("dict_results_S2")
dict_group_S3=groupdict("dict_results_S3")

# Calculate statistics
dict_stat_T=statsdict(dict_group_T)
dict_stat_S1=statsdict(dict_group_S1)
dict_stat_S2=statsdict(dict_group_S2)
dict_stat_S3=statsdict(dict_group_S3)

# Make new lists for slow versus fast ejaculators per series
list_slowejac=[]
list_normalejac=[]
list_fastejac=[]
for ids, parameters in my_dict_behavior["dict_results_T"].items():
    for parameter,value in parameters.items():
        if parameter =='TN_Ejaculation':
            if value >= 4:
                list_fastejac.append(ids)
            if value <= 1:
                list_slowejac.append(ids)
            if value == 2 or value == 3:
                list_normalejac.append(ids)
                
# Make a new dictionary with id lists for other parameters on which mean +- stdev was taken as cut-off points
list_performers=['Low','Middle','High']

def parameter_dict(dictionary,dictionary_stat):
    """
    Parameters
    ----------
    dictionary : string
        Add the dictionary of behavioral data results
        e.g. "dict_results_T", "dict_results_S1", "dict_results_S2"
    dictionary_stat : dictionary
        Add the dictionary of statistical data results
        e.g. dict_stat_T, dict_stat_S1, dict_stat_S2

    Returns
    -------
    dict_parameters : dictionary
        Creates a new dictionary with lists of testid for the parameters of extremes 
        (low, middle and high performers with mean +- stdev as cut-off points)

    """
    dict_beh=my_dict_behavior[dictionary]

    dict_parameters={}

    for key,parameters in dict_beh.items():
        for parameter,value in parameters.items():
            dict_parameters[parameter]={}
            for cop in list_cop:
                dict_parameters[parameter][cop]={}
                for performer in list_performers:
                    dict_parameters[parameter][cop][performer]=[]

    for key,parameters in dict_beh.items():
        for parameter,value in parameters.items():
            for cop in list_cop:
                if cop in key:
                    if value > dictionary_stat[parameter][cop]['max']:
                        dict_parameters[parameter][cop]['High'].append(key)
                    if value < dictionary_stat[parameter][cop]['min']:
                        dict_parameters[parameter][cop]['Low'].append(key)
                    if (value >= dictionary_stat[parameter][cop]['min']) and (value <= dictionary_stat[parameter][cop]['max']):
                        dict_parameters[parameter][cop]['Middle'].append(key)

    return dict_parameters

# Create dictionaries of the slow, middle and high performing animals per coptest and parameter.
dict_parameters_T=parameter_dict("dict_results_T",dict_stat_T)     
dict_parameters_S1=parameter_dict("dict_results_S1",dict_stat_S1)     
dict_parameters_S2=parameter_dict("dict_results_S2",dict_stat_S2)     
dict_parameters_S3=parameter_dict("dict_results_S3",dict_stat_S3)     

# Make new lists for mount and intromissions in first, middle and last part of ejaculatory series
# Both for series divided in three or five parts
for keys,dicts in my_dict_behavior["dict_results_tdt"].items():
    if keys != 'T':
        for key,behavior in dicts.items():
            if dicts[key]['Time_Mount']<dicts[key]['Time_Intromission']:
                time1=dicts[key]['Time_Mount']
            else:
                time1=dicts[key]['Time_Intromission']
            dicts[key]['treshold3']=(dicts[key]['Time_Ejaculation']-time1)/3
            dicts[key]['treshold3 end 1st part']=dicts[key]['Time_Ejaculation']-(2*dicts[key]['treshold3'])
            dicts[key]['treshold3 end 2nd part']=dicts[key]['Time_Ejaculation']-(dicts[key]['treshold3'])

            dicts[key]['treshold5']=(dicts[key]['Time_Ejaculation']-time1)/5
            dicts[key]['treshold5 end 1st part']=dicts[key]['Time_Ejaculation']-(4*dicts[key]['treshold5'])
            dicts[key]['treshold5 end 2nd part']=dicts[key]['Time_Ejaculation']-(3*dicts[key]['treshold5'])
            dicts[key]['treshold5 end 3rd part']=dicts[key]['Time_Ejaculation']-(2*dicts[key]['treshold5'])
            dicts[key]['treshold5 end 4th part']=dicts[key]['Time_Ejaculation']-(dicts[key]['treshold5'])

###############################AANGEPAST CHECK############################
# Make new lists for Mount and Intromissions in first, middle and last number of behaviors per series
for keys,dicts in my_dict_behavior["dict_results_tdt"].items():
    if keys != 'T':
        for key,behavior in dicts.items():
            for beh in list_behaviors:
                dicts[key]['treshold3_%s'%beh]=dicts[key]['TN_%s'%beh]/3
                dicts[key]['treshold3 end 1st part_%s'%beh]=math.floor(2*dicts[key]['treshold3_%s'%beh])
                dicts[key]['treshold3 end 2nd part_%s'%beh]=math.floor(dicts[key]['treshold3_%s'%beh])

                dicts[key]['treshold5_%s'%beh]=dicts[key]['TN_%s'%beh]/5
                dicts[key]['treshold5 end 1st part_%s'%beh]=math.floor(4*dicts[key]['treshold5_%s'%beh])
                dicts[key]['treshold5 end 2nd part_%s'%beh]=math.floor(3*dicts[key]['treshold5_%s'%beh])
                dicts[key]['treshold5 end 3rd part_%s'%beh]=math.floor(2*dicts[key]['treshold5_%s'%beh])
                dicts[key]['treshold5 end 4th part_%s'%beh]=math.floor(dicts[key]['treshold5_%s'%beh])

#############################################################################

# Make a dataframe with only the M/I/E
# Create a new dataframe with only the copulations, to distract the times between copulations
df_MIE=data_T.loc[(data_T[BEH]=='Start Mount')|(data_T[BEH]=='Start Intromission')|(data_T[BEH]=='Start Ejaculation')]
df_MIE['obs_num'] = df_MIE.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
df_MIE = df_MIE.sort_values(by=[OBS,TIME], ascending = False)
df_MIE['obs_num_back'] = df_MIE.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
df_MIE = df_MIE.sort_values(by=[OBS,TIME])
df_MIE['Previous_MIE_time']=df_MIE.groupby('ID')['Beh_end'].shift(1)
# fill in time previous copulation, but if it is the first, you set the time of previous even on 60 seconds earlier
df_MIE['Previous_MIE_time']=np.where((df_MIE['obs_num']==1),df_MIE['Beh_start']-60,df_MIE['Previous_MIE_time'])
df_MIE['Pretime']=np.where(((df_MIE[BEH]=='Start Mount')|(df_MIE[BEH]=='Start Intromission')|(df_MIE[BEH]=='Start Ejaculation')),
                           df_MIE['Beh_start']-df_MIE['Previous_MIE_time'],np.NaN)

# Create a dictionary with the start time of the copulation, the end time of the previous copulation and the pretime (end time-start time)
dict_MIE={}
for key in list_id:
    dict_MIE[key]={}
    for beh in list_sex:
        dict_MIE[key][beh]={}
        df_reduced = df_MIE[(df_MIE['ID'] == key) & (df_MIE[BEH] == 'Start %s'%beh)]
        temp_start = list(df_reduced[TIME])
        temp_end = list(df_reduced['Previous_MIE_time'])
        temp_pretime = list(df_reduced[TIME]-df_reduced['Previous_MIE_time'])
        dict_MIE[key][beh][TIME]=temp_start
        dict_MIE[key][beh]['Previous_MIE_time']=temp_end
        dict_MIE[key][beh]['Pretime']=temp_pretime

##########################################################################################################################
##########################################################################################################################
##########################################################################################################################

############# Behavioral graphs ################

##########################################################################################################################
##########################################################################################################################
##########################################################################################################################

# set font size for all figures
SMALL_SIZE = 12
MEDIUM_SIZE = 16
BIGGER_SIZE = 18
# plt.rcParams['font.size'] = 22 
plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=MEDIUM_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
custom_params = {"axes.spines.right": False, "axes.spines.top": False}        

# Determine some color codes for figures
color_startline='#515A5A'

color_snips='#95A5A6'
color_GCaMP='#117864'
color_shadow='xkcd:silver'
color_GFP_snips='#839192'
color_GFP='#9E3C86'

# color_AUC_post_T_bar='#5F6A6A'
# color_AUC_pre_T_bar='#D5DBDB'
# color_AUC_post_T_scatter='#4D5656'
# color_AUC_pre_T_scatter='#BFC9CA'

# color_AUC_post_S2_bar='#0E6655'
# color_AUC_pre_S2_bar='#A2D9CE'
# color_AUC_post_S2_scatter='#0B5345'
# color_AUC_pre_S2_scatter='#73C6B6'

# color_AUC_pre_bar='#98eddb'
# color_AUC_post_bar='#17A589'
# color_AUC_pre_scatter='#64b0a0'
# color_AUC_post_scatter='#0a5446'

color_AUC_bar1='#98eddb'
color_AUC_bar2='#17A589'
color_AUC_bar3='#64b0a0'
color_AUC_bar4='#0a5446'
color_AUC_bar5='#D5DBDB'

color_AUC_scatter1='#64b0a0'
color_AUC_scatter2='#0a5446'

color_M='#e784e8'
color_I='#b584e8'
color_E='#8485e8'



##########################################################################################################################
##########################################################################################################################
##########################################################################################################################

############# Analysis of TDT data from Synapse ################

##########################################################################################################################
##########################################################################################################################
##########################################################################################################################

# Create definitions that retrieve the timings of certain behaviors
def make_dict_behavior(dataframe,testsession,virus='GCaMP6',test='COP'):
    """
    Parameters
    ----------
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"

    Returns
    -------
    Dictionary with start and end times of the behaviors
    Start copulation = when "Start cop behavior" was scored, End copulation = when copulation was scored
    Start other behaviors = when behavior is scored, End other behaviors = when next behavior was scored
    """
    
    print("Start make dict behavior")
    
    # Load the dictionary with data
    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary = my_dict_process[d]
    
    start_end=['Start','End']
    
    # Create an empty dictionary
    make_dict_behavior={key:{startend:{} for startend in start_end} for key in dictionary.keys() if key in list_ID}
    for key,startends in make_dict_behavior.items():
        for startend,val in startends.items():
            for beh in list_beh_tdt:
                make_dict_behavior[key][startend][beh]=[]
            for behav in list_MB_behavior:
                make_dict_behavior[key][startend][behav]=[]

    # Get the time the video was started
    for rat,value in dictionary.items():
        if dictionary[rat]['START_on'] and rat in list_ID:
            START_on=dictionary[rat]['START_on']
            delay=START_on
            print(rat)
            
            # Fill in dictionary with times corrected with the delay of the video start
            for behav in list_beh_tdt:
                df_reduced = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav)]
                temp_start = list(df_reduced['Beh_start']+ delay)
                temp_end = list(df_reduced['Beh_end']+ delay)
                make_dict_behavior[rat]['Start'][behav]=temp_start 
                make_dict_behavior[rat]['End'][behav]=temp_end

            for behavior in list_MB_behavior:
                df_reduced = dataframe[(dataframe['ID'] == rat) & (dataframe['MB_cop_mark'] == behavior)]
                temp_start_MB = list(df_reduced['Beh_start']+ delay)
                temp_end_MB = list(df_reduced['Beh_end']+ delay)
                make_dict_behavior[rat]['Start'][behavior]=temp_start_MB
                make_dict_behavior[rat]['End'][behavior]=temp_end_MB

    return make_dict_behavior

def make_dict_beh_parts(series,dataframe,testsession,n_parts=3,type_parts='latency',virus='GCaMP6',test='COP'):
    """
    Parameters
    ----------
    series : string
        Add a string of the ejaculatory series that needs to be analyzed
        e.g. "T", "S1, or "S2""
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    n_parts : float -> Default = 3
        Add the number of part
        e.g. 3 or 5
    type_parts : string -> Default ='latency'
        Add the type on which parts are divided
        e.g. 'latency' or 'frequency'
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"

    Returns
    -------
    Dictionary with start and end times of the behaviors of parts of the test
    Start copulation = when "Start cop behavior" was scored, End copulation = when copulation was scored
    Start other behaviors = when behavior is scored, End other behaviors = when next behavior was scored
    Part of test is defined by taking the latency to 1st ejaculation or total number of that behavior, and divide this in 3 or 5 equal parts
    Behaviors taken place in the 1st 1/3 of time/frequency is part 1, 2nd 1/3 of time/frequency part 2, and final 1/3 of time/frequency part 3.
    """

    # Load the dictionary with data
    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary = my_dict_process[d]

    d2="dict_results_"+str(series) #my_dict_behavior["dict_results_tdt"]
    for key,dicts in my_dict_behavior.items():
        dictionary_results = my_dict_behavior[d2]

    # Create an empty dictionary
    if n_parts == 3:
        parts=['part1','part2','part3']
    elif n_parts == 5:
        parts=['part1','part2','part3','part4','part5']
    start_end=['Start','End']

    # Create an empty dictionary
    make_dict_beh_parts={}
    for key in dictionary.keys():
        if key in list_ID:
            make_dict_beh_parts[key]={}
            for startend in start_end:
                make_dict_beh_parts[key][startend]={}
                for beh in list_beh_tdt:
                    make_dict_beh_parts[key][startend][beh]={}
                    for part in parts:
                        make_dict_beh_parts[key][startend][beh][part]=[]
                        
    # Get the time the video was started
    for rat,value in dictionary.items():   
        if rat in dictionary_results.keys():
            if dictionary[rat]['START_on'] and rat in list_ID:
                START_on=dictionary[rat]['START_on']
                delay=START_on
                
                if n_parts==3 and type_parts=='latency':
                    part1=dictionary_results[rat]['treshold3 end 1st part']
                    part2=dictionary_results[rat]['treshold3 end 2nd part']

                    # Fill in dictionary with times corrected with the delay of the video start
                    for behav in list_behaviors:
                        df_reduced_1 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['Beh_start'] <= part1)]
                        df_reduced_2 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['Beh_start'] >= part1)&(dataframe['Beh_start'] <= part2))]
                        df_reduced_3 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['Beh_start'] >= part2)]
                        temp_start1 = list(df_reduced_1['Beh_start']+ delay)
                        temp_start2 = list(df_reduced_2['Beh_start']+ delay)
                        temp_start3 = list(df_reduced_3['Beh_start']+ delay)
                        temp_end1 = list(df_reduced_1['Beh_end']+ delay)
                        temp_end2 = list(df_reduced_2['Beh_end']+ delay)
                        temp_end3 = list(df_reduced_3['Beh_end']+ delay)
                        make_dict_beh_parts[rat]['Start'][behav]['part1']=temp_start1
                        make_dict_beh_parts[rat]['Start'][behav]['part2']=temp_start2
                        make_dict_beh_parts[rat]['Start'][behav]['part3']=temp_start3
                        make_dict_beh_parts[rat]['End'][behav]['part1']=temp_end1
                        make_dict_beh_parts[rat]['End'][behav]['part2']=temp_end2
                        make_dict_beh_parts[rat]['End'][behav]['part3']=temp_end3

                elif n_parts==5 and type_parts=='latency':
                    part1=dictionary_results[rat]['treshold5 end 1st part']
                    part2=dictionary_results[rat]['treshold5 end 2nd part']
                    part3=dictionary_results[rat]['treshold5 end 3rd part']
                    part4=dictionary_results[rat]['treshold5 end 4th part']

                    for behav in list_behaviors:
                        df_reduced_1 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['Beh_start'] <= part1)]
                        df_reduced_2 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['Beh_start'] >= part1)&(dataframe['Beh_start'] <= part2))]
                        df_reduced_3 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['Beh_start'] >= part2)&(dataframe['Beh_start'] <= part3))]
                        df_reduced_4 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['Beh_start'] >= part3)&(dataframe['Beh_start'] <= part4))]
                        df_reduced_5 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['Beh_start'] >= part4)]
                        temp_start1 = list(df_reduced_1['Beh_start']+ delay)
                        temp_start2 = list(df_reduced_2['Beh_start']+ delay)
                        temp_start3 = list(df_reduced_3['Beh_start']+ delay)
                        temp_start4 = list(df_reduced_4['Beh_start']+ delay)
                        temp_start5 = list(df_reduced_5['Beh_start']+ delay)
                        temp_end1 = list(df_reduced_1['Beh_end']+ delay)
                        temp_end2 = list(df_reduced_2['Beh_end']+ delay)
                        temp_end3 = list(df_reduced_3['Beh_end']+ delay)
                        temp_end4 = list(df_reduced_4['Beh_end']+ delay)
                        temp_end5 = list(df_reduced_5['Beh_end']+ delay)
                        make_dict_beh_parts[rat]['Start'][behav]['part1']=temp_start1
                        make_dict_beh_parts[rat]['Start'][behav]['part2']=temp_start2
                        make_dict_beh_parts[rat]['Start'][behav]['part3']=temp_start3
                        make_dict_beh_parts[rat]['Start'][behav]['part4']=temp_start4
                        make_dict_beh_parts[rat]['Start'][behav]['part5']=temp_start5
                        make_dict_beh_parts[rat]['End'][behav]['part1']=temp_end1
                        make_dict_beh_parts[rat]['End'][behav]['part2']=temp_end2
                        make_dict_beh_parts[rat]['End'][behav]['part3']=temp_end3
                        make_dict_beh_parts[rat]['End'][behav]['part4']=temp_end4
                        make_dict_beh_parts[rat]['End'][behav]['part5']=temp_end5

                elif n_parts==3 and type_parts=='frequency':
                    for behav in list_behaviors:
                        part1=dictionary_results[rat]['treshold3 end 1st part_%s'%behav]
                        part2=dictionary_results[rat]['treshold3 end 2nd part_%s'%behav]
        
                        # Fill in dictionary with times corrected with the delay of the video start
                        df_reduced_1 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['beh_num'] <= part1)]
                        df_reduced_2 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['beh_num'] > part1)&(dataframe['beh_num'] <= part2))]
                        df_reduced_3 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['beh_num'] > part2)]
                        temp_start1 = list(df_reduced_1['Beh_start']+ delay)
                        temp_start2 = list(df_reduced_2['Beh_start']+ delay)
                        temp_start3 = list(df_reduced_3['Beh_start']+ delay)
                        temp_end1 = list(df_reduced_1['Beh_end']+ delay)
                        temp_end2 = list(df_reduced_2['Beh_end']+ delay)
                        temp_end3 = list(df_reduced_3['Beh_end']+ delay)
                        make_dict_beh_parts[rat]['Start'][behav]['part1']=temp_start1
                        make_dict_beh_parts[rat]['Start'][behav]['part2']=temp_start2
                        make_dict_beh_parts[rat]['Start'][behav]['part3']=temp_start3
                        make_dict_beh_parts[rat]['End'][behav]['part1']=temp_end1
                        make_dict_beh_parts[rat]['End'][behav]['part2']=temp_end2
                        make_dict_beh_parts[rat]['End'][behav]['part3']=temp_end3

                elif n_parts==5 and type_parts=='frequency':
                    for behav in list_behaviors:
                        part1=dictionary_results[rat]['treshold5 end 1st part_%s'%behav]
                        part2=dictionary_results[rat]['treshold5 end 2nd part_%s'%behav]
                        part3=dictionary_results[rat]['treshold5 end 3rd part_%s'%behav]
                        part4=dictionary_results[rat]['treshold5 end 4th part_%s'%behav]

                        # Fill in dictionary with times corrected with the delay of the video start
                        df_reduced_1 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['beh_num'] <= part1)]
                        df_reduced_2 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['beh_num'] > part1)&(dataframe['beh_num'] <= part2))]
                        df_reduced_3 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['beh_num'] > part2)&(dataframe['beh_num'] <= part3))]
                        df_reduced_4 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & ((dataframe['beh_num'] > part3)&(dataframe['beh_num'] <= part4))]
                        df_reduced_5 = dataframe[(dataframe['ID'] == rat) & (dataframe[BEH] == behav) & (dataframe['beh_num'] > part4)]
                        temp_start1 = list(df_reduced_1['Beh_start']+ delay)
                        temp_start2 = list(df_reduced_2['Beh_start']+ delay)
                        temp_start3 = list(df_reduced_3['Beh_start']+ delay)
                        temp_start4 = list(df_reduced_4['Beh_start']+ delay)
                        temp_start5 = list(df_reduced_5['Beh_start']+ delay)
                        temp_end1 = list(df_reduced_1['Beh_end']+ delay)
                        temp_end2 = list(df_reduced_2['Beh_end']+ delay)
                        temp_end3 = list(df_reduced_3['Beh_end']+ delay)
                        temp_end4 = list(df_reduced_4['Beh_end']+ delay)
                        temp_end5 = list(df_reduced_5['Beh_end']+ delay)
                        make_dict_beh_parts[rat]['Start'][behav]['part1']=temp_start1
                        make_dict_beh_parts[rat]['Start'][behav]['part2']=temp_start2
                        make_dict_beh_parts[rat]['Start'][behav]['part3']=temp_start3
                        make_dict_beh_parts[rat]['Start'][behav]['part4']=temp_start4
                        make_dict_beh_parts[rat]['Start'][behav]['part5']=temp_start5
                        make_dict_beh_parts[rat]['End'][behav]['part1']=temp_end1
                        make_dict_beh_parts[rat]['End'][behav]['part2']=temp_end2
                        make_dict_beh_parts[rat]['End'][behav]['part3']=temp_end3
                        make_dict_beh_parts[rat]['End'][behav]['part4']=temp_end4
                        make_dict_beh_parts[rat]['End'][behav]['part5']=temp_end5
        
    return make_dict_beh_parts

# Create definitions that retrieve the timings of the artifacts that later should be removed
def artifact_time_checker_start(ID,dataframe,testsession,virus='GCaMP6',test='COP'):
    """
    Parameters
    ----------
    ID : string
        Add ID of rat/test you want to get the time of ejaculation from to remove as artifact
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"

    Returns
    -------
    Time of ejaculation with an artifact
    """
    
    print("Start make dict start behavior")
    
    get_time_dict=make_dict_behavior(dataframe,testsession,virus='GCaMP6',test='COP')
    
    start_end=['Start','End']
    artifact_time={}
    for startend in start_end:
        artifact_time[startend]=[]
        
    artifact_time['Start']=get_time_dict[ID]['Start']['Ejaculation']
    artifact_time['End']=get_time_dict[ID]['End']['Ejaculation']
    
    return artifact_time

# Create definitions that retrieve the timings of certain behaviors
def make_dict_behavior_excl(dataframe,testsession,virus='GCaMP6',test='COP',
                                  list_relevant=list_relevant_behaviors):
    """
    Parameters
    ----------
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    list_relevant: list -> Default = list_relevant_behaviors
        Add a list with the behaviors that cannot happen before the behavior you explore

    Returns
    -------
    Dictionary with start and end times of the behaviors EXCLUDING the behaviors before another (relevant) behavior has taken place.
    If behaviors are not part of the relevant list, they will be treated as "including".
    Start copulation = when "Start cop behavior" was scored, End copulation = when copulation was scored
    Start other behaviors = when behavior is scored, End other behaviors = when next behavior was scored
    """
    print("Start make dict start behavior exclude")

    # Make a new dictionary with start times excluding behavior before which another behavior has taken place
    original_dict=make_dict_behavior(dataframe,testsession,virus=virus,test=test)

    start_end=['Start','End']

    # Create empty dictionaries
    new_dict = {rat: {startend: [] for startend in start_end} for rat in original_dict}
    temp_dict = {rat: {startend: [] for startend in start_end} for rat in original_dict}
    final_dict = {rat: {startend: {} for startend in start_end} for rat in original_dict}
    
    # Create a temporary dictionary of start times that includes all times of behaviors              
    for rat,startends in original_dict.items():   
        for startend,behaviors in startends.items():
            temp=[]           
            for beh,time1 in behaviors.items():
                if beh in list_relevant_behaviors:
                    for i in time1:
                        temp.append(i)
            temp_dict[rat][startend]=temp
            temp_dict[rat][startend].sort()
    
    # Create a new dictionary after excluding behaviors with all times of behaviors
    for rat,startends in temp_dict.items():
        for startend,times in startends.items():
            temp=[]
            for index, elem in enumerate(times):
                if (len(times) and index - 1 >= 0):
                    prev_el = (times[index-1])
                    curr_el = (elem)
                    if curr_el-prev_el > 5:
                        temp.append(curr_el)

            new_dict[rat][startend]=temp
    
    # Create a new dictionary per behavior excluding the behaviors that needed exclusion
    for rat1,startends in original_dict.items():
        for startend1,behaviors in startends.items():
            for beh, times in behaviors.items():
                if beh in list_relevant_behaviors:
                    temp=[]
                    for time1 in times:
                        for rat2, startends in new_dict.items():
                            for startend2,time2 in startends.items():
                                if rat1 == rat2:
                                    if startend1 == startend2:
                                        if time1 in time2:
                                            temp.append(time1)
                    final_dict[rat1][startend1][beh]=temp
                else:
                    final_dict[rat1][startend1][beh]=original_dict[rat1][startend1][beh]
    return final_dict   

################ PARTS OF BEHAVIOR ###########################
def make_dict_beh_parts_excl(series,dataframe,testsession,n_parts=3,type_parts='latency',virus='GCaMP6',test='COP',
                                    list_relevant=list_relevant_behaviors):
    """
    Parameters
    ----------
    series : string
        Add a string of the ejaculatory series that needs to be analyzed
        e.g. "T", "S1, or "S2""
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    n_parts : float -> Default = 3
        Add the number of part
        e.g. 3 or 5
    type_parts : string -> Default ='latency'
        Add the type on which parts are divided
        e.g. 'latency' or 'frequency'
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    list_relevant: list -> Default = list_relevant_behaviors
        Add a list with the behaviors that cannot happen before the behavior you explore

    Returns
    -------
    Dictionary with start and end times of the behaviors of parts of the test
    EXCLUDING the behaviors before another (relevant) behavior has taken place.
    Start copulation = when "Start cop behavior" was scored, End copulation = when copulation was scored
    Start other behaviors = when behavior is scored, End other behaviors = when next behavior was scored
    Part of test is defined by taking the latency to 1st ejaculation or total number of that behavior, and divide this in 3 or 5 equal parts
    Behaviors taken place in the 1st 1/3 of time/frequency is part 1, 2nd 1/3 of time/frequency part 2, and final 1/3 of time/frequency part 3.
    """
    # Make a new dictionary with start times excluding behavior before which another behavior has taken place
    original_dict=make_dict_beh_parts(series,dataframe,testsession,n_parts=n_parts,type_parts=type_parts,virus=virus,test=test)
    
    if n_parts == 3:
        parts=['part1','part2','part3']
    elif n_parts == 5:
        parts=['part1','part2','part3','part4','part5']

    start_end=['Start','End']

    # Create empty dictionaries
    new_dict = {rat: {startend: {part: [] for part in parts} for startend in start_end} for rat in original_dict.keys()}
    temp_dict = {rat: {startend: {part: [] for part in parts} for startend in start_end} for rat in original_dict.keys()}
    final_dict = {rat: {startend: {beh: {part: {} for part in parts} for beh in list_beh_tdt} for startend in start_end} for rat in original_dict.keys()}

    # Create a temporary dictionary of start times that includes all times of behaviors              
    for rat,startends in original_dict.items():  
        for startend,behaviors in startends.items():
            temp_part1=[]           
            temp_part2=[]           
            temp_part3=[]           
            temp_part4=[]           
            temp_part5=[]           
            for beh,parts in behaviors.items():
                for part,times in parts.items():
                    if beh in list_relevant_behaviors:
                        if part=="part1":
                            for i in times:
                                temp_part1.append(i)
                        if part=="part2":
                            for i in times:
                                temp_part2.append(i)
                        if part=="part3":
                            for i in times:
                                temp_part3.append(i)
                        if part=="part4":
                            for i in times:
                                temp_part4.append(i)
                        if part=="part5":
                            for i in times:
                                temp_part5.append(i)
            temp_dict[rat][startend]["part1"]=temp_part1
            temp_dict[rat][startend]["part2"]=temp_part2
            temp_dict[rat][startend]["part3"]=temp_part3
            temp_dict[rat][startend]["part4"]=temp_part4
            temp_dict[rat][startend]["part5"]=temp_part5
            temp_dict[rat][startend]["part1"].sort()
            temp_dict[rat][startend]["part2"].sort()
            temp_dict[rat][startend]["part3"].sort()
            temp_dict[rat][startend]["part4"].sort()
            temp_dict[rat][startend]["part5"].sort()

    # Create a new dictionary after excluding behaviors with all times of behaviors
    for rat,startends in temp_dict.items():
        for startend,parts in startends.items():
            for part,times in parts.items():
                temp=[]
                for index, elem in enumerate(times):
                    if (len(times) and index - 1 >= 0):
                        prev_el = (times[index-1])
                        curr_el = (elem)
                        if curr_el-prev_el > 5:
                            temp.append(curr_el)
                new_dict[rat][startend][part]=temp

    # Create a new dictionary per behavior excluding the behaviors that needed exclusion
    for rat1,startends in original_dict.items():
        for startend1,behaviors in startends.items():
            for beh,parts in behaviors.items():
                for part1,times in parts.items():
                    if beh in list_relevant_behaviors:
                        temp=[]
                        for time1 in times:
                            for rat2, startends in new_dict.items():
                                for startend2, parts2 in startends.items():
                                    for part2,time2 in parts2.items():
                                        if rat1 == rat2:
                                            if startend1 == startend2:
                                                if part1 == part2:
                                                    if time1 in time2:
                                                        temp.append(time1)
                        final_dict[rat1][startend1][beh][part1]=temp
                    else:
                        final_dict[rat1][startend1][beh][part1]=original_dict[rat1][startend1][beh][part1]

    return final_dict   

# Create definition to make fullgraphs with the copulations marked.
def copmarkgraphs(dataframe,testsession,virus='GCaMP6',test='COP',exclude_outliers=status_outliers,graphtitle='COPGRAPH_'):
    """
    Parameters
    ----------
    dataframe : DataFrame -> Default = data_T
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    virus : string -> Default ='GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    exclude_outliers : boolean -> Default = what is stated in the top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    graphtitle : string -> Default = 'COPMARKGRAPH'
        Add the name of the figure 

    Returns
    -------
    Figure
        Processes the TDT data with processdata_fullgraph definition and make_dict_start/end_cop definition.
        The definition creates a figure with the dFF signals over the course of the full test with the mounts, 
        intromissions and ejaculation marked.
    Dictionary AUC parts
        Dictionary that contain the AUC of part 1, 2 and 3 of the series.
    """

    print("Start copmarkgraph")

    # Load in the dictionary with the data
    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary = my_dict_process[d]

    # Set directory for figures
    if exclude_outliers==False:
        directory_graph=directory_results
    else:
        directory_graph=directory_results_cor

    # Get the copulation times
    dict_beh=make_dict_behavior(dataframe,testsession,virus=virus,test=test)

    # Make empty dictionary for the AUC dict
    parts=['Part 1','Part 2','Part 3']
    dict_AUC_full={rat:{part:[] for part in parts}for rat in dictionary.keys()}
    
    # Get dFF,zscore, time and fs from dictionary of processed data
    for rat,value in dictionary.items(): 
        if rat in list_ID:
            print("Start behavior_snipper %s"%(rat))
            if exclude_outliers == False:
                dFF=dictionary[rat]['dFF']
                zscore=dictionary[rat]['zscore']
                time=dictionary[rat]['time']
            else: 
                dFF=dictionary[rat]['dFF_cor']
                zscore=dictionary[rat]['zscore_cor']
                time=np.array(dictionary[rat]['time_cor'])
    
            # Read out the data from the dFF dictionary and link to behavior
            MOUNT_on = dict_beh[rat]['Start'][BA] if dict_beh[rat]['Start'][BA] else [np.nan,np.nan]
            MOUNT_off = dict_beh[rat]['End'][BA] if dict_beh[rat]['End'][BA] else [np.nan,np.nan]
            INTRO_on = dict_beh[rat]['Start'][BB] if dict_beh[rat]['Start'][BB] else [np.nan,np.nan]
            INTRO_off = dict_beh[rat]['End'][BB] if dict_beh[rat]['End'][BB] else [np.nan,np.nan]
            EJAC_on = dict_beh[rat]['Start'][BC] if dict_beh[rat]['Start'][BC] else [np.nan,np.nan]
            EJAC_off = dict_beh[rat]['End'][BC] if dict_beh[rat]['End'][BC] else [np.nan,np.nan]

            # Snip out the time of the series wanted in the graph
            # Determine the times before and after the first and last behaviors that need to be in the graph
            MIN_TIME_MOUNT = MOUNT_on[0]-15 
            MIN_TIME_INTRO = INTRO_on[0]-15
            if MIN_TIME_MOUNT < MIN_TIME_INTRO:
                MIN_TIME = MIN_TIME_MOUNT
            else:
                MIN_TIME = MIN_TIME_INTRO
            MAX_TIME = EJAC_off[-1]+15
            
            THIRD_PART = (MAX_TIME-MIN_TIME-30)/3
            END_PART1 = (MIN_TIME+15)+THIRD_PART
            END_PART2 = (MAX_TIME-15)-THIRD_PART
            PRE_PART = (MIN_TIME+15)-THIRD_PART
            # Snip the time and DFF arrays
            dFF_snip=[b for b,t in zip(dFF,time) if t>MIN_TIME and t<MAX_TIME]
            zscore_snip=[z for z,t in zip(zscore,time) if t>MIN_TIME and t<MAX_TIME]
            time_snip=[t for b,t in zip(dFF,time) if t>MIN_TIME and t<MAX_TIME]
            
            # Snip the dFF for AUC dividing the test in three parts
            AUC_snip_part1=[b for b,t in zip(dFF,time) if t>MIN_TIME+15 and t<END_PART1]
            AUC_snip_part2=[b for b,t in zip(dFF,time) if t>END_PART1 and t<END_PART2]
            AUC_snip_part3=[b for b,t in zip(dFF,time) if t>END_PART2 and t<MAX_TIME-15]
            AUC_snip_prepart=[b for b,t in zip(dFF,time) if t>PRE_PART and t<MIN_TIME+15]

            # Calculate AUC
            AUC_part1=trapz(AUC_snip_part1)/THIRD_PART          
            AUC_part2=trapz(AUC_snip_part2)/THIRD_PART           
            AUC_part3=trapz(AUC_snip_part3)/THIRD_PART           
            AUC_prepart=trapz(AUC_snip_prepart)/THIRD_PART 

            dict_AUC_full[rat]['Pre-part']= AUC_prepart
            dict_AUC_full[rat]['Part 1']= AUC_part1
            dict_AUC_full[rat]['Part 2']= AUC_part2
            dict_AUC_full[rat]['Part 3']= AUC_part3
            
            # Make Dataframe of AUC
            dict_AUC={'Pre':AUC_prepart,'Part 1':AUC_part1, 'Part 2':AUC_part2, 'Part 3':AUC_part3}            
                
            # Convert to data frame
            df_AUC = pd.DataFrame(dict_AUC, index=[0])
            df_AUC = df_AUC.reset_index()
    
            # make one column of the data with a new column for pre-post
            df_AUC_melted=pd.melt(df_AUC, id_vars =['index'],value_vars =['Pre','Part 1','Part 2', 'Part 3'],var_name ='AUC')
            
            # Set the x-axis to zero
            time_snip2=[t-time_snip[0] for t in time_snip]
           
            # Make figures
            if len(time_snip)>0 and len(dFF_snip)>0 and MAX_TIME !=15:
                # Change directory to output folder
                if not os.path.isdir(directory_graph+directory_copgraphs):
                    os.mkdir(directory_graph+directory_copgraphs)
                if not os.path.isdir(directory_graph+directory_copgraphs+'/zscore'):
                    os.mkdir(directory_graph+directory_copgraphs+'/zscore')
                if not os.path.isdir(directory_graph+directory_copgraphs+'/AUC'):
                    os.mkdir(directory_graph+directory_copgraphs+'/AUC')
                
                os.chdir(directory_graph+directory_copgraphs)

                x_max=max(time_snip2)
                y_dFF_max=max(dFF_snip)
                y_dFF_min=min(dFF_snip)
                y_dFF_part=(y_dFF_max-y_dFF_min)/12
                y_dFF_M=y_dFF_max
                y_dFF_I=y_dFF_max-y_dFF_part
                y_dFF_E=y_dFF_max-2*y_dFF_part
                y_zscore_max=max(zscore_snip)
                y_zscore_min=min(zscore_snip)
                y_zscore_part=(y_zscore_max-y_zscore_min)/12
                y_zscore_M=y_zscore_max
                y_zscore_I=y_zscore_max-y_zscore_part
                y_zscore_E=y_zscore_max-2*y_zscore_part

                # dFF with copulation epocs
                sns.set(style="ticks")#, rc=custom_params)
                fig = plt.figure(figsize=(30,8))
                ax = fig.add_subplot(111)
                
                ax.plot(time_snip2, dFF_snip, linewidth=2, color=color_GCaMP)
                
                for on, off in zip(MOUNT_on-time_snip[0], MOUNT_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.5, color=color_M)
                for on, off in zip(INTRO_on-time_snip[0], INTRO_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.5, color=color_I)
                for on, off in zip(EJAC_on-time_snip[0], EJAC_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.8, color=color_E)
                
                ax.set_ylabel(r'$\Delta$F/F %',fontsize=18)
                ax.set_xlabel('Seconds',fontsize=18)
                ax.autoscale()
                ax.axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                plt.xticks(fontsize=xaxis_fontsize)
                plt.yticks(fontsize=yaxis_fontsize)
                ax.text(x_max,y_dFF_M,'Mount',horizontalalignment="left",verticalalignment="top", color= color_M,fontsize=label_fontsize,fontweight="bold")
                ax.text(x_max,y_dFF_I,'Intromission',horizontalalignment="left",verticalalignment="top",color= color_I,fontsize=label_fontsize,fontweight="bold")
                ax.text(x_max,y_dFF_E,'Ejaculation',horizontalalignment="left",verticalalignment="top", color= color_E,fontsize=label_fontsize,fontweight="bold")
                fig.tight_layout()
                sns.despine()
                plt.savefig(f"dFF {graphtitle}_{rat}_{virus}.png")
                plt.close(fig)

                # zscore with copulation epocs
                os.chdir(directory_graph+directory_copgraphs+'/zscore')
        
                sns.set(style="ticks")#, rc=custom_params)
                fig = plt.figure(figsize=(30,8))
                ax = fig.add_subplot(111)
                
                ax.plot(time_snip2, zscore_snip, linewidth=2, color=color_GCaMP)
                
                for on, off in zip(MOUNT_on-time_snip[0], MOUNT_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.5, color=color_M)
                for on, off in zip(INTRO_on-time_snip[0], INTRO_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.5, color=color_I)
                for on, off in zip(EJAC_on-time_snip[0], EJAC_off-time_snip[0]):
                    ax.axvspan(on, off, alpha=0.8, color=color_E)
                
                ax.set_ylabel('z-score',fontsize=18)
                ax.set_xlabel('Seconds',fontsize=18)
                ax.axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                ax.autoscale()
                plt.xticks(fontsize=xaxis_fontsize)
                plt.yticks(fontsize=yaxis_fontsize)
                ax.text(x_max,y_zscore_M,'Mount',horizontalalignment="left",verticalalignment="top", color= color_M,fontsize=label_fontsize,fontweight="bold")
                ax.text(x_max,y_zscore_I,'Intromission',horizontalalignment="left",verticalalignment="top",color= color_I,fontsize=label_fontsize,fontweight="bold")
                ax.text(x_max,y_zscore_E,'Ejaculation',horizontalalignment="left",verticalalignment="top", color= color_E,fontsize=label_fontsize,fontweight="bold")
                fig.tight_layout()
                sns.despine()
                plt.savefig(f"zscore {graphtitle}_{rat}_{virus}.png")
                plt.close(fig)

                # AUC bartplots
                ymax=np.max(df_AUC_melted['value'])
                ymin=np.min(df_AUC_melted['value'])
                
                y_max=round(ymax / 10) * 10 +10
                y_min=round(ymin / 10) * 10 -10

                os.chdir(directory_graph+directory_copgraphs+'/AUC')
                sns.set_style("ticks")
                palette_bar = [color_AUC_bar1,color_AUC_bar2, color_AUC_bar3,color_AUC_bar4]
                fig, ax = plt.subplots(figsize=(6, 4))
                sns.barplot(data=df_AUC_melted,x='AUC', y='value', errorbar = None, palette=palette_bar, width=0.4)
                ax.set_ylabel('AUC per second',fontsize=yaxis_fontsize)
                ax.set_xlabel(None)
                # ax.set_xticks(ticks=['Pre','Part 1','Part 2','Part 3'],fontsize=xaxis_fontsize)
                ax.tick_params(bottom=False)          
                ax.set_ylim([y_min,y_max])
                sns.despine()
                sns.despine(bottom=True)
                ax.axhline(y=0, linewidth=1, color=color_startline)
                fig.tight_layout()
                fig.savefig(f"AUC_{graphtitle}_{rat}_{virus}.png")
                plt.close(fig)
             
    # Change directory back
    os.chdir(directory)

    return dict_AUC_full
    print("copmarkgraphs defined")

############################################################################################################
############################################################################################################

# Make figures of the snips of the separate series with copulation marks
AUC_part_S1_GCaMP6_COP_1=copmarkgraphs(data_S1,1, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_2=copmarkgraphs(data_S1,2, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_3=copmarkgraphs(data_S1,3, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_4=copmarkgraphs(data_S1,4, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_5=copmarkgraphs(data_S1,5, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_6=copmarkgraphs(data_S1,6, graphtitle='COPGRAPH_S1_')
AUC_part_S1_GCaMP6_COP_7=copmarkgraphs(data_S1,7, graphtitle='COPGRAPH_S1_')


############################################################################################################
############################################################################################################


# Make a definition for the mean behavior snips per rat
def result_behavior_snipper (dataframe,testsession,virus='GCaMP6',test='COP',
                              beh_list=list_beh_tdt,excluding_behaviors=status_excluding,correction = status_correction,
                              list_relevant=list_relevant_behaviors,exclude_outliers=status_outliers,
                              sniptime_pre=presnip,sniptime_post=postsnip):
    """
    Parameters
    ----------
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    beh_list : list -> Default = list_beh_tdt
        Add the list with behaviors that need to be analyzed
        e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
    excluding_behaviors : string - Default = what is filled in on top of the script
        Add "exclude" if you want the delete the behaviors before which another behavior has taken place
    correction : boolean -> Default is True
        Add whether or not to correct for baseline
    list_relevant: list -> Default = list_relevant_behaviors
        If you have "exclude", add a list with the behaviors that cannot happen before the behavior you explore
        Note -> if you don't exclude, just name a random list. This variable will then not be used.
    exclude_outliers : boolean -> Default = what is filled in on top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    sniptime_pre : integer -> Default = 10
        Add the amount of seconds before the start of the behavior that needs to be analyzed
    sniptime_post : integer -> Default = 10
        Add the amount of seconds after the start of the behavior that needs to be analyzed

    Returns
    -------
    dict1: dict_of_means with all snips per rat and behavior and the mean of the these snips for rat
    dict2: dict_ratmeans with all mean snips per behavior and the mean of these snips.
    If correction = True: Dictionaries with the baseline-corrected mean dFF of snips before and after the behaviors per test. 
    First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
    Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
    the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
    """
    print("Start result_behavior_snipper %s%s"%(test,testsession))

    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary = my_dict_process[d]

    # Make snips around behavior
    if excluding_behaviors== "exclude":
        dict_beh=make_dict_behavior_excl(dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
    else:        
        dict_beh=make_dict_behavior(dataframe,testsession,virus=virus,test=test)
    
    # Make empty dictionaries
    dict_tdt_mean={}
    dict_tdt_AUC={}

    outs=['dFF','zscore','zscore_snip','dFF_snips','zscore_snips','zscore_dFF_snips']
    list_behavior=[]
    stats=['mean','sem']
    aucs=['AUC_pre','AUC_post']

    dict_tdt_mean={out:{rat:{} for rat in dictionary.keys() if rat not in list_signal_artifact_excl and rat in list_ID} for out in outs} 
    dict_tdt_AUC={auc:{rat:{} for rat in dictionary.keys() if rat not in list_signal_artifact_excl and rat in list_ID} for auc in aucs}
    
    # Get dFF,time and fs from dictionary of processed data
    for rat,value in dictionary.items():  
        if rat not in list_signal_artifact_excl and rat in list_ID:
            print("Start behavior_snipper %s"%(rat))
            if exclude_outliers == False:
                dFF=dictionary[rat]['dFF']
                zscore=dictionary[rat]['zscore']
                time=dictionary[rat]['time']
            else: 
                dFF=dictionary[rat]['dFF_cor']
                zscore=dictionary[rat]['zscore_cor']
                time=np.array(dictionary[rat]['time_cor'])

            fs=dictionary[rat]['fs']
            maxtime=np.max(time[-1])

            # Run over every behavior
            for beh in beh_list:
                # Only continue if the dictionairy contains numbers of events:
                # if len(dict_beh[rat][beh]) > 0:
                if dict_beh[rat]['Start'][beh]:
                    # First make a continous time series of behavior events (epocs) and plot
                    BEH_on = dict_beh[rat]['Start'][beh]
                    BEH_off = dict_beh[rat]['End'][beh]
    
                    # Create a list of these lists for later
                    EVENTS=[BEH_on,BEH_off]
                    # Create label names that come with it
                    LABEL_EVENTS=['Start %s'%beh, 'End %s'%beh]
    
                    # Now make snips of the data
                    PRE_TIME = sniptime_pre # number of seconds before event onset
                    POST_TIME = sniptime_post # number of seconds after
                    BASELINE_START = baseline_start
                    BASELINE_END = baseline_end
                   
                    TRANGE = [-PRE_TIME*np.floor(fs), POST_TIME*np.floor(fs)]
                    TRANGE_BASELINE = [BASELINE_START*np.floor(fs), BASELINE_END*np.floor(fs)]
    
                    # TRANGE_pre = [-PRE_TIME*np.floor(fs), np.floor(fs)]
                    # TRANGE_post = [np.floor(fs), np.floor(fs)*POST_TIME]

                    # time span for peri-event filtering, PRE and POST, in samples
                    for event,name in zip(EVENTS,LABEL_EVENTS):
                        dFF_snips = []
                        dFF_snips_BASELINE=[]
                        zscore_snips = []
                        zscore_snips_BASELINE=[]
                        array_ind = []
                        pre_stim = []
                        start_stim = []
                        post_stim = []
                        pre_BASELINE= []
                        post_BASELINE= []
                        dFF_snips_cor=[]
                        dFF_snips_list=[]
                        zscore_snips_cor=[]
                        zscore_snips_list=[]
                        
                        AUC_dFF_snips_pre_cor=[]
                        AUC_dFF_snips_post_cor=[]
                        AUC_dFF_snips_pre_list=[]
                        AUC_dFF_snips_post_list=[]
                        AUC_pre_list=[]
                        AUC_post_list=[]
    
                        for on in event:
                            #If the event cannot include pre-time seconds before event, exclude it from the data analysis
                            if on > PRE_TIME and on < maxtime:
                                # find first time index after event onset
                                array_ind.append(np.where(time > on)[0][0])
                                # find index corresponding to pre and post stim durations
                                pre_stim.append(array_ind[-1] + TRANGE[0])
                                start_stim.append(array_ind[-1])
                                post_stim.append(array_ind[-1] + TRANGE[1])
                                pre_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[0])
                                post_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[1])
                                BASELINE_dFF=dFF[int(pre_BASELINE[-1]):int(post_BASELINE[-1])]
                                BASELINE_zscore=zscore[int(pre_BASELINE[-1]):int(post_BASELINE[-1])]
                                mean_BASELINE_dFF=np.mean(BASELINE_dFF)
                                mean_BASELINE_zscore=np.mean(BASELINE_zscore)
                                dFF_snip=dFF[int(pre_stim[-1]):int(post_stim[-1])]
                                dFF_snips_cor.append(np.subtract(dFF_snip, mean_BASELINE_dFF))
                                dFF_snips_list.append(np.subtract(dFF_snip, 0))
                                zscore_snip=zscore[int(pre_stim[-1]):int(post_stim[-1])]
                                zscore_snips_cor.append(np.subtract(zscore_snip,mean_BASELINE_zscore))
                                zscore_snips_list.append(np.subtract(zscore_snip,0))

                                AUC_dFF_snips_pre=dFF[int(pre_stim[-1]):int(start_stim[-1])]
                                AUC_dFF_snips_pre_cor.append(np.subtract(AUC_dFF_snips_pre, mean_BASELINE_dFF))
                                AUC_dFF_snips_pre_list.append(np.subtract(AUC_dFF_snips_pre, 0))

                                AUC_dFF_snips_post=dFF[int(start_stim[-1]):int(post_stim[-1])]
                                AUC_dFF_snips_post_cor.append(np.subtract(AUC_dFF_snips_post, mean_BASELINE_dFF))
                                AUC_dFF_snips_post_list.append(np.subtract(AUC_dFF_snips_post, 0))
            
                        # Based on condition correct or don't correct for baseline
                        if correction == True:
                            dFF_snips=dFF_snips_cor
                            zscore_snips=zscore_snips_cor
                            AUC_snips_pre=AUC_dFF_snips_pre_cor
                            AUC_snips_post=AUC_dFF_snips_post_cor
                        else:
                            dFF_snips=dFF_snips_list
                            zscore_snips=zscore_snips_list
                            AUC_snips_pre=AUC_dFF_snips_pre_list
                            AUC_snips_post=AUC_dFF_snips_post_list
    
                        # Remove the snips that are shorter in size
                        if dFF_snips:
                            max1 = np.max([np.size(x) for x in dFF_snips])
                            dFF_snips=[snip for snip in dFF_snips if np.size(snip)==max1]                    
                            zscore_snips=[snip for snip in zscore_snips if np.size(snip)==max1]                    

                            max2 = np.max([np.size(x) for x in AUC_snips_pre])
                            max3 = np.max([np.size(x) for x in AUC_snips_post])
            
                            AUC_snips_pre=[snip for snip in AUC_snips_pre if (np.size(snip)==max2 and np.size(snip)==max3)]                    
                            AUC_snips_post=[snip for snip in AUC_snips_post if (np.size(snip)==max2 and np.size(snip)==max3)]                    
                            
                            # Take the mean of the snips
                            mean_dFF_snips = np.mean(dFF_snips, axis=0)
                            std_dFF_snips = np.std(dFF_snips, axis=0)
    
                            mean_zscore_snips = np.mean(zscore_snips, axis=0)
                            std_zscore_snips = np.std(zscore_snips, axis=0)
                        
                            zall = []
                            for snip in dFF_snips: 
                                zb = np.mean(snip)
                                zsd = np.std(snip)
                                zall.append((snip - zb)/zsd)
                               
                            zscore_dFF_snips = np.mean(zall, axis=0)
 
                            # Calculate AUC
                            AUC_pre=[trapz(snip) for snip in AUC_snips_pre]             
                            AUC_post=[trapz(snip) for snip in AUC_snips_post]             
            
                            AUC_pre_list.append(AUC_pre)
                            AUC_post_list.append(AUC_post)
                            
                            mean_pre=np.mean(AUC_pre_list, axis=1)/sniptime_pre
                            mean_post=np.mean(AUC_post_list, axis=1)/sniptime_post
            
                            # Put the data in the dictionaries
                            dict_tdt_AUC['AUC_pre'][rat][name]=mean_pre
                            dict_tdt_AUC['AUC_post'][rat][name]=mean_post
            
                            # Put the data in the dictionaries
                            dict_tdt_mean['dFF'][rat][name]=mean_dFF_snips
                            dict_tdt_mean['zscore'][rat][name]=mean_zscore_snips
                            dict_tdt_mean['zscore_snip'][rat][name]=zscore_dFF_snips
                            dict_tdt_mean['dFF_snips'][rat][name]=dFF_snips
                            dict_tdt_mean['zscore_snips'][rat][name]=zscore_snips
                            dict_tdt_mean['zscore_dFF_snips'][rat][name]=zall
                            list_behavior.append(name)

    # Make new dictorionary and fill in with the data (e.g. all dFF snips per rat per behavior)
    dict_of_means = {out: {beh: [dict_tdt_mean[out][rat][beh] for rat in dict_tdt_mean[out].keys() 
                                  if beh in dict_tdt_mean[out][rat]] for beh in list_behavior} for out in outs}
    dict_AUC_means = {auc: {beh: [dict_tdt_AUC[auc][rat][beh] for rat in dict_tdt_AUC[auc].keys() 
                                  if beh in dict_tdt_AUC[auc][rat]] for beh in list_behavior} for auc in aucs}
    
    # Make empty dictionary for future output
    dict_ratmeans = {out: {beh: {stat: [] for stat in stats} for beh in list_behavior} for out in outs}
    dict_AUC_ratmeans = {auc: {beh: {stat:[] for stat in stats} for beh in list_behavior} for auc in aucs}

    # Calculate the data
    for out in outs:
        for beh in list_behavior:
            if dict_of_means['dFF'][beh]:
                # Find the maximum length of snips across all lists
                max2 = np.max([np.size(x) for x in dict_of_means['dFF'][beh]])

                # Filter lists to only include snips with the maximum length
                dict_of_means[out][beh] = [snip for snip in dict_of_means[out][beh] if np.size(snip) == max2]

                # Calculate the dFF data
                yarray_dFF = np.array(dict_of_means['dFF'][beh])
                y_dFF = np.mean(yarray_dFF, axis=0)
                yerror_dFF = np.std(yarray_dFF, axis=0)/np.sqrt(len(yarray_dFF))

                # Calculate the z-score data (determined on full data-set)
                yarray_zscore = np.array(dict_of_means['zscore'][beh])
                y_zscore = np.mean(yarray_zscore, axis=0)
                yerror_zscore = np.std(yarray_zscore, axis=0)/np.sqrt(len(yarray_zscore))
 
                # Calculate the new z-score from the dFF of the snips only
                yarray_zscore_snip = np.array(dict_of_means['zscore_snip'][beh])
                y_zscore_snip = np.mean(yarray_zscore_snip, axis=0)
                yerror_zscore_snip = np.std(yarray_zscore_snip, axis=0)/np.sqrt(len(yarray_zscore_snip))
    
                # Put the data in the dictionaries
                dict_ratmeans['dFF'][beh]['mean']=y_dFF
                dict_ratmeans['dFF'][beh]['sem']=yerror_dFF
                dict_ratmeans['zscore'][beh]['mean']=y_zscore
                dict_ratmeans['zscore'][beh]['sem']=yerror_zscore
                dict_ratmeans['zscore_snip'][beh]['mean']=y_zscore_snip
                dict_ratmeans['zscore_snip'][beh]['sem']=yerror_zscore_snip
                dict_ratmeans['dFF_snips'][beh]=dict_of_means['dFF'][beh]
                dict_ratmeans['zscore_snips'][beh]=dict_of_means['zscore'][beh]
                dict_ratmeans['zscore_dFF_snips'][beh]=dict_of_means['zscore_snips'][beh]

    # Calculate the AUC data
    for auc in aucs:
        for beh in list_behavior:
            # Filter lists to only include snips with the maximum length
            dict_AUC_means[auc][beh] = [snip for snip in dict_AUC_means[auc][beh]]
            yarray_AUC = np.array(dict_AUC_means[auc][beh])
            y_AUC = np.mean(yarray_AUC, axis=0)
            yerror_AUC = np.std(yarray_AUC, axis=0)/np.sqrt(len(yarray_AUC))

            dict_AUC_ratmeans[auc][beh]['mean']=y_AUC
            dict_AUC_ratmeans[auc][beh]['sem']=yerror_AUC
            dict_AUC_ratmeans[auc][beh]['mean_all']=dict_AUC_means[auc][beh]
            

    return dict_tdt_mean,dict_ratmeans,dict_tdt_AUC,dict_AUC_ratmeans

def graphmaker_behaviors_perrat(dictionary,testsession,directory_figure,graphtitle,virus='GCaMP6',test='COP',
                     beh_list=list_beh_tdt,exclude_outliers=status_outliers,
                     sniptime_pre=presnip,sniptime_post=postsnip):  
    """
    Parameters
    ----------
    dictionary : dictionary
        Add dictionary that contains the data you want to make figures of
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    graphtitle : string 
        Add the start name of the figure that is saved.
    directory_figure : directory name
        Add the directory under which you want to save the figures
        e.g. directory_results_perrat, directory_results_total, directory_results_parts, directory_AUC etc
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    beh_list : list -> Default = list_beh_tdt
        Add the list with behaviors that need to be analyzed
        e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
    excluding_behaviors : string - Default = what is filled in on top of the script
        Add "exclude" if you want the delete the behaviors before which another behavior has taken place
    exclude_outliers : boolean -> Default = what is filled in on top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    sniptime_pre : integer -> Default = 10
        Add the amount of seconds before the start of the behavior that needs to be analyzed
    sniptime_post : integer -> Default = 10
        Add the amount of seconds after the start of the behavior that needs to be analyzed

    Returns
    -------
    Figures (per rat per coptest)
    Figures of individual behavioral snip and the mean of snips dFF signals aligned to the behaviors
    """

    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary_analysis = my_dict_process[d]

    # Set directory for figures
    if exclude_outliers==False:
        directory_graph=directory_results
    else:
        directory_graph=directory_results_cor

    # Change directory to output folder
    if not os.path.isdir(directory_graph+directory_figure):
        os.mkdir(directory_graph+directory_figure)
    if not os.path.isdir(directory_graph+directory_figure+"/zscore"):
        os.mkdir(directory_graph+directory_figure+"/zscore")
    if not os.path.isdir(directory_graph+directory_figure+"/zscoresnips"):
        os.mkdir(directory_graph+directory_figure+"/zscoresnips")
  
    # Make figures
    for output,rats in dictionary.items():
        for rat,beh_outcomes in rats.items():
            if rat in list_ID:
                fs=dictionary_analysis[rat]['fs']
                for beh_outcome, value in beh_outcomes.items():
                    for beh in beh_list:
                        if beh_outcome == 'Start %s'%beh or beh_outcome == 'End %s'%beh:
                            peri_time = np.linspace(1, len(dictionary['dFF'][rat][beh_outcome]), len(dictionary['dFF'][rat][beh_outcome]))/fs - sniptime_pre
                
                            os.chdir(directory_graph+directory_figure)
                            sns.set_style("ticks")
                            fig, ax = plt.subplots(figsize=(7, 5))
                            for snip in dictionary['dFF_snips'][rat][beh_outcome]:
                                p1, = ax.plot(peri_time, snip, linewidth=.5, color=color_snips, label='Individual Trials')
                            p2, = ax.plot(peri_time, dictionary['dFF'][rat][beh_outcome], linewidth=1.5, color=color_GCaMP, label='Mean Response')
                            ax.axvline(x=0, ymin=y_min, ymax=y_max, linestyle='--',linewidth=1, color=color_startline)
                            ax.axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                            ax.set_xticks(np.arange(-sniptime_pre, sniptime_post+1, 2),fontsize=axis_fontsize)
                            ax.set_xlabel('Seconds',fontsize=axis_fontsize)
                            ax.set_ylabel(r'$\Delta$F/F (%)',fontsize=axis_fontsize)
                            # ax.set_title(f"{graphtitle}_{beh_outcome}_{rat}",fontsize=title_fontsize)
                            sns.despine()
                            fig.tight_layout()
                            fig.savefig(f"dFF_{graphtitle}_{beh_outcome}_{rat}.png")
                            plt.close(fig)
            
                            os.chdir(directory_graph+directory_figure+"/zscore")
                            sns.set_style("ticks")
                            fig, ax = plt.subplots(figsize=(7, 5))
                            for snip in dictionary['zscore_snips'][rat][beh_outcome]:
                                p1, = ax.plot(peri_time, snip, linewidth=.5, color=color_snips, label='Individual Trials')
                            p2, = ax.plot(peri_time, dictionary['zscore'][rat][beh_outcome], linewidth=1.5, color=color_GCaMP, label='Mean Response')
                            ax.axvline(x=0, ymin=y_min, ymax=y_max, linestyle='--',linewidth=1, color=color_startline)
                            ax.axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                            ax.set_xticks(np.arange(-sniptime_pre, sniptime_post+1, 2),fontsize=axis_fontsize)
                            ax.set_xlabel('Seconds',fontsize=axis_fontsize)
                            ax.set_ylabel('z-score',fontsize=axis_fontsize)
                            # ax.set_title(f"{graphtitle}_{beh_outcome}_{rat}",fontsize=title_fontsize)
                            sns.despine()
                            fig.tight_layout()
                            fig.savefig(f"zscore_{graphtitle}_{beh_outcome}_{rat}.png")
                            plt.close(fig)
            
                            os.chdir(directory_graph+directory_figure+"/zscoresnips")
                            sns.set_style("ticks")
                            fig, ax = plt.subplots(figsize=(7, 5))
                            for snip in dictionary['zscore_dFF_snips'][rat][beh_outcome]:
                                p1, = ax.plot(peri_time, snip, linewidth=.5, color=color_snips, label='Individual Trials')
                            p2, = ax.plot(peri_time, dictionary['zscore_snip'][rat][beh_outcome], linewidth=1.5, color=color_GCaMP, label='Mean Response')
                            ax.axvline(x=0, ymin=y_min, ymax=y_max, linestyle='--',linewidth=1, color=color_startline)
                            ax.axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                            ax.set_xticks(np.arange(-sniptime_pre, sniptime_post+1, 2),fontsize=axis_fontsize)
                            ax.set_xlabel('Seconds',fontsize=axis_fontsize)
                            ax.set_ylabel('z-score',fontsize=axis_fontsize)
                            # ax.set_title(f"{graphtitle}_{beh_outcome}_{rat}",fontsize=title_fontsize)
                            sns.despine()
                            fig.tight_layout()
                            fig.savefig(f"zscoresnip_{graphtitle}_{beh_outcome}_{rat}.png")
                            plt.close(fig)
                print(rat,'- Figures made')
            
    # Change directory back
    os.chdir(directory)

def calculate_axis(dict_ratmeans):
    """
    Works only in other definition!
    
    Parameters
    ----------
    dict_of_means : dictionaru
        Dict_of_means is the dictionary that runs out second from the result_behavior_snipper or result_behavior_part_snipper
        Make sure to fill in the

    Returns
    -------
    Maximum and minimal Y values for dFF, z-score and z-score snip figures

    """
    ymax_dFF = []
    ymin_dFF = []
    ymax_zscore = []
    ymin_zscore = []
    ymax_zscore_snip = []
    ymin_zscore_snip = []

    outs=['dFF','zscore','zscore_snip']

    for out in outs:
        for beh in dict_ratmeans['dFF_snips'].keys():
            if dict_ratmeans['dFF_snips'][beh]:
                # Calculate dFF data
                yarray_dFF = np.array(dict_ratmeans['dFF_snips'][beh])
                y_dFF = np.mean(yarray_dFF, axis=0)
                yerror_dFF = np.std(yarray_dFF, axis=0)/np.sqrt(len(yarray_dFF))
                ymin_dFF.append(np.min(y_dFF-yerror_dFF))
                ymax_dFF.append(np.max(y_dFF+yerror_dFF))

                # Calculate z-score data
                yarray_zscore = np.array(dict_ratmeans['zscore_snips'][beh])
                y_zscore = np.mean(yarray_zscore, axis=0)
                yerror_zscore = np.std(yarray_zscore, axis=0)/np.sqrt(len(yarray_zscore))
                ymin_zscore.append(np.min(y_zscore-yerror_zscore))
                ymax_zscore.append(np.max(y_zscore+yerror_zscore))

                # Calculate z-score data from snips only
                yarray_zscore_snip = np.array(dict_ratmeans['zscore_dFF_snips'][beh])
                y_zscore_snip = np.mean(yarray_zscore_snip, axis=0)
                yerror_zscore_snip = np.std(yarray_zscore_snip, axis=0)/np.sqrt(len(yarray_zscore_snip))
                ymin_zscore_snip.append(np.min(y_zscore_snip-yerror_zscore_snip))
                ymax_zscore_snip.append(np.max(y_zscore_snip+yerror_zscore_snip))

    return ymax_dFF, ymin_dFF, ymax_zscore, ymin_zscore, ymax_zscore_snip, ymin_zscore_snip

def graphmaker_results(dictionary,testsession,graphtitle,directory_figure=directory_results_total,virus='GCaMP6',test='COP',
                      beh_list=list_beh_tdt,exclude_outliers=status_outliers,
                      sniptime_pre=presnip,sniptime_post=postsnip):  
    """
    Parameters
    ----------
    dictionary : dictionary
        Add dictionary that contains the data you want to make figures of that runs second out of result_behavior_snipper
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    graphtitle : string 
        Add the start name of the figure that is saved.
    directory_figure : directory name -> Default = directory_results_total
        Add the directory under which you want to save the figures
        e.g. directory_results_perrat, directory_results_total, directory_results_parts, directory_AUC etc
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    beh_list : list -> Default = list_beh_tdt
        Add the list with behaviors that need to be analyzed
        e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
    excluding_behaviors : string - Default = what is filled in on top of the script
        Add "exclude" if you want the delete the behaviors before which another behavior has taken place
    exclude_outliers : boolean -> Default = what is filled in on top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    sniptime_pre : integer -> Default = what you determined
        Add the amount of seconds before the start of the behavior that needs to be analyzed
    sniptime_post : integer -> Default = what you determined
        Add the amount of seconds after the start of the behavior that needs to be analyzed
    Returns
    -------
    Figures (per coptest)
    Figures of the mean of each individual rat and the mean of rats dFF signals aligned to the behaviors
    """

    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary_analysis = my_dict_process[d]

    d_auc='AUC_'+str(dictionary)
    dictionary_AUC = AUC_results_S1_GCaMP6_COP_1
    
    # Set directory for figures
    if exclude_outliers==False:
        directory_graph=directory_results
    else:
        directory_graph=directory_results_cor

    # Change directory to output folder
    if not os.path.isdir(directory_graph+directory_figure):
        os.mkdir(directory_graph+directory_figure)
    if not os.path.isdir(directory_graph+directory_figure+"/zscore"):
        os.mkdir(directory_graph+directory_figure+"/zscore")
    if not os.path.isdir(directory_graph+directory_figure+"/zscoresnips"):
        os.mkdir(directory_graph+directory_figure+"/zscoresnips")
    if not os.path.isdir(directory_graph+directory_figure+"/AUC"):
        os.mkdir(directory_graph+directory_figure+"/AUC")

    # Calculate max values of axis with calculate_axis definition
    ymax_dFF, ymin_dFF, ymax_zscore, ymin_zscore, ymax_zscore_snip, ymin_zscore_snip=calculate_axis(dictionary)

    # Get fs from dictionary of processed data
    for rat,value in dictionary_analysis.items():        
        fs=dictionary_analysis[rat]['fs']

    outs=['dFF','zscore','zscore_snip']
    aucs=['AUC_pre','AUC_post']
    
    # Make figures
    for output in outs:
        for beh_outcome in dictionary[output].keys():
            for beh in beh_list:
                if beh_outcome == 'Start %s'%beh or beh_outcome == 'End %s'%beh:
                    # Get the size of the data
                    length=dictionary[output][beh_outcome]['mean'].size
                    x = np.linspace(1, length, length)/fs - sniptime_pre

                    # Plot the data
                    if output=='dFF':
                        os.chdir(directory_graph+directory_figure)
                    elif output=='zscore':
                        os.chdir(directory_graph + directory_figure + "/zscore")
                    elif output=='zscore_snip':
                        os.chdir(directory_graph + directory_figure + "/zscoresnips")
                    sns.set_style("ticks")
                    palette = [color_GCaMP, color_shadow, color_startline]
                    # plt.rcParams['figure.dpi'] = 360
                
                    fig, ax = plt.subplots(figsize=(7, 5))
                    ax.plot(x, dictionary[output][beh_outcome]['mean'], linewidth=1.5, color=palette[0], zorder=3)
                    ax.fill_between(x, dictionary[output][beh_outcome]['mean'] - dictionary[output][beh_outcome]['sem'], dictionary[output][beh_outcome]['mean'] + dictionary[output][beh_outcome]['sem'],
                                    color=palette[1], alpha=0.4)
                    if output=='dFF':
                        ymin=np.min(ymin_dFF)
                        ymax=np.max(ymax_dFF)
                    elif output=='zscore':
                        ymin=np.min(ymin_zscore)
                        ymax=np.max(ymax_zscore)
                    elif output=='zscore_snip':
                        ymin=np.min(ymin_zscore_snip)
                        ymax=np.max(ymax_zscore_snip)
                    ax.axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--', linewidth=1, color=palette[2])
                    ax.axhline(y=0, linewidth=0.2, color=palette[2], zorder=4)
                    ax.set_ylim([ymin,ymax])
                    ax.set_xticks(np.arange(-sniptime_pre, sniptime_post+1, 10),fontsize=xaxis_fontsize)
                    if output=='dFF':
                        ax.set_yticks(np.arange(0,11,10),fontsize=yaxis_fontsize)
                        ax.text(-14,0,r'$\Delta$F/F (%)', rotation='vertical',fontsize=label_fontsize)
                    else:
                        ax.set_yticks(np.arange(0,3,2),fontsize=yaxis_fontsize)
                        ax.text(-14,0,'z-score', rotation='vertical',fontsize=label_fontsize)
                    # ax.set_title(f"{graphtitle}_{beh}_{test}{testsession}", fontsize=title_fontsize)
                    sns.despine()
                    sns.despine(ax=ax, offset=10, trim=True)
                
                    fig.tight_layout()
                    fig.savefig(f"{output}_{graphtitle}_{beh_outcome}_{test}{testsession}.png")
                    plt.close(fig)
            print(output,beh,'- Figures made')


    # Transfer AUC dictionary into a dataframe
    dict_AUC_copy=AUC_results_S1_GCaMP6_COP_1.copy()
    for auc in aucs:
        for beh in dict_AUC_copy['AUC_pre'].keys():
            del(dict_AUC_copy[auc][beh]['mean'])
            del(dict_AUC_copy[auc][beh]['sem'])
            
            list_AUC_pre=[]
            list_AUC_post=[]
            for i in dict_AUC_copy['AUC_pre'][beh]['mean_all']:
                list_AUC_pre.append(float(i))
            for i in dict_AUC_copy['AUC_post'][beh]['mean_all']:
                list_AUC_post.append(float(i))
            dict_AUC={'Pre':list_AUC_pre, 'Post':list_AUC_post}            
                
            # Convert to data frame
            df_AUC = pd.DataFrame(dict_AUC)
            df_AUC = df_AUC.reset_index()
    
            # make one column of the data with a new column for pre-post
            df_AUC_melted=pd.melt(df_AUC, id_vars =['index'],value_vars =['Pre','Post'],var_name ='AUC')
                         
            # Create figures
            ymax=np.max(df_AUC_melted['value'])
            ymin=np.min(df_AUC_melted['value'])
            
            y_max=round(ymax / 10) * 10 +10
            y_min=round(ymin / 10) * 10 +10

            os.chdir(directory_graph+directory_figure+'/AUC')
            sns.set_style("ticks")
            palette_bar = [color_AUC_bar1, color_AUC_bar2]
            palette_swarm = [color_AUC_scatter2]
            fig, ax = plt.subplots(figsize=(4, 4))
            sns.barplot(data=df_AUC_melted,x='AUC', y='value', errorbar = None,palette=palette_bar, width=0.4)
            sns.lineplot(x='AUC', y='value', hue='index', data=df_AUC_melted,palette=palette_swarm, legend=False)
            ax.set_ylabel('AUC per second',fontsize=yaxis_fontsize)
            ax.set_xlabel(None)
            ax.set_xticks(ticks=['Pre','Post'],fontsize=xaxis_fontsize)
            # ax.set_yticks(yy)
            ax.tick_params(bottom=False)          
            ax.set_ylim([y_min,y_max])
    
            sns.despine()
            sns.despine(bottom=True)
            ax.axhline(y=0, linewidth=1, color=color_startline)
            fig.tight_layout()
            fig.savefig(f"AUC_{graphtitle}_{beh}_{rat}_{test}{testsession}.png")
    
            plt.close(fig)
            
    # Change directory back
    os.chdir(directory)
    
def result_behavior_snipper_parts (series,dataframe,testsession,n_parts=3,type_parts='latency',virus='GCaMP6',test='COP',
                         beh_list=list_behaviors,excluding_behaviors=status_excluding,correction = status_correction,
                         list_relevant=list_relevant_behaviors,exclude_outliers=status_outliers,
                         sniptime_pre=presnip,sniptime_post=postsnip):
    """
    Parameters
    ----------
    series : string
        Add a string of the ejaculatory series that needs to be analyzed
        e.g. "T", "S1, or "S2""
    dataframe : DataFrame
        Add dataframe of the data you want to process
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    n_parts : float -> Default = 3
        Add the number of part
        e.g. 3 or 5
    type_parts : string -> Default ='latency'
        Add the type on which parts are divided
        e.g. 'latency' or 'frequency'
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    beh_list : list -> Default = list_behaviors
        Add the list with behaviors that need to be analyzed
        e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
    excluding_behaviors : string - Default = what is filled in on top of the script
        Add "exclude" if you want the delete the behaviors before which another behavior has taken place
    exclude_outliers : boolean -> Default = what is filled in on top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    correction : boolean -> Default is True
        Add whether or not to correct for baseline
    list_relevant: list -> Default = list_relevant_behaviors
        If you have "exclude", add a list with the behaviors that cannot happen before the behavior you explore
        Note -> if you don't exclude, just name a random list. This variable will then not be used.
    sniptime_pre : integer -> Default = what you determined above the script
        Add the amount of seconds before the start of the behavior that needs to be analyzed
    sniptime_post : integer -> Default = what you determined above the script
        Add the amount of seconds after the start of the behavior that needs to be analyzed

    Returns
    -------
    dict1: dict_of_means with all snips per rat and behavior and the mean of the these snips for rat per parts
    dict2: dict_ratmeans with all mean snips per behavior and the mean of these snips per parts.
    If correction = True: Dictionaries with the baseline-corrected mean dFF of snips before and after the behaviors per test. 
    First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
    Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
    the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
    Part of test is defined by taking the latency to 1st ejaculation or number of copulations (frequency), and divide this in 3 or 5 equal parts.
    Behaviors taken place in e.g. the 1st 1/3 of time is part 1, 2nd 1/3 of time part 2, and final 1/3 of time part 3.
    """
    
    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary = my_dict_process[d]

    if excluding_behaviors== "exclude":
        dict_beh_part=make_dict_beh_parts_excl(series,dataframe,testsession,n_parts=n_parts,type_parts=type_parts,virus=virus,test=test,
                                                list_relevant=list_relevant)
    else:        
        dict_beh_part=make_dict_beh_parts(series,dataframe,testsession,n_parts=n_parts,type_parts=type_parts,virus=virus,test=test)

    if n_parts == 3:
        parts=['part1','part2','part3']
    elif n_parts == 5:
        parts=['part1','part2','part3','part4','part5']
    outs=['dFF','zscore','zscore_snip','dFF_snips','zscore_snips','zscore_dFF_snips']
    list_behavior=[]
    stats=['mean','sem']

    # Make empty dictionary
    dict_tdt_mean = {out: {rat: {part: {} for part in parts} for rat in dictionary.keys() if rat not in list_signal_artifact_excl and rat in dict_beh_part} for out in outs}

    # Get dFF,time and fs from dictionary of processed data
    for rat,value in dictionary.items():  
        print("Start behavior_snipper_parts %s"%(rat))
        if rat not in list_signal_artifact_excl and rat in dict_beh_part.keys():
            if exclude_outliers == False:
                dFF=dictionary[rat]['dFF']
                zscore=dictionary[rat]['zscore']
                time=dictionary[rat]['time']
            else: 
                dFF=dictionary[rat]['dFF_cor']
                zscore=dictionary[rat]['zscore_cor']
                time=np.array(dictionary[rat]['time_cor'])

            fs=dictionary[rat]['fs']
            maxtime=np.max(time[-1])
        
            for out in outs:
                for part in parts:
                    for beh in beh_list:
                        if beh != BC:
                            if dict_beh_part[rat]['Start'][beh][part]:
                                # First make a continous time series of behavior events (epocs) and plot
                                BEH_on = dict_beh_part[rat]['Start'][beh][part]
                                BEH_off = dict_beh_part[rat]['End'][beh][part]
                                    
                                # Create a list of these lists for later
                                EVENTS=[BEH_on,BEH_off]
                                # Create label names that come with it
                                LABEL_EVENTS=['Start %s'%beh, 'End %s'%beh]
                            
                                # Now make snips of the data
                                PRE_TIME = sniptime_pre # number of seconds before event onset
                                POST_TIME = sniptime_post # number of seconds after
                                BASELINE_START = baseline_start
                                BASELINE_END = baseline_end
                                TRANGE = [-PRE_TIME*np.floor(fs), POST_TIME*np.floor(fs)]
                                TRANGE_BASELINE = [BASELINE_START*np.floor(fs), BASELINE_END*np.floor(fs)]
                
                                # time span for peri-event filtering, PRE and POST, in samples
                                for event,name in zip(EVENTS,LABEL_EVENTS):
                                    dFF_snips = []
                                    dFF_snips_BASELINE=[]
                                    zscore_snips = []
                                    zscore_snips_BASELINE=[]
                                    array_ind = []
                                    pre_stim = []
                                    post_stim = []
                                    pre_BASELINE= []
                                    post_BASELINE= []
                                    dFF_snips_cor=[]
                                    zscore_snips_cor=[]
                                    dFF_snips_list=[]
                                    zscore_snips_list=[]
                                
                                    for on in event:
                                        #If the event cannot include pre-time seconds before event, exclude it from the data analysis
                                        if on > PRE_TIME and on < maxtime:
                                            # find first time index after event onset
                                            array_ind.append(np.where(time > on)[0][0])
                                            # find index corresponding to pre and post stim durations
                                            pre_stim.append(array_ind[-1] + TRANGE[0])
                                            post_stim.append(array_ind[-1] + TRANGE[1])
                                            pre_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[0])
                                            post_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[1])
                                            BASELINE_dFF=dFF[int(pre_BASELINE[-1]):int(post_BASELINE[-1])]
                                            BASELINE_zscore=zscore[int(pre_BASELINE[-1]):int(post_BASELINE[-1])]
                                            mean_BASELINE_dFF=np.mean(BASELINE_dFF)
                                            mean_BASELINE_zscore=np.mean(BASELINE_zscore)
                                            dFF_snip=dFF[int(pre_stim[-1]):int(post_stim[-1])]
                                            dFF_snips_cor.append(np.subtract(dFF_snip,mean_BASELINE_zscore))
                                            dFF_snips_list.append(np.subtract(dFF_snip, 0))
                                            zscore_snip=zscore[int(pre_stim[-1]):int(post_stim[-1])]
                                            zscore_snips_cor.append(np.subtract(zscore_snip,mean_BASELINE_zscore))
                                            zscore_snips_list.append(np.subtract(zscore_snip,0))

                                    # Based on condition correct or don't correct for baseline
                                    if correction == True:
                                        dFF_snips=dFF_snips_cor
                                        zscore_snips=zscore_snips_cor
                                    else:
                                        dFF_snips=dFF_snip
                                        zscore_snips=zscore_snip
                    
                                    # Remove the snips that are shorter in size
                                    if dFF_snips:
                                        max1 = np.max([np.size(x) for x in dFF_snips])
                                        dFF_snips=[snip for snip in dFF_snips if np.size(snip)==max1]                    
                                        zscore_snips=[snip for snip in zscore_snips if np.size(snip)==max1] 

                                        # Take the mean of the snips
                                        mean_dFF_snips = np.mean(dFF_snips, axis=0)
                                        std_dFF_snips = np.std(dFF_snips, axis=0)
                
                                        mean_zscore_snips = np.mean(zscore_snips, axis=0)
                                        std_zscore_snips = np.std(zscore_snips, axis=0)
                                    
                                        zall = []
                                        for snip in dFF_snips: 
                                            zb = np.mean(snip)
                                            zsd = np.std(snip)
                                            zall.append((snip - zb)/zsd)
                                           
                                        zscore_dFF_snips = np.mean(zall, axis=0)

                                        # Put the data in the dictionaries
                                        dict_tdt_mean['dFF'][rat][part][name]=mean_dFF_snips
                                        dict_tdt_mean['zscore'][rat][part][name]=mean_zscore_snips
                                        dict_tdt_mean['zscore_snip'][rat][part][name]=zscore_dFF_snips
                                        dict_tdt_mean['dFF_snips'][rat][part][name]=dFF_snips
                                        dict_tdt_mean['zscore_snips'][rat][part][name]=zscore_snips
                                        dict_tdt_mean['zscore_dFF_snips'][rat][part][name]=zall
                                        list_behavior.append(name)

    # Make new dictorionary and fill in with the data (e.g. all dFF snips per rat per behavior per part)
    dict_of_means = {out: {part: {beh: [dict_tdt_mean[out][rat][part][beh] for rat in dict_tdt_mean[out].keys() 
                                 if beh in dict_tdt_mean[out][rat][part]] for beh in list_behavior} for part in parts} for out in outs}

    # Make empty dictionary for future output
    dict_ratmeans = {out: {part: {beh: {stat: [] for stat in stats} for beh in list_behavior} for part in parts} for out in outs}

    # Calculate the data 
    for out in outs:
        for part in parts:
            for beh in list_behavior:
                if dict_of_means['dFF'][part][beh]:
                    # Find the maximum length of snips across all lists
                    max2 = np.max([np.size(x) for x in dict_of_means['dFF'][part][beh]])
                    
                    # Filter lists to only include snips with the maximum length
                    dict_of_means[out][part][beh] = [snip for snip in dict_of_means[out][part][beh] if np.size(snip) == max2]

                    # Calculate the dFF data
                    yarray_dFF = np.array(dict_of_means['dFF'][part][beh])
                    y_dFF = np.mean(yarray_dFF, axis=0)
                    yerror_dFF = np.std(yarray_dFF, axis=0)/np.sqrt(len(yarray_dFF))
        
                    # Calculate the z-score data (determined on full data-set)
                    yarray_zscore = np.array(dict_of_means['zscore'][part][beh])
                    y_zscore = np.mean(yarray_zscore, axis=0)
                    yerror_zscore = np.std(yarray_zscore, axis=0)/np.sqrt(len(yarray_zscore))
     
                    # Calculate the new z-score from the dFF of the snips only
                    yarray_zscore_snip = np.array(dict_of_means['zscore_snip'][part][beh])
                    y_zscore_snip = np.mean(yarray_zscore_snip, axis=0)
                    yerror_zscore_snip = np.std(yarray_zscore_snip, axis=0)/np.sqrt(len(yarray_zscore_snip))
    
                    # Put the data in the dictionaries
                    dict_ratmeans['dFF'][part][beh]['mean']=y_dFF
                    dict_ratmeans['dFF'][part][beh]['sem']=yerror_dFF
                    dict_ratmeans['zscore'][part][beh]['mean']=y_zscore
                    dict_ratmeans['zscore'][part][beh]['sem']=yerror_zscore
                    dict_ratmeans['zscore_snip'][part][beh]['mean']=y_zscore_snip
                    dict_ratmeans['zscore_snip'][part][beh]['sem']=yerror_zscore_snip
                    dict_ratmeans['dFF_snips'][part][beh]=dict_of_means['dFF'][part][beh]
                    dict_ratmeans['zscore_snips'][part][beh]=dict_of_means['zscore'][part][beh]
                    dict_ratmeans['zscore_dFF_snips'][part][beh]=dict_of_means['zscore_snips'][part][beh]

    print("result_behavior_snipper_part done")
    return dict_tdt_mean,dict_ratmeans
        

def find_level(dictionary):
    """
    Finds the level of nesting in dictionary

    Parameters
    ----------
    dictionary : dictionary
        Fill in dictionary for which you want to know the number of levels in nesting

    Returns
    -------
    The number of levels. E.g. 4 means 3 keys and 1 value.

    """
    if isinstance(dictionary, dict):
        return 1 + max(find_level(v) for v in dictionary.values())
    else:
        return 0

def calculate_axis(dict_ratmeans):
    """
    Works only in other definition!
    
    Parameters
    ----------
    dict_of_means : dictionaru
        Dict_of_means is the dictionary that runs out second from the result_behavior_snipper or result_behavior_part_snipper
        Make sure to fill in the

    Returns
    -------
    Maximum and minimal Y values for dFF, z-score and z-score snip figures

    """
    ymax_dFF = []
    ymin_dFF = []
    ymax_zscore = []
    ymin_zscore = []
    ymax_zscore_snip = []
    ymin_zscore_snip = []

    level=find_level(dict_ratmeans)
    if level == 3:
        for beh in dict_ratmeans['dFF_snips'].keys():
            if dict_ratmeans['dFF_snips'][beh]:
                # Calculate dFF data
                yarray_dFF = np.array(dict_ratmeans['dFF_snips'][beh])
                y_dFF = np.mean(yarray_dFF, axis=0)
                yerror_dFF = np.std(yarray_dFF, axis=0)/np.sqrt(len(yarray_dFF))
                ymin_dFF.append(np.min(y_dFF-yerror_dFF))
                ymax_dFF.append(np.max(y_dFF+yerror_dFF))

                # Calculate z-score data
                yarray_zscore = np.array(dict_ratmeans['zscore_snips'][beh])
                y_zscore = np.mean(yarray_zscore, axis=0)
                yerror_zscore = np.std(yarray_zscore, axis=0)/np.sqrt(len(yarray_zscore))
                ymin_zscore.append(np.min(y_zscore-yerror_zscore))
                ymax_zscore.append(np.max(y_zscore+yerror_zscore))

                # Calculate z-score data from snips only
                yarray_zscore_snip = np.array(dict_ratmeans['zscore_dFF_snips'][beh])
                y_zscore_snip = np.mean(yarray_zscore_snip, axis=0)
                yerror_zscore_snip = np.std(yarray_zscore_snip, axis=0)/np.sqrt(len(yarray_zscore_snip))
                ymin_zscore_snip.append(np.min(y_zscore_snip-yerror_zscore_snip))
                ymax_zscore_snip.append(np.max(y_zscore_snip+yerror_zscore_snip))

    elif level == 4:
        parts = dict_ratmeans['dFF_snips'].keys()        
        for part in parts:
            for beh in dict_ratmeans['dFF_snips'][part].keys():
                if dict_ratmeans['dFF_snips'][part][beh]:
                    # Calculate dFF data
                    yarray_dFF = np.array(dict_ratmeans['dFF_snips'][part][beh])
                    if yarray_dFF.size > 1:
                        y_dFF = np.mean(yarray_dFF, axis=0) 
                        yerror_dFF = np.std(yarray_dFF, axis=0)/np.sqrt(len(yarray_dFF))
                        ymin_dFF.append(np.min(y_dFF-yerror_dFF))
                        ymax_dFF.append(np.max(y_dFF+yerror_dFF))
                    else:
                        pass            
    
                    # Calculate z-score data
                    yarray_zscore = np.array(dict_ratmeans['zscore_snips'][part][beh])
                    if yarray_zscore.size > 1:
                        y_zscore = np.mean(yarray_zscore, axis=0)
                        yerror_zscore = np.std(yarray_zscore, axis=0)/np.sqrt(len(yarray_zscore))
                        ymin_zscore.append(np.min(y_zscore-yerror_zscore)) 
                        ymax_zscore.append(np.max(y_zscore+yerror_zscore)) 
                    else:
                        pass            
    
                    # Calculate z-score data from snips only
                    yarray_zscore_snip = np.array(dict_ratmeans['zscore_dFF_snips'][part][beh])
                    if yarray_zscore_snip.size > 1:
                        y_zscore_snip = np.mean(yarray_zscore_snip, axis=0)
                        yerror_zscore_snip = np.std(yarray_zscore_snip, axis=0)/np.sqrt(len(yarray_zscore_snip))
                        ymin_zscore_snip.append(np.min(y_zscore_snip-yerror_zscore_snip))
                        ymax_zscore_snip.append(np.max(y_zscore_snip+yerror_zscore_snip))
                    else:
                        pass            

    # Remove all NaN values from the list
    ymax_dFF = list(filter(lambda x: not math.isnan(x), ymax_dFF))
    ymin_dFF = list(filter(lambda x: not math.isnan(x), ymin_dFF))
    ymax_zscore = list(filter(lambda x: not math.isnan(x), ymax_zscore))
    ymin_zscore = list(filter(lambda x: not math.isnan(x), ymin_zscore))
    ymax_zscore_snip = list(filter(lambda x: not math.isnan(x), ymax_zscore_snip))
    ymin_zscore_snip = list(filter(lambda x: not math.isnan(x), ymin_zscore_snip))
    
    print('axis values determined')
    return ymax_dFF, ymin_dFF, ymax_zscore, ymin_zscore, ymax_zscore_snip, ymin_zscore_snip

def graphmaker_results_parts(dictionary,testsession,graphtitle,directory_figure=directory_results_parts,
                     n_parts=3,type_parts='latency',virus='GCaMP6',test='COP',
                     beh_list=list_behaviors,exclude_outliers=status_outliers,
                     sniptime_pre=presnip,sniptime_post=postsnip):  
    """
    NOTE: GRAPHS FOR FREQUENCY GIVES ERROR, BUT STILL RUNS 
    
    Parameters
    ----------
    dictionary : dictionary
        Add dictionary that contains the data you want to make figures of
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    graphtitle : string 
        Add the start name of the figure that is saved.
    directory_figure : directory name
        Add the directory under which you want to save the figures
        e.g. directory_results_parts, directory_results_perrat, directory_results_total, directory_AUC etc
    n_parts : float -> Default = 3
        Add the number of part
        e.g. 3 or 5
    type_parts : string -> Default ='latency'
        Add the type on which parts are divided
        e.g. 'latency' or 'frequency'
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    test : string -> Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    beh_list : list -> Default = list_behaviors
        Add the list with behaviors that need to be analyzed
        e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
    excluding_behaviors : string - Default = what is filled in on top of the script
        Add "exclude" if you want the delete the behaviors before which another behavior has taken place
    exclude_outliers : boolean -> Default = what is filled in on top of the script
        Add whether or not the dFF/zscore need to be corrected by taking out outliers in signals (e.g. when fiber needs to be re-adjusted)
        False = no corrections, True = corrections
    sniptime_pre : integer -> Default = 10
        Add the amount of seconds before the start of the behavior that needs to be analyzed
    sniptime_post : integer -> Default = 10
        Add the amount of seconds after the start of the behavior that needs to be analyzed

    Returns
    -------
    Figures (per rat per coptest)
    Figures of individual behavioral snip and the mean of snips dFF signals aligned to the behaviors
    """

    d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
    for key,dicts in my_dict_process.items():
        dictionary_analysis = my_dict_process[d]

    # Set directory for figures
    if exclude_outliers==False:
        directory_graph=directory_results
    else:
        directory_graph=directory_results_cor

    # Change directory to output folder
    if not os.path.isdir(directory_graph+directory_figure):
        os.mkdir(directory_graph+directory_figure)
    if not os.path.isdir(directory_graph+directory_figure+"/zscore"):
        os.mkdir(directory_graph+directory_figure+"/zscore")
    if not os.path.isdir(directory_graph+directory_figure+"/zscoresnips"):
        os.mkdir(directory_graph+directory_figure+"/zscoresnips")

    # Calculate max values of axis with calculate_axis definition
    ymax_dFF, ymin_dFF, ymax_zscore, ymin_zscore, ymax_zscore_snip, ymin_zscore_snip=calculate_axis(dictionary)

    # Get fs from dictionary of processed data
    for rat,value in dictionary_analysis.items():        
        fs=dictionary_analysis[rat]['fs']
    
    outs=['dFF','zscore','zscore_snip']

    # Make figures
    for output in outs:
        for beh_outcome in dictionary[output]['part1'].keys():
            for beh in beh_list:
                if beh_outcome == 'Start %s'%beh or beh_outcome == 'End %s'%beh and beh != BC and beh!=BD:
                    length=len(list(dictionary['dFF']['part1'][beh_outcome]['mean']))
                    x = np.linspace(1, length, length)/fs - sniptime_pre

                    try:
                        # Make figure dFF
                        if output=='dFF':
                            os.chdir(directory_graph+directory_figure)
                        elif output=='zscore':
                            os.chdir(directory_graph + directory_figure + "/zscore")
                        elif output=='zscore_snip':
                            os.chdir(directory_graph + directory_figure + "/zscoresnips")
                            
                        if output=='dFF':
                            ymin=np.min(ymin_dFF)
                            ymax=np.max(ymax_dFF)
                        elif output=='zscore':
                            ymin=np.min(ymin_zscore)
                            ymax=np.max(ymax_zscore)
                        elif output=='zscore_snip':
                            ymin=np.min(ymin_zscore_snip)
                            ymax=np.max(ymax_zscore_snip)

                        sns.set_style("ticks")
                        if n_parts==3:
                            fig, ax = plt.subplots(1,3, figsize=(12,4), sharex=True, sharey=True)
                        elif n_parts==5:
                            fig, ax = plt.subplots(1,5, figsize=(24,6), sharex=True, sharey=True)
                        # plt.rcParams['figure.dpi'] = 360

                        ax[0].plot(x, dictionary[output]['part1'][beh_outcome]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
                        ax[0].fill_between(x, dictionary[output]['part1'][beh_outcome]['mean']-dictionary[output]['part1'][beh_outcome]['sem'], 
                                              dictionary[output]['part1'][beh_outcome]['mean']+dictionary[output]['part1'][beh_outcome]['sem'], color=color_shadow, alpha=0.4)
                        ax[0].set_xticks(np.arange(-sniptime_pre, sniptime_post+1, 10),fontsize=xaxis_fontsize)
                        if output=='dFF':
                            ax[0].set_yticks(np.arange(0,11,10),fontsize=yaxis_fontsize)
                            ax[0].text(-16,0,r'$\Delta$F/F (%)', rotation='vertical',fontsize=label_fontsize)
                        else:
                            ax[0].set_yticks(np.arange(0,3,2),fontsize=yaxis_fontsize)
                            ax[0].text(-15,0,'z-score', rotation='vertical',fontsize=label_fontsize)
                        ax[0].set_title("Part 1",fontsize=subtitle_fontsize)
                        ax[0].axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--', linewidth=1, color=color_startline)
                        ax[0].axhline(y=0, linewidth=0.2, color=color_startline, zorder=4)
                        ax[0].set_ylim([ymin,ymax])

                        ax[1].plot(x, dictionary[output]['part2'][beh_outcome]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
                        ax[1].fill_between(x, dictionary[output]['part2'][beh_outcome]['mean']-dictionary[output]['part2'][beh_outcome]['sem'], 
                                              dictionary[output]['part2'][beh_outcome]['mean']+dictionary[output]['part2'][beh_outcome]['sem'], color=color_shadow, alpha=0.4)
                        ax[1].yaxis.set_visible(False)                
                        ax[1].xaxis.set_visible(False)                
                        ax[1].tick_params(left=False,bottom=False)          
                        ax[1].set_title("Part 2",fontsize=subtitle_fontsize)
                        ax[1].axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--',linewidth=1, color=color_startline)
                        ax[1].axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)

                        ax[2].plot(x, dictionary[output]['part3'][beh_outcome]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
                        ax[2].fill_between(x, dictionary[output]['part3'][beh_outcome]['mean']-dictionary[output]['part3'][beh_outcome]['sem'], 
                                              dictionary[output]['part3'][beh_outcome]['mean']+dictionary[output]['part3'][beh_outcome]['sem'], color=color_shadow, alpha=0.4)
                        ax[2].yaxis.set_visible(False)                
                        ax[2].xaxis.set_visible(False)                
                        ax[2].tick_params(left=False,bottom=False)          
                        ax[2].set_title("Part 3",fontsize=subtitle_fontsize)
                        ax[2].axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--',linewidth=1, color=color_startline)
                        ax[2].axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)

                        if n_parts==3:
                            sns.despine()
                            sns.despine(ax=ax[0], offset=10, trim=True)
                            sns.despine(ax=ax[1], left=True, right=True, bottom=True)
                            sns.despine(ax=ax[2], left=True, right=True, bottom=True)
                            fig.tight_layout()
                            fig.savefig(f"{output}_{graphtitle}_{n_parts}{type_parts}_{beh_outcome}_{test}{testsession}.png")
                            plt.close(fig)
                            print(beh_outcome,n_parts,type_parts,output,'dFF figure made')

                        elif n_parts==5:
                            ax[3].plot(x, dictionary[output]['part4'][beh_outcome]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
                            ax[3].fill_between(x, dictionary[output]['part4'][beh_outcome]['mean']-dictionary[output]['part4'][beh_outcome]['sem'], 
                                                  dictionary[output]['part4'][beh_outcome]['mean']+dictionary[output]['part4'][beh_outcome]['sem'], color=color_shadow, alpha=0.4)
                            ax[3].yaxis.set_visible(False)                
                            ax[3].xaxis.set_visible(False)                
                            ax[3].tick_params(left=False,bottom=False)          
                            ax[3].set_title("Part 4",fontsize=subtitle_fontsize)
                            ax[3].axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--',linewidth=1, color=color_startline)
                            ax[3].axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)

                            ax[4].plot(x, dictionary[output]['part5'][beh_outcome]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
                            ax[4].fill_between(x, dictionary[output]['part5'][beh_outcome]['mean']-dictionary[output]['part5'][beh_outcome]['sem'], 
                                                  dictionary[output]['part5'][beh_outcome]['mean']+dictionary[output]['part5'][beh_outcome]['sem'], color=color_shadow, alpha=0.4)
                            ax[4].yaxis.set_visible(False)                
                            ax[4].xaxis.set_visible(False)                
                            ax[4].tick_params(left=False,bottom=False)          
                            ax[4].set_title("Part 5",fontsize=subtitle_fontsize)
                            ax[4].axvline(x=0, ymin=ymin, ymax=ymax, linestyle='--',linewidth=1, color=color_startline)
                            ax[4].axhline(y=0, linewidth=0.2, color=color_startline,zorder=4)
                    
                            sns.despine()
                            sns.despine(ax=ax[0], offset=10, trim=True)
                            sns.despine(ax=ax[1], left=True, right=True, bottom=True)
                            sns.despine(ax=ax[2], left=True, right=True, bottom=True)
                            sns.despine(ax=ax[3], left=True, right=True, bottom=True)
                            sns.despine(ax=ax[4], left=True, right=True, bottom=True)
                            fig.tight_layout()
                            fig.savefig(f"{output}_{graphtitle}_{n_parts}{type_parts}_{beh_outcome}_{test}{testsession}.png")
                            plt.close(fig)
                            print(beh_outcome,n_parts,type_parts,output,'figure parts made')
                    except:
                        print("no parts for ",n_parts,type_parts,beh, output)
 
    # Change directory back
    os.chdir(directory)

################################################################################################################
################################################################################################################
########### DATA ANALYSIS  #####################################################################################
################################################################################################################
################################################################################################################

# Get results of result behavior snipper
S1_GCaMP6_COP_1,results_S1_GCaMP6_COP_1,AUC_S1_GCaMP6_COP_1,AUC_results_S1_GCaMP6_COP_1=result_behavior_snipper (data_S1,1)
S1_GCaMP6_COP_2,results_S1_GCaMP6_COP_2,AUC_S1_GCaMP6_COP_2,AUC_results_S1_GCaMP6_COP_2=result_behavior_snipper (data_S1,2)
S1_GCaMP6_COP_3,results_S1_GCaMP6_COP_3,AUC_S1_GCaMP6_COP_3,AUC_results_S1_GCaMP6_COP_3=result_behavior_snipper (data_S1,3)
S1_GCaMP6_COP_4,results_S1_GCaMP6_COP_4,AUC_S1_GCaMP6_COP_4,AUC_results_S1_GCaMP6_COP_4=result_behavior_snipper (data_S1,4)
S1_GCaMP6_COP_5,results_S1_GCaMP6_COP_5,AUC_S1_GCaMP6_COP_5,AUC_results_S1_GCaMP6_COP_5=result_behavior_snipper (data_S1,5)
S1_GCaMP6_COP_6,results_S1_GCaMP6_COP_6,AUC_S1_GCaMP6_COP_6,AUC_results_S1_GCaMP6_COP_6=result_behavior_snipper (data_S1,6)
S1_GCaMP6_COP_7,results_S1_GCaMP6_COP_7,AUC_S1_GCaMP6_COP_7,AUC_results_S1_GCaMP6_COP_7=result_behavior_snipper (data_S1,7)

# Get results of result behavior snipper per 3 parts based on latency
S1_GCaMP6_COP_1_3L,results_S1_GCaMP6_COP_1_3L=result_behavior_snipper_parts ('S1',data_S1,1)
S1_GCaMP6_COP_2_3L,results_S1_GCaMP6_COP_2_3L=result_behavior_snipper_parts ('S1',data_S1,2)
S1_GCaMP6_COP_3_3L,results_S1_GCaMP6_COP_3_3L=result_behavior_snipper_parts ('S1',data_S1,3)
S1_GCaMP6_COP_4_3L,results_S1_GCaMP6_COP_4_3L=result_behavior_snipper_parts ('S1',data_S1,4)
S1_GCaMP6_COP_5_3L,results_S1_GCaMP6_COP_5_3L=result_behavior_snipper_parts ('S1',data_S1,5)
S1_GCaMP6_COP_6_3L,results_S1_GCaMP6_COP_6_3L=result_behavior_snipper_parts ('S1',data_S1,6)
S1_GCaMP6_COP_7_3L,results_S1_GCaMP6_COP_7_3L=result_behavior_snipper_parts ('S1',data_S1,7)

# Get results of result behavior snipper per 3 parts based on frequency
S1_GCaMP6_COP_1_3F,results_S1_GCaMP6_COP_1_3F=result_behavior_snipper_parts ('S1',data_S1,1,type_parts='frequency')
S1_GCaMP6_COP_2_3F,results_S1_GCaMP6_COP_2_3F=result_behavior_snipper_parts ('S1',data_S1,2,type_parts='frequency')
S1_GCaMP6_COP_3_3F,results_S1_GCaMP6_COP_3_3F=result_behavior_snipper_parts ('S1',data_S1,3,type_parts='frequency')
S1_GCaMP6_COP_4_3F,results_S1_GCaMP6_COP_4_3F=result_behavior_snipper_parts ('S1',data_S1,4,type_parts='frequency')
S1_GCaMP6_COP_5_3F,results_S1_GCaMP6_COP_5_3F=result_behavior_snipper_parts ('S1',data_S1,5,type_parts='frequency')
S1_GCaMP6_COP_6_3F,results_S1_GCaMP6_COP_6_3F=result_behavior_snipper_parts ('S1',data_S1,6,type_parts='frequency')
S1_GCaMP6_COP_7_3F,results_S1_GCaMP6_COP_7_3F=result_behavior_snipper_parts ('S1',data_S1,7,type_parts='frequency')

# Get results of result behavior snipper per 5 parts based on latency
S1_GCaMP6_COP_1_5L,results_S1_GCaMP6_COP_1_5L=result_behavior_snipper_parts ('S1',data_S1,1,n_parts=5)
S1_GCaMP6_COP_2_5L,results_S1_GCaMP6_COP_2_5L=result_behavior_snipper_parts ('S1',data_S1,2,n_parts=5)
S1_GCaMP6_COP_3_5L,results_S1_GCaMP6_COP_3_5L=result_behavior_snipper_parts ('S1',data_S1,3,n_parts=5)
S1_GCaMP6_COP_4_5L,results_S1_GCaMP6_COP_4_5L=result_behavior_snipper_parts ('S1',data_S1,4,n_parts=5)
S1_GCaMP6_COP_5_5L,results_S1_GCaMP6_COP_5_5L=result_behavior_snipper_parts ('S1',data_S1,5,n_parts=5)
S1_GCaMP6_COP_6_5L,results_S1_GCaMP6_COP_6_5L=result_behavior_snipper_parts ('S1',data_S1,6,n_parts=5)
S1_GCaMP6_COP_7_5L,results_S1_GCaMP6_COP_7_5L=result_behavior_snipper_parts ('S1',data_S1,7,n_parts=5)

# Get results of result behavior snipper per 5 parts based on frequency
S1_GCaMP6_COP_1_5F,results_S1_GCaMP6_COP_1_5F=result_behavior_snipper_parts ('S1',data_S1,1,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_2_5F,results_S1_GCaMP6_COP_2_5F=result_behavior_snipper_parts ('S1',data_S1,2,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_3_5F,results_S1_GCaMP6_COP_3_5F=result_behavior_snipper_parts ('S1',data_S1,3,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_4_5F,results_S1_GCaMP6_COP_4_5F=result_behavior_snipper_parts ('S1',data_S1,4,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_5_5F,results_S1_GCaMP6_COP_5_5F=result_behavior_snipper_parts ('S1',data_S1,5,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_6_5F,results_S1_GCaMP6_COP_6_5F=result_behavior_snipper_parts ('S1',data_S1,6,n_parts=5,type_parts='frequency')
S1_GCaMP6_COP_7_5F,results_S1_GCaMP6_COP_7_5F=result_behavior_snipper_parts ('S1',data_S1,7,n_parts=5,type_parts='frequency')

#########################################################################################################
############     MAKE FIGURES    ########################################################################
#########################################################################################################
dict_results_S1={1:results_S1_GCaMP6_COP_1,2:results_S1_GCaMP6_COP_2,3:results_S1_GCaMP6_COP_3,4:results_S1_GCaMP6_COP_4,
              5:results_S1_GCaMP6_COP_5,6:results_S1_GCaMP6_COP_6,7:results_S1_GCaMP6_COP_7}

dict_results_S1_3L={1:results_S1_GCaMP6_COP_1_3L,2:results_S1_GCaMP6_COP_2_3L,3:results_S1_GCaMP6_COP_3_3L,4:results_S1_GCaMP6_COP_4_3L,
              5:results_S1_GCaMP6_COP_5_3L,6:results_S1_GCaMP6_COP_6_3L,7:results_S1_GCaMP6_COP_7_3L}

dict_results_S1_5L={1:results_S1_GCaMP6_COP_1_5L,2:results_S1_GCaMP6_COP_2_5L,3:results_S1_GCaMP6_COP_3_5L,4:results_S1_GCaMP6_COP_4_5L,
              5:results_S1_GCaMP6_COP_5_5L,6:results_S1_GCaMP6_COP_6_5L,7:results_S1_GCaMP6_COP_7_5L}

dict_results_S1_3F={1:results_S1_GCaMP6_COP_1_3F,2:results_S1_GCaMP6_COP_2_3F,3:results_S1_GCaMP6_COP_3_3F,4:results_S1_GCaMP6_COP_4_3F,
              5:results_S1_GCaMP6_COP_5_3F,6:results_S1_GCaMP6_COP_6_3F,7:results_S1_GCaMP6_COP_7_3F}

dict_results_S1_5F={1:results_S1_GCaMP6_COP_1_5F,2:results_S1_GCaMP6_COP_2_5F,3:results_S1_GCaMP6_COP_3_5F,4:results_S1_GCaMP6_COP_4_5F,
              5:results_S1_GCaMP6_COP_5_5F,6:results_S1_GCaMP6_COP_6_5F,7:results_S1_GCaMP6_COP_7_5F}

# for testsession,dictionary in dict_results_S1.items(): 
#     graphmaker_results(dictionary,testsession,graphtitle='S1')  
    
# for testsession,dictionary in dict_results_S1_3L.items(): 
#     graphmaker_results_parts(dictionary,testsession,graphtitle="S1")

# for testsession,dictionary in dict_results_S1_3F.items(): 
#     graphmaker_results_parts(dictionary,testsession,graphtitle="S1",type_parts='frequency')

# for testsession,dictionary in dict_results_S1_5L.items(): 
#     graphmaker_results_parts(dictionary,testsession,graphtitle="S1",n_parts=5)

# for testsession,dictionary in dict_results_S1_5F.items(): 
#     graphmaker_results_parts(dictionary,testsession,graphtitle="S1",n_parts=5,type_parts='frequency')

#####################################################################################
#####################################################################################

# ################# AUC per second for period from previous copulation to this one ##################################
# # Make a definition for the AUC of behavior snips
# def AUC_pretime_snipper(dataframe,testsession,virus='GCaMP6',test='COP',beh_list=list_sex_MB,
#                          excluding_behaviors=status_excluding,list_relevant=list_relevant_behaviors):
#     """
#     Note -> If you get an error, check the dictionary used for fs
    
#     Parameters
#     ----------
#     dataframe : DataFrame
#         Add dataframe of the data you want to process
#         e.g. data_T, data_B, data_S1, data_S2, data_S3
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     virus : string -> Default = 'GCaMP6'
#         Add which virus you want to analyze 
#         e.g. "GCaMP6" or "GFP"
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     beh_list : list -> Default = list_sex_MB
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     excluding_behaviors : string - Default = 'exclude'
#         Add "exclude" if you want the delete the behaviors before which another behavior has taken place
#     list_relevant: list -> Default = list_relevant_behaviors
#         If you have "exclude", add a list with the behaviors that cannot happen before the behavior you explore
#         Note -> if you don't exclude, just name a random list. This variable will then not be used.

#     Returns
#     -------
#     Dictionary (per rat and coptest)
#     Dictionary with AUC of the corrected dFF of snips before and after the behaviors per rat and per test.
#     No correction to baseline is performed    
#     """

#     d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
#     for key,dicts in my_dict_process.items():
#         dictionary_analysis = my_dict_process[d]

#     if excluding_behaviors== "exclude":
#         dict_start_beh=make_dict_start_behavior_excl(dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#         dict_end_beh=make_dict_end_behavior_excl(dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#     else:        
#         dict_start_beh=make_dict_start_behavior(dataframe,testsession,virus=virus,test=test)
#         dict_end_beh=make_dict_end_behavior(dataframe,testsession,virus=virus,test=test)

#     # Make empty dictionaries
#     dict_tdt_AUC={}
#     list_AUC=['AUC_pre','AUC_post']
#     for i in list_AUC:
#         dict_tdt_AUC[i]={}
#         for rat,value in dictionary_analysis.items():  
#             for beh in beh_list:
#                 # Only continue if the dictionairy contains numbers of events:
#                 if dict_start_beh[rat][beh]:
#                     dict_tdt_AUC[i][beh]={}
#                     dict_tdt_AUC[i][beh][rat]=[]
    

#     # Get dFF,time and fs from dictionary of processed data
#     for rat,value in dictionary_analysis.items():  
#         print("Start AUC_behavior_snipper %s"%(rat))
#         dFF=dictionary_analysis[rat]['dFF']
#         fs=dictionary_analysis[rat]['fs']
#         zscore=dictionary_analysis[rat]['zscore']
#         time=dictionary_analysis[rat]['time']
#         delay=dictionary_analysis[rat]['START_on'] # -> + delay als pretime is used

#         for beh in beh_list:
#             # Only continue if the dictionairy contains numbers of events:
#             if dict_start_beh[rat][beh]:
#                 # First make a continous time series of behavior events (epocs) and plot
#                 BEH_on = dict_start_beh[rat][beh]
                
#                 # Get the time of the previous copulation
#                 if 'Mount' in beh:
#                     time_start= my_dict_behavior['dict_MIE'][rat]['Mount']['Time']+delay
#                     time_previous= my_dict_behavior['dict_MIE'][rat]['Mount']['Previous_MIE_time']+delay
#                     pretime= my_dict_behavior['dict_MIE'][rat]['Mount']['Pretime']
#                 elif 'Intromission' in beh:
#                     time_start= my_dict_behavior['dict_MIE'][rat]['Intromission']['Time']+delay
#                     time_previous= my_dict_behavior['dict_MIE'][rat]['Intromission']['Previous_MIE_time']+delay
#                     pretime= my_dict_behavior['dict_MIE'][rat]['Intromission']['Pretime']
#                 elif 'Ejaculation' in beh:
#                     time_start= my_dict_behavior['dict_MIE'][rat]['Ejaculation']['Time']+delay
#                     time_previous= my_dict_behavior['dict_MIE'][rat]['Ejaculation']['Previous_MIE_time']+delay
#                     pretime= my_dict_behavior['dict_MIE'][rat]['Ejaculation']['Pretime']
                
#                 for on in BEH_on:
#                     for b,c,d in zip(time_start,time_previous,pretime):
#                         if on==b:
#                             TRANGE = [c*np.floor(fs), b*np.floor(fs)]

#                             # time span for peri-event filtering, PRE and POST, in samples
#                             array_ind = []
#                             pre_stim = []
#                             start_stim = []
#                             dFF_snips_pre=[]
                        
#                             AUC_dFF_snips=[]
                    
#                             # find first time index after event onset
#                             array_ind.append(np.where(time > on)[0][0])
#                             # find index corresponding to pre and post stim durations
#                             pre_stim.append(array_ind[-1] + TRANGE[0])
#                             start_stim.append(array_ind[-1] + TRANGE[-1])
                            
#                             dFF_snips_pre.append(dFF[int(pre_stim[-1]):int(start_stim[-1])])
                            
#                         # Remove the snips that are shorter in size
#                         max1 = np.max([np.size(x) for x in dFF_snips_pre])
        
#                         dFF_snips_pre=[snip for snip in dFF_snips_pre if np.size(snip)==max1]                    
            
#                         # Calculate AUC
#                         AUC_pre=[trapz(snip) for snip in dFF_snips_pre]             
        
#                         AUC_dFF_snips.append(AUC_pre)
                        
#                         mean_pre=np.nanmean(AUC_dFF_snips, axis=1)/d # Corrected per second
        
#                         # Put the data in the dictionaries
#                         dict_tdt_AUC['AUC_pre'][beh][rat]=mean_pre
                    
#     print("AUC_behavior_snipper done")
#     return dict_tdt_AUC

# # Make a definition for the mean behavior snips per rat
# def AUC_result_pretime_snipper (testsession,test='COP',graphtitle=None):
#     """
#     Parameters
#     ----------
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.

#     Returns
#     -------
#     Dictionary & Figures (AUC means per coptest)
#     Dictionary with the baseline-corrected AUC of mean dFF of snips before and after the behaviors per test. 
#     First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     From this the AUC was calculated. No correction to baseline is performed
#     Figures of the AUC mean dFF signals before and after the behaviors, plus sem.
#     """
    
#     print("Start AUC_result_behavior_snipper")

#     dict_AUC_S1="AUC_S1_"+test+"_"+str(testsession)+"pretime"  
#     dict_AUC_S2="AUC_S2_"+test+"_"+str(testsession)+"pretime"    
#     dict_AUC_T="AUC_T_"+test+"_"+str(testsession)+"pretime"  

#     dictionary_S1= eval(dict_AUC_S1)
#     dictionary_S2= eval(dict_AUC_S2)
#     dictionary_T= eval(dict_AUC_T)

#     dictionary_S1
#     dictionary_S2
#     dictionary_T

#     list_series=['S1','S2','T']
#     list_AUC=['AUC_pre','AUC_post'] # Keeping post just in case I want it in the future
    
#     dict_AUC_means={}
#     dict_AUC_ratmeans={}
#     for d in list_series:
#         dict_AUC_means[d]={}
#         dict_AUC_ratmeans[d]={}

#         for moment in list_AUC:
#             dict_AUC_means[d][moment]={}
#             dict_AUC_ratmeans[d][moment]={}

#             for moments,behaviors in dictionary_S1.items():
#                 for beh,ids in behaviors.items():
#                     dict_AUC_ratmeans[d][moment][beh]=[]
#                     dict_AUC_means[d][moment][beh]=[]
    
#     # Fill dictionary
#     for moment,behavior in dictionary_S1.items():
#         if moment == 'AUC_pre':
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['S1']['AUC_pre'][beh]=list_value
#                 dict_AUC_ratmeans['S1']['AUC_pre'][beh]=np.nanmean(list_value)
#         else:
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['S1']['AUC_post'][beh]=list_value
#                 dict_AUC_ratmeans['S1']['AUC_post'][beh]=np.nanmean(list_value)

#     for moment,behavior in dictionary_S2.items():
#         if moment == 'AUC_pre':
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['S2']['AUC_pre'][beh]=list_value
#                 dict_AUC_ratmeans['S2']['AUC_pre'][beh]=np.nanmean(list_value)
#         else:
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['S2']['AUC_post'][beh]=list_value
#                 dict_AUC_ratmeans['S2']['AUC_post'][beh]=np.nanmean(list_value)

#     for moment,behavior in dictionary_T.items():
#         if moment == 'AUC_pre':
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['T']['AUC_pre'][beh]=list_value
#                 dict_AUC_ratmeans['T']['AUC_pre'][beh]=np.nanmean(list_value)
#         else:
#             for beh,values in behavior.items():
#                 list_value=[]
#                 for rat, value in values.items():
#                     for v in value:
#                         list_value.append(v)
#                 dict_AUC_means['T']['AUC_post'][beh]=list_value
#                 dict_AUC_ratmeans['T']['AUC_post'][beh]=np.nanmean(list_value)

#     # Make a barplot
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_AUC):
#             os.mkdir(directory_TDT_AUC)

#         for moments,behaviors in dictionary_S1.items():
#             for beh,ids in behaviors.items():

#                 # Plot the data in bar charts with individual datapoints
#                 # Set position of bar on X axis - MAKE SURE IT MATCHES YOUR NUMBER OF GROUPS
#                 # set width of bar
#                 os.chdir(directory_TDT_AUC)
#                 sns.set(style="ticks", rc=custom_params)
#                 barWidth = 0.6
#                 x1 = ['Mount']
#                 x2 = ['Intromission']
#                 x3 = ['Ejaculation']
#                 x1_scatter1=len(dict_AUC_means['S1']['AUC_pre']['Mount'])
#                 x1_scatter2=len(dict_AUC_means['S1']['AUC_pre']['Intromission'])
#                 x1_scatter3=len(dict_AUC_means['S1']['AUC_pre']['Ejaculation'])

#                 x2_scatter1=len(dict_AUC_means['S2']['AUC_pre']['Mount'])
#                 x2_scatter2=len(dict_AUC_means['S2']['AUC_pre']['Intromission'])
#                 x2_scatter3=len(dict_AUC_means['S2']['AUC_pre']['Ejaculation'])

#                 x3_scatter1=len(dict_AUC_means['T']['AUC_pre']['Mount'])
#                 x3_scatter2=len(dict_AUC_means['T']['AUC_pre']['Intromission'])
#                 x3_scatter3=len(dict_AUC_means['T']['AUC_pre']['Ejaculation'])
                
#                 fig, axs = plt.subplots(1,3, figsize=(8,4), sharex=True, sharey=True)
        
#                 axs[0].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['Mount'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[0].scatter(x1_scatter1*x1, dict_AUC_means['S1']['AUC_pre']['Mount'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[0].bar(x2, dict_AUC_ratmeans['S1']['AUC_pre']['Intromission'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[0].scatter(x1_scatter2*x1, dict_AUC_means['S1']['AUC_pre']['Intromission'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[0].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['Ejaculation'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[0].scatter(x1_scatter3*x3, dict_AUC_means['S1']['AUC_post']['Ejaculation'],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[0].set_title('First series')
#                 axs[0].set_ylabel('AUC')
#                 # Plotting the zero line
#                 axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                 axs[1].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['Mount'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[1].scatter(x2_scatter1*x1, dict_AUC_means['S2']['AUC_pre']['Mount'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[1].bar(x2, dict_AUC_ratmeans['S2']['AUC_pre']['Intromission'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[1].scatter(x2_scatter2*x1, dict_AUC_means['S2']['AUC_pre']['Intromission'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[1].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['Ejaculation'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[1].scatter(x2_scatter3*x3, dict_AUC_means['S2']['AUC_post']['Ejaculation'],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[1].set_title('Second series')
#                 axs[1].spines['left'].set_visible(False)                
#                 axs[1].tick_params(left=False)              
#                 axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
               
#                 axs[1].bar(x1, dict_AUC_ratmeans['T']['AUC_pre']['Mount'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[1].scatter(x3_scatter1*x1, dict_AUC_means['T']['AUC_pre']['Mount'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[1].bar(x2, dict_AUC_ratmeans['T']['AUC_pre']['Intromission'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[1].scatter(x3_scatter2*x1, dict_AUC_means['T']['AUC_pre']['Intromission'], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[1].bar(x3, dict_AUC_ratmeans['T']['AUC_post']['Ejaculation'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[1].scatter(x3_scatter3*x3, dict_AUC_means['T']['AUC_post']['Ejaculation'],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[2].set_title('Total test')
#                 axs[2].spines['left'].set_visible(False)                
#                 axs[2].tick_params(left=False)              
#                 axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
                
#                 plt.subplots_adjust(wspace=0.25, hspace=0.2)
       
#                 plt.savefig('%s %s %s%s.png'%(graphtitle,beh,test,testsession))
#                 plt.close(fig)

#         # Change directory back
#         os.chdir(directory)

#     return dict_AUC_means
#     print("AUC_result_behavior_snipper done")

# #######################################################
# #######################################################

# #################AUC PARTS EJACULATION LATENCY ##################################
# # Make a definition for the AUC of behavior snips
# def AUC_behavior_snipper_3part(series,dataframe,testsession,virus='GCaMP6',test='COP',correction=status_correction,
#                                beh_list=list_sex,excluding_behaviors=status_excluding,list_relevant=list_relevant_behaviors,
#                                sniptime=5):
#     """
#     Note -> If you get an error, check the dictionary used for fs
    
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     dataframe : DataFrame
#         Add dataframe of the data you want to process
#         e.g. data_T, data_B, data_S1, data_S2, data_S3
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     virus : string -> Default = 'GCaMP6'
#         Add which virus you want to analyze 
#         e.g. "GCaMP6" or "GFP"
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     correction : boolean -> Default is True
#         Add whether or not to correct for baseline
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     excluding_behaviors : string - Default = 'exclude'
#         Add "exclude" if you want the delete the behaviors before which another behavior has taken place
#     list_relevant: list -> Default = list_relevant_behaviors
#         If you have "exclude", add a list with the behaviors that cannot happen before the behavior you explore
#         Note -> if you don't exclude, just name a random list. This variable will then not be used.
#     sniptime : integer -> Default = 5
#         Add the amount of seconds before and after the start of the behavior that needs to be analyzed

#     Returns
#     -------
#     Dictionary (per rat and coptest)
#     Dictionary with AUC of the corrected dFF of snips before and after the behaviors per rat and per test.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Part of test is defined by taking the latency to 1st ejaculation, and divide this in 3 equal parts.
#     Behaviors taken place in the 1st 1/3 of time is part 1, 2nd 1/3 of time part 2, and final 1/3 of time part 3.
#     """
#     d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
#     for key,dicts in my_dict_process.items():
#         dictionary_analysis = my_dict_process[d]

#     if excluding_behaviors== "exclude":
#         dict_start_beh_parts=make_dict_start_beh_3parts_excl(series,dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#         # dict_end_beh_parts=make_dict_end_beh_3parts_excl(series,dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#     else:        
#         dict_start_beh_parts=make_dict_start_beh_3parts(series,dataframe,testsession,virus=virus,test=test)
#         # dict_end_beh_parts=make_dict_end_beh_3parts(series,dataframe,testsession,virus=virus,test=test)

#     # Make empty dictionaries
#     dict_tdt_AUC={}
#     list_AUC=['AUC_pre','AUC_post']
#     parts=['part1','part2','part3']
   
#     for i in list_AUC:
#         dict_tdt_AUC[i]={}
#         for part in parts:
#             dict_tdt_AUC[i][part]={}
#             for rat,value in dictionary_analysis.items():  
#                 for beh in beh_list:
#                     if beh !='Ejaculation':
#                         # Only continue if the dictionairy contains numbers of events:
#                         if dict_start_beh_parts[rat][beh][part]:
#                             dict_tdt_AUC[i][part][beh]={}
#                             dict_tdt_AUC[i][part][beh][rat]=[]
    
#     # Get dFF,time and fs from dictionary of processed data
#     for rat,value in dictionary_analysis.items():  
#         print("Start AUC_behavior_snipper %s"%(rat))
#         dFF=dictionary_analysis[rat]['dFF']
#         fs=dictionary_analysis[rat]['fs']
#         time1=dictionary_analysis[rat]['time']
        
#         for part in parts:
#             for beh in beh_list:
#                 if beh !='Ejaculation':
#                     # Only continue if the dictionairy contains numbers of events:
#                     if dict_start_beh_parts[rat][beh][part]:
#                         # First make a continous time series of behavior events (epocs) and plot
#                         BEH_on = dict_start_beh_parts[rat][beh][part]
#                         BASELINE_START = baseline_start
#                         BASELINE_END = baseline_end
#                         TRANGE_pre = [-sniptime*np.floor(fs), np.floor(fs)]
#                         TRANGE_post = [np.floor(fs), np.floor(fs)*sniptime]
#                         TRANGE_BASELINE = [BASELINE_START*np.floor(fs), BASELINE_END*np.floor(fs)]
        
#                         # time span for peri-event filtering, PRE and POST, in samples
#                         array_ind = []
#                         pre_stim = []
#                         start_stim = []
#                         end_stim = []
#                         start_BASELINE= []
#                         end_BASELINE= []
#                         dFF_snips_pre1=[]
#                         dFF_snips_post1=[]
#                         dFF_snips_pre_cor=[]
#                         dFF_snips_post_cor=[]
                        
#                         AUC_dFF_snips_pre=[]
#                         AUC_dFF_snips_post=[]
                    
#                         #If the event cannot include pre-time seconds before event, exclude it from the data analysis
#                         for on in BEH_on:
#                             # find first time index after event onset
#                             array_ind.append(np.where(time1 > on)[0][0])
#                             # find index corresponding to pre and post stim durations
#                             pre_stim.append(array_ind[-1] + TRANGE_pre[0])
#                             start_stim.append(array_ind[-1])
#                             end_stim.append(array_ind[-1] + TRANGE_post[-1])
                            
#                             start_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[0])
#                             end_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[-1])
                            
#                             BASELINE=dFF[int(start_BASELINE[-1]):int(end_BASELINE[-1])]
#                             mean_BASELINE=np.mean(BASELINE)
                            
#                             dFF_snips_pre1.append(dFF[int(pre_stim[-1]):int(start_stim[-1])])
#                             dFF_snips_post1.append(dFF[int(start_stim[-1]):int(end_stim[-1])])
                            
#                             dFF_snips_pre_cor.append(np.subtract(dFF_snips_pre1,mean_BASELINE))
#                             dFF_snips_post_cor.append(np.subtract(dFF_snips_post1,mean_BASELINE))
                
#                         if correction==True:
#                             dFF_snips_pre=dFF_snips_pre_cor
#                             dFF_snips_post=dFF_snips_post_cor
#                         else:
#                             dFF_snips_pre=dFF_snips_pre1
#                             dFF_snips_post=dFF_snips_post1
        
#                         # Remove the snips that are shorter in size
#                         max1 = np.max([np.size(x) for x in dFF_snips_pre])
#                         max2 = np.max([np.size(x) for x in dFF_snips_post])
        
#                         dFF_snips_pre=[snip for snip in dFF_snips_pre if (np.size(snip)==max1 and np.size(snip)==max2)]                    
#                         dFF_snips_post=[snip for snip in dFF_snips_post if (np.size(snip)==max1 and np.size(snip)==max2)]                    
            
#                         # Calculate AUC
#                         AUC_pre=[trapz(snip) for snip in dFF_snips_pre]             
#                         AUC_post=[trapz(snip) for snip in dFF_snips_post]             
        
#                         AUC_dFF_snips_pre.append(AUC_pre)
#                         AUC_dFF_snips_post.append(AUC_post)
                        
#                         mean_pre=np.nanmean(AUC_dFF_snips_pre, axis=1)
#                         mean_post=np.nanmean(AUC_dFF_snips_post, axis=1)
        
#                         # Put the data in the dictionaries
#                         dict_tdt_AUC['AUC_pre'][part][beh][rat]=mean_pre
#                         dict_tdt_AUC['AUC_post'][part][beh][rat]=mean_post
                    
#     print("AUC_behavior_snipper done")
#     return dict_tdt_AUC


# # Make a definition for the mean behavior snips per rat
# def AUC_result_behavior_snipper_3part (testsession,test='COP',sniptime=5,graphtitle=None):
#     """
#     Parameters
#     ----------
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     sniptime : integer -> Default = 5
#         Add the amount of seconds before and after the start of the behavior that needs to be analyzed
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.

#     Returns
#     -------
#     Dictionary & Figures (AUC means per coptest)
#     Dictionary with the baseline-corrected AUC of mean dFF of snips before and after the behaviors per test. 
#     First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     From this the AUC was calculated.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Part of test is defined by taking the latency to 1st ejaculation, and divide this in 3 equal parts.
#     Behaviors taken place in the 1st 1/3 of time is part 1, 2nd 1/3 of time part 2, and final 1/3 of time part 3.
#     Figures of the AUC mean dFF signals before and after the behaviors, plus sem.
#     """

#     print("Start AUC_result_behavior_snipper")

#     dict_AUC_S1_3part="AUC_S1_3part_"+test+"_"+str(testsession)+"_%ssec"%sniptime   
#     dict_AUC_S2_3part="AUC_S2_3part_"+test+"_"+str(testsession)+"_%ssec"%sniptime   

#     dictionary_S1= eval(dict_AUC_S1_3part)
#     dictionary_S2= eval(dict_AUC_S2_3part)
    
#     dictionary_S1
#     dictionary_S2
    
#     list_series=['S1','S2']
#     list_AUC=['AUC_pre','AUC_post']
#     parts=['part1','part2','part3']

#     dict_AUC_means={}
#     dict_AUC_ratmeans={}
#     for d in list_series:
#         dict_AUC_means[d]={}
#         dict_AUC_ratmeans[d]={}

#         for moment in list_AUC:
#             dict_AUC_means[d][moment]={}
#             dict_AUC_ratmeans[d][moment]={}
            
#             for part in parts:
#                 dict_AUC_means[d][moment][part]={}
#                 dict_AUC_ratmeans[d][moment][part]={}
                
#                 for beh in list_sex:
#                     if beh!='Attempt to mount' and beh!='Ejaculation':
#                         dict_AUC_ratmeans[d][moment][part][beh]=[]
#                         dict_AUC_means[d][moment][part][beh]=[]
   
#     # Fill dictionary
#     for moment,parts in dictionary_S1.items():
#         for part,behavior in parts.items():
#             if moment == 'AUC_pre':
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S1']['AUC_pre'][part][beh]=list_value
#                     dict_AUC_ratmeans['S1']['AUC_pre'][part][beh]=np.nanmean(list_value)
#             else:
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S1']['AUC_post'][part][beh]=list_value
#                     dict_AUC_ratmeans['S1']['AUC_post'][part][beh]=np.nanmean(list_value)
    
#     for moment,parts in dictionary_S2.items():
#         for part,behavior in parts.items():
#             if moment == 'AUC_pre':
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S2']['AUC_pre'][part][beh]=list_value
#                     dict_AUC_ratmeans['S2']['AUC_pre'][part][beh]=np.nanmean(list_value)
#             else:
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S2']['AUC_post'][part][beh]=list_value
#                     dict_AUC_ratmeans['S2']['AUC_post'][part][beh]=np.nanmean(list_value)


#     # Make a barplot
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_partsAUC):
#             os.mkdir(directory_TDT_partsAUC)

#         os.chdir(directory_TDT_partsAUC)

#         sns.set(style="ticks", rc=custom_params)
#         barWidth = 0.6
#         x1 = ['Pre']
#         x3 = ['Post']

#         fig, axs = plt.subplots(2,3, figsize=(8,6), sharex=True, sharey=True)

#         for moment,parts in dictionary_S1.items():
#             for part,behavior in parts.items():
#                 for beh,values in behavior.items():
#                     x_scatter1_p1=len(dict_AUC_means['S1']['AUC_pre']['part1'][beh])
#                     x_scatter2_p1=len(dict_AUC_means['S2']['AUC_pre']['part1'][beh])
                    
#                     x_scatter1_p2=len(dict_AUC_means['S1']['AUC_pre']['part2'][beh])
#                     x_scatter2_p2=len(dict_AUC_means['S2']['AUC_pre']['part2'][beh])
            
#                     x_scatter1_p3=len(dict_AUC_means['S1']['AUC_pre']['part3'][beh])
#                     x_scatter2_p3=len(dict_AUC_means['S2']['AUC_pre']['part3'][beh])

#                     if dict_AUC_means['S1']['AUC_pre']['part1'][beh]:
#                         axs[0,0].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part1'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,0].scatter(x_scatter1_p1*x1, dict_AUC_means['S1']['AUC_pre']['part1'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,0].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part1'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,0].scatter(x_scatter1_p1*x3, dict_AUC_means['S1']['AUC_post']['part1'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,0].set_title('First series - Part 1')
#                         axs[0,0].set_ylabel('AUC')
#                         # Plotting the zero line
#                         axs[0,0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S1']['AUC_pre']['part2'][beh]:
#                         axs[0,1].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part2'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,1].scatter(x_scatter1_p2*x1, dict_AUC_means['S1']['AUC_pre']['part2'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,1].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part2'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,1].scatter(x_scatter1_p2*x3, dict_AUC_means['S1']['AUC_post']['part2'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,1].set_title('First series - Part 2')
#                         # axs[0,1].set_ylabel('AUC')
#                         axs[0,1].spines['left'].set_visible(False)                
#                         axs[0,1].tick_params(left=False)              
#                         # Plotting the zero line
#                         axs[0,1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S1']['AUC_pre']['part3'][beh]:
#                         axs[0,2].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part3'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,2].scatter(x_scatter1_p3*x1, dict_AUC_means['S1']['AUC_pre']['part3'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,2].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part3'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,2].scatter(x_scatter1_p3*x3, dict_AUC_means['S1']['AUC_post']['part3'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,2].set_title('First series - Part 3')
#                         # axs[0,2].set_ylabel('AUC')
#                         axs[0,2].spines['left'].set_visible(False)                
#                         axs[0,2].tick_params(left=False)              
#                         # Plotting the zero line
#                         axs[0,2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
            
#                     if dict_AUC_means['S2']['AUC_pre']['part1'][beh]:
#                         axs[1,0].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part1'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,0].scatter(x_scatter2_p1*x1, dict_AUC_means['S2']['AUC_pre']['part1'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,0].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part1'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,0].scatter(x_scatter2_p1*x3, dict_AUC_means['S2']['AUC_post']['part1'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,0].set_title('Second series - Part 1')
#                         axs[1,0].set_ylabel('AUC')
#                         # axs[1,0].spines['left'].set_visible(False)                
#                         # axs[1,0].tick_params(left=False)              
#                         axs[1,0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S2']['AUC_pre']['part2'][beh]:
#                         axs[1,1].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part2'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,1].scatter(x_scatter2_p2*x1, dict_AUC_means['S2']['AUC_pre']['part2'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,1].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part2'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,1].scatter(x_scatter2_p2*x3, dict_AUC_means['S2']['AUC_post']['part2'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,1].set_title('Second series - Part 2')
#                         axs[1,1].spines['left'].set_visible(False)                
#                         axs[1,1].tick_params(left=False)              
#                         axs[1,1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S2']['AUC_pre']['part3'][beh]:
#                         axs[1,2].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part3'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,2].scatter(x_scatter2_p3*x1, dict_AUC_means['S2']['AUC_pre']['part3'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,2].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part3'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,2].scatter(x_scatter2_p3*x3, dict_AUC_means['S2']['AUC_post']['part3'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,2].set_title('Second series - Part 3')
#                         axs[1,2].spines['left'].set_visible(False)                
#                         axs[1,2].tick_params(left=False)              
#                         axs[1,2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     plt.subplots_adjust(wspace=0.25, hspace=0.3)
           
#         plt.savefig('%s %s %s%s.png'%(graphtitle,beh,test,testsession))
#         plt.close(fig)

#         # Change directory back
#         os.chdir(directory)

#     return dict_AUC_means

#     print("AUC_result_behavior_snipper done")

# #################AUC PARTS TN behaviors ##################################
# # Make a definition for the AUC of behavior snips
# def AUC_behavior_snipper_TN3part(series,dataframe,testsession,virus='GCaMP6',test='COP',correction=status_correction,
#                                  beh_list=list_sex,excluding_behaviors=status_excluding,list_relevant=list_relevant_behaviors,sniptime=5):
    
#     """
#     Note -> If you get an error, check the dictionary used for fs
    
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     dataframe : DataFrame
#         Add dataframe of the data you want to process
#         e.g. data_T, data_B, data_S1, data_S2, data_S3
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     virus : string -> Default = 'GCaMP6'
#         Add which virus you want to analyze 
#         e.g. "GCaMP6" or "GFP"
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     correction : boolean -> Default is True
#         Add whether or not to correct for baseline
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     excluding_behaviors : string - Default = 'exclude'
#         Add "exclude" if you want the delete the behaviors before which another behavior has taken place
#     list_relevant: list -> Default = list_relevant_behaviors
#         If you have "exclude", add a list with the behaviors that cannot happen before the behavior you explore
#         Note -> if you don't exclude, just name a random list. This variable will then not be used.
#     sniptime : integer -> Default = 5
#         Add the amount of seconds before and after the start of the behavior that needs to be analyzed

#     Returns
#     -------
#     Dictionary (per rat and coptest)
#     Dictionary with AUC of the corrected dFF of snips before and after the behaviors per rat and per test.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Part of test is defined by taking the total number of copulations, and divide this in 3 equal parts.
#     The 1st 1/3 of behaviors is part 1, the 2nd 1/3 of behavior is part 2, and final 1/3 of behaviors is part 3.
#     """
    
#     d="dict_dFF_"+virus+"_"+test+"_"+str(testsession)      
#     for key,dicts in my_dict_process.items():
#         dictionary_analysis = my_dict_process[d]
    
#     if excluding_behaviors== "exclude":
#         dict_start_beh_parts=make_dict_start_beh_TN3parts_excl(series,dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#         # dict_end_beh_parts=make_dict_end_beh_TN3parts_excl(series,dataframe,testsession,virus=virus,test=test,list_relevant=list_relevant)
#     else:        
#         dict_start_beh_parts=make_dict_start_beh_TN3parts(series,dataframe,testsession,virus=virus,test=test)
#         # dict_end_beh_parts=make_dict_end_beh_TN3parts(series,dataframe,testsession,virus=virus,test=test)

#     # Make empty dictionaries
#     dict_tdt_AUC={}
#     list_AUC=['AUC_pre','AUC_post']
#     parts=['part1','part2','part3']
   
#     for i in list_AUC:
#         dict_tdt_AUC[i]={}
#         for part in parts:
#             dict_tdt_AUC[i][part]={}
#             for rat,value in dictionary_analysis.items():  
#                 for beh in beh_list:
#                     if beh != 'Attempt to mount' and beh !='Ejaculation':
#                         # Only continue if the dictionairy contains numbers of events:
#                         if dict_start_beh_parts[rat][beh][part]:
#                             dict_tdt_AUC[i][part][beh]={}
#                             dict_tdt_AUC[i][part][beh][rat]=[]
    
#     # Get dFF,time and fs from dictionary of processed data
#     for rat,value in dictionary_analysis.items():  
#         print("Start AUC_behavior_snipper %s"%(rat))
#         dFF=dictionary_analysis[rat]['dFF']
#         fs=dictionary_analysis[rat]['fs']
#         time1=dictionary_analysis[rat]['time']
        
#         for part in parts:
#             for beh in beh_list:
#                 if beh != 'Attempt to mount'and beh !='Ejaculation':
#                     # Only continue if the dictionairy contains numbers of events:
#                     if dict_start_beh_parts[rat][beh][part]:
#                         # First make a continous time series of behavior events (epocs) and plot
#                         BEH_on = dict_start_beh_parts[rat][beh][part]
#                         BASELINE_START = baseline_start
#                         BASELINE_END = baseline_end
#                         TRANGE_pre = [-sniptime*np.floor(fs), np.floor(fs)]
#                         TRANGE_post = [np.floor(fs), np.floor(fs)*sniptime]
#                         TRANGE_BASELINE = [BASELINE_START*np.floor(fs), BASELINE_END*np.floor(fs)]
        
#                         # time span for peri-event filtering, PRE and POST, in samples
#                         array_ind = []
#                         pre_stim = []
#                         start_stim = []
#                         end_stim = []
#                         start_BASELINE= []
#                         end_BASELINE= []
#                         dFF_snips_pre1=[]
#                         dFF_snips_post1=[]
#                         dFF_snips_pre_cor=[]
#                         dFF_snips_post_cor=[]
                        
#                         AUC_dFF_snips_pre=[]
#                         AUC_dFF_snips_post=[]
                    
#                         #If the event cannot include pre-time seconds before event, exclude it from the data analysis
#                         for on in BEH_on:
#                             # find first time index after event onset
#                             array_ind.append(np.where(time1 > on)[0][0])
#                             # find index corresponding to pre and post stim durations
#                             pre_stim.append(array_ind[-1] + TRANGE_pre[0])
#                             start_stim.append(array_ind[-1])
#                             end_stim.append(array_ind[-1] + TRANGE_post[-1])
                            
#                             start_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[0])
#                             end_BASELINE.append(array_ind[-1] + TRANGE_BASELINE[-1])
                            
#                             BASELINE=dFF[int(start_BASELINE[-1]):int(end_BASELINE[-1])]
#                             mean_BASELINE=np.mean(BASELINE)
                            
#                             dFF_snips_pre1.append(dFF[int(pre_stim[-1]):int(start_stim[-1])])
#                             dFF_snips_post1.append(dFF[int(start_stim[-1]):int(end_stim[-1])])
                            
#                             dFF_snips_pre_cor.append(np.subtract(dFF_snips_pre1,mean_BASELINE))
#                             dFF_snips_post_cor.append(np.subtract(dFF_snips_post1,mean_BASELINE))
 
#                         if correction==True:
#                             dFF_snips_pre=dFF_snips_pre_cor
#                             dFF_snips_post=dFF_snips_post_cor
#                         else:
#                             dFF_snips_pre=dFF_snips_pre1
#                             dFF_snips_post=dFF_snips_post1

#                         # Remove the snips that are shorter in size
#                         max1 = np.max([np.size(x) for x in dFF_snips_pre])
#                         max2 = np.max([np.size(x) for x in dFF_snips_post])
        
#                         dFF_snips_pre=[snip for snip in dFF_snips_pre if (np.size(snip)==max1 and np.size(snip)==max2)]                    
#                         dFF_snips_post=[snip for snip in dFF_snips_post if (np.size(snip)==max1 and np.size(snip)==max2)]                    
            
#                         # Calculate AUC
#                         AUC_pre=[trapz(snip) for snip in dFF_snips_pre]             
#                         AUC_post=[trapz(snip) for snip in dFF_snips_post]             
        
#                         AUC_dFF_snips_pre.append(AUC_pre)
#                         AUC_dFF_snips_post.append(AUC_post)
                        
#                         mean_pre=np.nanmean(AUC_dFF_snips_pre, axis=1)
#                         mean_post=np.nanmean(AUC_dFF_snips_post, axis=1)
        
#                         # Put the data in the dictionaries
#                         dict_tdt_AUC['AUC_pre'][part][beh][rat]=mean_pre
#                         dict_tdt_AUC['AUC_post'][part][beh][rat]=mean_post
                    
#     print("AUC_behavior_snipper done")
#     return dict_tdt_AUC


# # Make a definition for the mean behavior snips per rat
# def AUC_result_behavior_snipper_TN3part (testsession,test='COP',sniptime=5,graphtitle=None):
#     """
#     Parameters
#     ----------
#     test : string -> Default = 'COP'
#         Add what type of behavioral test you want to analyze
#         e.g. "COP"
#     testsession : float
#         Add which COP-test number you want to analyze
#         e.g. 1 for COP1, 2 for COP2
#     sniptime : integer -> Default = 5
#         Add the amount of seconds before and after the start of the behavior that needs to be analyzed
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.

#     Returns
#     -------
#     Dictionary & Figures (AUC means per coptest)
#     Dictionary with the baseline-corrected AUC of mean dFF of snips before and after the behaviors per test. 
#     First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     From this the AUC was calculated.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Part of test is defined by taking the total number of copulations, and divide this in 3 equal parts.
#     The 1st 1/3 of behaviors is part 1, the 2nd 1/3 of behavior is part 2, and final 1/3 of behaviors is part 3.
#     Figures of the AUC mean dFF signals before and after the behaviors, plus sem.
#     """

#     print("Start AUC_result_behavior_snipper")

#     dict_AUC_S1_3part="AUC_S1_TN3part_"+test+"_"+str(testsession)+"_%ssec"%sniptime   
#     dict_AUC_S2_3part="AUC_S2_TN3part_"+test+"_"+str(testsession)+"_%ssec"%sniptime   

#     dictionary_S1= eval(dict_AUC_S1_3part)
#     dictionary_S2= eval(dict_AUC_S2_3part)
    
#     list_series=['S1','S2']
#     list_AUC=['AUC_pre','AUC_post']
#     parts=['part1','part2','part3']

#     dict_AUC_means={}
#     dict_AUC_ratmeans={}
#     for d in list_series:
#         dict_AUC_means[d]={}
#         dict_AUC_ratmeans[d]={}

#         for moment in list_AUC:
#             dict_AUC_means[d][moment]={}
#             dict_AUC_ratmeans[d][moment]={}
            
#             for part in parts:
#                 dict_AUC_means[d][moment][part]={}
#                 dict_AUC_ratmeans[d][moment][part]={}
                
#                 for beh in list_sex:
#                     if beh!='Ejaculation':
#                         dict_AUC_ratmeans[d][moment][part][beh]=[]
#                         dict_AUC_means[d][moment][part][beh]=[]
   
#     # Fill dictionary
#     for moment,parts in dictionary_S1.items():
#         for part,behavior in parts.items():
#             if moment == 'AUC_pre':
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S1']['AUC_pre'][part][beh]=list_value
#                     dict_AUC_ratmeans['S1']['AUC_pre'][part][beh]=np.nanmean(list_value)
#             else:
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S1']['AUC_post'][part][beh]=list_value
#                     dict_AUC_ratmeans['S1']['AUC_post'][part][beh]=np.nanmean(list_value)
    
#     for moment,parts in dictionary_S2.items():
#         for part,behavior in parts.items():
#             if moment == 'AUC_pre':
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S2']['AUC_pre'][part][beh]=list_value
#                     dict_AUC_ratmeans['S2']['AUC_pre'][part][beh]=np.nanmean(list_value)
#             else:
#                 for beh,values in behavior.items():
#                     list_value=[]
#                     for rat, value in values.items():
#                         for v in value:
#                             list_value.append(v)
#                     dict_AUC_means['S2']['AUC_post'][part][beh]=list_value
#                     dict_AUC_ratmeans['S2']['AUC_post'][part][beh]=np.nanmean(list_value)


#     # Make a barplot
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_partsAUC):
#             os.mkdir(directory_TDT_partsAUC)

#         os.chdir(directory_TDT_partsAUC)

#         sns.set(style="ticks", rc=custom_params)
#         barWidth = 0.8
#         x1 = ['Pre']
#         x3 = ['Post']

#         fig, axs = plt.subplots(2,3, figsize=(8,6), sharex=True, sharey=True)

#         for moment,parts in dictionary_S1.items():
#             for part,behavior in parts.items():
#                 for beh,values in behavior.items():
#                     x_scatter1_p1=len(dict_AUC_means['S1']['AUC_pre']['part1'][beh])
#                     x_scatter2_p1=len(dict_AUC_means['S2']['AUC_pre']['part1'][beh])
                    
#                     x_scatter1_p2=len(dict_AUC_means['S1']['AUC_pre']['part2'][beh])
#                     x_scatter2_p2=len(dict_AUC_means['S2']['AUC_pre']['part2'][beh])
            
#                     x_scatter1_p3=len(dict_AUC_means['S1']['AUC_pre']['part3'][beh])
#                     x_scatter2_p3=len(dict_AUC_means['S2']['AUC_pre']['part3'][beh])

#                     if dict_AUC_means['S1']['AUC_pre']['part1'][beh]:
#                         axs[0,0].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part1'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,0].scatter(x_scatter1_p1*x1, dict_AUC_means['S1']['AUC_pre']['part1'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,0].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part1'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,0].scatter(x_scatter1_p1*x3, dict_AUC_means['S1']['AUC_post']['part1'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,0].set_title('First series - Part 1')
#                         axs[0,0].set_ylabel('AUC')
#                         # Plotting the zero line
#                         axs[0,0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S1']['AUC_pre']['part2'][beh]:
#                         axs[0,1].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part2'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,1].scatter(x_scatter1_p2*x1, dict_AUC_means['S1']['AUC_pre']['part2'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,1].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part2'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,1].scatter(x_scatter1_p2*x3, dict_AUC_means['S1']['AUC_post']['part2'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,1].set_title('First series - Part 2')
#                         # axs[0,1].set_ylabel('AUC')
#                         axs[0,1].spines['left'].set_visible(False)                
#                         axs[0,1].tick_params(left=False)              
#                         # Plotting the zero line
#                         axs[0,1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S1']['AUC_pre']['part3'][beh]:
#                         axs[0,2].bar(x1, dict_AUC_ratmeans['S1']['AUC_pre']['part3'][beh], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0,2].scatter(x_scatter1_p3*x1, dict_AUC_means['S1']['AUC_pre']['part3'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0,2].bar(x3, dict_AUC_ratmeans['S1']['AUC_post']['part3'][beh], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0,2].scatter(x_scatter1_p3*x3, dict_AUC_means['S1']['AUC_post']['part3'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0,2].set_title('First series - Part 3')
#                         # axs[0,2].set_ylabel('AUC')
#                         axs[0,2].spines['left'].set_visible(False)                
#                         axs[0,2].tick_params(left=False)              
#                         # Plotting the zero line
#                         axs[0,2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
            
#                     if dict_AUC_means['S2']['AUC_pre']['part1'][beh]:
#                         axs[1,0].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part1'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,0].scatter(x_scatter2_p1*x1, dict_AUC_means['S2']['AUC_pre']['part1'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,0].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part1'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,0].scatter(x_scatter2_p1*x3, dict_AUC_means['S2']['AUC_post']['part1'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,0].set_title('Second series - Part 1')
#                         axs[1,0].set_ylabel('AUC')
#                         # axs[1,0].spines['left'].set_visible(False)                
#                         # axs[1,0].tick_params(left=False)              
#                         axs[1,0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S2']['AUC_pre']['part2'][beh]:
#                         axs[1,1].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part2'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,1].scatter(x_scatter2_p2*x1, dict_AUC_means['S2']['AUC_pre']['part2'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,1].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part2'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,1].scatter(x_scatter2_p2*x3, dict_AUC_means['S2']['AUC_post']['part2'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,1].set_title('Second series - Part 2')
#                         axs[1,1].spines['left'].set_visible(False)                
#                         axs[1,1].tick_params(left=False)              
#                         axs[1,1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     if dict_AUC_means['S2']['AUC_pre']['part3'][beh]:
#                         axs[1,2].bar(x1, dict_AUC_ratmeans['S2']['AUC_pre']['part3'][beh], color=color_AUC_pre_S2_bar , width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1,2].scatter(x_scatter2_p3*x1, dict_AUC_means['S2']['AUC_pre']['part3'][beh],color=color_AUC_pre_S2_scatter, alpha=.9,zorder=3)
#                         axs[1,2].bar(x3, dict_AUC_ratmeans['S2']['AUC_post']['part3'][beh], color=color_AUC_post_S2_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1,2].scatter(x_scatter2_p3*x3, dict_AUC_means['S2']['AUC_post']['part3'][beh], color=color_AUC_post_S2_scatter,alpha=.9,zorder=3)
#                         axs[1,2].set_title('Second series - Part 3')
#                         axs[1,2].spines['left'].set_visible(False)                
#                         axs[1,2].tick_params(left=False)              
#                         axs[1,2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)

#                     plt.subplots_adjust(wspace=0.25, hspace=0.3)
           
#         plt.savefig('%s %s %s%s.png'%(graphtitle,beh,test,testsession))
#         plt.close(fig)

#         # Change directory back
#         os.chdir(directory)

#     return dict_AUC_means

#     print("AUC_result_behavior_snipper done")

# # ###########################################################################################################
# # ########## Get times that need exclusion due to artifacts #################################################
# # ###########################################################################################################
# # ### RH001 has artifacts in S2_115COP2 and S2_115COP5 ###
# # gettimeS2_115COP2_start=artifact_time_checker_start("115COP2",data_S2,2)
# # gettimeS2_115COP5_start=artifact_time_checker_start("115COP5",data_S2,5)
# # gettimeS2_115COP2_end=artifact_time_checker_end("115COP2",data_S2,2)
# # gettimeS2_115COP5_end=artifact_time_checker_end("115COP5",data_S2,5)
# # gettimeT_115COP2_start=gettimeS2_115COP2_start.copy()
# # gettimeT_115COP5_start=gettimeS2_115COP5_start.copy()
# # gettimeT_115COP2_end=gettimeS2_115COP2_end.copy()
# # gettimeT_115COP5_end=gettimeS2_115COP5_end.copy()
# # ###########################################################################################################
# ###########################################################################################################

# ##########################################################################################################################
# ##########################################################################################################################
# ############# BEHAVIOR SNIPPER ################
# ##########################################################################################################################
# ##########################################################################################################################

# # Run behavioral snipper if graphs are needed
# S1_GCaMP6_COP_1=behavior_snipper(data_S1,1,graphtitle='S1_')
# S1_GCaMP6_COP_2=behavior_snipper(data_S1,2,graphtitle='S1_')
# S1_GCaMP6_COP_3=behavior_snipper(data_S1,3,graphtitle='S1_')
# S1_GCaMP6_COP_4=behavior_snipper(data_S1,4,graphtitle='S1_')
# S1_GCaMP6_COP_5=behavior_snipper(data_S1,5,graphtitle='S1_')
# S1_GCaMP6_COP_6=behavior_snipper(data_S1,6,graphtitle='S1_')
# S1_GCaMP6_COP_7=behavior_snipper(data_S1,7,graphtitle='S1_')

# S2_GCaMP6_COP_1=behavior_snipper(data_S2,1,graphtitle='S2_')
# S2_GCaMP6_COP_2=behavior_snipper(data_S2,2,graphtitle='S2_')
# S2_GCaMP6_COP_3=behavior_snipper(data_S2,3,graphtitle='S2_')
# S2_GCaMP6_COP_4=behavior_snipper(data_S2,4,graphtitle='S2_')
# S2_GCaMP6_COP_5=behavior_snipper(data_S2,5,graphtitle='S2_')
# S2_GCaMP6_COP_6=behavior_snipper(data_S2,6,graphtitle='S2_')
# S2_GCaMP6_COP_7=behavior_snipper(data_S2,7,graphtitle='S2_')
                                 
# T_GCaMP6_COP_1=behavior_snipper(data_T,1,graphtitle='T_')
# T_GCaMP6_COP_2=behavior_snipper(data_T,2,graphtitle='T_')
# T_GCaMP6_COP_3=behavior_snipper(data_T,3,graphtitle='T_')
# T_GCaMP6_COP_4=behavior_snipper(data_T,4,graphtitle='T_')
# T_GCaMP6_COP_5=behavior_snipper(data_T,5,graphtitle='T_')
# T_GCaMP6_COP_6=behavior_snipper(data_T,6,graphtitle='T_')
# T_GCaMP6_COP_7=behavior_snipper(data_T,7,graphtitle='T_')

# # # Calculate for other behaviors -> only temporary
# # T_GCaMP6_COP_1=behavior_snipper(data_T,1,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_2=behavior_snipper(data_T,2,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_3=behavior_snipper(data_T,3,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_4=behavior_snipper(data_T,4,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_5=behavior_snipper(data_T,5,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_6=behavior_snipper(data_T,6,beh_list=list_other_behaviors)
# # T_GCaMP6_COP_7=behavior_snipper(data_T,7,beh_list=list_other_behaviors)

# ##########################################################################################################################
# ##########################################################################################################################
# ############# BEHAVIOR SNIPPER 3 PARTS ################
# ##########################################################################################################################
# ##########################################################################################################################

# # Run behavioral snipper for 3parts
# S1_GCaMP6_COP_1_3part=behavior_snipper_3part("S1",data_S1,1)
# S1_GCaMP6_COP_2_3part=behavior_snipper_3part("S1",data_S1,2)
# S1_GCaMP6_COP_3_3part=behavior_snipper_3part("S1",data_S1,3)
# S1_GCaMP6_COP_4_3part=behavior_snipper_3part("S1",data_S1,4)
# S1_GCaMP6_COP_5_3part=behavior_snipper_3part("S1",data_S1,5)
# S1_GCaMP6_COP_6_3part=behavior_snipper_3part("S1",data_S1,6)
# S1_GCaMP6_COP_7_3part=behavior_snipper_3part("S1",data_S1,7)
# S2_GCaMP6_COP_1_3part=behavior_snipper_3part("S2",data_S2,1)
# S2_GCaMP6_COP_2_3part=behavior_snipper_3part("S2",data_S2,2)
# S2_GCaMP6_COP_3_3part=behavior_snipper_3part("S2",data_S2,3)
# S2_GCaMP6_COP_4_3part=behavior_snipper_3part("S2",data_S2,4)
# S2_GCaMP6_COP_5_3part=behavior_snipper_3part("S2",data_S2,5)
# S2_GCaMP6_COP_6_3part=behavior_snipper_3part("S2",data_S2,6)
# S2_GCaMP6_COP_7_3part=behavior_snipper_3part("S2",data_S2,7)

# # Run behavioral snipper for TN3parts
# S1_GCaMP6_COP_1_TN3part=behavior_snipper_TN3part("S1",data_S1,1)
# S1_GCaMP6_COP_2_TN3part=behavior_snipper_TN3part("S1",data_S1,2)
# S1_GCaMP6_COP_3_TN3part=behavior_snipper_TN3part("S1",data_S1,3)
# S1_GCaMP6_COP_4_TN3part=behavior_snipper_TN3part("S1",data_S1,4)
# S1_GCaMP6_COP_5_TN3part=behavior_snipper_TN3part("S1",data_S1,5)
# S1_GCaMP6_COP_6_TN3part=behavior_snipper_TN3part("S1",data_S1,6)
# S1_GCaMP6_COP_7_TN3part=behavior_snipper_TN3part("S1",data_S1,7)
# S2_GCaMP6_COP_1_TN3part=behavior_snipper_TN3part("S2",data_S2,1)
# S2_GCaMP6_COP_2_TN3part=behavior_snipper_TN3part("S2",data_S2,2)
# S2_GCaMP6_COP_3_TN3part=behavior_snipper_TN3part("S2",data_S2,3)
# S2_GCaMP6_COP_4_TN3part=behavior_snipper_TN3part("S2",data_S2,4)
# S2_GCaMP6_COP_5_TN3part=behavior_snipper_TN3part("S2",data_S2,5)
# S2_GCaMP6_COP_6_TN3part=behavior_snipper_TN3part("S2",data_S2,6)
# S2_GCaMP6_COP_7_TN3part=behavior_snipper_TN3part("S2",data_S2,7)

# ##########################################################################################################################
# ##########################################################################################################################
# #############  RESULTS BEHAVIOR SNIPPER ################
# ##########################################################################################################################
# ##########################################################################################################################

# results_S1_GCaMP6_COP_1=result_behavior_snipper(data_S1,1)
# results_S1_GCaMP6_COP_2=result_behavior_snipper(data_S1,2)
# results_S1_GCaMP6_COP_3=result_behavior_snipper(data_S1,3)
# results_S1_GCaMP6_COP_4=result_behavior_snipper(data_S1,4)
# results_S1_GCaMP6_COP_5=result_behavior_snipper(data_S1,5)
# results_S1_GCaMP6_COP_6=result_behavior_snipper(data_S1,6)
# results_S1_GCaMP6_COP_7=result_behavior_snipper(data_S1,7)

# results_S2_GCaMP6_COP_1=result_behavior_snipper(data_S2,1)
# results_S2_GCaMP6_COP_2=result_behavior_snipper(data_S2,2)
# results_S2_GCaMP6_COP_3=result_behavior_snipper(data_S2,3)
# results_S2_GCaMP6_COP_4=result_behavior_snipper(data_S2,4)
# results_S2_GCaMP6_COP_5=result_behavior_snipper(data_S2,5)
# results_S2_GCaMP6_COP_6=result_behavior_snipper(data_S2,6)
# results_S2_GCaMP6_COP_7=result_behavior_snipper(data_S2,7)

# results_T_GCaMP6_COP_1=result_behavior_snipper(data_T,1)
# results_T_GCaMP6_COP_2=result_behavior_snipper(data_T,2)
# results_T_GCaMP6_COP_3=result_behavior_snipper(data_T,3)
# results_T_GCaMP6_COP_4=result_behavior_snipper(data_T,4)
# results_T_GCaMP6_COP_5=result_behavior_snipper(data_T,5)
# results_T_GCaMP6_COP_6=result_behavior_snipper(data_T,6)
# results_T_GCaMP6_COP_7=result_behavior_snipper(data_T,7)


# # # Other behaviors -> only temporary! Has same name as other result snippers, and name is needed in definitions
# # results_T_GCaMP6_COP_1=result_behavior_snipper_cor(data_T,1,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_2=result_behavior_snipper_cor(data_T,2,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_3=result_behavior_snipper_cor(data_T,3,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_4=result_behavior_snipper_cor(data_T,4,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_5=result_behavior_snipper_cor(data_T,5,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_6=result_behavior_snipper_cor(data_T,6,beh_list=list_other_behaviors)
# # results_T_GCaMP6_COP_7=result_behavior_snipper_cor(data_T,7,beh_list=list_other_behaviors)

# ##########################################################################################################################
# ##########################################################################################################################
# ############# RESULTS BEHAVIOR SNIPPER PARTS ################
# ##########################################################################################################################
# ##########################################################################################################################

# # result snippers 3 part
# results_3part_S1_GCaMP6_COP_1=result_behavior_snipper_3part('S1',data_S1,1)
# results_3part_S1_GCaMP6_COP_2=result_behavior_snipper_3part('S1',data_S1,2)
# results_3part_S1_GCaMP6_COP_3=result_behavior_snipper_3part('S1',data_S1,3)
# results_3part_S1_GCaMP6_COP_4=result_behavior_snipper_3part('S1',data_S1,4)
# results_3part_S1_GCaMP6_COP_5=result_behavior_snipper_3part('S1',data_S1,5)
# results_3part_S1_GCaMP6_COP_6=result_behavior_snipper_3part('S1',data_S1,6)
# results_3part_S1_GCaMP6_COP_7=result_behavior_snipper_3part('S1',data_S1,7)

# results_3part_S2_GCaMP6_COP_1=result_behavior_snipper_3part('S2',data_S2,1)
# results_3part_S2_GCaMP6_COP_2=result_behavior_snipper_3part('S2',data_S2,2)
# results_3part_S2_GCaMP6_COP_3=result_behavior_snipper_3part('S2',data_S2,3)
# results_3part_S2_GCaMP6_COP_4=result_behavior_snipper_3part('S2',data_S2,4)
# results_3part_S2_GCaMP6_COP_5=result_behavior_snipper_3part('S2',data_S2,5)
# results_3part_S2_GCaMP6_COP_6=result_behavior_snipper_3part('S2',data_S2,6)
# results_3part_S2_GCaMP6_COP_7=result_behavior_snipper_3part('S2',data_S2,7)

# # result snippers TN3 part
# results_TN3part_S1_GCaMP6_COP_1=result_behavior_snipper_TN3part('S1',data_S1,1)
# results_TN3part_S1_GCaMP6_COP_2=result_behavior_snipper_TN3part('S1',data_S1,2)
# results_TN3part_S1_GCaMP6_COP_3=result_behavior_snipper_TN3part('S1',data_S1,3)
# results_TN3part_S1_GCaMP6_COP_4=result_behavior_snipper_TN3part('S1',data_S1,4)
# results_TN3part_S1_GCaMP6_COP_5=result_behavior_snipper_TN3part('S1',data_S1,5)
# results_TN3part_S1_GCaMP6_COP_6=result_behavior_snipper_TN3part('S1',data_S1,6)
# results_TN3part_S1_GCaMP6_COP_7=result_behavior_snipper_TN3part('S1',data_S1,7)

# results_TN3part_S2_GCaMP6_COP_1=result_behavior_snipper_TN3part('S2',data_S2,1)
# results_TN3part_S2_GCaMP6_COP_2=result_behavior_snipper_TN3part('S2',data_S2,2)
# results_TN3part_S2_GCaMP6_COP_3=result_behavior_snipper_TN3part('S2',data_S2,3)
# results_TN3part_S2_GCaMP6_COP_4=result_behavior_snipper_TN3part('S2',data_S2,4)
# results_TN3part_S2_GCaMP6_COP_5=result_behavior_snipper_TN3part('S2',data_S2,5)
# results_TN3part_S2_GCaMP6_COP_6=result_behavior_snipper_TN3part('S2',data_S2,6)
# results_TN3part_S2_GCaMP6_COP_7=result_behavior_snipper_TN3part('S2',data_S2,7)

# # result snippers 5 part
# results_5part_S1_GCaMP6_COP_1=result_behavior_snipper_5part('S1',data_S1,1)
# results_5part_S1_GCaMP6_COP_2=result_behavior_snipper_5part('S1',data_S1,2)
# results_5part_S1_GCaMP6_COP_3=result_behavior_snipper_5part('S1',data_S1,3)
# results_5part_S1_GCaMP6_COP_4=result_behavior_snipper_5part('S1',data_S1,4)
# results_5part_S1_GCaMP6_COP_5=result_behavior_snipper_5part('S1',data_S1,5)
# results_5part_S1_GCaMP6_COP_6=result_behavior_snipper_5part('S1',data_S1,6)
# results_5part_S1_GCaMP6_COP_7=result_behavior_snipper_5part('S1',data_S1,7)

# results_5part_S2_GCaMP6_COP_1=result_behavior_snipper_5part('S2',data_S2,1)
# results_5part_S2_GCaMP6_COP_2=result_behavior_snipper_5part('S2',data_S2,2)
# results_5part_S2_GCaMP6_COP_3=result_behavior_snipper_5part('S2',data_S2,3)
# results_5part_S2_GCaMP6_COP_4=result_behavior_snipper_5part('S2',data_S2,4)
# results_5part_S2_GCaMP6_COP_5=result_behavior_snipper_5part('S2',data_S2,5)
# results_5part_S2_GCaMP6_COP_6=result_behavior_snipper_5part('S2',data_S2,6)
# results_5part_S2_GCaMP6_COP_7=result_behavior_snipper_5part('S2',data_S2,7)

# ##########################################################################################################################
# ##########################################################################################################################
# ############# RESULTS AUC ################
# ##########################################################################################################################
# ##########################################################################################################################

# # FIVE SECONDS
# AUC_S1_COP_1_5sec=AUC_behavior_snipper(data_S1,1)  
# AUC_S1_COP_2_5sec=AUC_behavior_snipper(data_S1,2)  
# AUC_S1_COP_3_5sec=AUC_behavior_snipper(data_S1,3)  
# AUC_S1_COP_4_5sec=AUC_behavior_snipper(data_S1,4)  
# AUC_S1_COP_5_5sec=AUC_behavior_snipper(data_S1,5)  
# AUC_S1_COP_6_5sec=AUC_behavior_snipper(data_S1,6)  
# AUC_S1_COP_7_5sec=AUC_behavior_snipper(data_S1,7)  

# AUC_S2_COP_1_5sec=AUC_behavior_snipper(data_S2,1)  
# AUC_S2_COP_2_5sec=AUC_behavior_snipper(data_S2,2)  
# AUC_S2_COP_3_5sec=AUC_behavior_snipper(data_S2,3)  
# AUC_S2_COP_4_5sec=AUC_behavior_snipper(data_S2,4)  
# AUC_S2_COP_5_5sec=AUC_behavior_snipper(data_S2,5)  
# AUC_S2_COP_6_5sec=AUC_behavior_snipper(data_S2,6)  
# AUC_S2_COP_7_5sec=AUC_behavior_snipper(data_S2,7)  

# AUC_T_COP_1_5sec=AUC_behavior_snipper(data_T,1)  
# AUC_T_COP_2_5sec=AUC_behavior_snipper(data_T,2)  
# AUC_T_COP_3_5sec=AUC_behavior_snipper(data_T,3)  
# AUC_T_COP_4_5sec=AUC_behavior_snipper(data_T,4)  
# AUC_T_COP_5_5sec=AUC_behavior_snipper(data_T,5)  
# AUC_T_COP_6_5sec=AUC_behavior_snipper(data_T,6)  
# AUC_T_COP_7_5sec=AUC_behavior_snipper(data_T,7)  

# AUC_result_COP_1_5sec=AUC_result_behavior_snipper(1,graphtitle="AUC_5sec")  
# AUC_result_COP_2_5sec=AUC_result_behavior_snipper(2,graphtitle="AUC_5sec")  
# AUC_result_COP_3_5sec=AUC_result_behavior_snipper(3,graphtitle="AUC_5sec")  
# AUC_result_COP_4_5sec=AUC_result_behavior_snipper(4,graphtitle="AUC_5sec")  
# AUC_result_COP_5_5sec=AUC_result_behavior_snipper(5,graphtitle="AUC_5sec")  
# AUC_result_COP_6_5sec=AUC_result_behavior_snipper(6,graphtitle="AUC_5sec")  
# AUC_result_COP_7_5sec=AUC_result_behavior_snipper(7,graphtitle="AUC_5sec")  

# # change seconds for analysis in results!
# # TWO SECONDS
# AUC_S1_COP_1_2sec=AUC_behavior_snipper(data_S1,1,sniptime=2)  
# AUC_S1_COP_2_2sec=AUC_behavior_snipper(data_S1,2,sniptime=2)  
# AUC_S1_COP_3_2sec=AUC_behavior_snipper(data_S1,3,sniptime=2)  
# AUC_S1_COP_4_2sec=AUC_behavior_snipper(data_S1,4,sniptime=2)  
# AUC_S1_COP_5_2sec=AUC_behavior_snipper(data_S1,5,sniptime=2)  
# AUC_S1_COP_6_2sec=AUC_behavior_snipper(data_S1,6,sniptime=2)  
# AUC_S1_COP_7_2sec=AUC_behavior_snipper(data_S1,7,sniptime=2)  

# AUC_S2_COP_1_2sec=AUC_behavior_snipper(data_S2,1,sniptime=2)  
# AUC_S2_COP_2_2sec=AUC_behavior_snipper(data_S2,2,sniptime=2)  
# AUC_S2_COP_3_2sec=AUC_behavior_snipper(data_S2,3,sniptime=2)  
# AUC_S2_COP_4_2sec=AUC_behavior_snipper(data_S2,4,sniptime=2)  
# AUC_S2_COP_5_2sec=AUC_behavior_snipper(data_S2,5,sniptime=2)  
# AUC_S2_COP_6_2sec=AUC_behavior_snipper(data_S2,6,sniptime=2)  
# AUC_S2_COP_7_2sec=AUC_behavior_snipper(data_S2,7,sniptime=2)  

# AUC_T_COP_1_2sec=AUC_behavior_snipper(data_T,1,sniptime=2)  
# AUC_T_COP_2_2sec=AUC_behavior_snipper(data_T,2,sniptime=2)  
# AUC_T_COP_3_2sec=AUC_behavior_snipper(data_T,3,sniptime=2)  
# AUC_T_COP_4_2sec=AUC_behavior_snipper(data_T,4,sniptime=2)  
# AUC_T_COP_5_2sec=AUC_behavior_snipper(data_T,5,sniptime=2)  
# AUC_T_COP_6_2sec=AUC_behavior_snipper(data_T,6,sniptime=2)  
# AUC_T_COP_7_2sec=AUC_behavior_snipper(data_T,7,sniptime=2)  

# AUC_result_COP_1_2sec=AUC_result_behavior_snipper(1,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_2_2sec=AUC_result_behavior_snipper(2,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_3_2sec=AUC_result_behavior_snipper(3,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_4_2sec=AUC_result_behavior_snipper(4,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_5_2sec=AUC_result_behavior_snipper(5,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_6_2sec=AUC_result_behavior_snipper(6,sniptime=2,graphtitle="AUC_2sec")  
# AUC_result_COP_7_2sec=AUC_result_behavior_snipper(7,sniptime=2,graphtitle="AUC_2sec")  

# # change seconds for analysis in results!
# # TEN SECONDS
# AUC_S1_COP_1_10sec=AUC_behavior_snipper(data_S1,1,sniptime=10)  
# AUC_S1_COP_2_10sec=AUC_behavior_snipper(data_S1,2,sniptime=10)  
# AUC_S1_COP_3_10sec=AUC_behavior_snipper(data_S1,3,sniptime=10)  
# AUC_S1_COP_4_10sec=AUC_behavior_snipper(data_S1,4,sniptime=10)  
# AUC_S1_COP_5_10sec=AUC_behavior_snipper(data_S1,5,sniptime=10)  
# AUC_S1_COP_6_10sec=AUC_behavior_snipper(data_S1,6,sniptime=10)  
# AUC_S1_COP_7_10sec=AUC_behavior_snipper(data_S1,7,sniptime=10)  

# AUC_S2_COP_1_10sec=AUC_behavior_snipper(data_S2,1,sniptime=10)  
# AUC_S2_COP_2_10sec=AUC_behavior_snipper(data_S2,2,sniptime=10)  
# AUC_S2_COP_3_10sec=AUC_behavior_snipper(data_S2,3,sniptime=10)  
# AUC_S2_COP_4_10sec=AUC_behavior_snipper(data_S2,4,sniptime=10)  
# AUC_S2_COP_5_10sec=AUC_behavior_snipper(data_S2,5,sniptime=10)  
# AUC_S2_COP_6_10sec=AUC_behavior_snipper(data_S2,6,sniptime=10)  
# AUC_S2_COP_7_10sec=AUC_behavior_snipper(data_S2,7,sniptime=10)  

# AUC_T_COP_1_10sec=AUC_behavior_snipper(data_T,1,sniptime=10)  
# AUC_T_COP_2_10sec=AUC_behavior_snipper(data_T,2,sniptime=10)  
# AUC_T_COP_3_10sec=AUC_behavior_snipper(data_T,3,sniptime=10)  
# AUC_T_COP_4_10sec=AUC_behavior_snipper(data_T,4,sniptime=10)  
# AUC_T_COP_5_10sec=AUC_behavior_snipper(data_T,5,sniptime=10)  
# AUC_T_COP_6_10sec=AUC_behavior_snipper(data_T,6,sniptime=10)  
# AUC_T_COP_7_10sec=AUC_behavior_snipper(data_T,7,sniptime=10)  

# AUC_result_COP_1_10sec=AUC_result_behavior_snipper(1,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_2_10sec=AUC_result_behavior_snipper(2,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_3_10sec=AUC_result_behavior_snipper(3,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_4_10sec=AUC_result_behavior_snipper(4,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_5_10sec=AUC_result_behavior_snipper(5,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_6_10sec=AUC_result_behavior_snipper(6,sniptime=10,graphtitle="AUC_10sec")  
# AUC_result_COP_7_10sec=AUC_result_behavior_snipper(7,sniptime=10,graphtitle="AUC_10sec")  

# ##########################################################################################################################
# ############# RESULTS AUC PARTS################
# ##########################################################################################################################

# # FIVE SECONDS
# AUC_S1_3part_COP_1_5sec=AUC_behavior_snipper_3part('S1',data_S1,1)  
# AUC_S1_3part_COP_2_5sec=AUC_behavior_snipper_3part('S1',data_S1,2)  
# AUC_S1_3part_COP_3_5sec=AUC_behavior_snipper_3part('S1',data_S1,3)  
# AUC_S1_3part_COP_4_5sec=AUC_behavior_snipper_3part('S1',data_S1,4)  
# AUC_S1_3part_COP_5_5sec=AUC_behavior_snipper_3part('S1',data_S1,5)  
# AUC_S1_3part_COP_6_5sec=AUC_behavior_snipper_3part('S1',data_S1,6)  
# AUC_S1_3part_COP_7_5sec=AUC_behavior_snipper_3part('S1',data_S1,7)  

# AUC_S2_3part_COP_1_5sec=AUC_behavior_snipper_3part('S2',data_S2,1)  
# AUC_S2_3part_COP_2_5sec=AUC_behavior_snipper_3part('S2',data_S2,2)  
# AUC_S2_3part_COP_3_5sec=AUC_behavior_snipper_3part('S2',data_S2,3)  
# AUC_S2_3part_COP_4_5sec=AUC_behavior_snipper_3part('S2',data_S2,4)  
# AUC_S2_3part_COP_5_5sec=AUC_behavior_snipper_3part('S2',data_S2,5)  
# AUC_S2_3part_COP_6_5sec=AUC_behavior_snipper_3part('S2',data_S2,6)  
# AUC_S2_3part_COP_7_5sec=AUC_behavior_snipper_3part('S2',data_S2,7)  

# AUC_result_3part_COP_1_5sec=AUC_result_behavior_snipper_3part(1,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_2_5sec=AUC_result_behavior_snipper_3part(2,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_3_5sec=AUC_result_behavior_snipper_3part(3,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_4_5sec=AUC_result_behavior_snipper_3part(4,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_5_5sec=AUC_result_behavior_snipper_3part(5,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_6_5sec=AUC_result_behavior_snipper_3part(6,graphtitle="AUC_3part_5sec")  
# AUC_result_3part_COP_7_5sec=AUC_result_behavior_snipper_3part(7,graphtitle="AUC_3part_5sec")  

# # change seconds for analysis in results!
# # TWO SECONDS
# AUC_S1_3part_COP_1_2sec=AUC_behavior_snipper_3part('S1',data_S1,1,sniptime=2)  
# AUC_S1_3part_COP_2_2sec=AUC_behavior_snipper_3part('S1',data_S1,2,sniptime=2)  
# AUC_S1_3part_COP_3_2sec=AUC_behavior_snipper_3part('S1',data_S1,3,sniptime=2)  
# AUC_S1_3part_COP_4_2sec=AUC_behavior_snipper_3part('S1',data_S1,4,sniptime=2)  
# AUC_S1_3part_COP_5_2sec=AUC_behavior_snipper_3part('S1',data_S1,5,sniptime=2)  
# AUC_S1_3part_COP_6_2sec=AUC_behavior_snipper_3part('S1',data_S1,6,sniptime=2)  
# AUC_S1_3part_COP_7_2sec=AUC_behavior_snipper_3part('S1',data_S1,7,sniptime=2)  

# AUC_S2_3part_COP_1_2sec=AUC_behavior_snipper_3part('S2',data_S2,1,sniptime=2)  
# AUC_S2_3part_COP_2_2sec=AUC_behavior_snipper_3part('S2',data_S2,2,sniptime=2)  
# AUC_S2_3part_COP_3_2sec=AUC_behavior_snipper_3part('S2',data_S2,3,sniptime=2)  
# AUC_S2_3part_COP_4_2sec=AUC_behavior_snipper_3part('S2',data_S2,4,sniptime=2)  
# AUC_S2_3part_COP_5_2sec=AUC_behavior_snipper_3part('S2',data_S2,5,sniptime=2)  
# AUC_S2_3part_COP_6_2sec=AUC_behavior_snipper_3part('S2',data_S2,6,sniptime=2)  
# AUC_S2_3part_COP_7_2sec=AUC_behavior_snipper_3part('S2',data_S2,7,sniptime=2)  

# AUC_result_3part_COP_1_2sec=AUC_result_behavior_snipper_3part(1,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_2_2sec=AUC_result_behavior_snipper_3part(2,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_3_2sec=AUC_result_behavior_snipper_3part(3,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_4_2sec=AUC_result_behavior_snipper_3part(4,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_5_2sec=AUC_result_behavior_snipper_3part(5,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_6_2sec=AUC_result_behavior_snipper_3part(6,sniptime=2,graphtitle="AUC_3part_2sec")  
# AUC_result_3part_COP_7_2sec=AUC_result_behavior_snipper_3part(7,sniptime=2,graphtitle="AUC_3part_2sec")  

# # TEN SECONDS
# AUC_S1_3part_COP_1_10sec=AUC_behavior_snipper_3part('S1',data_S1,1,sniptime=10)  
# AUC_S1_3part_COP_2_10sec=AUC_behavior_snipper_3part('S1',data_S1,2,sniptime=10)  
# AUC_S1_3part_COP_3_10sec=AUC_behavior_snipper_3part('S1',data_S1,3,sniptime=10)  
# AUC_S1_3part_COP_4_10sec=AUC_behavior_snipper_3part('S1',data_S1,4,sniptime=10)  
# AUC_S1_3part_COP_5_10sec=AUC_behavior_snipper_3part('S1',data_S1,5,sniptime=10)  
# AUC_S1_3part_COP_6_10sec=AUC_behavior_snipper_3part('S1',data_S1,6,sniptime=10)  
# AUC_S1_3part_COP_7_10sec=AUC_behavior_snipper_3part('S1',data_S1,7,sniptime=10)  

# AUC_S2_3part_COP_1_10sec=AUC_behavior_snipper_3part('S2',data_S2,1,sniptime=10)  
# AUC_S2_3part_COP_2_10sec=AUC_behavior_snipper_3part('S2',data_S2,2,sniptime=10)  
# AUC_S2_3part_COP_3_10sec=AUC_behavior_snipper_3part('S2',data_S2,3,sniptime=10)  
# AUC_S2_3part_COP_4_10sec=AUC_behavior_snipper_3part('S2',data_S2,4,sniptime=10)  
# AUC_S2_3part_COP_5_10sec=AUC_behavior_snipper_3part('S2',data_S2,5,sniptime=10)  
# AUC_S2_3part_COP_6_10sec=AUC_behavior_snipper_3part('S2',data_S2,6,sniptime=10)  
# AUC_S2_3part_COP_7_10sec=AUC_behavior_snipper_3part('S2',data_S2,7,sniptime=10)  

# AUC_result_3part_COP_1_10sec=AUC_result_behavior_snipper_3part(1,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_2_10sec=AUC_result_behavior_snipper_3part(2,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_3_10sec=AUC_result_behavior_snipper_3part(3,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_4_10sec=AUC_result_behavior_snipper_3part(4,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_5_10sec=AUC_result_behavior_snipper_3part(5,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_6_10sec=AUC_result_behavior_snipper_3part(6,sniptime=10,graphtitle="AUC_3part_10sec")  
# AUC_result_3part_COP_7_10sec=AUC_result_behavior_snipper_3part(7,sniptime=10,graphtitle="AUC_3part_10sec")  

# # AUC TN3part
# # FIVE SECONDS
# AUC_S1_TN3part_COP_1_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,1)  
# AUC_S1_TN3part_COP_2_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,2)  
# AUC_S1_TN3part_COP_3_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,3)  
# AUC_S1_TN3part_COP_4_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,4)  
# AUC_S1_TN3part_COP_5_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,5)  
# AUC_S1_TN3part_COP_6_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,6)  
# AUC_S1_TN3part_COP_7_5sec=AUC_behavior_snipper_TN3part('S1',data_S1,7)  

# AUC_S2_TN3part_COP_1_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,1)  
# AUC_S2_TN3part_COP_2_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,2)  
# AUC_S2_TN3part_COP_3_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,3)  
# AUC_S2_TN3part_COP_4_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,4)  
# AUC_S2_TN3part_COP_5_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,5)  
# AUC_S2_TN3part_COP_6_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,6)  
# AUC_S2_TN3part_COP_7_5sec=AUC_behavior_snipper_TN3part('S2',data_S2,7)  

# AUC_result_TN3part_COP_1_5sec=AUC_result_behavior_snipper_TN3part(1,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_2_5sec=AUC_result_behavior_snipper_TN3part(2,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_3_5sec=AUC_result_behavior_snipper_TN3part(3,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_4_5sec=AUC_result_behavior_snipper_TN3part(4,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_5_5sec=AUC_result_behavior_snipper_TN3part(5,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_6_5sec=AUC_result_behavior_snipper_TN3part(6,graphtitle="AUC_TN3part_5sec")  
# AUC_result_TN3part_COP_7_5sec=AUC_result_behavior_snipper_TN3part(7,graphtitle="AUC_TN3part_5sec")  

# # change seconds for analysis in results!
# # TWO SECONDS
# AUC_S1_TN3part_COP_1_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,1,sniptime=2)  
# AUC_S1_TN3part_COP_2_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,2,sniptime=2)  
# AUC_S1_TN3part_COP_3_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,3,sniptime=2)  
# AUC_S1_TN3part_COP_4_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,4,sniptime=2)  
# AUC_S1_TN3part_COP_5_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,5,sniptime=2)  
# AUC_S1_TN3part_COP_6_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,6,sniptime=2)  
# AUC_S1_TN3part_COP_7_2sec=AUC_behavior_snipper_TN3part('S1',data_S1,7,sniptime=2)  

# AUC_S2_TN3part_COP_1_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,1,sniptime=2)  
# AUC_S2_TN3part_COP_2_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,2,sniptime=2)  
# AUC_S2_TN3part_COP_3_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,3,sniptime=2)  
# AUC_S2_TN3part_COP_4_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,4,sniptime=2)  
# AUC_S2_TN3part_COP_5_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,5,sniptime=2)  
# AUC_S2_TN3part_COP_6_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,6,sniptime=2)  
# AUC_S2_TN3part_COP_7_2sec=AUC_behavior_snipper_TN3part('S2',data_S2,7,sniptime=2)  

# AUC_result_TN3part_COP_1_2sec=AUC_result_behavior_snipper_TN3part(1,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_2_2sec=AUC_result_behavior_snipper_TN3part(2,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_3_2sec=AUC_result_behavior_snipper_TN3part(3,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_4_2sec=AUC_result_behavior_snipper_TN3part(4,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_5_2sec=AUC_result_behavior_snipper_TN3part(5,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_6_2sec=AUC_result_behavior_snipper_TN3part(6,sniptime=2,graphtitle="AUC_TN3part_2sec")  
# AUC_result_TN3part_COP_7_2sec=AUC_result_behavior_snipper_TN3part(7,sniptime=2,graphtitle="AUC_TN3part_2sec")  

# # change seconds for analysis in results!
# # TEN SECONDS
# AUC_S1_TN3part_COP_1_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,1,sniptime=10)  
# AUC_S1_TN3part_COP_2_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,2,sniptime=10)  
# AUC_S1_TN3part_COP_3_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,3,sniptime=10)  
# AUC_S1_TN3part_COP_4_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,4,sniptime=10)  
# AUC_S1_TN3part_COP_5_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,5,sniptime=10)  
# AUC_S1_TN3part_COP_6_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,6,sniptime=10)  
# AUC_S1_TN3part_COP_7_10sec=AUC_behavior_snipper_TN3part('S1',data_S1,7,sniptime=10)  

# AUC_S2_TN3part_COP_1_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,1,sniptime=10)  
# AUC_S2_TN3part_COP_2_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,2,sniptime=10)  
# AUC_S2_TN3part_COP_3_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,3,sniptime=10)  
# AUC_S2_TN3part_COP_4_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,4,sniptime=10)  
# AUC_S2_TN3part_COP_5_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,5,sniptime=10)  
# AUC_S2_TN3part_COP_6_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,6,sniptime=10)  
# AUC_S2_TN3part_COP_7_10sec=AUC_behavior_snipper_TN3part('S2',data_S2,7,sniptime=10)  

# AUC_result_TN3part_COP_1_10sec=AUC_result_behavior_snipper_TN3part(1,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_2_10sec=AUC_result_behavior_snipper_TN3part(2,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_3_10sec=AUC_result_behavior_snipper_TN3part(3,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_4_10sec=AUC_result_behavior_snipper_TN3part(4,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_5_10sec=AUC_result_behavior_snipper_TN3part(5,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_6_10sec=AUC_result_behavior_snipper_TN3part(6,sniptime=10,graphtitle="AUC_TN3part_10sec")  
# AUC_result_TN3part_COP_7_10sec=AUC_result_behavior_snipper_TN3part(7,sniptime=10,graphtitle="AUC_TN3part_10sec")  

# ############# OVERALL RESULTS ################

# ##########################################################################################################################
# ##########################################################################################################################
# ##########################################################################################################################

# # Create a list with which rat is inexperienced and which is experienced
# list_id_naive = []
# list_id_naive_plus = []
# list_temp1=[]
# list_temp2=[]
# list_temp3=[]
# list_temp4=[]
# list_temp5=[]
# list_temp6=[]
# for key,parameters in my_dict_behavior["dict_results_T"].items():
#     for parameter,value in parameters.items():
#        if 'COP1' in key: 
#            if parameter == 'TN_Ejaculation':
#                if value > 0:
#                    list_id_naive.append(key)
#                    list_id_naive_plus.append(key)
#                if value == 0:
#                    list_temp1.append(key[0:3])
#                    list_id_naive_plus.append(key)

#        if 'COP2' in key: 
#            for i in list_temp1:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)
#                        if value == 0:
#                            list_temp2.append(i)
#                            list_id_naive_plus.append(key)

#        if 'COP3' in key: 
#            for i in list_temp2:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)
#                        if value == 0:
#                            list_temp3.append(i)
#                            list_id_naive_plus.append(key)

#        if 'COP4' in key: 
#            for i in list_temp3:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)
#                        if value == 0:
#                            list_temp4.append(i)
#                            list_id_naive_plus.append(key)

#        if 'COP5' in key: 
#            for i in list_temp4:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)
#                        if value == 0:
#                            list_temp5.append(i)
#                            list_id_naive_plus.append(key)

#        if 'COP6' in key: 
#            for i in list_temp5:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)
#                        if value == 0:
#                            list_temp6.append(i)
#                            list_id_naive_plus.append(key)

#        if 'COP7' in key: 
#            for i in list_temp6:
#                if i in key:
#                    if parameter == 'TN_Ejaculation':
#                        if value > 0:
#                            list_id_naive.append(key)
#                            list_id_naive_plus.append(key)

# list_id_inexp = []
# list_id_exp = []
# list_id_afterbreak = []
# for i in list_id_naive:
#     if 'COP1' in i:
#         temp= i[0:3]
#         list_id_exp.append('%sCOP4'%temp)
#         list_id_exp.append('%sCOP5'%temp)
#         list_id_exp.append('%sCOP6'%temp)
#         list_id_inexp.append('%sCOP2'%temp)
#         list_id_inexp.append('%sCOP3'%temp)

#     if 'COP2' in i:
#         temp= i[0:3]
#         list_id_exp.append('%sCOP5'%temp)
#         list_id_exp.append('%sCOP6'%temp)
#         list_id_inexp.append('%sCOP3'%temp)
#         list_id_inexp.append('%sCOP4'%temp)
#     if 'COP3' in i:
#         temp= i[0:3]
#         list_id_exp.append('%sCOP6'%temp)
#         list_id_inexp.append('%sCOP4'%temp)
#         list_id_inexp.append('%sCOP5'%temp)
#     if 'COP4' in i:
#         temp= i[0:3]
#         list_id_inexp.append('%sCOP5'%temp)
#         list_id_inexp.append('%sCOP6'%temp)
#     if 'COP5' in i:
#         temp= i[0:3]
#         list_id_inexp.append('%sCOP6'%temp)

# # Create a list with ids for COP7
# for i in S1_GCaMP6_COP_7.keys():
#     list_id_afterbreak.append(i)
    
# # Delete the non-existing ids from the lists
# for i in list_id_naive:
#     if i not in list_id:
#         list_id_naive.remove(i)

# for i in list_id_inexp:
#     if i not in list_id:
#         list_id_inexp.remove(i)

# for i in list_id_exp:
#     if i not in list_id:
#         list_id_exp.remove(i)

# list_id_exp_all=list_id_inexp+list_id_exp
        
# # Definition to remove empty lists from nested dictionary
# def remove_empty_arrays_from_dict(dict_to_check):

#     for key in list(dict_to_check.keys()):
#         val = dict_to_check[key]
#         if type(val) == dict:
#             remove_empty_arrays_from_dict(val)
#         if type(val) == list:
#             if (len(val) == 0): #or (np.isnan(val).any()):
#                 print("Removing key:", key)
#                 del dict_to_check[key]
#             if (len(val) >= 1): #or (np.isnan(val).any()):
#                 dict_to_check[key] = [ele for ele in dict_to_check[key] if ele != []]
        
# # Make definition that creates a mean signal per rat for the naive, inexperienced, experienced and after break sessions
# def experience_means(series,groups=3,beh_list=list_sex_MB):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     groups : float -> Default = 3
#         Add the number of group you would like to divide
#         e.g. 3 for naive-experienced-after break or 4 if inexperienced is included
#     beh_list : list -> Default = list_sex_MB
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt

#     Returns
#     -------
#     Dictionary (Means per experience level)
#     Dictionary with the baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     """
#     print("Start experience_means")

#     d1="%s_GCaMP6_COP_1"%series      
#     dictionary1= eval(d1)

#     d2="%s_GCaMP6_COP_2"%series      
#     dictionary2= eval(d2)

#     d3="%s_GCaMP6_COP_3"%series      
#     dictionary3= eval(d3)

#     d4="%s_GCaMP6_COP_4"%series      
#     dictionary4= eval(d4)

#     d5="%s_GCaMP6_COP_5"%series      
#     dictionary5= eval(d5)

#     d6="%s_GCaMP6_COP_6"%series      
#     dictionary6= eval(d6)

#     d7="%s_GCaMP6_COP_7"%series      
#     dictionary7= eval(d7)

#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in beh_list:
#         temp1='Start %s'%beh
#         temp2='End %s'%beh
#         list_means.append(temp1)
#         list_means.append(temp2)

#     dict_of_means={}  
#     dict_of_ratmeans={}
    
#     if groups==4:
#         exp=['Naive','Inexperienced','Experienced','After break']
#     else:
#         exp=['Naive','Experienced','After break']

#     stats=['mean','sem']
    
#     for e in exp:
#         dict_of_means[e]={}
#     for i in list_id_naive:
#         rat=i[0:3]
#         dict_of_means['Naive'][rat]={}
#         for beh in list_means:
#             dict_of_means['Naive'][rat][beh]=[]
#     if groups == 4:
#         for i in list_id_inexp:
#             rat=i[0:3]
#             dict_of_means['Inexperienced'][rat]={}
#             for beh in list_means:
#                 dict_of_means['Inexperienced'][rat][beh]=[]
#         for i in list_id_exp:
#             rat=i[0:3]
#             dict_of_means['Experienced'][rat]={}
#             for beh in list_means:
#                 dict_of_means['Experienced'][rat][beh]=[]
#     else:
#         for i in list_id_exp_all:
#             rat=i[0:3]
#             dict_of_means['Experienced'][rat]={}
#             for beh in list_means:
#                 dict_of_means['Experienced'][rat][beh]=[]
        
#     # for i in dictionary7.keys():
#     for i in list_id_afterbreak:
#         rat=i[0:3]
#         dict_of_means['After break'][rat]={}
#         for beh in list_means:
#             dict_of_means['After break'][rat][beh]=[]

#     # Make empty dictionary for the ratmeans
#     for e in exp:
#         dict_of_ratmeans[e]={}
#         for beh in list_means:
#             dict_of_ratmeans[e][beh]={}
#             for stat in stats:
#                 dict_of_ratmeans[e][beh][stat]={}

#     # Fill in dictionary
#     for beh in list_means:
#         for stat in stats:
#             for i in list_id_naive:
#                 rat=i[0:3]
#                 dict_of_ratmeans['Naive'][beh][stat][rat]=[]
#             if groups==4:
#                 for i in list_id_inexp:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Inexperienced'][beh][stat][rat]=[]
#                 for i in list_id_exp:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Experienced'][beh][stat][rat]=[]
#             else:
#                 for i in list_id_exp_all:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Experienced'][beh][stat][rat]=[]

#             for i in dictionary7.keys():
#                 rat=i[0:3]
#                 dict_of_ratmeans['After break'][beh][stat][rat]=[]

#     for keys,behavior in dictionary1.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary1[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary1[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary1[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary1[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary1[keys][beh])

#     for keys,behavior in dictionary2.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary2[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary2[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary2[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary2[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary2[keys][beh])

#     for keys,behavior in dictionary3.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary3[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary3[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary3[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary3[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary3[keys][beh])

#     for keys,behavior in dictionary4.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary4[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary4[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary4[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary4[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary4[keys][beh])
    
#     for keys,behavior in dictionary5.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary5[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary5[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary5[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary5[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary5[keys][beh])

#     for keys,behavior in dictionary6.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary6[keys]:
#                     if keys in list_id_naive:
#                         rat=keys[0:3]
#                         dict_of_means['Naive'][rat][beh].append(dictionary6[keys][beh])
#                     if groups==4:
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][rat][beh].append(dictionary6[keys][beh])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary6[keys][beh])
#                     else:
#                         if keys in list_id_exp_all:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][rat][beh].append(dictionary6[keys][beh])
    
#     for keys,behavior in dictionary7.items():
#         for beh,value in behavior.items():
#             if beh in list_means:
#                 if beh in dictionary7[keys]:
#                     rat=keys[0:3]
#                     dict_of_means['After break'][rat][beh].append(dictionary7[keys][beh])
    
#     # remove_empty_arrays_from_dict(dict_of_means)

#     for e in dict_of_means.keys():
#         for rat in dict_of_means[e].keys():
#             for beh in list_means:
#                 if dict_of_means[e][rat][beh]:
#                     yarray = np.array(dict_of_means[e][rat][beh])
#                     y = np.mean(yarray, axis=0)
#                     yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
    
#                     dict_of_ratmeans[e][beh]['mean'][rat]=y
#                     dict_of_ratmeans[e][beh]['sem'][rat]=yerror

#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     return dict_of_ratmeans


# #############################################
# # Make definition that creates a mean signal per rat for the inexperienced and experienced sessions
# def results_experience_means(series,groups=3,beh_list=list_sex_MB,sniptime_pre=10,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     groups : float -> Default = 3
#         Add the number of group you would like to divide
#         e.g. 3 for naive-experienced-after break or 4 if inexperienced is included
#     beh_list : list -> Default = list_sex_MB
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     sniptime_pre : integer -> Default = 10
#         Add the analyzed amount of seconds before and after the start of behavior
#     output : string
#         add the output "dFF" or "zcore" -> Default = 'dFF'
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.
    
#     Returns
#     -------
#     Dictionary & Figures (Means per experience level)
#     Dictionary with the baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the dFF signal during the defined "baseline" period, and correcting 
#     the real dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Figures of the mean dFF signals aligned to the behaviors, plus sem-bands, per experience level
#     """
    
#     print("Start results_experience_means")

#     dictionary=experience_means(series,groups=groups,beh_list=beh_list)
    
#     list_means=[]
#     for beh in beh_list:
#         temp1='Start %s'%beh
#         temp2='End %s'%beh
#         list_means.append(temp1)
#         list_means.append(temp2)

#     dict_of_totalmeans={}
#     dict_of_means={}
#     if groups==4:
#         exp=['Naive','Inexperienced','Experienced','After break']
#     else:
#         exp=['Naive','Experienced','After break']

#     stats=['mean','sem']

#     ymax=[]
#     ymin=[]
    
#     for e in exp:
#         dict_of_totalmeans[e]={}
#         dict_of_means[e]={}
#         for beh in list_means:
#             dict_of_means[e][beh]=[]
#             dict_of_totalmeans[e][beh]={}
#             for stat in stats:
#                 dict_of_totalmeans[e][beh][stat]=[]

#     for exp,behavior in dictionary.items():
#         for beh,stats in behavior.items():
#             for stat,rats in stats.items():
#                 for rat,value in rats.items():
#                     if beh in list_means:
#                         if stat == 'mean':
#                             dict_of_means[exp][beh].append(value)
   
#     for exp,behaviors in dict_of_means.items():
#         for beh,value in behaviors.items():
#             for beh in list_means:
#                 if dict_of_means[exp][beh]:
#                     max2 = np.max([np.size(x) for x in dict_of_means[exp][beh]])
#                     dict_of_means[exp][beh]=[snip for snip in dict_of_means[exp][beh] if np.size(snip)==max2]                    

#                     yarray = np.array(dict_of_means[exp][beh])
#                     yarray2 = yarray.astype(float)
#                     y = np.mean(yarray2, axis=0)
#                     yerror = np.std(yarray2, axis=0)/np.sqrt(len(yarray2))
        
#                     min_ymin = np.min(y)
#                     max_ymax = np.max(y)
                    
#                     min_yerrormin = np.min(yerror)
#                     max_yerrormax = np.max(yerror)
                    
#                     ymax.append(max_ymax+max_yerrormax)
#                     ymin.append(min_ymin-min_yerrormin)
   
#                     length=y.size
            
#                     # Put the data in the dictionaries
#                     dict_of_totalmeans[exp][beh]['mean']=y
#                     dict_of_totalmeans[exp][beh]['sem']=yerror
        
#                     # Get fs from dictionary of processed data
#                     for rat,value in my_dict_process["dict_dFF_GCaMP6_COP_1"].items():        
#                         fs=my_dict_process["dict_dFF_GCaMP6_COP_1"][rat]['fs']
#                         x = np.linspace(1, length, length)/fs - sniptime_pre

#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if beh_list==list_other_behaviors:
#             if not os.path.isdir(directory_TDT_results_other):
#                 os.mkdir(directory_TDT_results_other)
            
#             os.chdir(directory_TDT_results_other)
            
#         else:
#             if not os.path.isdir(directory_TDT_results_parameters):
#                 os.mkdir(directory_TDT_results_parameters)
    
#             os.chdir(directory_TDT_results_parameters)

#         if groups ==4:
#             for beh in list_means:
#                 sns.set(style="ticks", rc=custom_params)
#                 fig, axs = plt.subplots(1,4, figsize=(18,6), sharex=True, sharey=True)
                
#                 if np.any(dict_of_totalmeans['Naive'][beh]['mean']):
#                     axs[0].plot(x, dict_of_totalmeans['Naive'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[0].fill_between(x, dict_of_totalmeans['Naive'][beh]['mean']-dict_of_totalmeans['Naive'][beh]['sem'], 
#                                           dict_of_totalmeans['Naive'][beh]['mean']+dict_of_totalmeans['Naive'][beh]['sem'], color=color_shadow, alpha=0.4)
    
#                     # Plotting the start line & appropiate axes
#                     xx=np.arange(-sniptime_pre,sniptime_pre+1,2).tolist()
#                     if output=="dFF":
#                         y_max=np.max(ymax)
#                         y_max= round(y_max / 0.1) * 0.1
        
#                         y_min=np.min(ymin)
#                         y_min= round(y_min / 0.1) * 0.1
#                         yy=np.arange(y_min-0.1,y_max+0.15,0.1).tolist()
#                     else:
#                         y_max=np.max(ymax)
#                         y_max= round(y_max / 2) * 2
        
#                         y_min=np.min(ymin)
#                         y_min= round(y_min / 2) * 2
#                         yy=np.arange(y_min-1,y_max+1,1).tolist()
    
#                     axs[0].set_xticks(xx)
#                     axs[0].set_yticks(yy)
#                     if output=='dFF':
#                         axs[0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                     else:
#                         axs[0].set_ylabel('z-score',fontsize=16)
#                     axs[0].set_title('Naive',fontsize=16)
#                     axs[0].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 if np.any(dict_of_totalmeans['Inexperienced'][beh]['mean']):
#                     axs[1].plot(x, dict_of_totalmeans['Inexperienced'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[1].fill_between(x, dict_of_totalmeans['Inexperienced'][beh]['mean']-dict_of_totalmeans['Inexperienced'][beh]['sem'], 
#                                           dict_of_totalmeans['Inexperienced'][beh]['mean']+dict_of_totalmeans['Inexperienced'][beh]['sem'], color=color_shadow, alpha=0.4)
        
#                     # Plotting the start line
#                     axs[1].set_xticks(xx)
#                     axs[1].set_yticks(yy)
#                     axs[1].set_title('Inexperienced',fontsize=16)
#                     axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                     axs[1].spines['left'].set_visible(False)                
#                     axs[1].tick_params(left=False)          
#                 else:
#                     axs[1].spines['left'].set_visible(False)                
#                     axs[1].tick_params(left=False)          
#                     axs[1].set_title('Inexperienced',fontsize=16)
#                     axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
        
#                 if np.any(dict_of_totalmeans['Experienced'][beh]['mean']):
#                     axs[2].plot(x, dict_of_totalmeans['Experienced'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[2].fill_between(x, dict_of_totalmeans['Experienced'][beh]['mean']-dict_of_totalmeans['Experienced'][beh]['sem'], 
#                                           dict_of_totalmeans['Experienced'][beh]['mean']+dict_of_totalmeans['Experienced'][beh]['sem'], color=color_shadow, alpha=0.4)
        
#                     # Plotting the start line
#                     axs[2].set_xticks(xx)
#                     axs[2].set_yticks(yy)
#                     axs[2].set_title('Experienced',fontsize=16)
#                     axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                     axs[2].spines['left'].set_visible(False)                
#                     axs[2].tick_params(left=False)          
#                 else:
#                     axs[2].spines['left'].set_visible(False)                
#                     axs[2].tick_params(left=False)          
#                     axs[2].set_title('Experienced',fontsize=16)
#                     axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 if np.any(dict_of_totalmeans['After break'][beh]['mean']):
#                     axs[3].plot(x, dict_of_totalmeans['After break'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[3].fill_between(x, dict_of_totalmeans['After break'][beh]['mean']-dict_of_totalmeans['After break'][beh]['sem'], 
#                                           dict_of_totalmeans['After break'][beh]['mean']+dict_of_totalmeans['After break'][beh]['sem'], color=color_shadow, alpha=0.4)
        
#                     # Plotting the start line
#                     axs[3].set_xticks(xx)
#                     axs[3].set_yticks(yy)
#                     axs[3].set_title('After break',fontsize=16)
#                     axs[3].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[3].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                     axs[3].spines['left'].set_visible(False)                
#                     axs[3].tick_params(left=False)          
#                 else:
#                     axs[3].spines['left'].set_visible(False)                
#                     axs[3].tick_params(left=False)          
#                     axs[3].set_title('After break',fontsize=16)
#                     axs[3].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[3].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#                 plt.subplots_adjust(hspace=0.0)
#                 plt.savefig("%s %s.png"%(graphtitle,beh))
#                 plt.close(fig)    
#         else:
#             for beh in list_means:
#                 sns.set(style="ticks", rc=custom_params)
#                 fig, axs = plt.subplots(1,3, figsize=(18,6), sharex=True, sharey=True)
                
#                 if np.any(dict_of_totalmeans['Naive'][beh]['mean']):
#                     axs[0].plot(x, dict_of_totalmeans['Naive'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[0].fill_between(x, dict_of_totalmeans['Naive'][beh]['mean']-dict_of_totalmeans['Naive'][beh]['sem'], 
#                                           dict_of_totalmeans['Naive'][beh]['mean']+dict_of_totalmeans['Naive'][beh]['sem'], color=color_shadow, alpha=0.4)
    
#                     # Plotting the start line & appropiate axes
#                     xx=np.arange(-sniptime_pre,sniptime_pre+1,2).tolist()
#                     if output=="dFF":
#                         y_max=np.max(ymax)
#                         y_max= round(y_max / 0.1) * 0.1
        
#                         y_min=np.min(ymin)
#                         y_min= round(y_min / 0.1) * 0.1
#                         yy=np.arange(y_min-0.1,y_max+0.15,0.1).tolist()
                       
#                         # #################################
#                         # # adaptation for other behavior
#                         # yy=np.arange(-0.3,0.5,0.15).tolist()
#                         # #################################

#                     else:
#                         y_max=np.max(ymax)
#                         y_max= round(y_max / 2) * 2
        
#                         y_min=np.min(ymin)
#                         y_min= round(y_min / 2) * 2
#                         yy=np.arange(y_min-1,y_max+1,1).tolist()
                    
                    
#                     axs[0].set_xticks(xx)
#                     axs[0].set_yticks(yy)
#                     if output=='dFF':
#                         axs[0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                     else:
#                         axs[0].set_ylabel('z-score',fontsize=16)
#                     axs[0].set_title('Naive',fontsize=16)
#                     axs[0].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 if np.any(dict_of_totalmeans['Experienced'][beh]['mean']):
#                     axs[1].plot(x, dict_of_totalmeans['Experienced'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[1].fill_between(x, dict_of_totalmeans['Experienced'][beh]['mean']-dict_of_totalmeans['Experienced'][beh]['sem'], 
#                                           dict_of_totalmeans['Experienced'][beh]['mean']+dict_of_totalmeans['Experienced'][beh]['sem'], color=color_shadow, alpha=0.4)
        
#                     # Plotting the start line
#                     axs[1].set_xticks(xx)
#                     axs[1].set_yticks(yy)
#                     axs[1].set_title('Experienced',fontsize=16)
#                     axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                     axs[1].spines['left'].set_visible(False)                
#                     axs[1].tick_params(left=False)          
#                 else:
#                     axs[1].spines['left'].set_visible(False)                
#                     axs[1].tick_params(left=False)          
#                     axs[1].set_title('Experienced',fontsize=16)
#                     axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 if np.any(dict_of_totalmeans['After break'][beh]['mean']):
#                     axs[2].plot(x, dict_of_totalmeans['After break'][beh]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                     axs[2].fill_between(x, dict_of_totalmeans['After break'][beh]['mean']-dict_of_totalmeans['After break'][beh]['sem'], 
#                                           dict_of_totalmeans['After break'][beh]['mean']+dict_of_totalmeans['After break'][beh]['sem'], color=color_shadow, alpha=0.4)
        
#                     # Plotting the start line
#                     axs[2].set_xticks(xx)
#                     axs[2].set_yticks(yy)
#                     axs[2].set_title('After break',fontsize=16)
#                     axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                     axs[2].spines['left'].set_visible(False)                
#                     axs[2].tick_params(left=False)          
#                 else:
#                     axs[2].spines['left'].set_visible(False)                
#                     axs[2].tick_params(left=False)          
#                     axs[2].set_title('After break',fontsize=16)
#                     axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                     axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#                 # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#                 plt.subplots_adjust(hspace=0.0)
#                 plt.savefig("%s %s.png"%(graphtitle,beh))
#                 plt.close(fig)    

#         # Change directory back
#         os.chdir(directory)

#     print("results_experience_means done")
#     return dict_of_totalmeans

# #################################################################################################################
# ################### ANALYSIS ####################################################################################
# #################################################################################################################

# # Make dictionaries and figures of the final results per experience phase
# # Default = 3 groups (naieve, exp, after break), change to groups=4 if you want inexperienced group in addition
# S1_results=results_experience_means('S1',groups=3,graphtitle='Final S1')
# S2_results=results_experience_means('S2',groups=3,graphtitle='Final S2')
# T_results=results_experience_means('T',groups=3,graphtitle='Final T')

# # # # Other behaviors -> Needs adaptation of yy values (turn off, or open standardization), and run temporary the behavioral snipper.
# # S1_results=results_experience_means('S1',graphtitle='Final S1',beh_list=list_other_behaviors)
# # S2_results=results_experience_means('S2',graphtitle='Final S2',beh_list=list_other_behaviors)
# # T_results=results_experience_means('T',graphtitle='Final T',beh_list=list_other_behaviors)

# # Make figures of different efficiencies

# # Create a list with which rat is slow,middle,fast ejaculator for inexperienced and experienced sessions
# list_id_inexp_slow = []
# list_id_exp_slow = []
# list_id_inexp_normal = []
# list_id_exp_normal = []
# list_id_inexp_fast = []
# list_id_exp_fast = []

# for s in list_slowejac:
#     if s in list_id_naive_plus:
#         list_id_inexp_slow.append(s)
# for n in list_normalejac:
#     if n in list_id_naive_plus:
#         list_id_inexp_normal.append(n)
# for f in list_fastejac:
#     if f in list_id_naive_plus:
#         list_id_inexp_fast.append(f)

# for s in list_slowejac:
#     if s not in list_id_naive_plus:
#         list_id_exp_slow.append(s)
# for n in list_normalejac:
#     if n not in list_id_naive_plus:
#         list_id_exp_normal.append(n)
# for f in list_fastejac:
#     if f not in list_id_naive_plus:
#         list_id_exp_fast.append(f)

# # Make lists from efficiency parameter dictionaries      
# def parameter_list_maker(series,parameter,performance):
#     """    
#     Note -> Keep in mind that when talking about e.g latency, a "low performer" actually had a short ejaculation latency, and is in 
#        that perfective a "high perfomer", despite being called a low performer for analysis.

#     Parameters
#     ----------
#     series : string
#         Fill the ejaculation series that is analyzed.
#         e.g. "T", "S1", "S2"
#     parameter : string
#         Fill in parameter that is analyzed.
#         e.g. "TN_copulations","IR","III" etc.
#     performance : string
#         Fill in level of performance that is analyzed.
#         e.g. "Low", "Middle", "High"

#     Returns
#     -------
#     list_parameter
#     List with the rat-cop-ids that fitted in the level of performance that was analyzed.
#     Performance was calculated per coptest, by taking the mean plus and minus the standard deviation.
#     All rats performing below this cut-off are considered low performers, all within the cut-off, middle performers,
#     and all higher than the cut-off high performers.

#     """
#     print("Start parameter_list_maker %s %s"%(parameter,performance))
    
#     d="dict_parameters_%s"%series      
#     dictionary= eval(d)

#     dictionary
    
#     list_parameter=[]
    
#     for para,coptest in dictionary.items():
#         for cop,endos in coptest.items():
#             for endo, value in endos.items():
#                 if para == parameter:
#                     if endo == performance:
#                         if value != []:
#                             for i in value:
#                                 list_parameter.append(i)
    
#     return list_parameter

# def experience_list_maker(list_pre,experience):
#     """
#     Note -> Keep in mind that when talking about e.g latency, a "low performer" actually had a short ejaculation latency, and is in 
#        that perfective a "high perfomer", despite being called a low performer for analysis.

#     Parameters
#     ----------
#     list_pre : list
#         Fill in the list that need splitting up.
#     experience : string
#         Fill in the experience level.
#         e.g. "Naive" or "Experienced"

#     Returns
#     -------
#     list
#     List with rat-cop-ids that fitted in the level of performance that was analyzed.
#     Now splitted up by "naive" and "experienced", with naive consisting of only the sessions in which the rat achieved their
#     first ejaculations. Naive_plus includes also the session before 1st ejaculatoin, and all other copulation sessions are included in "experienced".
#     Performance was calculated per coptest, by taking the mean plus and minus the standard deviation.
#     All rats performing below this cut-off are considered low performers, all within the cut-off, middle performers,
#     and all higher than the cut-off high performers.
#     """
   
#     list_id = []

#     if experience == "Naive_plus":    
#         for s in list_pre:
#             if s in list_id_naive_plus:
#                 list_id.append(s)
#     if experience == "Naive":    
#         for s in list_pre:
#             if s in list_id_naive:
#                 list_id.append(s)
#     if experience == "Experienced":    
#         for i in list_pre:
#             if i not in list_id_naive_plus:
#                 list_id.append(i)
    
#     return list_id

# def figure_from_3_lists(series,list1,list2,list3,cond1,cond2,cond3,
#                         list_beh=list_sex,sniptime=10,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Fill the ejaculation series that is analyzed.
#         e.g. "T", "S1", "S2"
#     list1-3 : list
#         Fill in the 3 lists you want to visualize in a figure
#         e.g. list_III_low,list_III_middle,list_III_high,
#     cond1-3 : string
#         Fill in the different conditions you explore (usually performance)
#         e.g. "Low", "Middle", "High" -> this is the subtitle used in the figure
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     sniptime_pre : integer -> Default = 10
#         Add the analyzed amount of seconds before and after the start of behavior
#     output : string
#         add the output "dFF" or "zcore" -> Default = 'dFF'
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.

#     Returns
#     -------
#     Figure with 3 horizontal subplots
#     """

#     print("Start figure_from_3_lists")

#     d1="%s_GCaMP6_COP_1"%series      
#     dictionary1= eval(d1)

#     d2="%s_GCaMP6_COP_2"%series      
#     dictionary2= eval(d2)

#     d3="%s_GCaMP6_COP_3"%series      
#     dictionary3= eval(d3)

#     d4="%s_GCaMP6_COP_4"%series      
#     dictionary4= eval(d4)

#     d5="%s_GCaMP6_COP_5"%series      
#     dictionary5= eval(d5)

#     d6="%s_GCaMP6_COP_6"%series      
#     dictionary6= eval(d6)

#     d7="%s_GCaMP6_COP_7"%series      
#     dictionary7= eval(d7)
    
#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in list_beh:
#         temp1='Start %s'%beh
#         # temp2='End %s'%beh
#         list_means.append(temp1)
#         # list_means.append(temp2)
    
#     list_cond=[cond1,cond2,cond3]
#     stats=['mean','sem']
    
#     dict_of_means={}  
#     dict_of_ratmeans={}
#     dict_of_totalmeans={}
    
#     for beh in list_means:
#         dict_of_means[beh]={}
#         dict_of_ratmeans[beh]={}
#         dict_of_totalmeans[beh]={}
#         for cond in list_cond:
#             dict_of_means[beh][cond]={}
#             dict_of_ratmeans[beh][cond]=[]
#             dict_of_totalmeans[beh][cond]={}
#             for stat in stats:
#                 dict_of_totalmeans[beh][cond][stat]=[]
    
#     for beh in list_means:
#         for cond in list_cond:
#             for i in list1:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond1][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list2:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond2][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list3:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond3][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
                        
    
#     for beh,condition in dict_of_means.items():
#         for cond,rats in condition.items():
#             for rat, value in rats.items():
#                 yarray = np.array(dict_of_means[beh][cond][rat])
#                 y = np.mean(yarray, axis=0)

#                 dict_of_ratmeans[beh][cond].append(y)
    
#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     ymax=[]
#     ymin=[]

#     for beh,condition in dict_of_ratmeans.items():
#         for cond,value in condition.items():
#             if dict_of_ratmeans[beh][cond]:
#                 max2 = np.max([np.size(x) for x in dict_of_ratmeans[beh][cond]])
#                 dict_of_ratmeans[beh][cond]=[snip for snip in dict_of_ratmeans[beh][cond] if np.size(snip)==max2]                    

#                 yarray = np.array(dict_of_ratmeans[beh][cond])
#                 y = np.mean(value, axis=0)
#                 yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
               
#                 min_ymin = np.min(y)
#                 max_ymax = np.max(y)
                
#                 min_yerrormin = np.min(yerror)
#                 max_yerrormax = np.max(yerror)
                
#                 ymax.append(max_ymax+max_yerrormax)
#                 ymin.append(min_ymin-min_yerrormin)
   
#                 length=y.size
    
#                 dict_of_totalmeans[beh][cond]['mean']=y
#                 dict_of_totalmeans[beh][cond]['sem']=yerror
  
#                 # Get fs from dictionary of processed data
#                 for rat,value in my_dict_process["dict_dFF_GCaMP6_COP_1"].items():        
#                     fs=my_dict_process["dict_dFF_GCaMP6_COP_1"][rat]['fs']
#                     x = np.linspace(1, length, length)/fs - sniptime

#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_results_parameters):
#             os.mkdir(directory_TDT_results_parameters)

#         os.chdir(directory_TDT_results_parameters)

#         for beh in list_means:
#             sns.set(style="ticks", rc=custom_params)
#             fig, axs = plt.subplots(1,3, figsize=(18,6), sharex=True, sharey=True)
            
#             if np.any(dict_of_totalmeans[beh][cond1]['mean']):
#                 axs[0].plot(x, dict_of_totalmeans[beh][cond1]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[0].fill_between(x, dict_of_totalmeans[beh][cond1]['mean']-dict_of_totalmeans[beh][cond1]['sem'], 
#                                       dict_of_totalmeans[beh][cond1]['mean']+dict_of_totalmeans[beh][cond1]['sem'], color=color_shadow, alpha=0.4)

#                 # Plotting the start line & appropiate axes
#                 xx=np.arange(-sniptime,sniptime+1,2).tolist()
#                 if output=="dFF":
#                     y_max=np.max(ymax)
#                     y_max= round(y_max / 0.1) * 0.1
    
#                     y_min=np.min(ymin)
#                     y_min= round(y_min / 0.1) * 0.1
#                     yy=np.arange(y_min-0.1,y_max+0.15,0.1).tolist()
#                 else:
#                     y_max=np.max(ymax)
#                     y_max= round(y_max / 2) * 2
    
#                     y_min=np.min(ymin)
#                     y_min= round(y_min / 2) * 2
#                     yy=np.arange(y_min-1,y_max+1,1).tolist()

#                 axs[0].set_xticks(xx)
#                 axs[0].set_yticks(yy)
#                 if output=='dFF':
#                     axs[0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                 else:
#                     axs[0].set_ylabel('z-score',fontsize=16)
#                 axs[0].set_title(cond1,fontsize=16)
#                 axs[0].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)

#             if np.any(dict_of_totalmeans[beh][cond2]['mean']):
#                 axs[1].plot(x, dict_of_totalmeans[beh][cond2]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[1].fill_between(x, dict_of_totalmeans[beh][cond2]['mean']-dict_of_totalmeans[beh][cond2]['sem'], 
#                                       dict_of_totalmeans[beh][cond2]['mean']+dict_of_totalmeans[beh][cond2]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[1].set_xticks(xx)
#                 axs[1].set_yticks(yy)
#                 axs[1].set_title(cond2,fontsize=16)
#                 axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[1].spines['left'].set_visible(False)                
#                 axs[1].tick_params(left=False)          
#             else:
#                 axs[1].spines['left'].set_visible(False)                
#                 axs[1].tick_params(left=False)          
#                 axs[1].set_title(cond2,fontsize=16)
#                 axs[1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#             if np.any(dict_of_totalmeans[beh][cond3]['mean']):
#                 axs[2].plot(x, dict_of_totalmeans[beh][cond3]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[2].fill_between(x, dict_of_totalmeans[beh][cond3]['mean']-dict_of_totalmeans[beh][cond3]['sem'], 
#                                       dict_of_totalmeans[beh][cond3]['mean']+dict_of_totalmeans[beh][cond3]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[2].set_xticks(xx)
#                 axs[2].set_yticks(yy)
#                 axs[2].set_title(cond3,fontsize=16)
#                 axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[2].spines['left'].set_visible(False)                
#                 axs[2].tick_params(left=False)          
#             else:
#                 axs[2].spines['left'].set_visible(False)                
#                 axs[2].tick_params(left=False)          
#                 axs[2].set_title(cond3,fontsize=16)
#                 axs[2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)


#             # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#             plt.subplots_adjust(hspace=0.0)
#             plt.savefig("%s %s.png"%(graphtitle,beh))
#             plt.close(fig)    
             
#         # Change directory back
#         os.chdir(directory)
                        
#     return dict_of_totalmeans


# def figure_from_2x3_lists(series,list1,list2,list3,list4,list5,list6,cond1,cond2,cond3,cond4,cond5,cond6,
#                           list_beh=list_sex,sniptime=10,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Fill the ejaculation series that is analyzed.
#         e.g. "T", "S1", "S2"
#     list1-6 : list
#         Fill in the 6 lists you want to visualize in a figure
#         e.g. list_III_low_naive,list_III_middle_naive,list_III_high_naive,list_III_low_exp,list_III_middle_exp,list_III_high_exp
#     cond1-6 : string
#         Fill in the different conditions you explore (usually performance)
#         e.g. "Low", "Middle", "High" -> this is the subtitle used in the figure
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     sniptime : integer
#         Add the analyzed amount of seconds before and after the start of behavior
#     output : string
#         add the output "dFF" or "zcore" -> Default = 'dFF'
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.

#     Returns
#     -------
#     Figure with 6 subplots, 2 vertical columns and 3 horizontal columns
#     """
#     print("Start figure_from_2x3_lists")
    
#     d1="%s_GCaMP6_COP_1"%series      
#     dictionary1= eval(d1)

#     d2="%s_GCaMP6_COP_2"%series      
#     dictionary2= eval(d2)

#     d3="%s_GCaMP6_COP_3"%series      
#     dictionary3= eval(d3)

#     d4="%s_GCaMP6_COP_4"%series      
#     dictionary4= eval(d4)

#     d5="%s_GCaMP6_COP_5"%series      
#     dictionary5= eval(d5)

#     d6="%s_GCaMP6_COP_6"%series      
#     dictionary6= eval(d6)

#     d7="%s_GCaMP6_COP_7"%series      
#     dictionary7= eval(d7)

#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in list_beh:
#         temp1='Start %s'%beh
#         # temp2='End %s'%beh
#         list_means.append(temp1)
#         # list_means.append(temp2)
    
#     list_cond=[cond1,cond2,cond3,cond4,cond5,cond6]
#     stats=['mean','sem']
    
#     dict_of_means={}  
#     dict_of_ratmeans={}
#     dict_of_totalmeans={}
    
#     for beh in list_means:
#         dict_of_means[beh]={}
#         dict_of_ratmeans[beh]={}
#         dict_of_totalmeans[beh]={}
#         for cond in list_cond:
#             dict_of_means[beh][cond]={}
#             dict_of_ratmeans[beh][cond]=[]
#             dict_of_totalmeans[beh][cond]={}
#             for stat in stats:
#                 dict_of_totalmeans[beh][cond][stat]=[]
    
#     for beh in list_means:
#         for cond in list_cond:
#             for i in list1:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond1][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond1][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list2:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond2][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond2][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list3:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond3][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond3][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list4:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond4][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond4][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list5:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond5][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond5][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
#             for i in list6:
#                 temp=i[0:3]
#                 dict_of_means[beh][cond6][temp]=[]
#                 if 'COP1' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary1[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP2' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary2[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP3' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary3[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP4' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary4[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP5' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary5[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP6' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary6[i][beh])
#                     except:
#                         print("missing value")
#                 if 'COP7' in i:
#                     try:
#                         dict_of_means[beh][cond6][temp].append(dictionary7[i][beh])
#                     except:
#                         print("missing value")
                        
    
#     for beh,condition in dict_of_means.items():
#         for cond,rats in condition.items():
#             for rat, value in rats.items():
#                 yarray = np.array(dict_of_means[beh][cond][rat])
#                 y = np.mean(yarray, axis=0)

#                 dict_of_ratmeans[beh][cond].append(y)
    
#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     ymax=[]
#     ymin=[]

#     for beh,condition in dict_of_ratmeans.items():
#         for cond,value in condition.items():
#             if dict_of_ratmeans[beh][cond]:
#                 max2 = np.max([np.size(x) for x in dict_of_ratmeans[beh][cond]])
#                 dict_of_ratmeans[beh][cond]=[snip for snip in dict_of_ratmeans[beh][cond] if np.size(snip)==max2]                    

#                 yarray = np.array(dict_of_ratmeans[beh][cond])
#                 y = np.mean(value, axis=0)
#                 yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
               
#                 min_ymin = np.min(y)
#                 max_ymax = np.max(y)
                
#                 min_yerrormin = np.min(yerror)
#                 max_yerrormax = np.max(yerror)
                
#                 ymax.append(max_ymax+max_yerrormax)
#                 ymin.append(min_ymin-min_yerrormin)
   
#                 length=y.size
    
#                 dict_of_totalmeans[beh][cond]['mean']=y
#                 dict_of_totalmeans[beh][cond]['sem']=yerror
  
#                 # Get fs from dictionary of processed data
#                 for rat,value in my_dict_process["dict_dFF_GCaMP6_COP_1"].items():        
#                     fs=my_dict_process["dict_dFF_GCaMP6_COP_1"][rat]['fs']
#                     x = np.linspace(1, length, length)/fs - sniptime

#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
        
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_results_parameters):
#             os.mkdir(directory_TDT_results_parameters)

#         os.chdir(directory_TDT_results_parameters)

#         for beh in list_means:
#             sns.set(style="ticks", rc=custom_params)
#             fig, axs = plt.subplots(2,3, figsize=(20,15), sharex=True, sharey=True)
            
#             # Improve axes
#             xx=np.arange(-sniptime,sniptime+1,2).tolist()
#             if output=="dFF":
#                 y_max=np.max(ymax)
#                 y_max= round(y_max / 0.1) * 0.1

#                 y_min=np.min(ymin)
#                 y_min= round(y_min / 0.1) * 0.1
#                 yy=np.arange(y_min-0.1,y_max+0.15,0.1).tolist()
#             else:
#                 y_max=np.max(ymax)
#                 y_max= round(y_max / 2) * 2

#                 y_min=np.min(ymin)
#                 y_min= round(y_min / 2) * 2
#                 yy=np.arange(y_min-1,y_max+1,1).tolist()
            
#             # Fill in figure
#             if np.any(dict_of_totalmeans[beh][cond1]['mean']):
#                 axs[0,0].plot(x, dict_of_totalmeans[beh][cond1]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[0,0].fill_between(x, dict_of_totalmeans[beh][cond1]['mean']-dict_of_totalmeans[beh][cond1]['sem'], 
#                                       dict_of_totalmeans[beh][cond1]['mean']+dict_of_totalmeans[beh][cond1]['sem'], color=color_shadow, alpha=0.4)

#                 # Plotting the start line & appropiate axes
#                 axs[0,0].set_xticks(xx)
#                 axs[0,0].set_yticks(yy)
#                 if output=='dFF':
#                     axs[0,0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                 else:
#                     axs[0,0].set_ylabel('z-score',fontsize=16)
#                 axs[0,0].set_title(cond1,fontsize=16)
#                 axs[0,0].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#             else:
#                 if output=='dFF':
#                     axs[0,0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                 else:
#                     axs[0,0].set_ylabel('z-score',fontsize=16)
#                 axs[0,0].set_title(cond1,fontsize=16)
#                 axs[0,0].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)

#             if np.any(dict_of_totalmeans[beh][cond2]['mean']):
#                 axs[0,1].plot(x, dict_of_totalmeans[beh][cond2]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[0,1].fill_between(x, dict_of_totalmeans[beh][cond2]['mean']-dict_of_totalmeans[beh][cond2]['sem'], 
#                                       dict_of_totalmeans[beh][cond2]['mean']+dict_of_totalmeans[beh][cond2]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[0,1].set_xticks(xx)
#                 axs[0,1].set_yticks(yy)
#                 axs[0,1].set_title(cond2,fontsize=16)
#                 axs[0,1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[0,1].spines['left'].set_visible(False)                
#                 axs[0,1].tick_params(left=False)          
#             else:
#                 axs[0,1].spines['left'].set_visible(False)                
#                 axs[0,1].tick_params(left=False)          
#                 axs[0,1].set_title(cond2,fontsize=16)
#                 axs[0,1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#             if np.any(dict_of_totalmeans[beh][cond3]['mean']):
#                 axs[0,2].plot(x, dict_of_totalmeans[beh][cond3]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[0,2].fill_between(x, dict_of_totalmeans[beh][cond3]['mean']-dict_of_totalmeans[beh][cond3]['sem'], 
#                                       dict_of_totalmeans[beh][cond3]['mean']+dict_of_totalmeans[beh][cond3]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[0,2].set_xticks(xx)
#                 axs[0,2].set_yticks(yy)
#                 axs[0,2].set_title(cond3,fontsize=16)
#                 axs[0,2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[0,2].spines['left'].set_visible(False)                
#                 axs[0,2].tick_params(left=False)          
#             else:
#                 axs[0,2].spines['left'].set_visible(False)                
#                 axs[0,2].tick_params(left=False)          
#                 axs[0,2].set_title(cond3,fontsize=16)
#                 axs[0,2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[0,2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)

#             if np.any(dict_of_totalmeans[beh][cond4]['mean']):
#                 axs[1,0].plot(x, dict_of_totalmeans[beh][cond4]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[1,0].fill_between(x, dict_of_totalmeans[beh][cond4]['mean']-dict_of_totalmeans[beh][cond4]['sem'], 
#                                       dict_of_totalmeans[beh][cond4]['mean']+dict_of_totalmeans[beh][cond4]['sem'], color=color_shadow, alpha=0.4)

#                 # Plotting the start line & appropiate axes
#                 axs[1,0].set_xticks(xx)
#                 axs[1,0].set_yticks(yy)
#                 if output=='dFF':
#                     axs[1,0].set_ylabel(r'$\Delta$F/F (%)',fontsize=16)
#                 else:
#                     axs[1,0].set_ylabel('z-score',fontsize=16)
#                 axs[1,0].set_title(cond4,fontsize=16)
#                 axs[1,0].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1,0].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)

#             if np.any(dict_of_totalmeans[beh][cond5]['mean']):
#                 axs[1,1].plot(x, dict_of_totalmeans[beh][cond5]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[1,1].fill_between(x, dict_of_totalmeans[beh][cond5]['mean']-dict_of_totalmeans[beh][cond5]['sem'], 
#                                       dict_of_totalmeans[beh][cond5]['mean']+dict_of_totalmeans[beh][cond5]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[1,1].set_xticks(xx)
#                 axs[1,1].set_yticks(yy)
#                 axs[1,1].set_title(cond5,fontsize=16)
#                 axs[1,1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1,1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[1,1].spines['left'].set_visible(False)                
#                 axs[1,1].tick_params(left=False)          
#             else:
#                 axs[1,1].spines['left'].set_visible(False)                
#                 axs[1,1].tick_params(left=False)          
#                 axs[1,1].set_title(cond5,fontsize=16)
#                 axs[1,1].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1,1].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
    
#             if np.any(dict_of_totalmeans[beh][cond6]['mean']):
#                 axs[1,2].plot(x, dict_of_totalmeans[beh][cond6]['mean'], linewidth=1.5, color=color_GCaMP,zorder=3)
#                 axs[1,2].fill_between(x, dict_of_totalmeans[beh][cond6]['mean']-dict_of_totalmeans[beh][cond6]['sem'], 
#                                       dict_of_totalmeans[beh][cond6]['mean']+dict_of_totalmeans[beh][cond6]['sem'], color=color_shadow, alpha=0.4)
    
#                 # Plotting the start line
#                 axs[1,2].set_xticks(xx)
#                 axs[1,2].set_yticks(yy)
#                 axs[1,2].set_title(cond6,fontsize=16)
#                 axs[1,2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1,2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)
#                 axs[1,2].spines['left'].set_visible(False)                
#                 axs[1,2].tick_params(left=False)          
#             else:
#                 axs[1,2].spines['left'].set_visible(False)                
#                 axs[1,2].tick_params(left=False)          
#                 axs[1,2].set_title(cond6,fontsize=16)
#                 axs[1,2].axvline(x=0, linewidth=2, color=color_startline, )
#                 axs[1,2].axhline(y=0, linewidth=0.5, color=color_startline,zorder=4)

#             # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#             plt.subplots_adjust(wspace=0.1, hspace=0.15)
#             plt.savefig("%s %s.png"%(graphtitle,beh))
#             plt.close(fig)    
             
#         # Change directory back
#         os.chdir(directory)
                        
#     return dict_of_totalmeans

# # Make definition that creates a mean signal per rat for the naive, inexperienced, experienced and after break sessions
# def experience_means_AUC(series,seconds=5,beh_list=list_sex_MB):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default =5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex_MB
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt

#     Returns
#     -------
#     Dictionary (Means per experience level)
#     Dictionary with AUC of the baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     """
#     print("Start experience_means")
    
#     d1="AUC_%s_COP_1_%ssec"%(series,seconds)      
#     dictionary1= eval(d1)

#     d2="AUC_%s_COP_2_%ssec"%(series,seconds)      
#     dictionary2= eval(d2)

#     d3="AUC_%s_COP_3_%ssec"%(series,seconds)      
#     dictionary3= eval(d3)

#     d4="AUC_%s_COP_4_%ssec"%(series,seconds)      
#     dictionary4= eval(d4)

#     d5="AUC_%s_COP_5_%ssec"%(series,seconds)      
#     dictionary5= eval(d5)

#     d6="AUC_%s_COP_6_%ssec"%(series,seconds)      
#     dictionary6= eval(d6)

#     d7="AUC_%s_COP_7_%ssec"%(series,seconds)      
#     dictionary7= eval(d7)

#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_means={}  
#     dict_of_ratmeans={}
    
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']
    
#     for e in exp:
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_means[e][AUC]={}
            
#     for AUC in list_AUC:
#         for i in list_id_naive:
#             rat=i[0:3]
#             dict_of_means['Naive'][AUC][rat]={}
#             for beh in list_means:
#                 dict_of_means['Naive'][AUC][rat][beh]=[]
#         for i in list_id_inexp:
#             rat=i[0:3]
#             dict_of_means['Inexperienced'][AUC][rat]={}
#             for beh in list_means:
#                 dict_of_means['Inexperienced'][AUC][rat][beh]=[]
#         for i in list_id_exp:
#             rat=i[0:3]
#             dict_of_means['Experienced'][AUC][rat]={}
#             for beh in list_means:
#                 dict_of_means['Experienced'][AUC][rat][beh]=[]
#         for i in list_id_afterbreak:
#             rat=i[0:3]
#             dict_of_means['After break'][AUC][rat]={}
#             for beh in list_means:
#                 dict_of_means['After break'][AUC][rat][beh]=[]
    
#     for e in exp:
#         dict_of_ratmeans[e]={}
#         for AUC in list_AUC:
#             dict_of_ratmeans[e][AUC]={}
#             for beh in list_means:
#                 dict_of_ratmeans[e][AUC][beh]={}
#                 for stat in stats:
#                     dict_of_ratmeans[e][AUC][beh][stat]={}

#     for AUC in list_AUC:
#         for beh in list_means:
#             for stat in stats:
#                 for i in list_id_naive:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Naive'][AUC][beh][stat][rat]=[]
#                 for i in list_id_inexp:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Inexperienced'][AUC][beh][stat][rat]=[]
#                 for i in list_id_exp:
#                     rat=i[0:3]
#                     dict_of_ratmeans['Experienced'][AUC][beh][stat][rat]=[]
#                 for i in dictionary7.keys():
#                     rat=i[0:3]
#                     dict_of_ratmeans['After break'][AUC][beh][stat][rat]=[]

#     for AUC,behavior in dictionary1.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary1[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary1[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary1[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary1[AUC][beh][keys])
    
#     for AUC,behavior in dictionary2.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary2[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary2[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary2[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary2[AUC][beh][keys])

#     for AUC,behavior in dictionary3.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary3[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary3[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary3[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary3[AUC][beh][keys])

#     for AUC,behavior in dictionary4.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary4[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary4[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary4[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary4[AUC][beh][keys])

#     for AUC,behavior in dictionary5.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary5[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary5[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary5[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary5[AUC][beh][keys])

#     for AUC,behavior in dictionary6.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary6[AUC]:
#                         if keys in list_id_naive:
#                             rat=keys[0:3]
#                             dict_of_means['Naive'][AUC][rat][beh].append(dictionary6[AUC][beh][keys])
#                         if keys in list_id_inexp:
#                             rat=keys[0:3]
#                             dict_of_means['Inexperienced'][AUC][rat][beh].append(dictionary6[AUC][beh][keys])
#                         if keys in list_id_exp:
#                             rat=keys[0:3]
#                             dict_of_means['Experienced'][AUC][rat][beh].append(dictionary6[AUC][beh][keys])

#     for AUC,behavior in dictionary7.items():
#         for beh,ids in behavior.items():
#             for keys, value in ids.items():
#                 if beh in list_means:
#                     if beh in dictionary7[AUC]:
#                         rat=keys[0:3]
#                         dict_of_means['After break'][AUC][rat][beh].append(dictionary7[AUC][beh][keys])
    
#     # remove_empty_arrays_from_dict(dict_of_means)
#     for e,AUCS in dict_of_means.items():
#         for AUC,rats in AUCS.items():
#             for rat,behavior in rats.items():
#                 for beh,value in behavior.items():
#                     if dict_of_means[e][AUC][rat][beh]:
#                         yarray = np.array(dict_of_means[e][AUC][rat][beh])
#                         y = np.mean(yarray, axis=0)
#                         yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
        
#                         dict_of_ratmeans[e][AUC][beh]['mean'][rat]=y
#                         dict_of_ratmeans[e][AUC][beh]['sem'][rat]=yerror

#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     return dict_of_ratmeans

# #############################################
# # Make definition that creates a mean signal per rat for the inexperienced and experienced sessions
# def results_experience_means_AUC(series,seconds=5,beh_list=list_sex_MB,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default =5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex_MB
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.
    
#     Returns
#     -------
#     Dictionary & Figures (Means per experience level)
#     Dictionary with the AUC of baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Figures of the mean dFF signals aligned to the behaviors, plus sem-bands, per experience level
#     """
    
#     print("Start results_experience_means_AUC")

#     dictionary=experience_means_AUC(series,seconds=seconds,beh_list=beh_list)

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_totalmeans={}
#     dict_of_means={}
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']

#     for e in exp:
#         dict_of_totalmeans[e]={}
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_totalmeans[e][AUC]={}
#             dict_of_means[e][AUC]={}
#             for beh in list_means:
#                 dict_of_means[e][AUC][beh]=[]
#                 dict_of_totalmeans[e][AUC][beh]={}
#                 for stat in stats:
#                     dict_of_totalmeans[e][AUC][beh][stat]=[]

#     for exp,AUCS in dictionary.items():
#         for AUC,behaviors in AUCS.items():
#             for beh,stats in behaviors.items():
#                 for stat,rats in stats.items():
#                     for rat,value in rats.items():
#                         if beh in list_means:
#                             if stat == 'mean':
#                                 for i in value:
#                                     dict_of_means[exp][AUC][beh].append(i)

#     # Put the data in the dictionaries
#     for exp,AUCS in dict_of_means.items():
#         for AUC,behaviors in AUCS.items():
#             for beh,value in behaviors.items():
#                 for beh in list_means:
#                     if dict_of_means[exp][AUC][beh]:
#                         dict_of_totalmeans[exp][AUC][beh]['mean']=np.nanmean(dict_of_means[exp][AUC][beh])
#                         dict_of_totalmeans[exp][AUC][beh]['sem']=(np.nanstd(dict_of_means[exp][AUC][beh])/np.sqrt(len(dict_of_means[exp][AUC][beh])))
            
#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_AUC_total):
#             os.mkdir(directory_TDT_AUC_total)

#         os.chdir(directory_TDT_AUC_total)

#         for beh in list_means:
#             sns.set(style="ticks", rc=custom_params)
#             barWidth = 0.8
#             x1 = ['Pre']
#             x3 = ['Post']
    
#             x_scatter1=len(dict_of_means['Naive']['AUC_pre'][beh])
#             x_scatter2=len(dict_of_means['Inexperienced']['AUC_pre'][beh])
#             x_scatter3=len(dict_of_means['Experienced']['AUC_pre'][beh])
#             x_scatter4=len(dict_of_means['After break']['AUC_pre'][beh])
           
#             fig, axs = plt.subplots(1,4, figsize=(18,6), sharex=True, sharey=True)
            
#             if np.any(dict_of_totalmeans['Naive']['AUC_pre'][beh]['mean']):
#                 axs[0].bar(x1, dict_of_totalmeans['Naive']['AUC_pre'][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[0].scatter(x_scatter1*x1, dict_of_means['Naive']['AUC_pre'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[0].bar(x3, dict_of_totalmeans['Naive']['AUC_post'][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[0].scatter(x_scatter1*x3, dict_of_means['Naive']['AUC_post'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[0].set_title('Naive',fontsize=16)
#                 axs[0].set_ylabel('AUC',fontsize=16)
#                 axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[0].tick_params(axis='x', labelsize=16)
#             else:
#                 axs[0].set_ylabel('AUC',fontsize=16)
#                 axs[0].set_title('Naive',fontsize=16)
#                 axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[0].tick_params(axis='x', labelsize=16)

#             if np.any(dict_of_totalmeans['Inexperienced']['AUC_pre'][beh]['mean']):
#                 axs[1].bar(x1, dict_of_totalmeans['Inexperienced']['AUC_pre'][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[1].scatter(x_scatter2*x1, dict_of_means['Inexperienced']['AUC_pre'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[1].bar(x3, dict_of_totalmeans['Inexperienced']['AUC_post'][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[1].scatter(x_scatter2*x3, dict_of_means['Inexperienced']['AUC_post'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[1].set_title('Inexperienced',fontsize=16)
#                 axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[1].spines['left'].set_visible(False)                
#                 axs[1].tick_params(left=False)              
#                 axs[1].tick_params(axis='x', labelsize=16)
#             else:
#                 axs[1].set_title('Inexperienced',fontsize=16)
#                 axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[1].spines['left'].set_visible(False)                
#                 axs[1].tick_params(left=False)              
#                 axs[1].tick_params(axis='x', labelsize=16)

#             if np.any(dict_of_totalmeans['Experienced']['AUC_pre'][beh]['mean']):
#                 axs[2].bar(x1, dict_of_totalmeans['Experienced']['AUC_pre'][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[2].scatter(x_scatter3*x1, dict_of_means['Experienced']['AUC_pre'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[2].bar(x3, dict_of_totalmeans['Experienced']['AUC_post'][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[2].scatter(x_scatter3*x3, dict_of_means['Experienced']['AUC_post'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[2].set_title('Experienced',fontsize=16)
#                 axs[2].spines['left'].set_visible(False)                
#                 axs[2].tick_params(left=False)              
#                 axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[2].tick_params(axis='x', labelsize=16)
#             else:
#                 axs[2].set_title('Experienced',fontsize=16)
#                 axs[2].spines['left'].set_visible(False)                
#                 axs[2].tick_params(left=False)              
#                 axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[2].tick_params(axis='x', labelsize=16)

#             if np.any(dict_of_totalmeans['After break']['AUC_pre'][beh]['mean']):
#                 axs[3].bar(x1, dict_of_totalmeans['After break']['AUC_pre'][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                 axs[3].scatter(x_scatter4*x1, dict_of_means['After break']['AUC_pre'][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                 axs[3].bar(x3, dict_of_totalmeans['After break']['AUC_post'][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                 axs[3].scatter(x_scatter4*x3, dict_of_means['After break']['AUC_post'][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                 axs[3].set_title('After break',fontsize=16)
#                 axs[3].spines['left'].set_visible(False)                
#                 axs[3].tick_params(left=False)              
#                 axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[3].tick_params(axis='x', labelsize=16)
#             else:
#                 axs[3].set_title('After break',fontsize=16)
#                 axs[3].spines['left'].set_visible(False)                
#                 axs[3].tick_params(left=False)              
#                 axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                 axs[3].tick_params(axis='x', labelsize=16)

#             # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#             plt.subplots_adjust(hspace=0.0)
#             plt.savefig("%s %s.png"%(graphtitle,beh))
#             plt.close(fig)    

#         # Change directory back
#         os.chdir(directory)

#     print("results_experience_means_AUC done")
#     return dict_of_totalmeans


# # Make definition that creates a mean signal per rat for the naive, inexperienced, experienced and after break sessions
# def experience_means_AUC_3part(series,seconds=5,beh_list=list_sex):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default = 5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt

#     Returns
#     -------
#     Dictionary (Means per experience level)
#     Dictionary with AUC of the baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Parts are based on latency to ejaculation, divided in 3 equal parts
#     """
#     print("Start experience_means_AUC_3part")
    
#     d1="AUC_%s_3part_COP_1_%ssec"%(series,seconds)      
#     dictionary1= eval(d1)

#     d2="AUC_%s_3part_COP_2_%ssec"%(series,seconds)      
#     dictionary2= eval(d2)

#     d3="AUC_%s_3part_COP_3_%ssec"%(series,seconds)      
#     dictionary3= eval(d3)

#     d4="AUC_%s_3part_COP_4_%ssec"%(series,seconds)      
#     dictionary4= eval(d4)

#     d5="AUC_%s_3part_COP_5_%ssec"%(series,seconds)      
#     dictionary5= eval(d5)

#     d6="AUC_%s_3part_COP_6_%ssec"%(series,seconds)      
#     dictionary6= eval(d6)

#     d7="AUC_%s_3part_COP_7_%ssec"%(series,seconds)      
#     dictionary7= eval(d7)

#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_means={}  
#     dict_of_ratmeans={}
    
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']
#     list_parts=['part1','part2','part3']
    
#     for e in exp:
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_means[e][AUC]={}
#             for part in list_parts:
#                 dict_of_means[e][AUC][part]={}
                
            
#     for AUC in list_AUC:
#         for part in list_parts:
#             for i in list_id_naive:
#                 rat=i[0:3]
#                 dict_of_means['Naive'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Naive'][AUC][part][rat][beh]=[]
#             for i in list_id_inexp:
#                 rat=i[0:3]
#                 dict_of_means['Inexperienced'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Inexperienced'][AUC][part][rat][beh]=[]
#             for i in list_id_exp:
#                 rat=i[0:3]
#                 dict_of_means['Experienced'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Experienced'][AUC][part][rat][beh]=[]
#             for i in list_id_afterbreak:
#                 rat=i[0:3]
#                 dict_of_means['After break'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['After break'][AUC][part][rat][beh]=[]
    
#     for e in exp:
#         dict_of_ratmeans[e]={}
#         for AUC in list_AUC:
#             dict_of_ratmeans[e][AUC]={}
#             for part in list_parts:
#                 dict_of_ratmeans[e][AUC][part]={}
#                 for beh in list_means:
#                     dict_of_ratmeans[e][AUC][part][beh]={}
#                     for stat in stats:
#                         dict_of_ratmeans[e][AUC][part][beh][stat]={}

#     for AUC in list_AUC:
#         for part in list_parts:
#             for beh in list_means:
#                 for stat in stats:
#                     for i in list_id_naive:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Naive'][AUC][part][beh][stat][rat]=[]
#                     for i in list_id_inexp:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Inexperienced'][AUC][part][beh][stat][rat]=[]
#                     for i in list_id_exp:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Experienced'][AUC][part][beh][stat][rat]=[]
#                     for i in dictionary7.keys():
#                         rat=i[0:3]
#                         dict_of_ratmeans['After break'][AUC][part][beh][stat][rat]=[]

#     for AUC,parts in dictionary1.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary1[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
    
#     for AUC,parts in dictionary2.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary2[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])

#     for AUC,parts in dictionary3.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary3[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])

#     for AUC,parts in dictionary4.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary4[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])

#     for AUC,parts in dictionary5.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary5[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])

#     for AUC,parts in dictionary6.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary6[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])

#     for AUC,parts in dictionary7.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary7[AUC][part]:
#                             rat=keys[0:3]
#                             dict_of_means['After break'][AUC][part][rat][beh].append(dictionary7[AUC][part][beh][keys])
    
#     # remove_empty_arrays_from_dict(dict_of_means)
#     for e,AUCS in dict_of_means.items():
#         for AUC,parts in AUCS.items():
#             for part, rats in parts.items():
#                 for rat,behavior in rats.items():
#                     for beh,value in behavior.items():
#                         if dict_of_means[e][AUC][part][rat][beh]:
#                             yarray = np.array(dict_of_means[e][AUC][part][rat][beh])
#                             y = np.mean(yarray, axis=0)
#                             yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
            
#                             dict_of_ratmeans[e][AUC][part][beh]['mean'][rat]=y
#                             dict_of_ratmeans[e][AUC][part][beh]['sem'][rat]=yerror

#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     return dict_of_ratmeans

# #############################################
# # Make definition that creates a mean signal per rat for the inexperienced and experienced sessions
# def results_experience_means_AUC_3part(series,seconds=5,beh_list=list_sex,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default = 5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.
    
#     Returns
#     -------
#     Dictionary & Figures (Means per experience level)
#     Dictionary with the AUC of baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Parts are based on latency to ejaculation, divided in 3 equal parts
#     Figures of the mean dFF signals aligned to the behaviors, plus sem-bands, per experience level
#     """
    
#     print("Start results_experience_means_AUC_3part")

#     dictionary=experience_means_AUC_3part(series,seconds=seconds,beh_list=beh_list)

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_totalmeans={}
#     dict_of_means={}
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']
#     list_parts=['part1','part2','part3']

#     for e in exp:
#         dict_of_totalmeans[e]={}
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_totalmeans[e][AUC]={}
#             dict_of_means[e][AUC]={}
#             for part in list_parts:
#                 dict_of_totalmeans[e][AUC][part]={}
#                 dict_of_means[e][AUC][part]={}
#                 for beh in list_means:
#                     dict_of_means[e][AUC][part][beh]=[]
#                     dict_of_totalmeans[e][AUC][part][beh]={}
#                     for stat in stats:
#                         dict_of_totalmeans[e][AUC][part][beh][stat]=[]

#     for exp,AUCS in dictionary.items():
#         for AUC,parts in AUCS.items():
#             for part,behaviors in parts.items():
#                 for beh,stats in behaviors.items():
#                     for stat,rats in stats.items():
#                         for rat,value in rats.items():
#                             if beh in list_means:
#                                 if stat == 'mean':
#                                     for i in value:
#                                         dict_of_means[exp][AUC][part][beh].append(i)

#     # Put the data in the dictionaries
#     for exp,AUCS in dict_of_means.items():
#         for AUC,parts in AUCS.items():
#             for part,behaviors in parts.items():
#                 for beh,value in behaviors.items():
#                     for beh in list_means:
#                         if dict_of_means[exp][AUC][part][beh]:
#                             dict_of_totalmeans[exp][AUC][part][beh]['mean']=np.nanmean(dict_of_means[exp][AUC][part][beh])
#                             dict_of_totalmeans[exp][AUC][part][beh]['sem']=(np.nanstd(dict_of_means[exp][AUC][part][beh])/np.sqrt(len(dict_of_means[exp][AUC][part][beh])))
            
#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_AUC_total):
#             os.mkdir(directory_TDT_AUC_total)


#         for part in list_parts:
#             for beh in list_means:
#                 if beh != 'Ejaculation':
#                     sns.set(style="ticks", rc=custom_params)
#                     barWidth = 0.8
#                     x1 = ['Pre']
#                     x3 = ['Post']
        
#                     x_scatter1=len(dict_of_means['Naive']['AUC_pre'][part][beh])
#                     x_scatter2=len(dict_of_means['Inexperienced']['AUC_pre'][part][beh])
#                     x_scatter3=len(dict_of_means['Experienced']['AUC_pre'][part][beh])
#                     x_scatter4=len(dict_of_means['After break']['AUC_pre'][part][beh])
                    
#                     os.chdir(directory_TDT_AUC_total)

#                     fig, axs = plt.subplots(1,4, figsize=(18,6), sharex=True, sharey=True)
                    
#                     if np.any(dict_of_totalmeans['Naive']['AUC_pre'][part][beh]['mean']):
#                         axs[0].bar(x1, dict_of_totalmeans['Naive']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0].scatter(x_scatter1*x1, dict_of_means['Naive']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0].bar(x3, dict_of_totalmeans['Naive']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0].scatter(x_scatter1*x3, dict_of_means['Naive']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0].set_title('Naive',fontsize=16)
#                         axs[0].set_ylabel('AUC',fontsize=16)
#                         axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[0].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[0].set_ylabel('AUC',fontsize=16)
#                         axs[0].set_title('Naive',fontsize=16)
#                         axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[0].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['Inexperienced']['AUC_pre'][part][beh]['mean']):
#                         axs[1].bar(x1, dict_of_totalmeans['Inexperienced']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1].scatter(x_scatter2*x1, dict_of_means['Inexperienced']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[1].bar(x3, dict_of_totalmeans['Inexperienced']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1].scatter(x_scatter2*x3, dict_of_means['Inexperienced']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[1].set_title('Inexperienced',fontsize=16)
#                         axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[1].spines['left'].set_visible(False)                
#                         axs[1].tick_params(left=False)              
#                         axs[1].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[1].set_title('Inexperienced',fontsize=16)
#                         axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[1].spines['left'].set_visible(False)                
#                         axs[1].tick_params(left=False)              
#                         axs[1].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['Experienced']['AUC_pre'][part][beh]['mean']):
#                         axs[2].bar(x1, dict_of_totalmeans['Experienced']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[2].scatter(x_scatter3*x1, dict_of_means['Experienced']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[2].bar(x3, dict_of_totalmeans['Experienced']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[2].scatter(x_scatter3*x3, dict_of_means['Experienced']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[2].set_title('Experienced',fontsize=16)
#                         axs[2].spines['left'].set_visible(False)                
#                         axs[2].tick_params(left=False)              
#                         axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[2].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[2].set_title('Experienced',fontsize=16)
#                         axs[2].spines['left'].set_visible(False)                
#                         axs[2].tick_params(left=False)              
#                         axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[2].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['After break']['AUC_pre'][part][beh]['mean']):
#                         axs[3].bar(x1, dict_of_totalmeans['After break']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[3].scatter(x_scatter4*x1, dict_of_means['After break']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[3].bar(x3, dict_of_totalmeans['After break']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[3].scatter(x_scatter4*x3, dict_of_means['After break']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[3].set_title('After break',fontsize=16)
#                         axs[3].spines['left'].set_visible(False)                
#                         axs[3].tick_params(left=False)              
#                         axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[3].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[3].set_title('After break',fontsize=16)
#                         axs[3].spines['left'].set_visible(False)                
#                         axs[3].tick_params(left=False)              
#                         axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[3].tick_params(axis='x', labelsize=16)
        
#                     # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#                     plt.subplots_adjust(hspace=0.0)
#                     plt.savefig("%s %s %s.png"%(graphtitle,beh,part))
#                     plt.close(fig)    
        
#                     # Change directory back
#                     os.chdir(directory)

#     print("results_experience_means_AUC_3part done")
#     return dict_of_means

# # Make definition that creates a mean signal per rat for the naive, inexperienced, experienced and after break sessions
# def experience_means_AUC_TN3part(series,seconds=5,beh_list=list_sex):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default = 5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt

#     Returns
#     -------
#     Dictionary (Means per experience level)
#     Dictionary with AUC of the baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Parts are based on latency to ejaculation, divided in 3 equal parts
#     """
#     print("Start experience_means_AUC_TN3part")
    
#     d1="AUC_%s_TN3part_COP_1_%ssec"%(series,seconds)      
#     dictionary1= eval(d1)

#     d2="AUC_%s_TN3part_COP_2_%ssec"%(series,seconds)      
#     dictionary2= eval(d2)

#     d3="AUC_%s_TN3part_COP_3_%ssec"%(series,seconds)      
#     dictionary3= eval(d3)

#     d4="AUC_%s_TN3part_COP_4_%ssec"%(series,seconds)      
#     dictionary4= eval(d4)

#     d5="AUC_%s_TN3part_COP_5_%ssec"%(series,seconds)      
#     dictionary5= eval(d5)

#     d6="AUC_%s_TN3part_COP_6_%ssec"%(series,seconds)      
#     dictionary6= eval(d6)

#     d7="AUC_%s_TN3part_COP_7_%ssec"%(series,seconds)      
#     dictionary7= eval(d7)

#     dictionary1
#     dictionary2
#     dictionary3
#     dictionary4
#     dictionary5
#     dictionary6
#     dictionary7

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_means={}  
#     dict_of_ratmeans={}
    
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']
#     list_parts=['part1','part2','part3']
    
#     for e in exp:
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_means[e][AUC]={}
#             for part in list_parts:
#                 dict_of_means[e][AUC][part]={}
                
            
#     for AUC in list_AUC:
#         for part in list_parts:
#             for i in list_id_naive:
#                 rat=i[0:3]
#                 dict_of_means['Naive'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Naive'][AUC][part][rat][beh]=[]
#             for i in list_id_inexp:
#                 rat=i[0:3]
#                 dict_of_means['Inexperienced'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Inexperienced'][AUC][part][rat][beh]=[]
#             for i in list_id_exp:
#                 rat=i[0:3]
#                 dict_of_means['Experienced'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['Experienced'][AUC][part][rat][beh]=[]
#             for i in list_id_afterbreak:
#                 rat=i[0:3]
#                 dict_of_means['After break'][AUC][part][rat]={}
#                 for beh in list_means:
#                     dict_of_means['After break'][AUC][part][rat][beh]=[]
    
#     for e in exp:
#         dict_of_ratmeans[e]={}
#         for AUC in list_AUC:
#             dict_of_ratmeans[e][AUC]={}
#             for part in list_parts:
#                 dict_of_ratmeans[e][AUC][part]={}
#                 for beh in list_means:
#                     dict_of_ratmeans[e][AUC][part][beh]={}
#                     for stat in stats:
#                         dict_of_ratmeans[e][AUC][part][beh][stat]={}

#     for AUC in list_AUC:
#         for part in list_parts:
#             for beh in list_means:
#                 for stat in stats:
#                     for i in list_id_naive:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Naive'][AUC][part][beh][stat][rat]=[]
#                     for i in list_id_inexp:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Inexperienced'][AUC][part][beh][stat][rat]=[]
#                     for i in list_id_exp:
#                         rat=i[0:3]
#                         dict_of_ratmeans['Experienced'][AUC][part][beh][stat][rat]=[]
#                     for i in dictionary7.keys():
#                         rat=i[0:3]
#                         dict_of_ratmeans['After break'][AUC][part][beh][stat][rat]=[]

#     for AUC,parts in dictionary1.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary1[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary1[AUC][part][beh][keys])
    
#     for AUC,parts in dictionary2.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary2[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary2[AUC][part][beh][keys])

#     for AUC,parts in dictionary3.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary3[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary3[AUC][part][beh][keys])

#     for AUC,parts in dictionary4.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary4[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary4[AUC][part][beh][keys])

#     for AUC,parts in dictionary5.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary5[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary5[AUC][part][beh][keys])

#     for AUC,parts in dictionary6.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary6[AUC][part]:
#                             if keys in list_id_naive:
#                                 rat=keys[0:3]
#                                 dict_of_means['Naive'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])
#                             if keys in list_id_inexp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Inexperienced'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])
#                             if keys in list_id_exp:
#                                 rat=keys[0:3]
#                                 dict_of_means['Experienced'][AUC][part][rat][beh].append(dictionary6[AUC][part][beh][keys])

#     for AUC,parts in dictionary7.items():
#         for part,behavior in parts.items():
#             for beh,ids in behavior.items():
#                 for keys, value in ids.items():
#                     if beh in list_means:
#                         if beh in dictionary7[AUC][part]:
#                             rat=keys[0:3]
#                             dict_of_means['After break'][AUC][part][rat][beh].append(dictionary7[AUC][part][beh][keys])
    
#     # remove_empty_arrays_from_dict(dict_of_means)
#     for e,AUCS in dict_of_means.items():
#         for AUC,parts in AUCS.items():
#             for part, rats in parts.items():
#                 for rat,behavior in rats.items():
#                     for beh,value in behavior.items():
#                         if dict_of_means[e][AUC][part][rat][beh]:
#                             yarray = np.array(dict_of_means[e][AUC][part][rat][beh])
#                             y = np.mean(yarray, axis=0)
#                             yerror = np.std(yarray, axis =0)/np.sqrt(len(yarray))
            
#                             dict_of_ratmeans[e][AUC][part][beh]['mean'][rat]=y
#                             dict_of_ratmeans[e][AUC][part][beh]['sem'][rat]=yerror

#     remove_empty_arrays_from_dict(dict_of_ratmeans)

#     return dict_of_ratmeans

# #############################################
# # Make definition that creates a mean signal per rat for the inexperienced and experienced sessions
# def results_experience_means_AUC_TN3part(series,seconds=5,beh_list=list_sex,graphtitle=None):
#     """
#     Parameters
#     ----------
#     series : string
#         Add a string of the ejaculatory series that needs to be analyzed
#         e.g. "T", "S1, or "S2""
#     seconds : string -> Default = 5
#         Add the seconds you want to explore before and after
#         e.g."2sec","5sec","10sec"
#     beh_list : list -> Default = list_sex
#         Add the list with behaviors that need to be analyzed
#         e.g. list_sex_MB, list_sex, list_behaviors, list_startcop, list_other_behaviors, list_behaviors_extra, list_beh_tdt
#     graphtitle : string -> Default = None
#         Add the start name of the figure that is saved.
    
#     Returns
#     -------
#     Dictionary & Figures (Means per experience level)
#     Dictionary with the AUC of baseline-corrected mean dFF of snips before and after the behaviors per test. 
#     First a mean of AUC dFF-behavior-snips per rat is calculated. Then this mean is used to calculate the overall mean of the coptest.
#     Then a mean per experience level was calculated for further analysis.
#     Correction is done by taking the average of the AUC dFF signal during the defined "baseline" period, and correcting 
#     the real AUC dFF by minusing this baseline. The signals are thus "aligned to zero" from the start.
#     Experience levels: 
#         Naive -> all cops until and including the cop in which 1st ejaculation was reached
#         Inexperienced -> The 2 coptests after the coptest with the 1st ejaculation
#         Experienced -> The last coptests after 3 coptest with ejaculations were done
#         After break -> COP7, first coptest after 2-3 weeks of break
#     Parts are based on latency to ejaculation, divided in 3 equal parts
#     Figures of the mean dFF signals aligned to the behaviors, plus sem-bands, per experience level
#     """
    
#     print("Start results_experience_means_AUC_TN3part")

#     dictionary=experience_means_AUC_TN3part(series,seconds=seconds,beh_list=beh_list)

#     list_means=[]
#     for beh in beh_list:
#         list_means.append(beh)

#     dict_of_totalmeans={}
#     dict_of_means={}
#     exp=['Naive','Inexperienced','Experienced','After break']
#     stats=['mean','sem']
#     list_AUC=['AUC_pre','AUC_post']
#     list_parts=['part1','part2','part3']

#     for e in exp:
#         dict_of_totalmeans[e]={}
#         dict_of_means[e]={}
#         for AUC in list_AUC:
#             dict_of_totalmeans[e][AUC]={}
#             dict_of_means[e][AUC]={}
#             for part in list_parts:
#                 dict_of_totalmeans[e][AUC][part]={}
#                 dict_of_means[e][AUC][part]={}
#                 for beh in list_means:
#                     dict_of_means[e][AUC][part][beh]=[]
#                     dict_of_totalmeans[e][AUC][part][beh]={}
#                     for stat in stats:
#                         dict_of_totalmeans[e][AUC][part][beh][stat]=[]

#     for exp,AUCS in dictionary.items():
#         for AUC,parts in AUCS.items():
#             for part,behaviors in parts.items():
#                 for beh,stats in behaviors.items():
#                     for stat,rats in stats.items():
#                         for rat,value in rats.items():
#                             if beh in list_means:
#                                 if stat == 'mean':
#                                     for i in value:
#                                         dict_of_means[exp][AUC][part][beh].append(i)

#     # Put the data in the dictionaries
#     for exp,AUCS in dict_of_means.items():
#         for AUC,parts in AUCS.items():
#             for part,behaviors in parts.items():
#                 for beh,value in behaviors.items():
#                     for beh in list_means:
#                         if dict_of_means[exp][AUC][part][beh]:
#                             dict_of_totalmeans[exp][AUC][part][beh]['mean']=np.nanmean(dict_of_means[exp][AUC][part][beh])
#                             dict_of_totalmeans[exp][AUC][part][beh]['sem']=(np.nanstd(dict_of_means[exp][AUC][part][beh])/np.sqrt(len(dict_of_means[exp][AUC][part][beh])))
            
#     #Plot the data
#     if graphtitle == None:
#         pass
#     else:
#         # Change directory to figure save location
#         if not os.path.isdir(directory_TDT_AUC_total):
#             os.mkdir(directory_TDT_AUC_total)


#         for part in list_parts:
#             for beh in list_means:
#                 if beh != 'Ejaculation':
#                     sns.set(style="ticks", rc=custom_params)
#                     barWidth = 0.8
#                     x1 = ['Pre']
#                     x3 = ['Post']
        
#                     x_scatter1=len(dict_of_means['Naive']['AUC_pre'][part][beh])
#                     x_scatter2=len(dict_of_means['Inexperienced']['AUC_pre'][part][beh])
#                     x_scatter3=len(dict_of_means['Experienced']['AUC_pre'][part][beh])
#                     x_scatter4=len(dict_of_means['After break']['AUC_pre'][part][beh])
                    
#                     os.chdir(directory_TDT_AUC_total)

#                     fig, axs = plt.subplots(1,4, figsize=(18,6), sharex=True, sharey=True)
                    
#                     if np.any(dict_of_totalmeans['Naive']['AUC_pre'][part][beh]['mean']):
#                         axs[0].bar(x1, dict_of_totalmeans['Naive']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[0].scatter(x_scatter1*x1, dict_of_means['Naive']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[0].bar(x3, dict_of_totalmeans['Naive']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[0].scatter(x_scatter1*x3, dict_of_means['Naive']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[0].set_title('Naive',fontsize=16)
#                         axs[0].set_ylabel('AUC',fontsize=16)
#                         axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[0].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[0].set_ylabel('AUC',fontsize=16)
#                         axs[0].set_title('Naive',fontsize=16)
#                         axs[0].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[0].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['Inexperienced']['AUC_pre'][part][beh]['mean']):
#                         axs[1].bar(x1, dict_of_totalmeans['Inexperienced']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[1].scatter(x_scatter2*x1, dict_of_means['Inexperienced']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[1].bar(x3, dict_of_totalmeans['Inexperienced']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[1].scatter(x_scatter2*x3, dict_of_means['Inexperienced']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[1].set_title('Inexperienced',fontsize=16)
#                         axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[1].spines['left'].set_visible(False)                
#                         axs[1].tick_params(left=False)              
#                         axs[1].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[1].set_title('Inexperienced',fontsize=16)
#                         axs[1].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[1].spines['left'].set_visible(False)                
#                         axs[1].tick_params(left=False)              
#                         axs[1].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['Experienced']['AUC_pre'][part][beh]['mean']):
#                         axs[2].bar(x1, dict_of_totalmeans['Experienced']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[2].scatter(x_scatter3*x1, dict_of_means['Experienced']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[2].bar(x3, dict_of_totalmeans['Experienced']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[2].scatter(x_scatter3*x3, dict_of_means['Experienced']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[2].set_title('Experienced',fontsize=16)
#                         axs[2].spines['left'].set_visible(False)                
#                         axs[2].tick_params(left=False)              
#                         axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[2].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[2].set_title('Experienced',fontsize=16)
#                         axs[2].spines['left'].set_visible(False)                
#                         axs[2].tick_params(left=False)              
#                         axs[2].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[2].tick_params(axis='x', labelsize=16)
        
#                     if np.any(dict_of_totalmeans['After break']['AUC_pre'][part][beh]['mean']):
#                         axs[3].bar(x1, dict_of_totalmeans['After break']['AUC_pre'][part][beh]['mean'], color=color_AUC_pre_bar, width=barWidth, edgecolor='white', label='Pre',zorder=2)
#                         axs[3].scatter(x_scatter4*x1, dict_of_means['After break']['AUC_pre'][part][beh], color=color_AUC_pre_scatter, alpha=.9,zorder=3)
#                         axs[3].bar(x3, dict_of_totalmeans['After break']['AUC_post'][part][beh]['mean'], color=color_AUC_post_bar, width=barWidth, edgecolor='white', label='Post',zorder=2)
#                         axs[3].scatter(x_scatter4*x3, dict_of_means['After break']['AUC_post'][part][beh],color=color_AUC_post_scatter,  alpha=.9,zorder=3)
#                         axs[3].set_title('After break',fontsize=16)
#                         axs[3].spines['left'].set_visible(False)                
#                         axs[3].tick_params(left=False)              
#                         axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[3].tick_params(axis='x', labelsize=16)
#                     else:
#                         axs[3].set_title('After break',fontsize=16)
#                         axs[3].spines['left'].set_visible(False)                
#                         axs[3].tick_params(left=False)              
#                         axs[3].axhline(y=0, linewidth=1, color=color_startline,zorder=4)
#                         axs[3].tick_params(axis='x', labelsize=16)
        
#                     # fig.suptitle('%s%s'%(test,testsession),fontsize=20)
#                     plt.subplots_adjust(hspace=0.0)
#                     plt.savefig("%s %s %s.png"%(graphtitle,beh,part))
#                     plt.close(fig)    
        
#                     # Change directory back
#                     os.chdir(directory)

#     print("results_experience_means_AUC_TN3part done")
#     return dict_of_means

# #############################################################################################################################            
# ####################### ANALYSIS ############################################################################################
# #############################################################################################################################            

# Results_endo_naive=figure_from_3_lists("T",list_id_inexp_slow,list_id_inexp_normal,list_id_inexp_fast,
#                           'sluggish','normal','fast',graphtitle='Endo_naive')
# Results_endo_experienced=figure_from_3_lists("T",list_id_exp_slow,list_id_exp_normal,list_id_exp_fast,
#                           'sluggish','normal','fast',graphtitle='Endo_exp')

# Results_endo=figure_from_2x3_lists("T",list_id_inexp_slow,list_id_inexp_normal,list_id_inexp_fast,
#                                           list_id_exp_slow,list_id_exp_normal,list_id_exp_fast,
#                           'Naive - sluggish','Naive - normal','Naive -fast','Experienced - sluggish','Experienced - normal','Experienced - fast',
#                           graphtitle='Endo')


# # Make lists per paramater efficiency
# # Options: 'TN_Mount', 'TN_Intromission', 'TN_Ejaculation', 'TN_Attempt to mount', 'TN_Anogenital sniffing', 
# # 'TN_Chasing', 'TN_Genital grooming', 'TN_Sniffing bedding', 'TN_Sniffing female', 'TN_Head away from female', 
# #'TN_Head to female', 'TN_Other', 'TD_Mount', 'TD_Intromission', 'TD_Ejaculation', 'TD_Attempt to mount', 
# #'TD_Anogenital sniffing', 'TD_Chasing', 'TD_Genital grooming', 'TD_Sniffing bedding', 'TD_Sniffing female', 
# #'TD_Head away from female', 'TD_Head to female', 'TD_Other', 'Starttime', 'L1_Mount', 'Time_Mount', 
# #Time_end_Mount', 'L1_Intromission', 'Time_Intromission', 'Time_end_Intromission', 'L1_Ejaculation', 'Time_Ejaculation', 
# #'Time_end_Ejaculation', 'L1_Attempt to mount', 'Time_Attempt to mount', 'Time_end_Attempt to mount', 
# #'L1_Anogenital sniffing', 'Time_Anogenital sniffing', 'Time_end_Anogenital sniffing', 'L1_Chasing', 
# #'Time_Chasing', 'Time_end_Chasing', 'L1_Genital grooming', 'Time_Genital grooming', 'Time_end_Genital grooming', 
# #'L1_Sniffing bedding', 'Time_Sniffing bedding', 'Time_end_Sniffing bedding', 'L1_Sniffing female', 
# #'Time_Sniffing female', 'Time_end_Sniffing female', 'L1_Head away from female', 'Time_Head away from female', 
# #'Time_end_Head away from female', 'L1_Head to female', 'Time_Head to female', 'Time_end_Head to female', 'L1_Other', 
# #'Time_Other', 'Time_end_Other', 'L1_B', 'L1_EM', 'L1_EI', 'L1_EB', 'TN_Copulations', 'IR', 'III', 
# #'TN_Copulation_oriented behavior', 'TN_Female_oriented behavior', 'TD_Copulations', 'TD_Copulation_oriented behavior', 
# #'TD_Female_oriented behavior', 'TN_MB_single_Mount', 'TD_MB_single_Mount', 'TN_MB_single_Intromission', 
# #'TD_MB_single_Intromission', 'TN_MB_single_Ejaculation', 'TD_MB_single_Ejaculation', 'TN_MB', 'TD_MB', 'TN_TO', 
# #'TD_TO', 'MD_TO', 'MD_IMBI', 'TN_MB Mount', 'TN_MB Intromission', 'TN_Start MB Mount', 'TN_Start MB Intromission', 
# #'TN_End MB Mount', 'TN_End MB Intromission', 'TN_Mounts in MB', 'TN_Intromissions in MB', 'TD_MB Mount', 
# #'TD_MB Intromission', 'TD_Start MB Mount', 'TD_Start MB Intromission', 'TD_End MB Mount', 'TD_End MB Intromission',
# #'TD_Mounts in MB', 'TD_Intromissions in MB', 'CR'])

# list_III_low=parameter_list_maker('S1','III','Low')
# list_III_middle=parameter_list_maker('S1','III','Middle')
# list_III_high=parameter_list_maker('S1','III','High')

# list_IR_low=parameter_list_maker('S1','IR','Low')
# list_IR_middle=parameter_list_maker('S1','IR','Middle')
# list_IR_high=parameter_list_maker('S1','IR','High')

# list_TD_TO_low=parameter_list_maker('S1','TD_TO','Low')
# list_TD_TO_middle=parameter_list_maker('S1','TD_TO','Middle')
# list_TD_TO_high=parameter_list_maker('S1','TD_TO','High')

# list_MD_TO_low=parameter_list_maker('S1','MD_TO','Low')
# list_MD_TO_middle=parameter_list_maker('S1','MD_TO','Middle')
# list_MD_TO_high=parameter_list_maker('S1','MD_TO','High')

# list_IMBI_low=parameter_list_maker('S1','MD_IMBI','Low')
# list_IMBI_middle=parameter_list_maker('S1','MD_IMBI','Middle')
# list_IMBI_high=parameter_list_maker('S1','MD_IMBI','High')

# list_TN_MB_low=parameter_list_maker('S1','TN_MB','Low')
# list_TN_MB_middle=parameter_list_maker('S1','TN_MB','Middle')
# list_TN_MB_high=parameter_list_maker('S1','TN_MB','High')

# list_TD_MB_low=parameter_list_maker('S1','TD_MB','Low')
# list_TD_MB_middle=parameter_list_maker('S1','TD_MB','Middle')
# list_TD_MB_high=parameter_list_maker('S1','TD_MB','High')

# # Make lists to divide them into naive versus experienced
# list_III_low_naive=experience_list_maker(list_III_low,"Naive")
# list_III_low_naive_plus=experience_list_maker(list_III_low,"Naive_plus")
# list_III_low_exp=experience_list_maker(list_III_low,"Experienced")
# list_III_middle_naive=experience_list_maker(list_III_middle,"Naive")
# list_III_middle_naive_plus=experience_list_maker(list_III_middle,"Naive_plus")
# list_III_middle_exp=experience_list_maker(list_III_middle,"Experienced")
# list_III_high_naive=experience_list_maker(list_III_high,"Naive")
# list_III_high_naive_plus=experience_list_maker(list_III_high,"Naive_plus")
# list_III_high_exp=experience_list_maker(list_III_high,"Experienced")

# list_IR_low_naive=experience_list_maker(list_IR_low,"Naive")
# list_IR_low_naive_plus=experience_list_maker(list_IR_low,"Naive_plus")
# list_IR_low_exp=experience_list_maker(list_IR_low,"Experienced")
# list_IR_middle_naive=experience_list_maker(list_IR_middle,"Naive")
# list_IR_middle_naive_plus=experience_list_maker(list_IR_middle,"Naive_plus")
# list_IR_middle_exp=experience_list_maker(list_IR_middle,"Experienced")
# list_IR_high_naive=experience_list_maker(list_IR_high,"Naive")
# list_IR_high_naive_plus=experience_list_maker(list_IR_high,"Naive_plus")
# list_IR_high_exp=experience_list_maker(list_IR_high,"Experienced")

# list_TD_TO_low_naive=experience_list_maker(list_TD_TO_low,"Naive")
# list_TD_TO_low_naive_plus=experience_list_maker(list_TD_TO_low,"Naive_plus")
# list_TD_TO_low_exp=experience_list_maker(list_TD_TO_low,"Experienced")
# list_TD_TO_middle_naive=experience_list_maker(list_TD_TO_middle,"Naive")
# list_TD_TO_middle_naive_plus=experience_list_maker(list_TD_TO_middle,"Naive_plus")
# list_TD_TO_middle_exp=experience_list_maker(list_TD_TO_middle,"Experienced")
# list_TD_TO_high_naive=experience_list_maker(list_TD_TO_high,"Naive")
# list_TD_TO_high_naive_plus=experience_list_maker(list_TD_TO_high,"Naive_plus")
# list_TD_TO_high_exp=experience_list_maker(list_TD_TO_high,"Experienced")

# list_MD_TO_low_naive=experience_list_maker(list_MD_TO_low,"Naive")
# list_MD_TO_low_naive_plus=experience_list_maker(list_MD_TO_low,"Naive_plus")
# list_MD_TO_low_exp=experience_list_maker(list_MD_TO_low,"Experienced")
# list_MD_TO_middle_naive=experience_list_maker(list_MD_TO_middle,"Naive")
# list_MD_TO_middle_naive_plus=experience_list_maker(list_MD_TO_middle,"Naive_plus")
# list_MD_TO_middle_exp=experience_list_maker(list_MD_TO_middle,"Experienced")
# list_MD_TO_high_naive=experience_list_maker(list_MD_TO_high,"Naive")
# list_MD_TO_high_naive_plus=experience_list_maker(list_MD_TO_high,"Naive_plus")
# list_MD_TO_high_exp=experience_list_maker(list_MD_TO_high,"Experienced")

# list_IMBI_low_naive=experience_list_maker(list_IMBI_low,"Naive")
# list_IMBI_low_naive_plus=experience_list_maker(list_IMBI_low,"Naive_plus")
# list_IMBI_low_exp=experience_list_maker(list_IMBI_low,"Experienced")
# list_IMBI_middle_naive=experience_list_maker(list_IMBI_middle,"Naive")
# list_IMBI_middle_naive_plus=experience_list_maker(list_IMBI_middle,"Naive_plus")
# list_IMBI_middle_exp=experience_list_maker(list_IMBI_middle,"Experienced")
# list_IMBI_high_naive=experience_list_maker(list_IMBI_high,"Naive")
# list_IMBI_high_naive_plus=experience_list_maker(list_IMBI_high,"Naive_plus")
# list_IMBI_high_exp=experience_list_maker(list_IMBI_high,"Experienced")

# list_TN_MB_low_naive=experience_list_maker(list_TN_MB_low,"Naive")
# list_TN_MB_low_naive_plus=experience_list_maker(list_TN_MB_low,"Naive_plus")
# list_TN_MB_low_exp=experience_list_maker(list_TN_MB_low,"Experienced")
# list_TN_MB_middle_naive=experience_list_maker(list_TN_MB_middle,"Naive")
# list_TN_MB_middle_naive_plus=experience_list_maker(list_TN_MB_middle,"Naive_plus")
# list_TN_MB_middle_exp=experience_list_maker(list_TN_MB_middle,"Experienced")
# list_TN_MB_high_naive=experience_list_maker(list_TN_MB_high,"Naive")
# list_TN_MB_high_naive_plus=experience_list_maker(list_TN_MB_high,"Naive_plus")
# list_TN_MB_high_exp=experience_list_maker(list_TN_MB_high,"Experienced")

# list_TD_MB_low_naive=experience_list_maker(list_TD_MB_low,"Naive")
# list_TD_MB_low_naive_plus=experience_list_maker(list_TD_MB_low,"Naive_plus")
# list_TD_MB_low_exp=experience_list_maker(list_TD_MB_low,"Experienced")
# list_TD_MB_middle_naive=experience_list_maker(list_TD_MB_middle,"Naive")
# list_TD_MB_middle_naive_plus=experience_list_maker(list_TD_MB_middle,"Naive_plus")
# list_TD_MB_middle_exp=experience_list_maker(list_TD_MB_middle,"Experienced")
# list_TD_MB_high_naive=experience_list_maker(list_TD_MB_high,"Naive")
# list_TD_MB_high_naive_plus=experience_list_maker(list_TD_MB_high,"Naive_plus")
# list_TD_MB_high_exp=experience_list_maker(list_TD_MB_high,"Experienced")

# # Make figures without level of experience (all) and with level of experience (sel)
# Results_III_all=figure_from_3_lists("T",list_III_low,list_III_middle,list_III_high,
#                           'Short III','Average III','Long III',graphtitle='Para_III_all')

# Results_III_sel=figure_from_2x3_lists("T",list_III_low_naive,list_III_middle_naive,list_III_high_naive,
#                                           list_III_low_exp,list_III_middle_exp,list_III_high_exp,
#                           'Naive - Short III','Naive - Average III','Naive - long III','Experienced - Short III',
#                           'Experienced - Average III','Experienced - Long III',
#                           graphtitle='Para_III_sel')

# Results_IR_all=figure_from_3_lists("T",list_IR_low,list_IR_middle,list_IR_high,
#                           'Low IR','Average IR','High IR',graphtitle='Para_IR_all')

# Results_IR_sel=figure_from_2x3_lists("T",list_IR_low_naive,list_IR_middle_naive,list_IR_high_naive,
#                                           list_IR_low_exp,list_IR_middle_exp,list_IR_high_exp,
#                           'Naive - Low IR','Naive - Average IR','Naive - High IR','Experienced - Low IR',
#                           'Experienced - Average IR','Experienced - High IR',
#                           graphtitle='Para_IR_sel')

# Results_TD_TO_all=figure_from_3_lists("S1",list_TD_TO_low,list_TD_TO_middle,list_TD_TO_high,
#                           'Short TO','Average TO','Long TO',graphtitle='Para_TD_TO_all')

# Results_TD_TO_sel=figure_from_2x3_lists("T",list_TD_TO_low_naive,list_TD_TO_middle_naive,list_TD_TO_high_naive,
#                                           list_TD_TO_low_exp,list_TD_TO_middle_exp,list_TD_TO_high_exp,
#                           'Naive - Short TO','Naive - Average TO','Naive - Long TO',
#                           'Experienced - Short TO','Experienced - Average TO','Experienced - Long TO',
#                           graphtitle='Para_TD_TO_sel')

# Results_MD_TO_all=figure_from_3_lists("S1",list_MD_TO_low,list_MD_TO_middle,list_MD_TO_high,
#                           'Short Mean TO','Average Mean TO','Long mean TO',graphtitle='Para_MD_TO_all')

# Results_MD_TO_sel=figure_from_2x3_lists("T",list_MD_TO_low_naive,list_MD_TO_middle_naive,list_MD_TO_high_naive,
#                                           list_MD_TO_low_exp,list_MD_TO_middle_exp,list_MD_TO_high_exp,
#                           'Naive - Short Mean TO','Naive - Average Mean TO','Naive - Long Mean TO',
#                           'Experienced - Short Mean TO','Experienced - Average Mean TO','Experienced - Long Mean TO',
#                           graphtitle='Para_MD_TO_sel')

# Results_IMBI_all=figure_from_3_lists("T",list_IMBI_low,list_IMBI_middle,list_IMBI_high,
#                           'Short IMBI','Average IMBI','Long IMBI',graphtitle='Para_IMBI_all')

# Results_IMBI_sel=figure_from_2x3_lists("T",list_IMBI_low_naive,list_IMBI_middle_naive,list_IMBI_high_naive,
#                                           list_IMBI_low_exp,list_IMBI_middle_exp,list_IMBI_high_exp,
#                           'Naive - Short IMBI','Naive - Average IMBI','Naive - long IMBI','Experienced - Short IMBI',
#                           'Experienced - Average IMBI','Experienced - Long IMBI',
#                           graphtitle='Para_IMBI_sel')

# Results_TN_MB_all=figure_from_3_lists("T",list_TN_MB_low,list_TN_MB_middle,list_TN_MB_high,
#                           'Low number mount bouts','Average number mount bouts','High number mount bouts',graphtitle='Para_TN_MB_all')

# Results_TN_MB_sel=figure_from_2x3_lists("T",list_TN_MB_low_naive,list_TN_MB_middle_naive,list_TN_MB_high_naive,
#                                           list_TN_MB_low_exp,list_TN_MB_middle_exp,list_TN_MB_high_exp,
#                           'Naive - Low number mount bouts','Naive - Average number mount bouts','Naive - High number mount bouts','Experienced - Low number mount bouts',
#                           'Experienced - Average number mount bouts','Experienced - High number mount bouts',
#                           graphtitle='Para_TN_MB_sel')

# Results_TD_MB_all=figure_from_3_lists("T",list_TD_MB_low,list_TD_MB_middle,list_TD_MB_high,
#                           'Low duration mount bouts','Average duration mount bouts','High duration mount bouts',graphtitle='Para_TD_MB_all')

# Results_TD_MB_sel=figure_from_2x3_lists("T",list_TD_MB_low_naive,list_TD_MB_middle_naive,list_TD_MB_high_naive,
#                                           list_TD_MB_low_exp,list_TD_MB_middle_exp,list_TD_MB_high_exp,
#                           'Naive - Low duration mount bouts','Naive - Average duration mount bouts','Naive - High duration mount bouts','Experienced - Low duration mount bouts',
#                           'Experienced - Average duration mount bouts','Experienced - High duration mount bouts',
#                           graphtitle='Para_TD_MB_sel')

# ########NAIVE PLUS ##########
# # EXCLUDING PREVIOUS BEHAVIORS + NAIVE = e.g. COP2 AND the previous COPS if no ejac is reached)
# Results_III_sel_plus=figure_from_2x3_lists("T",list_III_low_naive_plus,list_III_middle_naive_plus,list_III_high_naive_plus,
#                                           list_III_low_exp,list_III_middle_exp,list_III_high_exp,
#                           'Naive - Short III','Naive - Average III','Naive - long III','Experienced - Short III',
#                           'Experienced - Average III','Experienced - Long III',
#                           graphtitle='Para_III_sel')

# Results_IR_sel_plus=figure_from_2x3_lists("T",list_IR_low_naive_plus,list_IR_middle_naive_plus,list_IR_high_naive_plus,
#                                           list_IR_low_exp,list_IR_middle_exp,list_IR_high_exp,
#                           'Naive - Low IR','Naive - Average IR','Naive - High IR','Experienced - Low IR',
#                           'Experienced - Average IR','Experienced - High IR',
#                           graphtitle='Para_IR_sel')

# Results_TD_TO_sel_plus=figure_from_2x3_lists("T",list_TD_TO_low_naive_plus,list_TD_TO_middle_naive_plus,list_TD_TO_high_naive_plus,
#                                           list_TD_TO_low_exp,list_TD_TO_middle_exp,list_TD_TO_high_exp,
#                           'Naive - Short TO','Naive - Average TO','Naive - Long TO',
#                           'Experienced - Short TO','Experienced - Average TO','Experienced - Long TO',
#                           graphtitle='Para_TD_TO_sel')

# Results_MD_TO_sel_plus=figure_from_2x3_lists("T",list_MD_TO_low_naive_plus,list_MD_TO_middle_naive_plus,list_MD_TO_high_naive_plus,
#                                           list_MD_TO_low_exp,list_MD_TO_middle_exp,list_MD_TO_high_exp,
#                           'Naive - Short Mean TO','Naive - Average Mean TO','Naive - Long Mean TO',
#                           'Experienced - Short Mean TO','Experienced - Average Mean TO','Experienced - Long Mean TO',
#                           graphtitle='Para_MD_TO_selpl')

# Results_IMBI_sel_plus=figure_from_2x3_lists("T",list_IMBI_low_naive_plus,list_IMBI_middle_naive_plus,list_IMBI_high_naive_plus,
#                                           list_IMBI_low_exp,list_IMBI_middle_exp,list_IMBI_high_exp,
#                           'Naive - Short IMBI','Naive - Average IMBI','Naive - long IMBI','Experienced - Short IMBI',
#                           'Experienced - Average IMBI','Experienced - Long IMBI',
#                           graphtitle='Para_IMBI_selpl')

# Results_TN_MB_sel_plus=figure_from_2x3_lists("T",list_TN_MB_low_naive_plus,list_TN_MB_middle_naive_plus,list_TN_MB_high_naive_plus,
#                                           list_TN_MB_low_exp,list_TN_MB_middle_exp,list_TN_MB_high_exp,
#                           'Naive - Low number mount bouts','Naive - Average number mount bouts','Naive - High number mount bouts','Experienced - Low number mount bouts',
#                           'Experienced - Average number mount bouts','Experienced - High number mount bouts',
#                           graphtitle='Para_TN_MB_selpl')

# Results_TD_MB_sel_plus=figure_from_2x3_lists("T",list_TD_MB_low_naive_plus,list_TD_MB_middle_naive_plus,list_TD_MB_high_naive_plus,
#                                           list_TD_MB_low_exp,list_TD_MB_middle_exp,list_TD_MB_high_exp,
#                           'Naive - Low duration mount bouts','Naive - Average duration mount bouts','Naive - High duration mount bouts','Experienced - Low duration mount bouts',
#                           'Experienced - Average duration mount bouts','Experienced - High duration mount bouts',
#                           graphtitle='Para_TD_MB_selpl')

# ###################################################################################################################
# ############## AUC RESULTS EXCL ###################################################################################
# ###################################################################################################################

# # Make figures of AUC results upon experience
# AUC_S1_exp_2sec=results_experience_means_AUC('S1',seconds=2,graphtitle='AUC_S1_2sec')
# AUC_S2_exp_2sec=results_experience_means_AUC('S2',seconds=2,graphtitle='AUC_S2_2sec')
# AUC_T_exp_2sec=results_experience_means_AUC('T',seconds=2,graphtitle='AUC_T_2sec')

# AUC_S1_exp_5sec=results_experience_means_AUC('S1',graphtitle='AUC_S1_5sec')
# AUC_S2_exp_5sec=results_experience_means_AUC('S2',graphtitle='AUC_S2_5sec')
# AUC_T_exp_5sec=results_experience_means_AUC('T',graphtitle='AUC_T_5sec')

# AUC_S1_exp_10sec=results_experience_means_AUC('S1',seconds=10,graphtitle='AUC_S1_10sec')
# AUC_S2_exp_10sec=results_experience_means_AUC('S2',seconds=10,graphtitle='AUC_S2_10sec')
# AUC_T_exp_10sec=results_experience_means_AUC('T',seconds=10,graphtitle='AUC_T_10sec')

# # Make figures of AUC results upon experience 3part
# AUC_S1_exp_3part_2sec=results_experience_means_AUC_3part('S1',seconds=2,graphtitle='AUC_S1_2sec_3part')
# AUC_S2_exp_3part_2sec=results_experience_means_AUC_3part('S2',seconds=2,graphtitle='AUC_S2_2sec_3part')

# AUC_S1_exp_3part_5sec=results_experience_means_AUC_3part('S1',graphtitle='AUC_S1_5sec_3part')
# AUC_S2_exp_3part_5sec=results_experience_means_AUC_3part('S2',graphtitle='AUC_S2_5sec_3part')

# AUC_S1_exp_3part_10sec=results_experience_means_AUC_3part('S1',seconds=10,graphtitle='AUC_S1_10sec_3part')
# AUC_S2_exp_3part_10sec=results_experience_means_AUC_3part('S2',seconds=10,graphtitle='AUC_S2_10sec_3part')

# # Make figures of AUC results upon experience TN3part
# AUC_S1_exp_TN3part_2sec=results_experience_means_AUC_TN3part('S1',seconds=2,graphtitle='AUC_S1_2sec_TN3part')
# AUC_S2_exp_TN3part_2sec=results_experience_means_AUC_TN3part('S2',seconds=2,graphtitle='AUC_S2_2sec_TN3part')

# AUC_S1_exp_TN3part_5sec=results_experience_means_AUC_TN3part('S1',graphtitle='AUC_S1_5sec_TN3part')
# AUC_S2_exp_TN3part_5sec=results_experience_means_AUC_TN3part('S2',graphtitle='AUC_S2_5sec_TN3part')

# AUC_S1_exp_TN3part_10sec=results_experience_means_AUC_TN3part('S1',seconds=10,graphtitle='AUC_S1_10sec_TN3part')
# AUC_S2_exp_TN3part_10sec=results_experience_means_AUC_TN3part('S2',seconds=10,graphtitle='AUC_S2_10sec_TN3part')


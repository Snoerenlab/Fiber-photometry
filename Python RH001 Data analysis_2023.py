# -*- coding: utf-8 -*-
"""
Created in 2022

Script to analyze the fiber photometry data with copulation test for RH001.
Based on Python 3.9, installed via anaconda.

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

# Define the directory folders (use / instead of \)
directory= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA" # Of the metafile and behavioral data
directory_tdt="D:/RH001 POA/TDT_tanks_and_metafile/" # Of the TDT recordings
directory_output= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Output" # Of the output folder for your results
directory_results= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results tdt" # Of the output folder for your results
directory_results_cor= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results tdt cor" # Of the output folder for your results corrected for outliers
directory_results_beh= "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Results behavior" # Of the output folder for your results
directory_pickle = "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Pickle files"
directory_fullgraphs = "C:/Users/esn001/OneDrive - UiT Office 365/Python 3.8/Data projects/RH001 POA/Fullgraphs"

if not os.path.isdir(directory_output):
    os.mkdir(directory_output)

if not os.path.isdir(directory_fullgraphs):
    os.mkdir(directory_fullgraphs)

if not os.path.isdir(directory_pickle):
    os.mkdir(directory_pickle)

############# FOR RESULTS PYTHON #############
# if not os.path.isdir(directory_results_cor):
#     os.mkdir(directory_results_cor)

# if not os.path.isdir(directory_results_beh):
#     os.mkdir(directory_results_beh)

# directory_TDT_results_perrat = "/Results per rat"
# directory_TDT_results_parts = "/Results parts"
# directory_TDT_AUC = "/AUC"
# directory_TDT_AUC_parts = "/AUC parts"
# wirectory_TDT_results_parameters = "/Results parameters"
###################################################

# Assign file names
file_TDT = 'Metafile TDT_RH001b_RH001c_python.xlsx' # Metafile
file_beh = 'RH001bc Raw data corrected_plus.xlsx' # Noldus raw data

# Define the directory from which the files should come
os.chdir(directory)

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

# # Extra doubts go out as well
# list_excltdt=[102,103,104,105,106,109,110,111,112,113,116, 119, 120, 123, 125]
# list_excl=['102','103','104','105','106','109','110','111','112','113','116', '119', '120', '123','125']

# For data analysis keep all files
list_excltdt=[]
list_excl=[]

dict_manual_adjustments={'Cut_start':{
    '101COP5':[1400,3000,3000,3000],
    '105COP2':[1080,3000,3000,3000],
    '114COP1':[540,1640,1950,2050],
    '121COP1':[420,700,990,3000],
    '122COP3':[1800,3000,3000,3000],
    '122COP5':[325,3000,3000,3000]},
    'Cut_end':{
    '101COP5':[1405,0,0,0],
    '105COP2':[1180,0,0,0],
    '114COP1':[600,1680,1980,2100],
    '121COP1':[440,800,1085,0],
    '122COP3':[2000,0,0,0],
    '122COP5':[500,0,0,0]}}


############################################################################################################################

# Set your baseline correction times before snips
baseline_start=-35
baseline_end=-5

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
list_copmark=list((BA,BB,BC,BN))
list_sex=list((BA,BB,BC))
list_behaviors=list((BA,BB,BC,BD,BE,BF,BG,BH,BI,BJ,BK,BL))
list_startcop=list(('Start Mount','Start Intromission','Start Ejaculation'))
list_other_behaviors=list((BD,BE,BF,BG,BH,BI,BJ,BK,BL))
list_behaviors_extra=list((EA,EB,EC,ED,EE,EF,EG,EH,EI,EJ))
list_beh_tdt=list((BA,BB,BC,BD,BE,BF,BG,BH,BI,BJ,BK,BL,BN))
list_sex_MB=list((BA,BB,BC,'Single Mount','Single Intromission','Single Ejaculation','Start MB Mount',
                  'Start MB Intromission','End MB Mount','End MB Intromission','End MB Ejaculation',
                  'MB Mount','MB Intromission'))


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

# # Save the dataframes to excel for check
# writer_data = pd.ExcelWriter(out_path2, engine='xlsxwriter')
# data_full.to_excel(writer_data, sheet_name='data_T')
# writer_data.save()
# writer_data.close()

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

# # Save the dataframes to excel for check
# writer_data = pd.ExcelWriter(out_path3, engine='xlsxwriter')
# data_T.to_excel(writer_data, sheet_name='data_T')
# data_S1.to_excel(writer_data, sheet_name='data_S1')
# data_S2.to_excel(writer_data, sheet_name='data_S2')
# data_S3.to_excel(writer_data, sheet_name='data_S3')
# data_S1_PEII.to_excel(writer_data, sheet_name='data_S1_PEII')
# data_S2_PEII.to_excel(writer_data, sheet_name='data_S2_PEII')
# data_S3_PEII.to_excel(writer_data, sheet_name='data_S3_PEII')
# writer_data.save()
# writer_data.close()

# Create list with unique IDs that are in dataset
list_id=list(data_full[ID].unique())

# Calculate the e.g. numbers, durations and latencies of behaviors
def data_beh(dataframe,title):
    """
    Parameters
    ----------
    dataframe : DataFrame
        Add the dataframe for analysis
        e.g. data_T, data_B, data_S1, data_S2, data_S3
    title : string
        This is just a marker for the console to keep track of progress.

    Returns
    -------
    dict_data : dictionary
        Returns a dictionary of all behavioral data per rat
    """
    
    dataframe['obs_num'] = dataframe.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))

    # Create an empty dictionary with ID and behaviors
    dict_data={}
    for key in list_id:
        dict_data[key]={}
        for beh in list_behaviors:
            dict_data[key]['TN_%s'%beh]=[]
    
    # Fill in behaviors and times in dictionary
    for key,value in dict_data.items():
        print (key)
        for beh in list_behaviors:
            TN_temp=0
            TD_temp=0
            for row in dataframe.itertuples():
                if row.ID==key:
                    if row.Behavior == beh:
                        TN_temp=TN_temp+1
                        TD_temp=TD_temp+row.durations
           
            # Fill in dictionary with total number, number in start compartment, and number in reward compartment
            dict_data[key]['TN_%s'%beh]=TN_temp
            dict_data[key]['TD_%s'%beh]=TD_temp

        # Fill in starttimes
        temp=0
        for row in dataframe.itertuples():
            if row.ID==key:
                if row.obs_num ==1:
                    temp = row.Time 
        dict_data[key]['Starttime']=temp
        
        # Fill in latency in dictionary
        for beh in list_behaviors:
            value=NaN
            temp_start=1800+dict_data[key]['Starttime']
            temp_end=1800+dict_data[key]['Starttime']
            for row in dataframe.itertuples():
                if row.ID==key:
                    if row.Behavior == beh and row.Time<temp_start:
                        temp_start=row.Beh_start
                        temp_end=row.Beh_end
                        value=temp_start-dict_data[key]['Starttime']
            dict_data[key]['L1_%s'%beh]=value if dict_data[key]['TN_%s'%beh]>0 else np.nan
            dict_data[key]['Time_%s'%beh]=temp_start if dict_data[key]['TN_%s'%beh]>0 else np.nan
            dict_data[key]['Time_end_%s'%beh]=temp_end if dict_data[key]['TN_%s'%beh]>0 else np.nan

        # Fix latency 1st behavior and L1E
        dict_data[key]['L1_B']=dict_data[key]['L1_%s'%BA] if dict_data[key]['L1_%s'%BA]<dict_data[key]['L1_%s'%BB] else dict_data[key]['L1_%s'%BB]
        dict_data[key]['L1_Ejaculation']=dict_data[key]['L1_Ejaculation'] if dict_data[key]['TN_%s'%BC]>=1 else 1800
        dict_data[key]['L1_EM']=dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BA] if dict_data[key]['TN_%s'%BC]>=1 and dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BA]>0 else 1800
        dict_data[key]['L1_EI']=dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BB] if dict_data[key]['TN_%s'%BC]>=1 and dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BB]>0else 1800
        dict_data[key]['L1_EB']=dict_data[key]['L1_EM'] if dict_data[key]['L1_EM']<dict_data[key]['L1_EI'] else dict_data[key]['L1_EI']
            
        # Calculate the extra behaviors of total test
        dict_data[key]['TN_%s'%EA]=dict_data[key]['TN_%s'%BA]+dict_data[key]['TN_%s'%BB]+dict_data[key]['TN_%s'%BC]
        dict_data[key][EB]=dict_data[key]['TN_%s'%BB]/(dict_data[key]['TN_%s'%BA]+dict_data[key]['TN_%s'%BB]) if (dict_data[key]['TN_%s'%BA]+dict_data[key]['TN_%s'%BB]) else 0
        dict_data[key][EC]=dict_data[key]['L1_%s'%BC]/dict_data[key]['TN_%s'%BB] if (dict_data[key]['TN_%s'%BB]) else 0
        dict_data[key]['TN_%s'%EH]=dict_data[key]['TN_%s'%EA]+dict_data[key]['TN_%s'%BD]+dict_data[key]['TN_%s'%BE]+dict_data[key]['TN_%s'%BF]+dict_data[key]['TN_%s'%BG]
        dict_data[key]['TN_%s'%EI]=dict_data[key]['TN_%s'%EA]+dict_data[key]['TN_%s'%BI]+dict_data[key]['TN_%s'%BK]
        dict_data[key]['TN_%s'%EJ]=dict_data[key]['TN_%s'%BJ]+dict_data[key]['TN_%s'%BH]+dict_data[key]['TN_%s'%BL]

        dict_data[key]['TD_%s'%EA]=dict_data[key]['TD_%s'%BA]+dict_data[key]['TD_%s'%BB]+dict_data[key]['TD_%s'%BC]
        dict_data[key]['TD_%s'%EH]=dict_data[key]['TD_%s'%EA]+dict_data[key]['TD_%s'%BD]+dict_data[key]['TD_%s'%BE]+dict_data[key]['TD_%s'%BF]+dict_data[key]['TD_%s'%BG]
        dict_data[key]['TD_%s'%EI]=dict_data[key]['TD_%s'%EA]+dict_data[key]['TD_%s'%BI]+dict_data[key]['TD_%s'%BK]
        dict_data[key]['TD_%s'%EJ]=dict_data[key]['TD_%s'%BJ]+dict_data[key]['TD_%s'%BH]+dict_data[key]['TD_%s'%BL]

        # Count single copulation total test
        # Count number mount bouts in total test
        for b in list_sex:
            TN_temp=0
            TD_temp=0
            for row in dataframe.itertuples():
                if row.ID==key:
                    if row.MB_cop_mark == 'Single %s'%b:
                        TN_temp=TN_temp+1
                        TD_temp=TD_temp+row.Duration_mount_bout

                    dict_data[key]['TN_MB_single_%s' %b]= TN_temp
                    dict_data[key]['TD_MB_single_%s' %b]= TD_temp

        TN_temp_MB=0
        TD_temp_MB=0
        TN_temp_TO=0
        TD_temp_TO=0
        IMBI=[]
        for row in dataframe.itertuples():
            if row.ID==key:
                if row.MB_mark == 'Single copulation' or row.MB_mark=='Start MB':
                    TN_temp_MB = TN_temp_MB+1
                    TD_temp_MB = TD_temp_MB+row.Duration_mount_bout

                dict_data[key]['TN_MB']= TN_temp_MB
                dict_data[key]['TD_MB']= TD_temp_MB if TN_temp_MB >0 else np.NaN

                if row.Duration_time_out > 0:
                    TN_temp_TO = TN_temp_TO+1
                    TD_temp_TO = TD_temp_TO+row.Duration_time_out
                
                dict_data[key]['TN_TO']= TN_temp_TO
                dict_data[key]['TD_TO']= TD_temp_TO if TN_temp_TO >0 else np.NaN
                dict_data[key]['MD_TO']= TD_temp_TO/TN_temp_TO if TN_temp_TO>0 else np.NaN
                    
                # Calculate IMBI, mean of interval mount bouts
                if row.Interval_MB >0:
                    IMBI.append(row.Interval_MB)
                dict_data[key]['MD_IMBI']=np.mean(IMBI) if TN_temp_MB>0 else np.NaN
      
        # calculate M/I as single cops or within mount bout        
        TN_M_single_temp=0
        TN_I_single_temp=0
        TN_M_MB_temp=0
        TN_I_MB_temp=0
        TN_M_start_MB_temp=0
        TN_I_start_MB_temp=0
        TN_M_end_MB_temp=0
        TN_I_end_MB_temp=0

        TD_M_single_temp=0
        TD_I_single_temp=0
        TD_M_MB_temp=0
        TD_I_MB_temp=0
        TD_M_start_MB_temp=0
        TD_I_start_MB_temp=0
        TD_M_end_MB_temp=0
        TD_I_end_MB_temp=0
        for row in dataframe.itertuples():
            if row.ID==key:
                if row.MB_cop_mark == 'Single Mount':
                    TN_M_single_temp = TN_M_single_temp+1
                    TD_M_single_temp = TD_M_single_temp+row.Duration_mount_bout
                if row.MB_cop_mark == 'Single Intromission':
                    TN_I_single_temp = TN_I_single_temp+1
                    TD_I_single_temp = TD_I_single_temp+row.Duration_mount_bout
                if row.MB_cop_mark == 'MB Mount':
                    TN_M_MB_temp = TN_M_MB_temp+1
                    TD_M_MB_temp = TD_M_MB_temp+row.Duration_mount_bout
                if row.MB_cop_mark == 'MB Intromission':
                    TN_I_MB_temp = TN_I_MB_temp+1
                    TD_I_MB_temp = TD_I_MB_temp+row.Duration_mount_bout
                if row.MB_cop_mark =='Start MB Mount': 
                    TN_M_start_MB_temp = TN_M_start_MB_temp+1
                    TD_M_start_MB_temp = TD_M_start_MB_temp+row.Duration_mount_bout
                if row.MB_cop_mark =='End MB mount':
                    TN_M_end_MB_temp = TN_M_end_MB_temp+1
                    TD_M_end_MB_temp = TD_M_end_MB_temp+row.Duration_mount_bout
                if row.MB_cop_mark =='Start MB Intromission' :
                    TN_I_start_MB_temp = TN_I_start_MB_temp+1
                    TD_I_start_MB_temp = TD_I_start_MB_temp+row.Duration_mount_bout
                if row.MB_cop_mark =='End MB Intromission':
                    TN_I_end_MB_temp = TN_I_end_MB_temp+1
                    TD_I_end_MB_temp = TD_I_end_MB_temp+row.Duration_mount_bout

                dict_data[key]['TN_MB Mount']= TN_M_MB_temp
                dict_data[key]['TN_MB Intromission']= TN_I_MB_temp
                dict_data[key]['TN_Start MB Mount']= TN_M_start_MB_temp
                dict_data[key]['TN_Start MB Intromission']= TN_I_start_MB_temp
                dict_data[key]['TN_End MB Mount']= TN_M_end_MB_temp
                dict_data[key]['TN_End MB Intromission']= TN_I_end_MB_temp
                dict_data[key]['TN_Mounts in MB']= dict_data[key]['TN_MB Mount']+dict_data[key]['TN_Start MB Mount']+dict_data[key]['TN_End MB Mount']
                dict_data[key]['TN_Intromissions in MB']= dict_data[key]['TN_MB Intromission']+dict_data[key]['TN_Start MB Intromission']+dict_data[key]['TN_End MB Intromission']

                dict_data[key]['TD_MB Mount']= TD_M_MB_temp
                dict_data[key]['TD_MB Intromission']= TD_I_MB_temp
                dict_data[key]['TD_Start MB Mount']= TD_M_start_MB_temp
                dict_data[key]['TD_Start MB Intromission']= TD_I_start_MB_temp
                dict_data[key]['TD_End MB Mount']= TD_M_end_MB_temp
                dict_data[key]['TD_End MB Intromission']= TD_I_end_MB_temp
                dict_data[key]['TD_Mounts in MB']= dict_data[key]['TD_MB Mount']+dict_data[key]['TD_Start MB Mount']+dict_data[key]['TD_End MB Mount']
                dict_data[key]['TD_Intromissions in MB']= dict_data[key]['TD_MB Intromission']+dict_data[key]['TD_Start MB Intromission']+dict_data[key]['TD_End MB Intromission']

    print('%s'%title)
    return dict_data

# Calculate the e.g. numbers, durations and latencies of behaviors for PEI period, so that this can later be used for correction
def data_beh_PEI(dataframe,title):
    """
    dataframe : DataFrame
        Add the dataframe of the PEI data sets for analysis
        e.g. data_S1_PEII, data_S2_PEII, data_S3_PEII
    title : string
        This is just a marker for the console to keep track of progress.

    Returns
    -------
    dict_data : dictionary
        Returns a dictionary of all behavioral data per rat for the PEI period
    """
    
    dataframe['obs_num'] = dataframe.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))

    # Create an empty dictionary with ID and behaviors
    dict_data={}
    for key in list_id:
        dict_data[key]={}
        for beh in list_behaviors:
            dict_data[key]['TN_%s'%beh]=[]
    
    # Fill in behaviors and times in dictionary
    for key,value in dict_data.items():
        print (key)
        for beh in list_behaviors:
            TN_temp=0
            TD_temp=0
            for row in dataframe.itertuples():
                if row.ID==key:
                    if row.Behavior == beh:
                        TN_temp=TN_temp+1
                        TD_temp=TD_temp+row.durations
           
            # Fill in dictionary with total number, number in start compartment, and number in reward compartment
            dict_data[key]['TN_%s'%beh]=TN_temp
            dict_data[key]['TD_%s'%beh]=TD_temp

        # Fill in starttimes
        temp=0
        for row in dataframe.itertuples():
            if row.ID==key:
                if row.obs_num ==1:
                    temp = row.Time 
        dict_data[key]['Starttime']=temp
        
        # Fill in latency in dictionary
        for beh in list_behaviors:
            value=NaN
            temp_start=1800+dict_data[key]['Starttime']
            temp_end=1800+dict_data[key]['Starttime']
            for row in dataframe.itertuples():
                if row.ID==key:
                    if row.Behavior == beh and row.Time<temp_start:
                        temp_start=row.Beh_start
                        temp_end=row.Beh_end
                        value=temp_start-dict_data[key]['Starttime']
            dict_data[key]['L1_%s'%beh]=value
            dict_data[key]['Time_%s'%beh]=temp_start
            dict_data[key]['Time_end_%s'%beh]=temp_end
            
        # Fix latency 1st behavior and L1E
        dict_data[key]['L1_B']=dict_data[key]['L1_%s'%BA] if dict_data[key]['L1_%s'%BA]<dict_data[key]['L1_%s'%BB] else dict_data[key]['L1_%s'%BB]
        dict_data[key]['L1_Ejaculation']=dict_data[key]['L1_Ejaculation'] if dict_data[key]['TN_%s'%BC]>=1 else 1800
        dict_data[key]['L1_EM']=dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BA] if dict_data[key]['TN_%s'%BC]>=1 and dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BA]>0 else 1800
        dict_data[key]['L1_EI']=dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BB] if dict_data[key]['TN_%s'%BC]>=1 and dict_data[key]['Time_%s'%BC]-dict_data[key]['Time_%s'%BB]>0else 1800
        dict_data[key]['L1_EB']=dict_data[key]['L1_EM'] if dict_data[key]['L1_EM']<dict_data[key]['L1_EI'] else dict_data[key]['L1_EI']

            
    print('%s'%title)
    return dict_data

print ('definition behavior done')

# dict_results_T=data_beh(data_T,'data_T')
# dict_results_S1=data_beh(data_S1,'data_S1')
# dict_results_S2=data_beh(data_S2,'data_S2')
# dict_results_S3=data_beh(data_S3,'data_S3')

# dict_results_S1_PEII=data_beh_PEI(data_S1_PEII,'data_S1_PEII')
# dict_results_S2_PEII=data_beh_PEI(data_S2_PEII,'data_S2_PEII')
# dict_results_S3_PEII=data_beh_PEI(data_S3_PEII,'data_S3_PEII')

# # Fill in PEI data per series 
# for keys,values in dict_results_S1.items():
#     for key,value in dict_results_S1_PEII.items():
#         if dict_results_S1[key]['TN_Ejaculation']>0 and dict_results_S1_PEII[key]['TN_Intromission']>0:
#             dict_results_S1[key]['PEII']=dict_results_S1_PEII[key]['Time_%s'%BB]-dict_results_S1_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S1[key]['PEII']=np.NaN

#         if dict_results_S1[key]['TN_Ejaculation']>0 and dict_results_S1_PEII[key]['TN_Mount']>0:
#             dict_results_S1[key]['PEIM']=dict_results_S1_PEII[key]['Time_%s'%BA]-dict_results_S1_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S1[key]['PEIM']=np.NaN

#         if dict_results_S1[key]['PEIM']<dict_results_S1[key]['PEII']:
#             dict_results_S1[key]['PEIB']=dict_results_S1[key]['PEIM']
#         else:
#             dict_results_S1[key]['PEIB']=dict_results_S1[key]['PEII']

#         # Calculate CR
#         dict_results_S1[key][ED]=(dict_results_S1[key]['TN_%s'%BA]+dict_results_S1[key]['TN_%s'%BB])/dict_results_S1[key]['L1_%s'%BC]  

# for keys,values in dict_results_S2.items():
#     for key,value in dict_results_S2_PEII.items():
#         if dict_results_S2[key]['TN_Ejaculation']>0 and dict_results_S2_PEII[key]['TN_Intromission']>0:
#             dict_results_S2[key]['PEII']=dict_results_S2_PEII[key]['Time_%s'%BB]-dict_results_S2_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S2[key]['PEII']=np.NaN

#         if dict_results_S2[key]['TN_Ejaculation']>0 and dict_results_S2_PEII[key]['TN_Mount']>0:
#             dict_results_S2[key]['PEIM']=dict_results_S2_PEII[key]['Time_%s'%BA]-dict_results_S2_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S2[key]['PEIM']=np.NaN

#         if dict_results_S2[key]['PEIM']<dict_results_S2[key]['PEII']:
#             dict_results_S2[key]['PEIB']=dict_results_S2[key]['PEIM']
#         else:
#             dict_results_S2[key]['PEIB']=dict_results_S2[key]['PEII']

#         # Calculate CR
#         dict_results_S2[key][ED]=(dict_results_S2[key]['TN_%s'%BA]+dict_results_S2[key]['TN_%s'%BB])/dict_results_S2[key]['L1_%s'%BC]  
    
# for keys,values in dict_results_S3.items():
#     for key,value in dict_results_S3_PEII.items():
#         if dict_results_S3[key]['TN_Ejaculation']>0 and dict_results_S3_PEII[key]['TN_Intromission']>0:
#             dict_results_S3[key]['PEII']=dict_results_S3_PEII[key]['Time_%s'%BB]-dict_results_S3_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S3[key]['PEII']=np.NaN

#         if dict_results_S3[key]['TN_Ejaculation']>0 and dict_results_S3_PEII[key]['TN_Mount']>0:
#             dict_results_S3[key]['PEIM']=dict_results_S3_PEII[key]['Time_%s'%BA]-dict_results_S3_PEII[key]['Time_end_%s'%BC]
#         else:
#             dict_results_S3[key]['PEIM']=np.NaN

#         if dict_results_S3[key]['PEIM']<dict_results_S3[key]['PEII']:
#             dict_results_S3[key]['PEIB']=dict_results_S3[key]['PEIM']
#         else:
#             dict_results_S3[key]['PEIB']=dict_results_S3[key]['PEII']

#         # Calculate CR
#         dict_results_S3[key][ED]=(dict_results_S3[key]['TN_%s'%BA]+dict_results_S3[key]['TN_%s'%BB])/dict_results_S3[key]['L1_%s'%BC]  
    
# # Calculate total intromissions interval (total time test / intromissions)
# for keys,values in dict_results_T.items():
#     if dict_results_T[keys]['TN_Copulations']>0:
#         dict_results_T[keys]['CR']=(dict_results_T[keys]['TN_%s' %BA]+dict_results_T[keys]['TN_%s' %BB]+dict_results_T[keys]['TN_%s' %BC])/Timetest
#     if dict_results_T[keys]['TN_%s'%(BB)]>0:
#         dict_results_T[keys]['III']=Timetest/dict_results_T[keys]['TN_%s'%(BB)] 

# for keys,values in dict_results_S1.items():
#     if dict_results_S1[keys]['TN_%s'%(BB)]>0:
#         dict_results_S1[keys]['IIII']=dict_results_S1[keys]['L1_EI']/dict_results_S1[keys]['TN_%s'%(BB)] 
#         dict_results_S1[keys]['IIIB']=dict_results_S1[keys]['L1_EB']/dict_results_S1[keys]['TN_%s'%(BB)]
        
# for keys,values in dict_results_S2.items():
#     if dict_results_S2[keys]['TN_%s'%(BB)]>0:
#         dict_results_S2[keys]['IIIB']=dict_results_S2[keys]['L1_EB']/dict_results_S2[keys]['TN_%s'%(BB)] 
#         dict_results_S2[keys]['IIII']=dict_results_S2[keys]['L1_EI']/dict_results_S2[keys]['TN_%s'%(BB)] 
        
# for keys,values in dict_results_S3.items():
#     if dict_results_S3[keys]['TN_%s'%(BB)]>0:
#         dict_results_S3[keys]['IIIB']=dict_results_S3[keys]['L1_EB']/dict_results_S3[keys]['TN_%s'%(BB)] 
#         dict_results_S3[keys]['IIII']=dict_results_S3[keys]['L1_EI']/dict_results_S3[keys]['TN_%s'%(BB)] 
 
# dict_results_tdt={'S1':dict_results_S1,'S2':dict_results_S2,'T':dict_results_T}

# # Make list of included IDs    
# list_activeID=list(dict_results_T.keys())

# Make a dataframe with only the M/I/E
# Create a new dataframe with only the copulations, to distract the times between copulations
df_MIE=data_T.loc[(data_T[BEH]=='Start Mount')|(data_T[BEH]=='Start Intromission')|(data_T[BEH]=='Start Ejaculation')]
df_MIE['obs_num'] = df_MIE.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
df_MIE = df_MIE.sort_values(by=[OBS,TIME], ascending = False)
df_MIE['obs_num_back'] = df_MIE.groupby(OBS)[BEH].transform(lambda x: np.arange(1, len(x) + 1))
df_MIE = df_MIE.sort_values(by=[OBS,TIME])
# df_MIE['Next_MIE']=df_MIE.groupby('ID')['Temp_MIE'].shift(-1)
df_MIE['Previous_MIE_time']=df_MIE.groupby('ID')['Beh_end'].shift(1)
df_MIE['Previous_MIE_time']=np.where((df_MIE['obs_num']==1),np.NaN,df_MIE['Previous_MIE_time'])
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


# # Make dataframes from the dictionairies
# df_results_T = pd.DataFrame(dict_results_T)
# df_results_T=df_results_T.T

# df_results_S1 = pd.DataFrame(dict_results_S1)
# df_results_S1=df_results_S1.T

# df_results_S2 = pd.DataFrame(dict_results_S2)
# df_results_S2=df_results_S2.T

# df_results_S3 = pd.DataFrame(dict_results_S3)
# df_results_S3=df_results_S3.T

# # Make dictionary of dataframes with total
# df_results={'T':df_results_T,'S1':df_results_S1,'S2':df_results_S2,'S3':df_results_S3}

# # Rename columns for practical use
# for keys in df_results.keys():
#       df_results[keys].columns=df_results[keys].columns.str.replace(' ','_', regex=True)

# # Add columns about virus etc
# for key,df in df_results.items():
#     df.reset_index(inplace=True)
#     df.columns = df.columns.str.replace('index','ID',regex=True) 

#     df[RATID]=df[ID]
#     df[RATID]=df[RATID].map(dict_id)

#     df[EXP]=df[ID]
#     df[EXP]=df[ID].map(dict_coptest)

#     df[VIRUS]=pd.to_numeric(df[RATID])
#     df[VIRUS]=df[VIRUS].map(dict_virus)

# start_columns=[ID,EXP,RATID,VIRUS]

# # Save the df_resultsframes to excel for check
# writer_df_results = pd.ExcelWriter(out_path4, engine='xlsxwriter')
# df_results_T.to_excel(writer_df_results, sheet_name='T')
# df_results_S1.to_excel(writer_df_results, sheet_name='S1')
# df_results_S2.to_excel(writer_df_results, sheet_name='S2')
# df_results_S3.to_excel(writer_df_results, sheet_name='S3')
# writer_df_results.save()
# writer_df_results.close()

# # Create a dictionairy with the codes and explanations for the info sheet 
# dict_info={'Observation':'Name of observation','ID':'Unique rat-test identifier','Experiment':'Experimental code','RatID':'RatID','Virus':'virus treatment',
#             'T, S1, S2, S3':'Total test or 1st-3rd ejaculatory series','TN':'Total number','TD':'Time spent (s)','MD':'mean duration (s)',
#             'IR':'Intromission ratio = I/(I+M)',
#             'III':'Inter intromission interval = Total time test (all results) or ejaculation latency (series)/ number of intromissions',
#             'CR':'Copulatory rate = (M+I+E)/Total time test (all results) or ejaculation latency (series)',
#             'L1_':'Latency to first ...., calculated to the start of the copulation',
#             'L1_B':'Latency to first behavior (either mount or intromission',
#             'L1_EB':'Latency to ejaculation from 1st behavior 1st (or 2nd) ejaculatory serie',
#             'L1_EI':'Latency to ejaculation from 1st intromissions 1st (or 2nd) ejaculatory serie',
#             'PEIB':'Postejaculatory interval to 1st behavior 1st (or 2nd) ejaculatory serie, calculated from the end of an ejaculation to the start of the next copulation',
#             'PEII':'Postejaculatory interval to 1st intromissions 1st (or 2nd) ejaculatory serie, calculated from the end of an ejaculation to the start of the next copulation',
#             'IIIB':'III based on time from 1st behavior (M/I) performed',
#             'IIII':'III based on time from 1st intromission performed',
#             'MB':'Mount bouts',
#             'TO':'Time-outs, defined from end of copulation of end mount bout until start of copulation next mount bout',
#             'IMBI':'Mean time from (start of) first copulation of one mount bout to the (start of) first copulation of the next mount bout',
#             'TN_MB Mount':'Total number of mounts in a MB that is not the first or the last',
#             'TN_Start MB mount':'Total number of mounts that started a mount bout (similar for intromissions)',
#             'TN_End MB mount':'Total number of mounts that end a mount bout (similar for intromissions)',
#             'TN_Mounts in MB':'Total number of mounts that are in a mount bout, including mounts that start and end a mount bout (similar for intromissions)',
#             'TN_Single mounts':'Total number of mounts that by itself form a mount bout (similar for intromissions)'}

# print("results finished")

# # Make dataframe from dict_info for printing
# df_info= pd.DataFrame.from_dict(dict_info, orient='index')
# df_info.reset_index()

# print('dataframes finished')

# # Determine which columns go where and in what order
# TN_main=['ID','Experiment','RatID', 'Virus','TN_Mount', 'TN_Intromission', 'TN_Ejaculation',
#         'TN_Attempt_to_mount','TN_Copulations','L1_B','L1_Mount','L1_Intromission', 'L1_Ejaculation', 'L1_EB', 'L1_EI', 'IR', 'III','IIIB', 'IIII','CR','PEII', 'PEIB']

# TN_extra=['ID','Experiment','RatID', 'Virus','TN_Copulation_oriented_behavior', 'TN_Female_oriented_behavior','TN_Anogenital_sniffing', 'TN_Chasing','TN_Genital_grooming', 'TN_Sniffing_bedding', 'TN_Sniffing_female', 'TN_Head_away_from_female', 'TN_Head_to_female', 'TN_Other', 
#         'L1_Attempt_to_mount', 'L1_Anogenital_sniffing',  'L1_Chasing','L1_Genital_grooming','L1_Sniffing_bedding','L1_Sniffing_female']
       
# TD_main=['ID','Experiment','RatID', 'Virus','TD_Mount','TD_Intromission', 'TD_Ejaculation', 'TD_Attempt_to_mount','TD_Copulations',
#         'TD_Copulation_oriented_behavior','TD_Female_oriented_behavior', 'TD_Anogenital_sniffing', 'TD_Chasing', 'TD_Genital_grooming',
#         'TD_Sniffing_bedding', 'TD_Sniffing_female', 'TD_Head_away_from_female','TD_Head_to_female', 'TD_Other']

# MB_main=['ID','Experiment','RatID', 'Virus','TN_MB', 'TD_MB','TN_TO','TD_TO','MD_TO','MD_IMBI','TN_MB_single_Mount','TN_MB_single_Intromission','TN_MB_single_Ejaculation',
#         'TD_MB_single_Mount', 'TD_MB_single_Intromission', 'TD_MB_single_Ejaculation', 'TN_MB_Mount','TN_MB_Intromission','TN_Start_MB_Mount','TN_Start_MB_Intromission','TN_End_MB_Mount',
#         'TN_End_MB_Intromission','TN_Mounts_in_MB','TN_Intromissions_in_MB','TD_MB_Mount','TD_MB_Intromission','TD_Start_MB_Mount','TD_Start_MB_Intromission','TD_End_MB_Mount',
#         'TD_End_MB_Intromission','TD_Mounts_in_MB','TD_Intromissions_in_MB']

# TN_main_T=['ID','Experiment','RatID', 'Virus','TN_Mount', 'TN_Intromission', 'TN_Ejaculation',
#         'TN_Attempt_to_mount','TN_Copulations','L1_B','L1_Mount','L1_Intromission', 'L1_Ejaculation', 'L1_EB', 'L1_EI', 'IR', 'III','CR']

# # Create new dataframes with the relevant data
# df_TN_main_T=pd.DataFrame()
# for i in start_columns:
#     df_TN_main_T['%s'%i]=df_results_T['%s'%i].copy()
# for t,title in enumerate(TN_main_T):
#     df_TN_main_T['T_%s'%title]=df_results_T['%s'%title].copy()

# df_TN_extra_T=pd.DataFrame()
# for i in start_columns:
#     df_TN_extra_T['%s'%i]=df_results_T['%s'%i].copy()
# for t,title in enumerate(TN_extra):
#     df_TN_extra_T['T_%s'%title]=df_results_T['%s'%title].copy()

# df_TD_main_T=pd.DataFrame()
# for i in start_columns:
#     df_TD_main_T['%s'%i]=df_results_T['%s'%i].copy()
# for t,title in enumerate(TD_main):
#     df_TD_main_T['T_%s'%title]=df_results_T['%s'%title].copy()

# df_MB_main_T=pd.DataFrame()
# for i in start_columns:
#     df_MB_main_T['%s'%i]=df_results_T['%s'%i].copy()
# for t,title in enumerate(MB_main):
#     df_MB_main_T['T_%s'%title]=df_results_T['%s'%title].copy()

# df_TN_main_S1=pd.DataFrame()
# for i in start_columns:
#     df_TN_main_S1['%s'%i]=df_results_S1['%s'%i].copy()
# for t,title in enumerate(TN_main):
#     df_TN_main_S1['S1_%s'%title]=df_results_S1['%s'%title].copy()

# df_TN_extra_S1=pd.DataFrame()
# for i in start_columns:
#     df_TN_extra_S1['%s'%i]=df_results_S1['%s'%i].copy()
# for t,title in enumerate(TN_extra):
#     df_TN_extra_S1['S1_%s'%title]=df_results_S1['%s'%title].copy()

# df_TD_main_S1=pd.DataFrame()
# for i in start_columns:
#     df_TD_main_S1['%s'%i]=df_results_S1['%s'%i].copy()
# for t,title in enumerate(TD_main):
#     df_TD_main_S1['S1_%s'%title]=df_results_S1['%s'%title].copy()

# df_MB_main_S1=pd.DataFrame()
# for i in start_columns:
#     df_MB_main_S1['%s'%i]=df_results_S1['%s'%i].copy()
# for t,title in enumerate(MB_main):
#     df_MB_main_S1['S1_%s'%title]=df_results_S1['%s'%title].copy()

# df_TN_main_S2=pd.DataFrame()
# for i in start_columns:
#     df_TN_main_S2['%s'%i]=df_results_S2['%s'%i].copy()
# for t,title in enumerate(TN_main):
#     df_TN_main_S2['S2_%s'%title]=df_results_S2['%s'%title].copy()

# df_TN_extra_S2=pd.DataFrame()
# for i in start_columns:
#     df_TN_extra_S2['%s'%i]=df_results_S2['%s'%i].copy()
# for t,title in enumerate(TN_extra):
#     df_TN_extra_S2['S2_%s'%title]=df_results_S2['%s'%title].copy()

# df_TD_main_S2=pd.DataFrame()
# for i in start_columns:
#     df_TD_main_S2['%s'%i]=df_results_S2['%s'%i].copy()
# for t,title in enumerate(TD_main):
#     df_TD_main_S2['S2_%s'%title]=df_results_S2['%s'%title].copy()

# df_MB_main_S2=pd.DataFrame()
# for i in start_columns:
#     df_MB_main_S2['%s'%i]=df_results_S2['%s'%i].copy()
# for t,title in enumerate(MB_main):
#     df_MB_main_S2['S2_%s'%title]=df_results_S2['%s'%title].copy()

# # Make dictionary with the result dataframes to save the dataframes to excel with total
# dfs_print={'Info':df_info,'TN_T':df_TN_main_T,'TN_S1':df_TN_main_S1,'TN_S2':df_TN_main_S2,
#             'TD_T':df_TD_main_T,'TD_S1':df_TD_main_S1,'TD_S2':df_TD_main_S2,
#             'TN_extra_T':df_TN_extra_T,'TN_extra_S1':df_TN_extra_S1,'TN_extra_S2':df_TN_extra_S2,
#             'MB_T':df_MB_main_T,'MB_S1':df_MB_main_S1,'MB_S2':df_MB_main_S2}

# # Save the dataframes to excel
# writer1 = pd.ExcelWriter(out_path1, engine='xlsxwriter')
# for sheetname, df in dfs_print.items():  # loop through `dict` of dataframes
#     df.to_excel(writer1, sheet_name=sheetname)  # send df to writer
#     worksheet = writer1.sheets[sheetname]  # pull worksheet object
#     for idx, col in enumerate(df):  # loop through all columns
#         series = df[col]
#         max_len = max((
#             series.astype(str).map(len).max(),  # len of largest item
#             len(str(series.name))  # len of column name/header
#             )) + 2  # adding a little extra space
#         worksheet.set_column(idx, idx, max_len)  # set column width
# writer1.save()
# writer1.close()

# print('results printed')

# ###############################################################################################################
# ######################### ANALYSIS OF BEHAVIOR FOR TDT ########################################################
# ##############################################################################################################

# # Create lists of coptest and statistics that needs to be calculated
# list_cop=['COP1','COP2','COP3','COP4','COP5','COP6','COP7']
# list_stat=['Mean','Median','Std','SEM','Q25','Q75','semedian','var']

# # Create definitions to calculate group averages and statistical outcomes
# def groupdict(dictionary):
#     """
#     Parameters
#     ----------
#     dictionary : string
#         Add the dictionary of behavioral data results
#         e.g. "dict_results_T", "dict_results_S1", "dict_results_S2"

#     Returns
#     -------
#     dict_groups : dictionary
#         Returns a new dictionary with the outcomes per coptest (for all rats) in a list
#     """
    
#     dict_beh=dictionary
    
#     # Create an empty dictionary with ID and behaviors
#     dict_groups={}

#     for key,parameters in dict_beh.items():
#         for parameter,value in parameters.items():
#             dict_groups[parameter]={}
#             for t in list_cop:
#                 dict_groups[parameter][t]=[]

#     for key,parameters in dict_beh.items():
#         for parameter,value in parameters.items():
#             for t in list_cop:
#                 if t in key:
#                     dict_groups[parameter][t].append(value)

#     return dict_groups

# def statsdict(dictionary_groups):
#     """
#     Parameters
#     ----------
#     dictionary : dictionary
#         Add the dictionary with behavioral data results per coptest
#         e.g. dict_group_T, dict_group_S1, dict_group_S2

#     Returns
#     -------
#     dict_groups : dictionary
#         Returns a new dictionary with the statistical data derived from the group_dictionary
#     """
 
#     # Create an empty dictionary with ID and behaviors
#     dict_stats={}
#     for parameter,cops in dictionary_groups.items():
#         dict_stats[parameter]={}
#         for cop,value in cops.items():
#             dict_stats[parameter][cop]={}
#             for cop in list_cop:
#                 dict_stats[parameter][cop]={}
#                 for i in list_stat:
#                     dict_stats[parameter][cop][i]=[]

#     # Fill dictionary with statistical measures
#     for parameter,cops in dictionary_groups.items():
#         for cop,values in cops.items():
#             dict_stats[parameter][cop]['Mean']=np.nanmean(values)
#             dict_stats[parameter][cop]['Median']=np.nanmedian(values)
#             dict_stats[parameter][cop]['Std']=np.nanstd(values)
#             dict_stats[parameter][cop]['SEM']=np.nanstd(values)/np.sqrt(np.size(values))
#             dict_stats[parameter][cop]['Q25']=np.nanquantile(values,0.25)
#             dict_stats[parameter][cop]['Q75']=np.nanquantile(values,0.75)
#             dict_stats[parameter][cop]['semedian']=(dict_stats[parameter][cop]['Q75']-dict_stats[parameter][cop]['Q25'])/len(values)*1.34
#             dict_stats[parameter][cop]['var']=np.nanvar(values)
#             dict_stats[parameter][cop]['len']=len(values)
#             dict_stats[parameter][cop]['max']=dict_stats[parameter][cop]['Mean']+dict_stats[parameter][cop]['Std']
#             dict_stats[parameter][cop]['min']=dict_stats[parameter][cop]['Mean']-dict_stats[parameter][cop]['Std']

#     return dict_stats

# # Create groupdictionaries
# dict_group_T=groupdict(dict_results_T)
# dict_group_S1=groupdict(dict_results_S1)
# dict_group_S2=groupdict(dict_results_S2)
# dict_group_S3=groupdict(dict_results_S3)

# # Calculate statistics
# dict_stat_T=statsdict(dict_group_T)
# dict_stat_S1=statsdict(dict_group_S1)
# dict_stat_S2=statsdict(dict_group_S2)
# dict_stat_S3=statsdict(dict_group_S3)

# ################ ################ ################ ################  
# ################ ################ ################ ################  
# # Create a dictionary of all dictionaries, dataframes, and lists to store as pickle, and later get back 
# list_behaviordata=[dict_results_T,dict_results_S1,dict_results_S2,dict_results_S3,dict_results_S1_PEII,dict_results_S2_PEII,
#                     dict_results_S3_PEII,dict_results_tdt,dict_MIE,
#                     dict_group_T,dict_group_S1,dict_group_S2,dict_group_S3,dict_stat_T,dict_stat_S1,dict_stat_S2,dict_stat_S3]
# list_behaviordata_names=["dict_results_T","dict_results_S1","dict_results_S2","dict_results_S3","dict_results_S1_PEII","dict_results_S2_PEII",
#                           "dict_results_S3_PEII","dict_results_tdt","dict_MIE",
#                     'dict_group_T','dict_group_S1','dict_group_S2','dict_group_S3','dict_stat_T','dict_stat_S1','dict_stat_S2','dict_stat_S3']

# # Change directory to output folder
# if not os.path.isdir(directory_pickle):
#     os.mkdir(directory_pickle)
# os.chdir(directory_pickle)

# # Save this dictionary as pickle file
# my_dict_behavior=dict(zip(list_behaviordata_names,list_behaviordata))
# with open("my_dict_behavior.pickle", "wb") as file:
#     pickle.dump(my_dict_behavior, file, protocol=pickle.HIGHEST_PROTOCOL)

# # Change directory back
# os.chdir(directory)

# # Make new lists for slow versus fast ejaculators per series
# list_slowejac=[]
# list_normalejac=[]
# list_fastejac=[]
# for ids, parameters in dict_results_T.items():
#     for parameter,value in parameters.items():
#         if parameter =='TN_Ejaculation':
#             if value >= 4:
#                 list_fastejac.append(ids)
#             if value <= 1:
#                 list_slowejac.append(ids)
#             if value == 2 or value == 3:
#                 list_normalejac.append(ids)
                
# # Make a new dictionary with id lists for other parameters on which mean +- stdev was taken as cut-off points
# list_performers=['Low','Middle','High']

# def parameter_dict(dictionary,dictionary_stat):
#     """
#     Parameters
#     ----------
#     dictionary : string
#         Add the dictionary of behavioral data results
#         e.g. "dict_results_T", "dict_results_S1", "dict_results_S2"
#     dictionary_stat : dictionary
#         Add the dictionary of statistical data results
#         e.g. dict_stat_T, dict_stat_S1, dict_stat_S2

#     Returns
#     -------
#     dict_parameters : dictionary
#         Creates a new dictionary with lists of testid for the parameters of extremes 
#         (low, middle and high performers with mean +- stdev as cut-off points)

#     """
#     dict_beh=dictionary

#     dict_parameters={}

#     for key,parameters in dict_beh.items():
#         for parameter,value in parameters.items():
#             dict_parameters[parameter]={}
#             for cop in list_cop:
#                 dict_parameters[parameter][cop]={}
#                 for performer in list_performers:
#                     dict_parameters[parameter][cop][performer]=[]

#     for key,parameters in dict_beh.items():
#         for parameter,value in parameters.items():
#             for cop in list_cop:
#                 if cop in key:
#                     if value > dictionary_stat[parameter][cop]['max']:
#                         dict_parameters[parameter][cop]['High'].append(key)
#                     if value < dictionary_stat[parameter][cop]['min']:
#                         dict_parameters[parameter][cop]['Low'].append(key)
#                     if (value >= dictionary_stat[parameter][cop]['min']) and (value <= dictionary_stat[parameter][cop]['max']):
#                         dict_parameters[parameter][cop]['Middle'].append(key)

#     return dict_parameters

# # Create dictionaries of the slow, middle and high performing animals per coptest and parameter.
# dict_parameters_T=parameter_dict(dict_results_T,dict_stat_T)     
# dict_parameters_S1=parameter_dict(dict_results_S1,dict_stat_S1)     
# dict_parameters_S2=parameter_dict(dict_results_S2,dict_stat_S2)     
# dict_parameters_S3=parameter_dict(dict_results_S3,dict_stat_S3)     

# # Make new lists for mount and intromissions in first, middle and last part of ejaculatory series
# # Both for series divided in three or five parts
# for keys,dicts in dict_results_tdt.items():
#     if keys != 'T':
#         for key,behavior in dicts.items():
#             if dicts[key]['Time_Mount']<dicts[key]['Time_Intromission']:
#                 time1=dicts[key]['Time_Mount']
#             else:
#                 time1=dicts[key]['Time_Intromission']
#             dicts[key]['treshold3']=(dicts[key]['Time_Ejaculation']-time1)/3
#             dicts[key]['treshold3 end 1st part']=dicts[key]['Time_Ejaculation']-(2*dicts[key]['treshold3'])
#             dicts[key]['treshold3 end 2nd part']=dicts[key]['Time_Ejaculation']-(dicts[key]['treshold3'])

#             dicts[key]['treshold5']=(dicts[key]['Time_Ejaculation']-time1)/5
#             dicts[key]['treshold5 end 1st part']=dicts[key]['Time_Ejaculation']-(4*dicts[key]['treshold5'])
#             dicts[key]['treshold5 end 2nd part']=dicts[key]['Time_Ejaculation']-(3*dicts[key]['treshold5'])
#             dicts[key]['treshold5 end 3rd part']=dicts[key]['Time_Ejaculation']-(2*dicts[key]['treshold5'])
#             dicts[key]['treshold5 end 4th part']=dicts[key]['Time_Ejaculation']-(dicts[key]['treshold5'])

# ###############################AANGEPAST CHECK############################
# # Make new lists for Mount and Intromissions in first, middle and last number of behaviors per series
# for keys,dicts in dict_results_td.items():
#     if keys != 'T':
#         for key,behavior in dicts.items():
#             for beh in list_behaviors:
#                 dicts[key]['treshold3_%s'%beh]=dicts[key]['TN_%s'%beh]/3
#                 dicts[key]['treshold3 end 1st part_%s'%beh]=math.floor(2*dicts[key]['treshold3_%s'%beh])
#                 dicts[key]['treshold3 end 2nd part_%s'%beh]=math.floor(dicts[key]['treshold3_%s'%beh])

#                 dicts[key]['treshold5_%s'%beh]=dicts[key]['TN_%s'%beh]/5
#                 dicts[key]['treshold5 end 1st part_%s'%beh]=math.floor(4*dicts[key]['treshold5_%s'%beh])
#                 dicts[key]['treshold5 end 2nd part_%s'%beh]=math.floor(3*dicts[key]['treshold5_%s'%beh])
#                 dicts[key]['treshold5 end 3rd part_%s'%beh]=math.floor(2*dicts[key]['treshold5_%s'%beh])
#                 dicts[key]['treshold5 end 4th part_%s'%beh]=math.floor(dicts[key]['treshold5_%s'%beh])

# # ##########################################################################################################################
# # ##########################################################################################################################
# # ##########################################################################################################################

############# Analysis of TDT data from Synapse ################

##########################################################################################################################
##########################################################################################################################
##########################################################################################################################

# set font size for all figures
SMALL_SIZE = 16
MEDIUM_SIZE = 18
BIGGER_SIZE = 20
# plt.rcParams['font.size'] = 22 
plt.rc('font', size=BIGGER_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=BIGGER_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=BIGGER_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
custom_params = {"axes.spines.right": False, "axes.spines.top": False}        

# Determine some color codes for figures
color_startline='#515A5A'

color_snips='#95A5A6'
color_GCaMP='#117864'
color_shadow='xkcd:silver'
color_GFP_snips='#839192'
color_GFP='#9E3C86'

color_AUC_post_T_bar='#5F6A6A'
color_AUC_pre_T_bar='#D5DBDB'
color_AUC_post_T_scatter='#4D5656'
color_AUC_pre_T_scatter='#BFC9CA'

color_AUC_post_S2_bar='#0E6655'
color_AUC_pre_S2_bar='#A2D9CE'
color_AUC_post_S2_scatter='#0B5345'
color_AUC_pre_S2_scatter='#73C6B6'

color_AUC_pre_bar='#98eddb'
color_AUC_post_bar='#17A589'
color_AUC_pre_scatter='#64b0a0'
color_AUC_post_scatter='#117864'

color_M='#e784e8'
color_I='#b584e8'
color_E='#8485e8'
color_F='#515A5A'

# Create a definition to analyze the full data on whether or not there was signal
# Does normally not run, only when turned on
def processdata(testsession,test='COP',metafile=file_TDT,virus="GCaMP6",method='Lerner'):
    """
    Parameters
    ----------
    testsession : float
        Add which COP-test number you want to analyze
        e.g. 1 for COP1, 2 for COP2
    test : string - Default = 'COP'
        Add what type of behavioral test you want to analyze
        e.g. "COP"
    metafile : string -> Default = file_TDT
        Code referring to the excel metafile document 
    virus : string -> Default = 'GCaMP6'
        Add which virus you want to analyze 
        e.g. "GCaMP6" or "GFP"
    method : string -> Default = 'Lerner'
        Add the method for dFF analysis you would like to use
        'Lerner' = uses a polyfit on the ISOS and GCaMP and average per 10 samples
        'Jaime' = uses another mathematical way from Konanur to substract ISOS from GCaMP 
                    -> it needs extra information that my code blocks (by normalize = False)

    Returns
    -------
    dict_dFF : dictionary & figure
        Processes the TDT data by correcting dFF signals (Lerner method is standard), z-score for the full test. 
        In addition, it removes the artifacts based on IQR standards, and re-calculates the dFF and z-score based on this new data.
        All data is stored in a new dictionary.
        The definition also creates a figure with the original and corrected dFF signals over the course of the full test with marking for mount, intromissions and ejaculations.
    """

    print("Start processing tdt data for fullgraph")
    
    # Make empty dictionaries
    dict_dFF={}

    # Read out the data of synapse per unique exp-rat-code and set in dictionary with GCAMP and ISOS
    for rat,v,t,ts,di,b,u,ct in zip(list_ID,list_virus,list_test,list_testsession,list_directory_tank,list_blue,list_uv,list_coptest):
        if v == virus:
            if t == test:
                if ts == testsession:
                    BLOCKPATH= "%s"%(di)
                    print('Analyzing %s'%rat)
                    data= tdt.read_block(BLOCKPATH)
                    # Make some variables up here to so if they change in new recordings you won't have to change everything downstream
                    if b == '465_A':
                        GCAMP="_465A"
                        ISOS="_405A"
                        START_SIGNAL = 'PC0_'
                        
                    else:
                        GCAMP="_465C"
                        ISOS="_405C"
                        START_SIGNAL = 'PC0_'

                    try:                    
                        START_on = data.epocs[START_SIGNAL].onset
                        print(START_on)
                    except:
                        START_on = 1800
                        print("#### % has no start video signal #####"%rat)
                        
                    # Make a time array based on the number of samples and sample freq of 
                    # the demodulated streams
                    time = np.linspace(1,len(data.streams[GCAMP].data), len(data.streams[GCAMP].data))/data.streams[GCAMP].fs
                    
                    #There is often a large artifact on the onset of LEDs turning on
                    #Remove data below a set time t
                    #Plot the demodulated strain without the beginning artifact
                    if START_on < 1800:
                        t=START_on
                    else: t=50
                    inds = np.where(time>t)
                    ind = inds[0][0]
                    time = time[ind:] # go from ind to final index
                    blue = data.streams[GCAMP].data[ind:]
                    uv = data.streams[ISOS].data[ind:]
                    
                    # Change directory to output folder
                    if not os.path.isdir(directory_fullgraphs):
                        os.mkdir(directory_fullgraphs)

                    os.chdir(directory_fullgraphs)
                    
                    try:
                        # Plot again at new time range
                        sns.set(style="ticks", rc=custom_params)
                        fig = plt.figure(figsize=(30, 18))
                        ax1 = fig.add_subplot(111)
                    
                        # Plotting the traces
                        p1, = ax1.plot(time,blue, linewidth=2, color=color_GCaMP, label='GCaMP')
                        p2, = ax1.plot(time,uv, linewidth=2, color='blueviolet', label='ISOS')
                        
                        ax1.set_ylabel('mV',fontsize=18)
                        ax1.set_xlabel('Seconds',fontsize=18)
                        ax1.set_title('Raw Demodulated Responsed with Artifact Removed',fontsize=20)
                        ax1.legend(handles=[p1,p2],loc='upper right',fontsize=18)
                        fig.tight_layout()
                        
                        plt.savefig("%s_1 raw.jpg"%(rat))
                        plt.close(fig)
                        # Change directory back
                        os.chdir(directory)

                    except:
                        print('%s No figure created '%rat)
                        # Change directory back
                        os.chdir(directory)


                    if method == 'Lerner':
                        # Average around every Nth point and downsample Nx
                        N = 10  # Average every Nth samples into 1 value
                        F405 = []
                        F465 = []
                        time_cor=time
                        
                        for i in range(0, len(blue), N):
                            F465.append(np.mean(blue[i:i+N-1])) # This is the moving window mean
                        blue_cor = F465
    
                        for i in range(0, len(uv), N):
                            F405.append(np.mean(uv[i:i+N-1]))
                        uv_cor = F405

                        # Decimate time array to match length of demodulated stream
                        time_cor = time_cor[::N] # go from beginning to end of array in steps on N
                        time_cor = time_cor[:len(blue_cor)]
                        
                        fs = data.streams[GCAMP].fs/N

                        # x = np.array(uv_cor)
                        # y = np.array(blue_cor)
                        x = uv_cor
                        y = blue_cor
                        
                        try:
                            bls = np.polyfit(x, y, 1)
                            Y_fit_all = np.multiply(bls[0], x) + bls[1]
                            blue_dF_all = y - Y_fit_all
                            # Calculate the corrected signal in percentage
                            dFF = np.multiply(100, np.divide(blue_dF_all, Y_fit_all))

                        except:
                            print("##### % has signal length problem #####"%rat)
                            dFF = []

                    elif method == 'Jaime':
                        ### In case you want to use the KONANUR method for correcting the signal #####
                        # Calculating dFF using Jaime's correction of the GCAMP versus ISOS signals
                        dFF=tp.processdata(blue, uv, normalize=False)
                        fs = data.streams[GCAMP].fs
                    
                    try:
                        zall = []
                        zb = np.mean(dFF)
                        zsd = np.std(dFF)
                        zall.append((dFF - zb)/zsd)
                       
                        zscore_dFF = np.mean(zall, axis=0)  
                    except:
                        zscore_dFF=[]

                    dict_dFF[rat]={}
                    dict_dFF[rat]['blue_raw']=blue
                    dict_dFF[rat]['uv_raw']=uv
                    dict_dFF[rat]['time_raw']=time
                    dict_dFF[rat]['blue']=blue_cor
                    dict_dFF[rat]['uv']=uv_cor
                    dict_dFF[rat]['dFF']=dFF
                    dict_dFF[rat]['zscore']=zscore_dFF
                    dict_dFF[rat]['START_on']=START_on
                    dict_dFF[rat]['time']=time_cor
                    dict_dFF[rat]['fs']=fs
                    print(rat)
                    print('Start on - ',START_on)

    # Get the corrected dFF and z-scores when the drops in GCaMP signal are taken out
    # Get interquartile range of raw GCaMP and UV signal to delete outliers
    for rat,value in dict_dFF.items():    
        try:
            IQR_blue = []
            IQR_uv = []
            
            Q1_blue,Q3_blue = np.percentile(dict_dFF[rat]['blue_raw'],[25,75])
            Q1_uv,Q3_uv = np.percentile(dict_dFF[rat]['uv_raw'],[25,75])
    
            IQR_blue = Q3_blue-Q1_blue
            IQR_uv = Q3_uv-Q1_uv
            
            lower_fence_blue =Q1_blue-(1.5*IQR_blue) 
            higher_fence_blue =Q3_blue+(6*IQR_blue) # increased it to 6 (instead of 1.5) to not miss the big signals
    
            lower_fence_uv = Q1_uv-(1.5*IQR_uv)
            higher_fence_uv = Q3_uv+(4*IQR_uv)
                        
        except:
            print('no IQR calculated')

        # Delete all GCaMP and UV that are outliers
        temp_blue=list(dict_dFF[rat]['blue_raw'])
        temp_uv=list(dict_dFF[rat]['uv_raw'])
        temp_time=list(dict_dFF[rat]['time_raw'])
        time_new=[]
        blue_new=[]
        uv_new=[]

        if rat in dict_manual_adjustments['Cut_start'].keys():
            cut_start1=dict_manual_adjustments['Cut_start'][rat][0]
            cut_end1=dict_manual_adjustments['Cut_end'][rat][0]
            cut_start2=dict_manual_adjustments['Cut_start'][rat][1]
            cut_end2=dict_manual_adjustments['Cut_end'][rat][1]
            cut_start3=dict_manual_adjustments['Cut_start'][rat][2]
            cut_end3=dict_manual_adjustments['Cut_end'][rat][2]
            cut_start4=dict_manual_adjustments['Cut_start'][rat][3]
            cut_end4=dict_manual_adjustments['Cut_end'][rat][3]
        else:
            cut_start1=3000
            cut_end1=0
            cut_start2=3000
            cut_end2=0
            cut_start3=3000
            cut_end3=0
            cut_start4=3000
            cut_end4=0

        # blue_new_temp=[b for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue and b<higher_fence_blue and u>lower_fence_uv and u<higher_fence_uv and (t<cut_start or t>cut_end)] 
        # uv_new_temp=[u for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue and b<higher_fence_blue and u>lower_fence_uv and u<higher_fence_uv and (t<cut_start or t>cut_end)] 
        # time_new_temp=[t for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue and b<higher_fence_blue and u>lower_fence_uv and u<higher_fence_uv and (t<cut_start or t>cut_end)] 

        blue_new_temp=[b for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue and u>lower_fence_uv  and (t<cut_start1 or t>cut_end1) and (t<cut_start2 or t>cut_end2) and (t<cut_start3 or t>cut_end3) and (t<cut_start4 or t>cut_end4)]
        uv_new_temp=[u for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue  and u>lower_fence_uv  and (t<cut_start1 or t>cut_end1) and (t<cut_start2 or t>cut_end2) and (t<cut_start3 or t>cut_end3) and (t<cut_start4 or t>cut_end4)] 
        time_new_temp=[t for b,u,t in zip(temp_blue,temp_uv,temp_time) if b>lower_fence_blue  and u>lower_fence_uv and (t<cut_start1 or t>cut_end1) and (t<cut_start2 or t>cut_end2) and (t<cut_start3 or t>cut_end3) and (t<cut_start4 or t>cut_end4)] 


        for b in blue_new_temp:
            blue_new.append(b)
        for u in uv_new_temp:
            uv_new.append(u)
        for t in time_new_temp:
            time_new.append(t)

        # Change directory to output folder
        if not os.path.isdir(directory_fullgraphs):
            os.mkdir(directory_fullgraphs)

        os.chdir(directory_fullgraphs)

        try:
            # Plot again at new time range
            sns.set(style="ticks", rc=custom_params)
            fig = plt.figure(figsize=(30, 18))
            ax1 = fig.add_subplot(111)
        
            # Plotting the traces
            p1, = ax1.plot(time_new,blue_new, linewidth=2, color=color_GCaMP, label='GCaMP')
            p2, = ax1.plot(time_new,uv_new, linewidth=2, color='blueviolet', label='ISOS')
            
            ax1.set_ylabel('mV',fontsize=18)
            ax1.set_xlabel('Seconds',fontsize=18)
            ax1.set_title('Raw Demodulated Responses with Outliers Removed',fontsize=20)
            # ax1.legend(handles=[p1,p2],loc='upper right',fontsize=18)
            fig.tight_layout()
            
            plt.savefig("%s_2 raw cor.jpg"%(rat))
            plt.close(fig)
            # Change directory back
            os.chdir(directory)
            print('%s Figure without outliers created '%rat)

        except:
            print('%s No figure created '%rat)
            # Change directory back
            os.chdir(directory)

        if method == 'Lerner':
            # Average around every Nth point and downsample Nx
            N = 10  # Average every Nth samples into 1 value
            F405_new = []
            F465_new = []
           
            for i in range(0, len(blue_new), N):
                F465_new.append(np.mean(blue_new[i:i+N-1])) # This is the moving window mean
            blue_new = F465_new
    
            for i in range(0, len(uv_new), N):
                F405_new.append(np.mean(uv_new[i:i+N-1]))
            uv_new = F405_new
    
            # Decimate time array to match length of demodulated stream
            time_new = time_new[::N] # go from beginning to end of array in steps on N
            time_new = time_new[:len(blue_new)]
            
            x_new = np.array(uv_new)
            y_new = np.array(blue_new)
            
            try:
                bls_new = np.polyfit(x_new, y_new, 1)
                Y_fit_all_new = np.multiply(bls_new[0], x_new) + bls_new[1]
                blue_dF_all_new = y_new - Y_fit_all_new
                # Calculate the corrected signal in percentage
                dFF_new = np.multiply(100, np.divide(blue_dF_all_new, Y_fit_all_new))
                
            except:
                print("##### % has signal length problem #####"%rat)
                dFF_new = []
            
        elif method == 'Jaime':
            ### In case you want to use the KONANUR method for correcting the signal #####
            # Calculating dFF using Jaime's correction of the GCAMP versus ISOS signals
            dFF_new=tp.processdata(blue_new, uv_new, normalize=False)
        
        try:
            zall_new = []
            zb_new = np.mean(dFF_new)
            zsd_new = np.std(dFF_new)
            zall_new.append((dFF_new - zb_new)/zsd_new)
           
            zscore_dFF_new = np.mean(zall_new, axis=0)  
        except:
            zscore_dFF_new=[]

        dict_dFF[rat]['blue_cor']=blue_new
        dict_dFF[rat]['uv_cor']=uv_new
        dict_dFF[rat]['dFF_cor']=dFF_new
        dict_dFF[rat]['zscore_cor']=zscore_dFF_new
        dict_dFF[rat]['time_cor']=time_new

        # Delete the raw data from dictionary to make the dictionary smaller in storage size
        del dict_dFF[rat]['blue_raw']
        del dict_dFF[rat]['uv_raw']
        del dict_dFF[rat]['time_raw']


    # Get the times of introduction female, mounts, intromissions and ejaculations -> and mark in figure
    dict_start_cop={}
    for key in dict_dFF.keys():
        dict_start_cop[key]={}
        for beh in list_copmark:
            dict_start_cop[key][beh]=[]

    # Get dFF,time and fs from dict_dFF of processed data
    for rat,value in dict_dFF.items():
        for behav in list_copmark:
            if dict_dFF[rat]['START_on']:
                START_on=dict_dFF[rat]['START_on']
                delay=START_on
    
                df_reduced = data_T[(data_T['ID'] == rat) & (data_T[BEH] == behav)]
                temp_start = list(df_reduced['Beh_start']+ delay)
                dict_start_cop[rat][behav]=temp_start 
            else:
                dict_start_cop[rat][behav]=[]

    dict_end_cop={}
    for key in dict_dFF.keys():
        dict_end_cop[key]={}
        for beh in list_copmark:
            dict_end_cop[key][beh]=[]

    # Get dFF,time and fs from dict_dFF of processed data
    for rat,value in dict_dFF.items():
        for behav in list_copmark:
            if dict_dFF[rat]['START_on']:
                START_on=dict_dFF[rat]['START_on']
                delay=START_on
    
                df_reduced = data_T[(data_T['ID'] == rat) & (data_T[BEH] == behav)]
                temp_end = list(df_reduced['Beh_end']+ delay)
                dict_end_cop[rat][behav]=temp_end 
            else:
                dict_end_cop[rat][behav]=[]
    
    # Read out the data from the dFF dictionary and link to behavior
    for rat,value in dict_dFF.items():
        # First make a continous time series of behavior events (epocs) and plot
        FEMALE_on = dict_start_cop[rat][BN] if dict_start_cop[rat][BN] else [0,0]
        FEMALE_off = dict_end_cop[rat][BN] if dict_end_cop[rat][BN] else [0,0]
        MOUNT_on = dict_start_cop[rat][BA] if dict_start_cop[rat][BA] else [0,0]
        MOUNT_off = dict_end_cop[rat][BA] if dict_end_cop[rat][BA] else [0,0]
        INTRO_on = dict_start_cop[rat][BB] if dict_start_cop[rat][BB] else [0,0]
        INTRO_off = dict_end_cop[rat][BB] if dict_end_cop[rat][BB] else [0,0]
        EJAC_on = dict_start_cop[rat][BC] if dict_start_cop[rat][BC] else [0,0]
        EJAC_off = dict_end_cop[rat][BC] if dict_end_cop[rat][BC] else [0,0]
        
        # Add the first and last time stamps to make tails on the TTL stream
        FEMALE_x = np.append(np.append(dict_dFF[rat]['time'][0], np.reshape(np.kron([FEMALE_on, FEMALE_off],
                            np.array([[1], [1]])).T, [1,-1])[0]), dict_dFF[rat]['time'][-1])
        sz_F = len(FEMALE_on)
        d_F=[0.2]*sz_F

        MOUNT_x = np.append(np.append(dict_dFF[rat]['time'][0], np.reshape(np.kron([MOUNT_on, MOUNT_off],
                            np.array([[1], [1]])).T, [1,-1])[0]), dict_dFF[rat]['time'][-1])
        sz_M = len(MOUNT_on)
        d_M=[0.2]*sz_M
        
        INTRO_x = np.append(np.append(dict_dFF[rat]['time'][0], np.reshape(np.kron([INTRO_on, INTRO_off],
                            np.array([[1], [1]])).T, [1,-1])[0]), dict_dFF[rat]['time'][-1])
        sz_I = len(INTRO_on)
        d_I=[0.2]*sz_I
        
        EJAC_x = np.append(np.append(dict_dFF[rat]['time'][0], np.reshape(np.kron([EJAC_on, EJAC_off],
                            np.array([[1], [1]])).T, [1,-1])[0]), dict_dFF[rat]['time'][-1])
        sz_E = len(EJAC_on)
        d_E=[0.2]*sz_E
           
        # Add zeros to beginning and end of 0,1 value array to match len of LICK_x
        FEMALE_y = np.append(np.append(0,np.reshape(np.vstack([np.zeros(sz_F),
            d_F, d_F, np.zeros(sz_F)]).T, [1, -1])[0]),0)

        MOUNT_y = np.append(np.append(0,np.reshape(np.vstack([np.zeros(sz_M),
            d_M, d_M, np.zeros(sz_M)]).T, [1, -1])[0]),0)
        
        INTRO_y = np.append(np.append(0,np.reshape(np.vstack([np.zeros(sz_I),
            d_I, d_I, np.zeros(sz_I)]).T, [1, -1])[0]),0)
        
        EJAC_y = np.append(np.append(0,np.reshape(np.vstack([np.zeros(sz_E),
            d_E, d_E, np.zeros(sz_E)]).T, [1, -1])[0]),0)
        
        y_scale = 30 # adjust according to data needs
        y_shift = -20 #scale and shift are just for asthetics
        
        if method == 'Lerner' and virus== 'GCaMP6':
            try:
                # First subplot in a series: dFF with lick epocs
                os.chdir(directory_fullgraphs)
                fig = plt.figure(figsize=(30,8))
                ax = fig.add_subplot(111)
                
                ax.plot(dict_dFF[rat]['time'], dict_dFF[rat]['dFF'], linewidth=2, color=color_GCaMP, label=virus)
                p1, = ax.plot(FEMALE_x, y_scale*FEMALE_y+y_shift, linewidth=2, color=color_F, label='Introduction female')
                p2, = ax.plot(MOUNT_x, y_scale*MOUNT_y+y_shift, linewidth=2, color=color_M, label='Mount')
                p3, = ax.plot(INTRO_x, y_scale*INTRO_y+y_shift, linewidth=2, color=color_I, label='Intromission')
                p4, = ax.plot(EJAC_x, y_scale*EJAC_y+y_shift, linewidth=2, color=color_E, label='Ejaculation')
                
                for on, off in zip(MOUNT_on, MOUNT_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_M, label='Mount')
                for on, off in zip(INTRO_on, INTRO_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_I, label='Intromission')
                for on, off in zip(EJAC_on, EJAC_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_E, label='Ejaculation')
                
                ax.set_ylabel(r'$\Delta$F/F (%)',fontsize=18)
                ax.set_xlabel('Seconds',fontsize=18)
                # ax.set_yticks(yy)
                ax.legend(handles=[p1,p2,p3,p4], loc='upper right',fontsize=18)
                fig.tight_layout()
                plt.savefig("%s_3 %s %s.jpg"%(rat, virus, method))
                plt.close(fig)
                # Change directory back
                os.chdir(directory)

            except:
                print('%s No COPMARK figure created '%rat)
                plt.close('all')
                # Change directory back
                os.chdir(directory)

            try:
                # First subplot in a series: dFF with copulation epocs
                os.chdir(directory_fullgraphs)
                fig = plt.figure(figsize=(30,8))
                ax = fig.add_subplot(111)
                
                ax.plot(dict_dFF[rat]['time_cor'], dict_dFF[rat]['dFF_cor'], linewidth=2, color=color_GCaMP, label=virus)
                p1, = ax.plot(FEMALE_x, y_scale*FEMALE_y+y_shift, linewidth=2, color=color_F, label='Introduction female')
                p2, = ax.plot(MOUNT_x, y_scale*MOUNT_y+y_shift, linewidth=2, color=color_M, label='Mount')
                p3, = ax.plot(INTRO_x, y_scale*INTRO_y+y_shift, linewidth=2, color=color_I, label='Intromission')
                p4, = ax.plot(EJAC_x, y_scale*EJAC_y+y_shift, linewidth=2, color=color_E, label='Ejaculation')
                
                for on, off in zip(MOUNT_on, MOUNT_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_M, label='Mount')
                for on, off in zip(INTRO_on, INTRO_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_I, label='Intromission')
                for on, off in zip(EJAC_on, EJAC_off):
                    ax.axvspan(on, off, alpha=0.25, color=color_E, label='Ejaculation')
                
                ax.set_ylabel(r'$\Delta$F/F (%)',fontsize=18)
                ax.set_xlabel('Seconds',fontsize=18)
                # ax.set_yticks(yy)
                ax.legend(handles=[p1,p2,p3,p4], loc='upper right',fontsize=18)
                fig.tight_layout()
                plt.savefig("%s_4 %s %s cor.jpg"%(rat, virus, method))
                plt.close(fig)
                
                # # Make figure of z-scores
                # fig = plt.figure(figsize=(30,8))
                # ax = fig.add_subplot(111)
                
                # ax.plot(dict_dFF[rat]['time_cor'], dict_dFF[rat]['zscore_cor'], linewidth=2, color=color_GCaMP, label=virus)
                # p1, = ax.plot(FEMALE_x, y_scale*FEMALE_y+y_shift, linewidth=2, color=color_F, label='Introduction female')
                # p2, = ax.plot(MOUNT_x, y_scale*MOUNT_y+y_shift, linewidth=2, color=color_M, label='Mount')
                # p3, = ax.plot(INTRO_x, y_scale*INTRO_y+y_shift, linewidth=2, color=color_I, label='Intromission')
                # p4, = ax.plot(EJAC_x, y_scale*EJAC_y+y_shift, linewidth=2, color=color_E, label='Ejaculation')
                
                # for on, off in zip(MOUNT_on, MOUNT_off):
                #     ax.axvspan(on, off, alpha=0.25, color=color_M, label='Mount')
                # for on, off in zip(INTRO_on, INTRO_off):
                #     ax.axvspan(on, off, alpha=0.25, color=color_I, label='Intromission')
                # for on, off in zip(EJAC_on, EJAC_off):
                #     ax.axvspan(on, off, alpha=0.25, color=color_E, label='Ejaculation')
                
                # ax.set_ylabel('z-score',fontsize=18)
                # ax.set_xlabel('Seconds',fontsize=18)
                # # ax.set_yticks(yy)
                # ax.legend(handles=[p1,p2,p3,p4], loc='upper right',fontsize=18)
                # fig.tight_layout()
                # plt.savefig("%s_5 %s %s cor.jpg"%(rat, virus, method))
                # plt.close(fig)

                # Change directory back
                os.chdir(directory)

            except:
                print('%s No COPMARK figure created '%rat)
                plt.close('all')
                # Change directory back
                os.chdir(directory)

        else:
            os.chdir(directory_fullgraphs)
            fig = plt.figure(figsize=(30,8))
            ax = fig.add_subplot(111)
            
            p1, = ax.plot(dict_dFF[rat]['time'], dict_dFF[rat]['dFF'], linewidth=2, color=color_GCaMP, label='GCaMP')
            
            ax.set_ylabel(r'$\Delta$F/F (%)',fontsize=18)
            ax.set_xlabel('Seconds',fontsize=18)
            # ax.set_title(r'%s - $\Delta$F/F',fontsize=18)
            fig.tight_layout()
            plt.savefig("%s_3 %s %s.jpg"%(rat, virus, method))
            plt.close(fig)
            # Change directory back
            os.chdir(directory)
            
   
    print('data processing fullgraph done')
    return dict_dFF

print('definition data processing for fullgraph made')

# ################ In case you want to see the data #######################################################
# GCAMP COPULATION TEST -> test='COP',virus="GCaMP6",method='Lerner'
dict_dFF_GCaMP6_COP_1=processdata(1)       
# dict_dFF_GCaMP6_COP_2=processdata(2)       
# dict_dFF_GCaMP6_COP_3=processdata(3)       
# dict_dFF_GCaMP6_COP_4=processdata(4)       
# dict_dFF_GCaMP6_COP_5=processdata(5)       
# dict_dFF_GCaMP6_COP_6=processdata(6)       
# dict_dFF_GCaMP6_COP_7=processdata(7)       

# # GFP COPULATION TEST -> test='COP',virus="GCaMP6",method='Lerner'
# dict_dFF_GFP_COP_1=processdata(1, virus='GFP')       
# dict_dFF_GFP_COP_2=processdata(2, virus='GFP')       
# dict_dFF_GFP_COP_3=processdata(3, virus='GFP')       
# dict_dFF_GFP_COP_4=processdata(4, virus='GFP')       
# dict_dFF_GFP_COP_5=processdata(5, virus='GFP')       
# dict_dFF_GFP_COP_6=processdata(6, virus='GFP')       
# dict_dFF_GFP_COP_7=processdata(7, virus='GFP')       


# ##################### ########################### ############################## ############################################
# ##################### ########################### ############################## ############################################
# ##################### ########################### ############################## ############################################
# # to save as pickle
# list_processdata=[dict_dFF_GCaMP6_COP_1,dict_dFF_GCaMP6_COP_2,dict_dFF_GCaMP6_COP_3,dict_dFF_GCaMP6_COP_4,dict_dFF_GCaMP6_COP_5,
#                   dict_dFF_GCaMP6_COP_6,dict_dFF_GCaMP6_COP_7,
#                   dict_dFF_GFP_COP_1,dict_dFF_GFP_COP_2,dict_dFF_GFP_COP_3,dict_dFF_GFP_COP_4,dict_dFF_GFP_COP_5,
#                   dict_dFF_GFP_COP_6,dict_dFF_GFP_COP_7]
# list_processdata_names=["dict_dFF_GCaMP6_COP_1","dict_dFF_GCaMP6_COP_2","dict_dFF_GCaMP6_COP_3","dict_dFF_GCaMP6_COP_4","dict_dFF_GCaMP6_COP_5",
#                   "dict_dFF_GCaMP6_COP_6","dict_dFF_GCaMP6_COP_7",
#                   "dict_dFF_GFP_COP_1","dict_dFF_GFP_COP_2","dict_dFF_GFP_COP_3","dict_dFF_GFP_COP_4","dict_dFF_GFP_COP_5",
#                   "dict_dFF_GFP_COP_6","dict_dFF_GFP_COP_7"]

# os.chdir(directory_pickle)

# my_dict_process=dict(zip(list_processdata_names,list_processdata))
# with open("my_dict_process.pickle", "wb") as file:
#     pickle.dump(my_dict_process, file, protocol=pickle.HIGHEST_PROTOCOL)
# # Change directory back
# os.chdir(directory)

# ##################### ########################### ############################### ###########################################
##################### ########################### ############################### ###########################################

# # GCAMP COPULATION TEST -> test='COP',virus="GCaMP6",method='Lerner'
# dict_dFF_GCaMP6_COP_1=processdata(1,method='Jaime')        
# dict_dFF_GCaMP6_COP_2=processdata(2,method='Jaime')        
# dict_dFF_GCaMP6_COP_3=processdata(3,method='Jaime')        
# dict_dFF_GCaMP6_COP_4=processdata(4,method='Jaime')        
# dict_dFF_GCaMP6_COP_5=processdata(5,method='Jaime')        
# dict_dFF_GCaMP6_COP_6=processdata(6,method='Jaime')        
# dict_dFF_GCaMP6_COP_7=processdata(7,method='Jaime')        


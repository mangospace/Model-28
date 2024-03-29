# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 17:12:34 2023

@author: manas
"""

import streamlit as st
#from streamlit import cli as stcli
from streamlit.web import cli as stcli
import pandas as pd
import openpyxl
import numpy as np
import regex as re
import plotnine as p9
import time
import urllib
import xlrd
from io import StringIO
import requests

st.title('Performance Year 2024 HCC RAF Model Change Impact V0.0')
st.caption('Made with \u2764\uFE0F @manas8u in Python and Streamlit')
st.caption('Understand the somewhat \U0001F479 nature of this version as well as design constrains imposed by Streamlit')
st.caption('Please share your feedback and suggestions. DM @manas8u')
"""
This model will allow you to compare the impact of the CMS RAF Model 28 **community dwelling beneficiaries** compared to Model 24 (payment year 2023).
- This model takes time to run. For ~10,000 members, the model can take 2-3 mins. Please do not refresh. 
- If you are analyzing data on more than 10,000 members I would suggest using one model at a time first.
- If you need to analyze more than 1 Medicare Advantage segments (e.g. Non Dual, Aged and Partial Benefit Dual Aged), please upload the member file and ICD10 information for different segments one at time (because the models for each population segment are different).
- If you dont know the Medicare Advantage segments, please use Non Dual, Aged.
- Please ensure that there are only two columns in the member file that you upload. The columns can have any name.
- Column 1: Unique patient identifier (please dont share HIPPA protected identifiers) 
- Column 2: ICD10s that were captured in 2022. ICD10s should be without decimal e.g. I700 (rather than I70.0) or D6878 (rather than D68.78)
"""
    
uploaded_file = st.file_uploader("Choose a xls or xlxs file")
option = st.selectbox(
    'Which model would you like to run?',
    ('Select', '2023 Model 24', 'Model 28', 'Both Models'))

option1 = st.selectbox(
    'Which Medicare Advantage population segment do these members belong to?',
    ('Select', 
"Community NonDual Aged",
"Community NonDual Disabled",
"Community FBDual Aged",
"Community FBDual Disabled",
"Community PBDual Aged",
"Community PBDual Disabled"
))

optiondict={
"Community NonDual Aged":"CNA",
"Community NonDual Disabled":"CND",
"Community FBDual Aged":"CFA",
"Community FBDual Disabled":"CFD",
"Community PBDual Aged":"CPA",
"Community PBDual Disabled":"CPD"   
    }
    
def prop24_impact(memberfile):
    
        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Running CMS-HCC RAF Model 24</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        #2023 model 
        #V2423 HCC names
        st.caption("Reading HCC names in Model 24.")
        hcc_name24=pd.read_csv(r"https://raw.githubusercontent.com/mangospace/Model-28/main/CMS-HCC%20software%20V2423.86.P1/V24H86L1.TXT", sep=' =', header=None, names=['HCC', 'HCC_name_24'], skiprows=6, skipinitialspace = True)
        hcc_name24['HCC_name_24']=hcc_name24['HCC_name_24'].str.replace(r'"', '')
        deletelist=['%MEND V24H86L1;',';']
        hcc_name24=(hcc_name24[hcc_name24.HCC.isin(deletelist) == False])
        hcc_name24['CC_24']=hcc_name24['HCC'].str.replace('CC|H','').astype(int) 
        hcc_name24=hcc_name24.drop(['HCC'], axis=1)
        hcc_name24 = hcc_name24.replace(r"^ +| +$", r"", regex=True)
       
        #V2423 ICD10-CC mapping
        st.caption("Reading ICD10-CC mapping in Model 24.")
        icd10_cc24=pd.read_csv("https://raw.githubusercontent.com/mangospace/Model-28/main/CMS-HCC%20software%20V2423.86.P1/F2423P1M.TXT", sep='	', header=None, names=['CC_24', 'Column2'], skipinitialspace = True)

        icd10_cc24.reset_index(inplace=True)
        icd10_cc24['CC_24'].astype(int)
        icd10_cc24= icd10_cc24.rename(columns = {'index':'ICD10_24'})
        icd10_cc24=icd10_cc24.drop(['Column2'], axis=1)
        icd10_cc24=icd10_cc24.drop_duplicates()
        
        #check if the data is read correctly by querying ICD10s linked with HCC 18
        
        #Merging file with a list of ICD10, corresponding CC, CC names
        st.caption("Creating a file with a list of ICD10, Corresponding CC, CC names.")
        icd10_cc24=icd10_cc24.merge(hcc_name24, left_on='CC_24', right_on='CC_24', how='left')
        icd10_cc24=icd10_cc24.drop_duplicates()
        icd10_cc24.drop_duplicates()
        
                   
        
        #Read the Model 24-2023 HCC_weight mapping
        st.caption("Reading RAF weights for HCCs in Model 24.")
        
        hcc_weight24= r"https://github.com/mangospace/Model-28/blob/05aacb6a795c259ab1d14d8397dacc89bd5744c5/CMS-HCC%20software%20V2423.86.P1/HCCv24.xlsx?raw=true"
        #Read the ICD10_HCC mapping
        hcc_wt24=pd.read_excel(hcc_weight24,sheet_name='transpose',names=['HCCname', 'RAF'],header=None, engine='openpyxl')  
        
        #create numeric values to represent interaction terms inline with other HCCs

        interdict={'HCC47_gCancer':'HCC1001',
           'DIABETES_CHF': 'HCC1002',
           'CHF_gCopdCF':'HCC1003',
           'HCC85_gRenal_V24':'HCC1004',
           'gCopdCF_CARD_RESP_FAIL':'HCC1005',
           'HCC85_HCC96':'HCC1006',
           'gSubstanceUseDisorder_gPsych':'HCC1007'
           }
        
        for key in interdict:
            hcc_wt24.HCCname= hcc_wt24.HCCname.str.replace(key, interdict[key], regex=False)
               
        hcc_wt24['segments']= hcc_wt24['HCCname'].str[:3] 
        hcc_wt24['number']= hcc_wt24['HCCname'].str.extract('(\d+)')
        hcc_wt24['HCC']= hcc_wt24['HCCname'].str[4:] 
        
        #limit dataset to community individuals
        #limit the table to only HCCs and not interactions
        
        #limit the table to only HCCs and not interactions
        #remove hard coding
        listoexcl=[
        'D6',
        'D7',
        'D8',
        'D9',
        'D10P',
        'F0_34',
        'F35_44',
        'F45_54',
        'F55_59',
        'F60_64',
        'M0_34',
        'M35_44',
        'M45_54',
        'M55_59',
        'M60_64',
        'OriginallyDisabled_Female',
        'OriginallyDisabled_Male']
        
        hcc_wt24 = hcc_wt24[~hcc_wt24["HCC"].isin(listoexcl)]
        #limit the table to only HCCs and not demographic 
        hcc_wt24 = hcc_wt24.loc[hcc_wt24 ['HCC'].str.contains("HCC", case=True)]
        #limit dataset to community individuals
        hcc_wt24= hcc_wt24[hcc_wt24['segments'] == segment]
        
        hcc_wt24 =hcc_wt24 [pd.to_numeric(hcc_wt24 ['number'], errors='coerce').notnull()]
        
        #create dictionary with RAF values and the HCCs
        hccva24=dict(zip(hcc_wt24 .number, hcc_wt24 .RAF))

        prodf1_24=pd.merge(memberfile, icd10_cc24, left_on='ICD10', right_on='ICD10_24', how='left')
#        prodf1_24=pd.merge(prodfeat, icd10_cc24, left_on='ICD10', right_on='ICD10_24', how='left')
        
        #number of HCCs remaining based on 2024 model
        hccnumber_2023=prodf1_24['CC_24'].notna().sum()
        st.caption(f"Number of HCCs before hierarchy is applied: {hccnumber_2023}")
        
        #limit dataset where CC is not null
        prodf1_24= prodf1_24[prodf1_24['CC_24'].notnull()]
        prodf1_24['CC_24']=prodf1_24['CC_24'].astype(int)
#        prodf1_24.columns
        
        prodf1_24['idx'] = prodf1_24.groupby('SUBSCRIBER_ID').cumcount()+1
        samplenum=len(prodf1_24)
        prodf2_24 = prodf1_24.pivot_table(index=['SUBSCRIBER_ID', ], columns='idx', 
        values=['ICD10_24','CC_24', 'HCC_name_24'], aggfunc='first')
        samplenum2=len(prodf2_24)
        prodf2_24= prodf2_24.sort_index(axis=1, level=1)
        prodf2_24.columns = [f'{x}_{y}' for x,y in prodf2_24.columns]
        prodf2_24 = prodf2_24.reset_index()
        
        prodf2_24 = prodf2_24.replace(r'\\r|\\n','', regex=True) 
        
        prodf2_24 = prodf2_24.replace(r'\\r+|\\n+|\\t+|\,|\;|\s|\n|\\n\\n',' ', regex=True) 
         
#        prodf2_24.columns
        
        cclist=prodf2_24.columns[prodf2_24.columns.str.contains(pat = 'CC_24_')]
        for x in cclist:
            prodf2_24[x]= prodf2_24[x].replace('-1', np.nan)
            prodf2_24[x] = prodf2_24[x].fillna(-1)
            prodf2_24[x]= prodf2_24[x].astype(int)
            prodf2_24[x]= prodf2_24[x].astype(str)
            prodf2_24[x]= prodf2_24[x].replace('-1', np.nan)
        
        st.caption("Creating and applying HCC model hierarchies.")
        target_url=r"https://raw.githubusercontent.com/mangospace/Model-28/main/CMS-HCC%20software%20V2423.86.P1/V24H86H1.TXT"
        file1 = urllib.request.urlopen(target_url)
        count= 0
        for line in file1:
            count+= 1
#            st.caption("Line{}: {}".format(count, line.strip()))
            x = re.search("\%\*imposing hierarchies\;", line.decode('utf-8'))
            if x:
                skiprowcnt=count    
            y = re.search("\%MEND V24H86H1", line.decode('utf-8'))
            if y:
                lastrowcnt=count    
        skipftcnt=count-lastrowcnt+1
        file1.close()    

        with st.spinner('Wait for it...'):
            
            #V2423 HIERARCHIES 
            create_hcc_frm_cc=pd.read_csv(r"https://raw.githubusercontent.com/mangospace/Model-28/main/CMS-HCC%20software%20V2423.86.P1/V24H86H1.TXT", sep="   , HIER=%STR", header=None, names=['top_CC', 'trump_HCC'], skiprows=skiprowcnt, skipinitialspace = True, skipfooter=skipftcnt)
            create_hcc_frm_cc['top_CC']=create_hcc_frm_cc['top_CC'].str.replace(".+\W[\s+]?\%SET0\(CC\=", '', regex=True)
            create_hcc_frm_cc['trump_HCC']=create_hcc_frm_cc['trump_HCC'].str.replace("\W\)\)\;|\(",'',regex=True)
            create_hcc_frm_cc['trump_HCC']=create_hcc_frm_cc['trump_HCC'].str.replace(" ","",regex=True)
            create_hcc_frm_cc['trump_HCC']= create_hcc_frm_cc['trump_HCC'].str.split()
            
            d = {}
            for index, value in create_hcc_frm_cc['trump_HCC'].items():
                d["string{0}".format(index)]=value
            #    d["string{0}".format(index)]=value.split(",")
            
            
            d1 = {}
            for index, value in create_hcc_frm_cc['top_CC'].items():
                d1["topc{0}".format(index)]=value
            #remove white spaces from this list
            
            cclist24=prodf2_24[cclist].values.tolist()
       
        
            immune_24=['47']
            cancer_24       = ['8','9','10','11','12']
            diabetes_24     = ['17','18','19']
            card_resp_fail_24 = ['82','83','84']
            chf_24          = ['85']
            gcopdcf_24        = ['110','111','112']
            renal_24        = ['134','135','136','137','138']
            sepsis_24       = ['2']
            arry_24         =['96'] 
            gsubstanceusedisorder_24 = ['54', '55', '56']
            gpsychiatric_24   = ['57', '58', '59', '60']
            
            for i in range(len(prodf2_24)): # how many rows to review from the list of disease
                for y in range(len(d1)): # how many heirarchies to traverse
            #        st.caption(set(cclist[i]))
            #        st.caption({d1["topc"+str(y)]})
                    if set(cclist24[i]).intersection({(d1["topc"+str(y)])}):
#                        atom=set(cclist24[i]).intersection({(d1["topc"+str(y)])})
                        atom2=set(cclist24[i])
                        atom3=set(d["string"+str(y)])   
                        atom2.difference_update(atom3)
                        cclist24[i]=list(atom2)
                if set(cclist24[i]).intersection(set(immune_24)) and set(cclist24[i]).intersection(cancer_24):
                    cclist24[i].append(1001)
                if set(cclist24[i]).intersection(set(diabetes_24)) and set(cclist24[i]).intersection(chf_24):
                    cclist24[i].append(1002)
                if set(cclist24[i]).intersection(set(gcopdcf_24)) and set(cclist24[i]).intersection(chf_24):
                    cclist24[i].append(1003)
                if set(cclist24[i]).intersection(set(renal_24)) and set(cclist24[i]).intersection(chf_24):
                    cclist24[i].append(1004)
                if set(cclist24[i]).intersection(set(gcopdcf_24)) and set(cclist24[i]).intersection(card_resp_fail_24):
                    cclist24[i].append(1005)
                if set(cclist24[i]).intersection(set(arry_24)) and set(cclist24[i]).intersection(chf_24):
                    cclist24[i].append(1006)    
                if set(cclist24[i]).intersection(set(gsubstanceusedisorder_24)) and set(cclist24[i]).intersection(gpsychiatric_24):
                    cclist24[i].append(1007)    
                #remove duplicate interaction terms
            print(f"{cclist24=}")
            cclist24 = [list(dict.fromkeys(x)) for x in cclist24 if x != np.nan]
        
                
            lenlist=[]
            for i in cclist24:
                lenlist.append(len(i))
            lenofcols24=max(lenlist)
            
            nocolist24=[]
            for  count in range(lenofcols24):
                nocolist24.append("NCC24_"+str(count))
            
            prodf3_24 = pd.DataFrame(cclist24,columns=nocolist24)
            prodf23_24=prodf2_24.merge(prodf3_24,left_index=True, right_index=True)
            
            raflist24=[]
            for  count in range(lenofcols24):
                raflist24.append("RAF24_"+str(count))
            
            
            change=0
            for key in hccva24:
                for x in range(len(prodf23_24)):
                    for z in range(len(raflist24)):
                        if prodf23_24[nocolist24[z]].iloc[x]==  str(key):
                            change +=1
                            prodf23_24.at[x,raflist24[z]] = np.where( prodf23_24[nocolist24[z]].iloc[x]==  str(key),
                                                           hccva24.get(key),np.nan)
            
       
        
            new_title = '<p style="font-family:sans-serif; color:Black; font-size: 42px;">Results: CMS-HCC RAF Model 24</p>'
            st.markdown(new_title, unsafe_allow_html=True)
    
    
            zeq=0

            raflist24= []
            for s in prodf23_24.columns:
               if 'RAF' in s:
                   raflist24.append(s)

            numHCCs=0
            for z in range(len(raflist24)):
                zeq+=prodf23_24[raflist24[z]].sum()
                numHCCs+=prodf23_24[raflist24[z]].notnull().tolist().count(True)
            zeq1=round(zeq/samplenum2, 3)
            zeq=round(zeq,1)
            avghcc=round(numHCCs/samplenum2,1)
        new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">RAW Cumulative Clinical RAF: {zeq} </p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.caption("RAW RAF means RAF is not adjusted for Coding Intensity Factor (CIF), does not include gender and does not account for number of conditions in CMS-HCC RAF Model 24")
        new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">RAW Avg Clinical RAF: {zeq1} </p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.caption("RAW Avg RAF has same caveats as before. Calculated Average RAF depends on if you uploaded all ICD10s for all members or uploaded a select sample (e.g. only individuals with open RAF gaps) so please interpret carefully.")
        new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of average HCCs in the population based on CMS-HCC RAF Model 24: {avghcc}</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.caption(f"Number of HCCs in the population based on CMS-HCC RAF Model 24: {numHCCs}")
        new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;"> </p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.caption(f"Number of unique patient with conditions that risk adjust: {samplenum2}")

      
        st.caption("")
        st.caption("")
        st.caption("")
        st.caption("")

        
        prodf23_24['rafcount']=len(raflist24)-(prodf23_24[raflist24].apply(lambda x: x.isnull().sum(), axis='columns'))
        prodf23_24['rafcount']= prodf23_24['rafcount'].astype("category")
        prodf23_24['Model']="V24"
    
        
        p=p9.ggplot(prodf23_24) + p9.aes(x="rafcount")  + p9.geom_bar() + p9.xlab("Number of HCC conditions") + p9.ylab("Number of beneficiaries")
#        + p9.ggtitle("Distribution of HCC's in the population")
        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Distribution of Number of HCCs in the sample based on CMS-HCC RAF Model 24</p>'
        st.markdown(new_title, unsafe_allow_html=True)
#

        st.pyplot(p9.ggplot.draw(p))        

        st.caption("")
        st.caption("")
        st.caption("")
        st.caption("")


        hcc24list=[]
        for i in range(1,len(raflist24)+1):
            hcc24list.append("HCC_name_24_"+str(i))
            

        ncclistnum= []
        for s in prodf23_24.columns:
           if 'NCC24' in s:
               ncclistnum.append(s)

        
        prodf23_24['index1'] = prodf23_24.index

        prodf23_24melt=pd.melt(prodf23_24, id_vars ='index1' , value_vars=ncclistnum)    

#        prodf2_24['index1'] = prodf2_24.index
#        prodf23_24melt=pd.melt(prodf2_24, id_vars ='index1' , value_vars=hcc24list)

        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Immune Disorders & Cancer', 1001] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Diabetes & Heart Failure', 1002] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Heart Failure & Chronic Lung Disease', 1003] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Heart Failure & Kidney', 1004] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Chronic Lung Disorder & Cardiorespiratory Failure', 1005] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Heart Failure & Specified Heart Arrhythmias', 1006] 
        hcc_name24.loc[len(hcc_name24.index)] = ['Interaction: Substance Abuse and Mental Health', 1007] 

        prodf23_24melt['value']="HCC"+prodf23_24melt['value'].astype(str)

        hcc_name24['C1C']="HCC"+hcc_name24['CC_24'].astype(str)

        for i in range(len(prodf23_24melt)):
            if prodf23_24melt.at[i,'value'] == 'HCCnan':
                prodf23_24melt.at[i,'value']=np.nan 
        
        prodf23_24melt=prodf23_24melt.merge(hcc_name24, how="left", left_on='value', right_on='C1C')
        matter23=pd.DataFrame(prodf23_24melt.HCC_name_24.value_counts())
        matter23.reset_index(inplace=True)
        matter23= matter23.rename(columns = {'index':'HCC Name',"HCC_name_24":"Number of beneficiaries" })       
    
        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">15 most common HCCs in the population based on  CMS-HCC RAF Model 24</p>'

        blankIndex=[''] * len(matter23)
        matter23.index=blankIndex
        st.markdown(new_title, unsafe_allow_html=True)
        st.dataframe(matter23.nlargest(20,"Number of beneficiaries"))

        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of members with interaction related conditions based on  CMS-HCC RAF Model 24</p>'
        st.markdown(new_title, unsafe_allow_html=True)

        interlist=['Interaction: Immune Disorders & Cancer', 'Interaction: Diabetes & Heart Failure', 'Interaction: Heart Failure & Chronic Lung Disease',
        'Interaction: Heart Failure & Kidney', 'Interaction: Chronic Lung Disorder & Cardiorespiratory Failure',
        'Interaction: Heart Failure & Specified Heart Arrhythmias','Interaction: Substance Abuse and Mental Health'] 
        
        blankIndex=[''] * len(matter23)
        matter23.index=blankIndex
        matter23.style.hide_index()
        st.caption("Interaction HCCs")
        st.dataframe(matter23[matter23['HCC Name'].isin(interlist)])

        bhlist23=['Substance Use Disorder, Moderate/Severe, or Substance Use with Complications',
                  'Substance Use with Psychotic Complications','Personality Disorders',
                  'Reactive and Unspecified Psychosis',
                  'Major Depressive, Bipolar, and Paranoid Disorders', 'Interaction: Substance Abuse and Mental Health'] 

        
        blankIndex=[''] * len(matter23)
        matter23.index=blankIndex
        matter23.style.hide_index()

        if len(matter23[matter23['HCC Name'].isin(bhlist23)])>0:
            new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of members with Behavioral Health conditions based on CMS-HCC RAF Model 24</p>'
            st.markdown(new_title, unsafe_allow_html=True)
            st.caption("Behavioral Health HCCs")
            st.dataframe(matter23[matter23['HCC Name'].isin(bhlist23)])
        else:
            st.caption("No Behavioral Health Diagnosis reported in the population")

        return prodf23_24 , matter23
   

def prop28_impact(memberfile):
    new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Running CMS-HCC RAF Model 28</p>'
    st.markdown(new_title, unsafe_allow_html=True)

    st.caption("Reading HCC names in Model 28.")
    url="https://raw.githubusercontent.com/mangospace/Model-28/main/Model%2028%20software/F2823T2N_FY22FY23.TXT"
    response = requests.get(url)
    csvStringIO = StringIO(response.text)
    icd10_cc=pd.read_csv(csvStringIO, sep='	', header=None, names=['CC', 'Column2'], skipinitialspace = True)
    icd10_cc.reset_index(inplace=True)
    icd10_cc['CC'].astype(int)
    icd10_cc= icd10_cc.rename(columns = {'index':'ICD10'})
    icd10_cc=icd10_cc.drop(['Column2'], axis=1)
    icd10_cc=icd10_cc.drop_duplicates()
    
    #create hcc names
    st.caption("Reading ICD10-CC mapping in Model 28.")
    hcc_name=pd.read_csv(r"https://raw.githubusercontent.com/mangospace/Model-28/main/Model%2028%20software/V28115L3.TXT", sep=' =', header=None, names=['HCC', 'HCC_name'], skiprows=6, skipinitialspace = True)
    hcc_name['HCC_name']=hcc_name['HCC_name'].str.replace(r'"', '')
    deletelist=['%MEND V28115L3;',';']
    hcc_name=(hcc_name[hcc_name.HCC.isin(deletelist) == False])
    hcc_name['CC']=hcc_name['HCC'].str.replace('CC|H','').astype(int) 
    hcc_name=hcc_name.drop(['HCC'], axis=1)
    hcc_name = hcc_name.replace(r"^ +| +$", r"", regex=True)


    #Merge ICD10_CC with HCC names
    st.caption("Creating a file with a list of ICD10, Corresponding CC, CC names.")
    icd10_cc=icd10_cc.merge(hcc_name, left_on='CC', right_on='CC', how='left')
    icd10_cc=icd10_cc.drop_duplicates()
    
    with st.spinner('Wait for it...'):
    
        
        # check the HCC category of particular icd10s
        #icd10_cc[icd10_cc['ICD10'].eq('I509')]
        #icd10_cc[icd10_cc['CC'].eq(38.0)]
        
        # Apply CCs to gap reports
        prodf1=pd.merge(memberfile, icd10_cc, left_on='ICD10', right_on='ICD10', how='left')
        
        
        #number of HCCs remaining based on 2024 model
        hccnumber_2024=prodf1['CC'].notna().sum()
        
        #limit dataset where CC is not null
        prodf1= prodf1[prodf1['CC'].notnull()]
        prodf1['CC']=prodf1['CC'].astype(int)
        
        
        #create long to wide
        #https://stackoverflow.com/questions/22798934/pandas-long-to-wide-reshape-by-two-variables
        prodf1['idx'] = prodf1.groupby('SUBSCRIBER_ID').cumcount()+1
        samplenum=len(prodf1)
    
        prodf2 = prodf1.pivot_table(index=['SUBSCRIBER_ID'], columns='idx', values=['ICD10','CC', 'HCC_name'], aggfunc='first')
        samplenum2=len(prodf2)    
        #prodf2 = prodf1.pivot_table(index=['CONSISTENT_MEMBER_ID', 'SUBSCRIBER_ID', 'LAST_NAME','FIRST_NAME', 'DOB_DATE',], columns='idx', values=['ICD10','CC', 'HCC_name'], aggfunc='first')
        prodf2= prodf2.sort_index(axis=1, level=1)
        prodf2.columns = [f'{x}_{y}' for x,y in prodf2.columns]
        prodf2 = prodf2.reset_index()
        
        prodf2 = prodf2.replace(r'\\r|\\n','', regex=True) 
        
        prodf2 = prodf2.replace(r'\\r+|\\n+|\\t+|\,|\;|\s|\n|\\n\\n',' ', regex=True) 
        cclist=prodf2.columns[prodf2.columns.str.contains(r"(?<!H)CC_",regex=True)]
        
        
        for x in cclist:
            prodf2[x]= prodf2[x].replace('-1', np.nan)
            prodf2[x] = prodf2[x].fillna(-1)
            prodf2[x]= prodf2[x].astype(int)
            prodf2[x]= prodf2[x].astype(str)
            prodf2[x]= prodf2[x].replace('-1', np.nan)
        
        
        #apply heirarhcy
        create_hcc_frm_cc=pd.read_csv(r"https://raw.githubusercontent.com/mangospace/Model-28/main/Model%2028%20software/V28115H1.TXT", sep="   , HIER=%STR", header=None, names=['top_CC', 'trump_HCC'], skiprows=30, skipinitialspace = True, skipfooter=1)
        create_hcc_frm_cc['top_CC']=create_hcc_frm_cc['top_CC'].str.replace(".+\W[\s+]?\%SET0\(CC\=", '', regex=True)
        #create_hcc_frm_cc['top_CC'].head(35)
        create_hcc_frm_cc['trump_HCC']=create_hcc_frm_cc['trump_HCC'].str.replace("\W\)\)\;|\(",'',regex=True)
        create_hcc_frm_cc['trump_HCC']=create_hcc_frm_cc['trump_HCC'].str.replace(" ","",regex=True)
        create_hcc_frm_cc['trump_HCC']= create_hcc_frm_cc['trump_HCC'].str.split()
        
        d = {}
        for index, value in create_hcc_frm_cc['trump_HCC'].items():
            d["string{0}".format(index)]=value
        
        d1 = {}
        for index, value in create_hcc_frm_cc['top_CC'].items():
            d1["topc{0}".format(index)]=value
        
        cclist1=prodf2[cclist].values.tolist()


        cancer_v28          = ['17', '18', '19', '20', '21', '22', '23']
        diabetes_v28        = ['35', '36', '37', '38']
        card_resp_fail      = ['211', '212', '213']
        hf_v28              = ['221', '222', '223', '224', '225', '226']
        chr_lung_v28        = ['276', '277', '278', '279', '280']
        kidney_v28          = ['326', '327', '328', '329']
        sepsis              = ['2']
        gSubUseDisorder_v28 = ['135', '136', '137', '138', '139']
        gpsychiatric_v28    = ['151', '152', '153', '154', '155']   
        neuro_v28           = ['180', '181', '182', '190', '191', '192', '195', '196', '198', '199']
        ulcer_v28           = ['379', '380', '381', '382']   
        hcc238              = ['238'] 
        
        for i in range(len(prodf2)): # how many rows to review from the list of disease
            for y in range(len(d1)): # how many heirarchies to traverse
                if set(cclist1[i]).intersection({(d1["topc"+str(y)])}):
##                    atom=set(cclist1[i]).intersection({(d1["topc"+str(y)])})
                    atom2=set(cclist1[i])
                    atom3=set(d["string"+str(y)])   
                    atom2.difference_update(atom3)
                    cclist1[i]=list(atom2)
            if set(cclist1[i]).intersection(set(diabetes_v28)) and set(cclist1[i]).intersection(hf_v28):
                cclist1[i].append(2001)
            if set(cclist1[i]).intersection(set(chr_lung_v28)) and set(cclist1[i]).intersection(hf_v28):
                cclist1[i].append(2002)
            if set(cclist1[i]).intersection(set(kidney_v28)) and set(cclist1[i]).intersection(hf_v28):
                cclist1[i].append(2003)
            if set(cclist1[i]).intersection(set(chr_lung_v28)) and set(cclist1[i]).intersection(card_resp_fail):
                cclist1[i].append(2004)
            if set(cclist1[i]).intersection(set(hf_v28)) and set(cclist1[i]).intersection(hcc238):
                cclist1[i].append(2005)
            if set(cclist1[i]).intersection(set(gSubUseDisorder_v28)) and set(cclist1[i]).intersection(gpsychiatric_v28):
                cclist1[i].append(2006)    
        cclist1 = [list(dict.fromkeys(x)) for x in cclist1 if x != np.nan]

#        cclist1=list(set(cclist1))
        lenlist=[]
        cclist_a=[]
        x=0
        for i in cclist1:
#            print(x)
            catc=set(i)
            catc.discard(np.nan)
#            print(catc)
            lenlist.append(len(catc))
#            print(len(catc))
            cclist_a.append(list(catc))
            x+=1
 #       print(lenlist)
        lenofcols=max(lenlist)
 #       print(f"{lenofcols=}")


#        cclist1=list(set(cclist1))
        cccollist=[]
        ncolist=[]
        raflist=[]
        for count in range(lenofcols):
            cccollist.append("CCC_"+str(count))
            raflist.append("RAF_"+str(count))
            ncolist.append("NCC_"+str(count))
#            st.caption(lenofcols)
#        print(len (cclist1))
#        print(f"{cclist1=}")
#        print(len (ncolist))
#        print(f"{ncolist=}")
        prodf3_a = pd.DataFrame(cclist_a)
        prodf3_a = prodf3_a.fillna(value=np.nan)
        for x in range(len(prodf3_a.axes[1])):
#            print(x)
            if prodf3_a[x].isnull().all():
                print(f"{x} All values in the column are NaN")
                prodf3_a=prodf3_a.drop(x, axis=1)
        prodf3 = prodf3_a.set_axis(ncolist, axis=1)
        
        prodf23=prodf2.merge(prodf3,left_index=True, right_index=True)
        
        #Read the HCC_weight mapping
        st.caption("Reading RAF weights for HCCs in Model 28.")
        hcc_weight= r'https://github.com/mangospace/Model-28/blob/05aacb6a795c259ab1d14d8397dacc89bd5744c5/Model%2028%20software/Coefficients%20HCC%20V28.xlsx?raw=true'
        #Read the ICD10_HCC mapping
        hcc_wtdf=pd.read_excel(hcc_weight,sheet_name='transpose',names=['HCCname', 'RAF'])  
        #create numeric values to represent interaction terms inline with other HCCs

        interdict28={'DIABETES_HF_V28':'HCC2001',
        'HF_CHR_LUNG_V28': 'HCC2002',
        'HF_KIDNEY_V28':'HCC2003',
        'CHR_LUNG_CARD_RESP_FAIL_V28':"HCC2004",
        'HF_HCC238_V28':"HCC2005",
        'gSubUseDisorder_gPsych_V28':'HCC2006'
        }

        for key in interdict28:
            hcc_wtdf.HCCname= hcc_wtdf.HCCname.str.replace(key, interdict28[key], regex=False)
               
        hcc_wtdf['segments']= hcc_wtdf['HCCname'].str[:3] 
        hcc_wtdf['number']= hcc_wtdf['HCCname'].str.extract('(\d+)')
        hcc_wtdf['HCC']= hcc_wtdf['HCCname'].str[4:] 
        hcc_wtdf= hcc_wtdf[hcc_wtdf['segments'] == segment]
        hcc_wtdf = hcc_wtdf[~hcc_wtdf["HCC"].str.contains("V28")]
        hcc_wtdf_1= hcc_wtdf.loc[hcc_wtdf['HCC'].str.contains("HCC", case=True)]
        hcc_wtdf_1=hcc_wtdf_1[pd.to_numeric(hcc_wtdf_1['number'], errors='coerce').notnull()]
        
        #create dictionary with RAF values and the HCCs
        hccva=dict(zip(hcc_wtdf_1.number, hcc_wtdf_1.RAF))
        
        change=0
        for key in hccva:
            for x in range(len(prodf23)):
                for z in range(len(raflist)):
                    if prodf23[ncolist[z]].iloc[x]== str(key):
                        change +=1
                        
        #                st.caption(prodf23[ncolist[z]].iloc[x])
        #                st.caption(str(key))
                        prodf23.at[x,raflist[z]] = np.where( prodf23[ncolist[z]].iloc[x]==  str(key),
                                                       hccva.get(key),np.nan)
        
    
        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 42px;">Results: CMS-HCC RAF Model 28</p>'
        st.markdown(new_title, unsafe_allow_html=True)
    
#        st.caption(prodf23)
    
        zeq28=0
        numHCCs28=0

        raflistnum= []
        for s in prodf23.columns:
           if 'RAF' in s:
               raflistnum.append(s)
                   
        for z in range(len(raflistnum)):
            zeq28 +=prodf23[raflistnum[z]].sum()
            numHCCs28 +=prodf23[raflistnum[z]].notnull().tolist().count(True)
    zeq128=round(zeq28/samplenum2, 3)
    zeq28=round(zeq28,1)
    avghcc28=round(numHCCs28/samplenum2,1)

    new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">RAW Cumulative Clinical RAF: {zeq28}</p>'
    st.markdown(new_title, unsafe_allow_html=True)
    st.caption("RAW RAF means RAF is not adjusted for Coding Intensity Factor (CIF), does not include gender, aged/disabled status, and whether a beneficiary lives in the community or in an institution, does not account for number of conditions in CMS-HCC RAF Model 28")
    new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">RAW Avg Clinical RAF: {zeq128} </p>'
    st.markdown(new_title, unsafe_allow_html=True)
    st.caption("RAW Avg RAF has same caveats as before. Average RAF depends on if you uploaded ICD10s for all members or a select sample (e.g. only individuals with open RAF gaps) so please interpret carefully.")
    new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of average HCCs in the population based on CMS-HCC RAF Model 28: {avghcc28}</p>'
    st.markdown(new_title, unsafe_allow_html=True)
    st.caption(f"Number of HCCs in the population based on CMS-HCC RAF Model 28: {numHCCs28}")
    new_title = f'<p style="font-family:sans-serif; color:Black; font-size: 30px;"> </p>'
    st.markdown(new_title, unsafe_allow_html=True)
    st.caption(f"Number of unique patient with conditions that risk adjust: {samplenum2}")

    prodf23['rafcount']=len(raflistnum)-(prodf23[raflistnum].apply(lambda x: x.isnull().sum(), axis='columns'))
    prodf23['rafcount']= prodf23['rafcount'].astype("category")
    
            
    st.caption("")
    st.caption("")
    st.caption("")
    st.caption("")

    
    new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Distribution of Number of HCCs in the sample based on CMS-HCC RAF Model 28</p>'
    st.markdown(new_title, unsafe_allow_html=True)
    prodf23['Model']="V28"
    p=p9.ggplot(prodf23) + p9.aes(x="rafcount")  + p9.geom_bar() + p9.xlab("Number of HCC conditions") + p9.ylab("Number of beneficiaries")
#    + p9.ggtitle("Distribution of HCC's in the population")
    st.pyplot(p9.ggplot.draw(p))      
    
    st.caption("")
    st.caption("")
    st.caption("")
    st.caption("")
    
    hcclist=[]
    for i in range(1,len(raflistnum)+1):
        hcclist.append("HCC_name_"+str(i))

    ncclistnum= []
    for s in prodf23.columns:
       if 'NCC' in s:
           ncclistnum.append(s)

        
    prodf23['index1'] = prodf23.index
    prodf2melt=pd.melt(prodf23, id_vars ='index1' , value_vars=ncclistnum)
    prodf2melt['value']="HCC"+prodf2melt['value'].astype(str)

    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Diabetes & Heart Failure', 2001] 
    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Heart Failure & Chronic Lung Disease', 2002] 
    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Heart Failure & Kidney', 2003] 
    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Chronic Lung Disorder & Cardiorespiratory Failure', 2004] 
    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Heart Failure & Specified Heart Arrhythmias', 2005] 
    hcc_name.loc[len(hcc_name.index)] = ['Interaction: Substance Abuse and Mental Health', 2006] 
                                 
    hcc_name['C1C']="HCC"+hcc_name['CC'].astype(str)

    for i in range(len(prodf2melt)):
        if prodf2melt.at[i,'value'] == 'HCCnan':
            prodf2melt.at[i,'value']=np.nan 
    
    prodf2melt=prodf2melt.merge(hcc_name, how="left", left_on='value', right_on='C1C')
    matter=pd.DataFrame(prodf2melt.HCC_name.value_counts())
    matter.reset_index(inplace=True)
    matter = matter.rename(columns = {'index':'HCC Name',"HCC_name":"Number of beneficiaries" })       
    new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">15 most common HCCs in the sample based on  CMS-HCC RAF Model 28</p>'
    st.markdown(new_title, unsafe_allow_html=True)
    blankIndex=[''] * len(matter)
    matter.index=blankIndex    
    st.dataframe(matter.nlargest(15,"Number of beneficiaries"))

    new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of members with interaction related conditions based on  CMS-HCC RAF Model 28</p>'
    st.markdown(new_title, unsafe_allow_html=True)

    interlist=['Interaction: Diabetes & Heart Failure', 'Interaction: Heart Failure & Chronic Lung Disease',
    'Interaction: Heart Failure & Kidney', 'Interaction: Chronic Lung Disorder & Cardiorespiratory Failure',
    'Interaction: Heart Failure & Specified Heart Arrhythmias',
    'Interaction: Heart Failure & Specified Heart Arrhythmias','Interaction: Substance Abuse and Mental Health'] 

    blankIndex=[''] * len(matter)
    matter.index=blankIndex
    matter.style.hide_index()
    st.caption("Interaction HCCs")
    st.dataframe(matter[matter['HCC Name'].isin(interlist)])


    bhlist=['Drug Use with Psychotic Complications','Alcohol Use with Psychotic Complications Drug Use Disorder, Moderate/Severe, or Drug Use with Non-Psychotic Complications',
        'Drug Use Disorder, Mild, Uncomplicated, Except Cannabis', 
        'Alcohol Use Disorder, Moderate/Severe, or Alcohol Use with Specified NonPsychotic Complications',
        'Schizophrenia','Psychosis, Except Schizophrenia', 'Personality Disorders; Anorexia/Bulimia Nervosa','Bipolar Disorders without Psychosis',
        'Depression, Moderate or Severe, without Psychosis','Interaction: Substance Abuse and Mental Health']
        
    blankIndex=[''] * len(matter)
    matter.index=blankIndex
    matter.style.hide_index()
    if len(matter[matter['HCC Name'].isin(bhlist)])>0:
        new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Number of members with Behavioral Health conditions based on CMS-HCC RAF Model 28</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.caption("Behavioral Health HCCs")
        st.dataframe(matter[matter['HCC Name'].isin(bhlist)])
    else:
        st.caption("No Behavioral Health Diagnosis reported in the population")
    
    return prodf23 , matter


if uploaded_file is not None:           
    x = re.search("\.", uploaded_file.name)
    file_extension= uploaded_file.name[x.start()+1:len(uploaded_file.name)]
    if file_extension == 'xlsx':
        prodfeat = pd.read_excel(uploaded_file.read(), engine='openpyxl')
    elif file_extension == 'xls':
        prodfeat = pd.read_excel(uploaded_file.read())
    elif file_extension == 'csv':
        prodfeat = pd.read_csv(uploaded_file.read())
       
    # Can be used wherever a "file-like" object is accepted:
    prodfeat = pd.read_excel(uploaded_file, names=['SUBSCRIBER_ID','ICD10'])
    prodfeat['ICD10']=prodfeat['ICD10'].str.strip()

    if option=='2023 Model 24':  
        if option1 != 'Select':
            segment= optiondict[option1]
            prodf23_24=prop24_impact(prodfeat)

    if option=='Model 28':  
        if option1 != 'Select':
            segment= optiondict[option1]
            prodf23=prop28_impact(prodfeat)

    if option=='Both Models':  
        if option1 != 'Select':
            segment= optiondict[option1]
            prodf23_24, matter23 =prop24_impact(prodfeat)
            prodf23, matter=prop28_impact(prodfeat)

            new_title = '<p style="font-family:sans-serif; color:Black; font-size: 30px;">Distribution of Number of HCCs in the population based on CMS-HCC RAF Model 24 and Model 28</p>'
            st.markdown(new_title, unsafe_allow_html=True)


            prodfnew = pd.concat([prodf23_24, prodf23], ignore_index=True)
            prodfnew.Model=prodfnew.Model.astype("category")
            p=(p9.ggplot(prodfnew) + p9.aes(x="rafcount", fill="Model")  + p9.geom_bar(stat='count', position='dodge')
            + p9.xlab("Number of HCC conditions") + p9.ylab("Number of beneficiaries")
            + p9.geom_text(
                p9.aes(label=p9.after_stat('count')),
                stat='count',
                nudge_y=0.125,
                va='bottom')
            )

            st.pyplot(p9.ggplot.draw(p))      
            st.caption("Same plot as above but without the labels")
            p=(p9.ggplot(prodfnew) + p9.aes(x="rafcount", fill="Model")  + p9.geom_bar(stat='count', position='dodge')
            + p9.xlab("Number of HCC conditions") + p9.ylab("Number of beneficiaries")
            )

            st.pyplot(p9.ggplot.draw(p))    



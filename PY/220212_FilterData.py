

"""
Filter and clean tax returns from Non Profits.
Filters by location using Zipcodes
Filters by location using Activity,etc codes
3 related fields: DILA, Activity code, and NTEE codes are used for class

Start with NYC then ID and WY
"""

#%% Import NYC 990 filings
# Here is the download location: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
# Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

import pandas as pd
pd.set_option("max_columns",None)
df = pd.read_csv(r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_ny.csv" , dtype={'ACTIVITY': object})

#Clean Data
remove = ['ICO','TAX_PERIOD','ASSET_CD','INCOME_CD','FILING_REQ_CD','PF_FILING_REQ_CD','ACCT_PD','SORT_NAME']
df = df.drop( remove, axis = 1)
df = df.dropna(how='all',axis =1)
df['ZIP_Short'] = [r.split("-")[0] for i,r in df['ZIP'].iteritems()]
df = df.drop_duplicates(subset=['EIN'],keep='first')

#Create Readable Activity Columns
df['act1'] = df['ACTIVITY'].str.slice(0,3)
df['act2'] = df['ACTIVITY'].str.slice(3,6)
df['act3'] = df['ACTIVITY'].str.slice(6,9)

print( "{} groups are in the list".format(len(df)) )
df.head()
# %% Bring in NYC Zipcodes and filter by location 

import geopandas as gpd
zips = gpd.read_file( r"C:\Users\csucuogl\Desktop\DATA\NYC\ZIP_CODE_040114\ZIP_CODE_040114.shp")
zips = zips[['ZIPCODE','PO_NAME','COUNTY']]
zips = zips.drop_duplicates(keep='first') #10004 is multip poly (Governers island,...)
zips.head()

df = df[ df["ZIP_Short"].isin( zips['ZIPCODE'] )]
df = df.join(zips.set_index("ZIPCODE"),on="ZIP_Short")

print( "{} groups are in the list".format(len(df)) )
df.head()

#%% IMPORT CODES and Definitions
# This is a filtered list from the Data dictionary -> Activity and NTEE codes
# Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

#ACTIVITY CODES
act_codes = pd.read_excel( r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\FocusCodes.xls" , sheet_name="Activity Codes", header = None)
act_codes = act_codes[0].str.split(" " ,expand = True , n=1)
act_codes.columns = ['code','definition']

#NTEE CODES
ntee_codes = pd.read_excel( r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\FocusCodes.xls" , sheet_name="NTEE Codes", header = None)
ntee_codes = ntee_codes[0].str.split(" " ,expand = True , n=1)
ntee_codes.columns = ['code','definition']

ntee_codes.head(10)

#%% FILTER DATA to RELEVANT CODES
# ACTIVITY Activity Codes -> Pre 1995 groups have this
# NTEE_CD National Taxonomy of Exempt Entities (NTEE) Code 
# Filter with whichever activity or ntee is full

df1 = df[ (df['NTEE_CD'].isin( ntee_codes['code'].values )) | (df['act1'].isin( act_codes['code'].values )) | (df['act2'].isin( act_codes['code'].values )) | (df['act3'].isin( act_codes['code'].values ))  ]

print( "{} groups are in the list".format(len(df1)) )
df1[["NAME", 'ACTIVITY', 'act1', 'act2', 'act3', "NTEE_CD"]].head(12)

#%% Assign Readable Org Focuses (Multiple for Actitivtye)
import numpy as np

df1['def1'] = None
df1['def2'] = None
df1['def3'] = None

# !Ntee code but in ACT
df1['def1'] = np.where(
    df1['act1'].isin( act_codes['code'].values ) , #If ntee code is in the list
    df1['act1'].replace( act_codes.set_index("code").to_dict()['definition'] ) ,
    None
)

df1['def1'] = np.where(
    df1['NTEE_CD'].isin( ntee_codes['code'].values ) , #If ntee code is in the list
    df1['NTEE_CD'].replace( ntee_codes.set_index("code").to_dict()['definition'] ) ,
    df1['def1']
)

df1['def2'] = np.where(
    df1['act2'].isin( act_codes['code'].values ) , #If ntee code is in the list
    df1['act2'].replace( act_codes.set_index("code").to_dict()['definition'] ) ,
    None
)

df1['def3'] = np.where(
    df1['act3'].isin( act_codes['code'].values ) , #If ntee code is in the list
    df1['act3'].replace( act_codes.set_index("code").to_dict()['definition'] ) ,
    None
)

df1['OrgFocus'] = [", ".join( list(filter(None, r.tolist())) ) for i,r in df1[['def1','def2','def3']].iterrows()]

df1[["NAME", 'act1', 'act2', 'act3', "NTEE_CD",'def1','def2','def3','OrgFocus']].sample(15)

#%%

splitter = [' AVE ',' ST '," STREET " , " AVENUE " , " PLACE "]

df1['address'] = df1['STREET'].str.split(" APT").str[0]

for _ in splitter:
    df1['address'] = [ " ".join( r.partition(_)[:-1] ) for i,r in df1['address'].iteritems() ]

df1['address'] = df1['address'] + ", " + df1['PO_NAME'] + ", " + df1['STATE'] + ", " + df1['ZIP_Short']

df1[['STREET','address']].sample(20)


#%% GEOCODE
import zipcodes
import geocoder

#Simplify Data
remove = 'CITY,FOUNDATION,ORGANIZATION,STATUS,NTEE_CD,COUNTY,def1,def2,def3,act1,act2,act3,ASSET_AMT,INCOME_AMT,REVENUE_AMT,RULING,DEDUCTIBILITY,EIN'.split(",")
df1 = df1[ df1.columns[ ~df1.columns.isin( remove ) ] ]

df1['lat'] = None
df1['lon'] = None

lats = []
lons = []
count = 0
for i,r in df1.iterrows():
    if "PO BOX" in r['STREET']: #if address is to a PO BOX
        loc = zipcodes.matching( r['ZIP'] )
        lat = loc[0]['lat']
        lon = loc[0]['long']
    else:
        loc = geocoder.arcgis(r['address']).json

        lat = loc['lat']
        lon = loc['lng']

    lats.append( lat )
    lons.append( lon )
    count + count + 1
    if count%50==0: print( "{}".format(count) )

df1['lat'] = lats
df1['lon'] = lons

df1.sample(10)


# %% ID & WY

np_id = pd.read_csv(r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_id.csv", dtype={'ACTIVITY': object})
np_wy = pd.read_csv(r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_wy.csv", dtype={'ACTIVITY': object})

#Merge datasets
np = np_id.append( np_wy )

#Clean
np = np.drop( remove, axis = 1)
np = np.dropna(how='all',axis =1)
np['ZIP_Short'] = [r.split("-")[0] for i,r in np['ZIP'].iteritems()]
np = np.drop_duplicates(subset=['EIN'],keep='first')

#Seperate Activity to individual codes
np['act1'] = np['ACTIVITY'].str.slice(0,3)
np['act2'] = np['ACTIVITY'].str.slice(3,6)
np['act3'] = np['ACTIVITY'].str.slice(6,9)

print( "{} groups are in the list".format(len(np1)) )
np1.head()


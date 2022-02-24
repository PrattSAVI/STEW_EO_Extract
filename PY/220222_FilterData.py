

"""
Join Datasets
Filter and clean tax returns from Non Profits.
Filters by location using Zipcodes
Filters by location using Activity,etc codes
3 related fields: DILA, Activity code, and NTEE codes are used for class

Start with NYC then ID and WY
"""

#%% 
# Import NYS / CT / NJ 990 filings
# Here is the download location: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
# Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

import pandas as pd
pd.set_option("max_columns",None)

# All folders
links = [
    r'C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_ct.csv',
    r'C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_nj.csv',
    r'C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_ny.csv'
]

df = pd.DataFrame()
for link in links:
    temp = pd.read_csv( link , dtype={'ACTIVITY': object})
    df = df.append( temp )

print( "{} groups are in the list".format(len(df)) )
df.sample(10)

#%%
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
# %% 
# Bring in MSA Zipcodes and filter by location 

# Read Zipcodes,  
zips = pd.read_excel(
    r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\FocusCodes.xls",
    sheet_name = 'ZipCodes',
    dtype={'MSA_Padded': object}
)

# Filter with Zips
df = df[ df['ZIP_Short'].isin( zips['MSA_Padded'] )]

print( "{} groups are in the list".format(len(df)) )
df.sample(5)

#%% IMPORT CODES and Definitions
# This is a filtered list from the Data dictionary -> Activity and NTEE codes
# Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

#ACTIVITY CODES
act_codes = pd.read_excel( r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\FocusCodes.xls" , sheet_name="Activity Codes" )
act_codes.columns = ['code','definition']
act_codes['code'] = act_codes['code'].astype( str )

#NTEE CODES
ntee_codes = pd.read_excel( r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\FocusCodes.xls" , sheet_name="NTEE Codes" )
ntee_codes.columns = ['code','definition']

print( "NTEE Codes" )
display( ntee_codes.head(10) )

print( "Activity Codes" )
display( act_codes.head(10) )

#%% FILTER DATA to RELEVANT CODES
# ACTIVITY Activity Codes -> Pre 1995 groups have this
# NTEE_CD National Taxonomy of Exempt Entities (NTEE) Code 
# Filter with whichever activity or ntee is full

df1 = df[ (df['NTEE_CD'].isin( ntee_codes['code'].values )) | (df['act1'].isin( act_codes['code'].values )) | (df['act2'].isin( act_codes['code'].values )) | (df['act3'].isin( act_codes['code'].values ))  ].copy()

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
df1.head()
#%% Correct Addresses

# Remove after these
splitter = [' AVE ',' ST '," STREET " , " AVENUE " , " PLACE "]

df1['address'] = df1['STREET'].str.split(" APT").str[0] #Remove APT numbers
for _ in splitter: # All the others
    df1['address'] = [ " ".join( r.partition(_)[:-1] ) for i,r in df1['address'].iteritems() ]

# Make a proper address 
df1['address'] = df1['address'] + ", " + df1['CITY'] + ", " + df1['STATE'] + ", " + df1['ZIP_Short']

df1[['STREET','address']].sample(20)


#%% 
# GEOCODE
# 1. PO BOX -> Gets the center of the zipcode
# 2. Good addresses get geocoded

import zipcodes
import geocoder

#Simplify Data
remove = 'CITY,FOUNDATION,ORGANIZATION,STATUS,NTEE_CD,COUNTY,def1,def2,def3,act1,act2,act3,ASSET_AMT,INCOME_AMT,REVENUE_AMT,RULING,DEDUCTIBILITY,EIN'.split(",")
df1 = df1[ df1.columns[ ~df1.columns.isin( remove ) ] ]

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
    count = count + 1
    if count%50==0: print( "{}".format(count) )

df1['lat'] = lats
df1['lon'] = lons

df1.sample(10)

#%% GEO DATAFRAME
import geopandas as gpd
import matplotlib.pyplot as plt

gdf = gpd.GeoDataFrame(
    df1,
    geometry = gpd.points_from_xy( df1['lon'],df1['lat']),
    crs = 4326
)

gdf.to_crs(3857).plot()
plt.show()

gdf.to_file(
    r'C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\EO_NYC_Filter.geojson',
    driver = "GeoJSON",
    encoding = 'utf-8'
)




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
remove = 'FOUNDATION,ORGANIZATION,STATUS,NTEE_CD,COUNTY,def1,def2,def3,act1,act2,act3,ASSET_AMT,INCOME_AMT,REVENUE_AMT,RULING,DEDUCTIBILITY,EIN'.split(",")
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

gdf['Stew_Gr'] = 0
gdf = gdf.drop( ['GROUP','SUBSECTION','AFFILIATION','CLASSIFICATION','ACTIVITY','ZIP_Short'] , axis=1 )
gdf.to_crs(3857).plot()
plt.show()

gdf.to_file(
    r'C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\EO_NYS_Filter.geojson',
    driver = "GeoJSON",
    encoding = 'utf-8'
)

# %% 
# Format Datasets for merging. 
# NAME, STREET, STATE, ZIP, OrgFocus, address, lat, lon

# POINT_X	POINT_Y -> in 2263
# From990s -> Y, originates from here.

#st is Public Stew-Map public
st = gpd.read_file( r"C:\Users\csucuogl\Desktop\DATA\NYC2017_STEWMAP\NYC2017_STEWMAP_Points_Public.shp" )
st = st[[ #Simplify Stew Map
    'OrgName',
    'OrgCity',
    'From990s',
    'OrgStreet1',
    'OrgState',
    'OrgZip',
    'PrimFocus',
    'PopID',
    'geometry']]

# Format columns names in 990s
gdf.columns = gdf.columns.str.replace('STREET','OrgStreet1')
gdf.columns = gdf.columns.str.replace('STATE','OrgState')
gdf.columns = gdf.columns.str.replace('ZIP','OrgZip')
gdf.columns = gdf.columns.str.replace('NAME','OrgName')
gdf.columns = gdf.columns.str.replace('OrgFocus','PrimFocus')
gdf['OrgCity'] = gdf['address'].str.split(', ').str[1]

st = st.to_crs(4326)
st['lon'] = st.geometry.x
st['lat'] = st.geometry.y
st['OrgName'] = st['OrgName'].str.upper()
st['Stew_Gr'] = 1

display( st.head(3) )
display( gdf.head(3) )

#%%
# Merge in the StewMap Data. 
# match_name contains the matched string
# st[ st['From990s'] == "Y"] -> 212 Enteries in total. Currently 150~ matches

# 1 Find exact matches
exact = st[ st['OrgName'].isin( gdf['OrgName'])]
exact['match_name'] = exact['OrgName']

# 2 If the 990 name is contained in Stew-MAP
partial = gpd.GeoDataFrame()
remain = gdf[ ~gdf['OrgName'].isin( exact['match_name'])].copy()

st = st[ ~st['OrgName'].isnull() ]
for i,r in remain.iterrows():
    t = st[st['OrgName'].str.contains( r['OrgName'] )].copy()
    if len( t ) == 1: # if there is a contained entery
        t['match_name'] = r['OrgName'] 
        partial = partial.append( t )

# 3 If the Stew-Map name is contained in 990
partial2 = gpd.GeoDataFrame()
for i,r in st.iterrows():
    try: 
        t = gdf[ gdf['OrgName'].str.contains(r['OrgName']) ].copy()
        if len( t ) == 1:
            t['match_name'] = t['OrgName'] 
            partial2 = partial2.append( t )
    except:
        print( "{} is broken".format(r['OrgName']) )

#Merge all these together.
matches = exact.append(partial)
matches = matches.append( partial2)
matches = matches.drop('address',axis = 1)
matches = matches.drop_duplicates(subset=['OrgName','OrgStreet1'])
matches

#%%
# Combine all seperated datasets 
matches['Stew_Gr'] = 1 #These are stated as coming from Stew-MAP data

gdf_f = gdf[ ~gdf['OrgName'].isin( matches['match_name'] ) ]
st_f = st[ ~st['OrgName'].isin( matches['match_name'] ) ]

print( len(matches) , len(gdf) , len(st) )
print( len(matches) , len(gdf_f) , len(st_f) )

combined = gdf_f.append( st_f )
combined = combined.append( matches )
combined = combined.drop(['address','match_name','From990s','PopID'],axis = 1)

combined.head()

#%%
# Use Lev distance to find similar enteries.
# There are extra points and commas

from Levenshtein import distance

not_st = combined[ combined['Stew_Gr'] == 0 ].copy()

p_mat = gpd.GeoDataFrame()
for i,r in not_st.iterrows():
    st1 = st.copy()
    #Apply Lev dist to everything in the database
    st1['score'] = st1['OrgName'].apply( lambda x: distance(x,r['OrgName']) )
    st1['match_name'] = r['OrgName']
    st1 = st1[ st1['score'] < 4 ]
    if len( st1 ) > 0:
        print( count , st1['OrgName'].values , r['OrgName'] ,'---' ,st1['score'].values )
        if st1['OrgName'].values[0] != 'KENT CONSERVATION FOUNDATION': #This is not matching
            p_mat = p_mat.append( st1 )
p_mat['Stew_Gr'] = 1 #from Stew-MAP
p_mat

#%%
#Combine lev dist similar results to the dataset
t = combined[ ~combined['OrgName'].isin( p_mat['OrgName']) ]
t = t.append( p_mat.drop(['From990s','PopID','score','match_name'],axis=1) )
t

#%%
# Geometry is not working really. 
# Clean up a few things here
t1 = t.drop(['geometry'],axis=1)
t1 = t1[ t1['OrgName'] != 'CORNELL UNIVERSITY RESEARCH' ]

#%%
# new geodataframe
geos = gpd.GeoDataFrame(
    t1,
    geometry=gpd.points_from_xy( t1['lon'],t1['lat'] ),
    crs = 4326
)

geos.plot()
plt.show()

#%%
# Export Data
geos.to_file(
    r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\EO_NY_MSA_Filter.geojson",
    driver='GeoJSON',
    encoding='utf-8'
)
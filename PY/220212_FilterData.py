

"""
Filter and clean tax returns from Non Profits.
Filters by location using Zipcodes
Filters by location using Activity,etc codes
3 related fields: DILA, Activity code, and NTEE codes are used for class
"""

#%% Import NYC 990 filings
#Here is the download location: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
#Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

import pandas as pd
pd.set_option("max_columns",None)
df = pd.read_csv(r"C:\Users\csucuogl\Documents\GitHub\STEW_EO_Extract\DATA\eo_ny.csv")

remove = ['ICO','TAX_PERIOD','ASSET_CD','INCOME_CD','FILING_REQ_CD','PF_FILING_REQ_CD','ACCT_PD','SORT_NAME']
df = df.drop( remove, axis = 1)
df = df.dropna(how='all',axis =1)
df['ZIP_Short'] = [r.split("-")[0] for i,r in df['ZIP'].iteritems()]

df = df.drop_duplicates(subset=['EIN'],keep='first')

print( "{} groups are in the list".format(len(df)) )
df.head()
# %% Bring in NYC Zipcodes and filter Returns 

import geopandas as gpd
zips = gpd.read_file( r"C:\Users\csucuogl\Desktop\DATA\NYC\ZIP_CODE_040114\ZIP_CODE_040114.shp")
zips = zips[['ZIPCODE','PO_NAME','COUNTY']]
zips = zips.drop_duplicates(keep='first')
zips.head()

df = df[ df["ZIP_Short"].isin( zips['ZIPCODE'] )]
df = df.join(zips.set_index("ZIPCODE"),on="ZIP_Short")

print( "{} groups are in the list".format(len(df)) )
df.head()

#%%
# ACTIVITY Activity Codes
# NTEE_CD National Taxonomy of Exempt Entities (NTEE) Code
# Filter OR

ntee1 = 'C01,C02,C03,C05,C11,C12,C19,C20,C27,C30,C32,C34,C35,C36,C40,C41,C42,C50,C60'.split(",")
ntee2 = 'D01,D02,D05,D03,D20,D30,D31,D32,D33,D34,D50,D60,D99'.split(',')
ntee = ntee1 + ntee2

activity = '350,351,352,353,354,402,355,356,379,230,231,232,233,234,235,404,296,297,325,324,400,524,900,903,923'.split(',')

df['ACTIVITY'] = df['ACTIVITY'].astype(str)
df1 = df[ (df['NTEE_CD'].isin(ntee)) | (df['ACTIVITY'].str.contains( "|".join(activity) ) )]

print( "{} groups are in the list".format(len(df1)) )
df1.head()


# %% GEOCODE
# 1. If PO BOX, use the zipcode geos
# 2. If not, how to deal with Apt Nos and Floor Levels. 
#To use zipcode shape file, dissovlde geos by zipcode. 

zips = gpd.read_file( r"C:\Users\csucuogl\Desktop\DATA\NYC\ZIP_CODE_040114\ZIP_CODE_040114.shp")
zips = zips.dissolve(by='ZIPCODE')
zips.head(10)

# %%

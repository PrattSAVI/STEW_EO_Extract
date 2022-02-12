# STEW_EO_Extract
Code and Data to Extract info from Statewide EO data

Data source: https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf
Data Dictionary: https://www.irs.gov/pub/irs-soi/eo_info.pdf

NTEE Codes: 
ntee1 = 'C01,C02,C03,C05,C11,C12,C19,C20,C27,C30,C32,C34,C35,C36,C40,C41,C42,C50,C60'
ntee2 = 'D01,D02,D05,D03,D20,D30,D31,D32,D33,D34,D50,D60,D99'

Activity Codes: (Formating has issues, might return some bad results)
activity = '350,351,352,353,354,402,355,356,379,230,231,232,233,234,235,404,296,297,325,324,400,524,900,903,923'.split(',')

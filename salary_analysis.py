#!/usr/bin/env python
# coding: utf-8

# # Import req libraries

# In[ ]:


import pandas as pd
import glob
import datetime
from matplotlib import pyplot as plt
import tabula as tb


# # Dolar histórico

# In[ ]:


# Search for "dolar histórico" in a website
dolar_historico = pd.read_html('http://estudiodelamo.com/cotizacion-historica-dolar-peso-argentina/')

# dolar_historico from pandas method read_html will be a list with several dataframes.
# We want to keep the 2nd element of the list, which is the desired df
dolar_blue_df = dolar_historico[1]

dolar_blue_df.tail()


# In[ ]:


# Create column names for dolar_blue_df, fix dtypes and drop null values

cols = ['Year', 'drop', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
dolar_blue_df.columns = cols
dolar_blue_df.drop(columns='drop', inplace=True)
dolar_blue_df.Year = dolar_blue_df.Year.astype(str)

# Melt df to unpivot df from wide to long format

dolar_blue_df = dolar_blue_df.melt(id_vars='Year', var_name='Month', value_name='exchange_rate')
dolar_blue_df.dropna(inplace=True)

# Fix $xxx,yy format to xxx.yy where x,y = numbers

dolar_blue_df['exchange_rate'] = dolar_blue_df['exchange_rate'].apply(lambda x: float(x[1:].replace(',','.')))

# Check it's not missing latest values

dolar_blue_df[dolar_blue_df['Year'] == '2022'].head()


# # Salary files

# In[ ]:


files_list = glob.glob("recibos/*")
payroll_list = [tb.read_pdf_with_template(
                file
                , pages='1'
                , template_path='recibo-short-table.json') for file in files_list]

# payroll_list will return a list of dataframes
# payroll_list[i][0]['Fecha liquidación'] = 'dd-mm-yy'
# payroll_list[i][0]['Categoría'][3] = 'xxx,yy'

salary_df = pd.DataFrame({'Year' : [payroll_list[i][0]['Fecha liquidación'][1][-4:] for i, v in enumerate(payroll_list)]
                , 'Month': [payroll_list[i][0]['Fecha liquidación'][1][3:5] for i, v in enumerate(payroll_list)]
                , 'Salary_ARS' : [float(payroll_list[i][0]['Categoría'][3][-10:-3])*1000 for i, v in enumerate(payroll_list)]}
                , index=[i for i, v in enumerate(payroll_list)])

salary_df.head()


# ##### Merge 'salary_df' and 'dolar_blue_df' into one 'df'

# In[ ]:


df = pd.merge(left=salary_df, right=dolar_blue_df, on=['Year', 'Month'], how='left')
df.head()


# In[ ]:


new_date_format='%Y%m'
old_date_format='%Y%m'
col = "fecha"

df["YearMonth"] = df['Year'] + df['Month']
df["YearMonth"] = pd.to_datetime(df["YearMonth"], format=old_date_format).dt.strftime(new_date_format)

df.head()


# Working on the USD Salary and adjustement for inflation

# In[ ]:


df['Salary_USD'] = df['Salary_ARS']/df['exchange_rate']

df = df.sort_values(by='YearMonth', ascending=True)

monthly_working_hours = 160

df['Hourly_rate'] = df['Salary_USD']/monthly_working_hours

df.head()


# ##### Create inflation df

# In[ ]:


inflation_df = pd.read_excel('https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_aperturas.xls', header=5, nrows=3, index_col='Región GBA')
inflation_df.dropna(inplace=True)
inflation_df = inflation_df.transpose()
inflation_df = inflation_df.reset_index()
inflation_df.columns = ['Date', 'Inflation_pct']
new_date_format='%Y%m'
old_date_format='%Y-%m-%d'

inflation_df["YearMonth"] = pd.to_datetime(inflation_df["Date"], format=old_date_format).dt.strftime(new_date_format)
inflation_df = inflation_df[['YearMonth', 'Inflation_pct']]
inflation_df.head()


# In[ ]:


df = df.merge(inflation_df, on='YearMonth')

# Calculate accumulated
acumular = 0
inflation_accumulated = []
for index, row in df.iterrows():
    acumular+=row['Inflation_pct']
    inflation_accumulated.append(acumular)

inflation_accumulated = [round(i/100,3) for i in inflation_accumulated]

df['Inflation_accum'] = inflation_accumulated

df.head()


# In[ ]:


df['Salary_ARS_Real'] = round(df['Salary_ARS']*(1 - df['Inflation_accum']),0)

df.head()


# Plot and export:
# ---
# * USD salary evolution plot
# * Salary adjusted for inflation plot
# * Dataframe

# In[ ]:


plt.figure(figsize=(12,5))
plt.title("Salario USD en el tiempo")
plt.axhline(y=df['Salary_USD'].min(), color='r', linestyle='-')
plt.axhline(y=df['Salary_USD'].max(), color='r', linestyle='-')
plt.axhline(y=df['Salary_USD'].mean(), color='g', linestyle='-')

x = df['YearMonth']
y = df['Salary_USD']

mark0 = [(row['YearMonth'], row['Salary_USD']) for index, row in df.iterrows() if row['Salary_USD'] <= df['Salary_USD'].mean()]

x0 = [i[0] for i in mark0]
y0 = [i[1] for i in mark0]

mark1 = [(row['YearMonth'], row['Salary_USD']) for index, row in df.iterrows() if row['Salary_USD'] > df['Salary_USD'].mean()]

x1 = [i[0] for i in mark1]
y1 = [i[1] for i in mark1]

plt.plot(x, y, color='blue')
plt.scatter(x0, y0, marker='x', color='r')
plt.scatter(x1, y1, marker='o', color='g')

plt.savefig('report/salary_usd.jpeg')
plt.show()


# Plot Salary adjusted for Inflation

# In[ ]:


plt.figure(figsize=(12,5))
plt.title("Salario real en pesos ajustado por inflacion")
plt.plot('YearMonth', 'Salary_ARS_Real', data=df)

if (len(glob.glob('/report/salary_ars_adjusted_for_inflation.jpeg')) == 0):
    plt.savefig('report/salary_ars_adjusted_for_inflation.jpeg')
    print('fig saved')


# In[ ]:


df.to_csv('report/salary_analysis.csv', index=False)


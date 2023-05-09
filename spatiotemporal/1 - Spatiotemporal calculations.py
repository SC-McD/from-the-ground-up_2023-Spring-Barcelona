#!/usr/bin/env python
# coding: utf-8

# In[1]:


from bw_temporalis import TemporalDistribution as TD, TemporalisLCA, Timeline
import bw2data as bd
import bw2calc as bc
import bw_temporalis as bwt
import numpy as np
import pandas as pd
from functools import partial
import bw2regional as bwr
from bw_graph_tools import NewNodeEachVisitGraphTraversal as GraphTraversal
from functools import partial


# In[2]:


PROJECT_NAME = "Spain case study spatiotemporal"


# In[3]:


bd.projects.set_current(PROJECT_NAME)


#%% ADD TEMPORAL INFORMATION TO EACH EXCHANGE


meal = bd.get_node(name="meal")

for x in meal.exchanges():
    length = np.random.randint(1, 100)
    DATE = np.linspace(-50, 50, length, dtype="timedelta64[Y]", endpoint=True)
    AMOUNT = np.around(np.random.uniform(low=0.0, high=200.0, size=length), decimals=2)
    x["temporal_distribution"] = TD(date=DATE, amount=AMOUNT)
    x.save()

meal.save()

for x in meal.exchanges():
    td = x["temporal_distribution"]
    print(x)
    print("\t", td)



# In[5]:


def combine_xts(xts: list, label: str):
    data = [elem for xt in xts for elem in bwr.ExtensionTable(xt).load()]

    geocollections = list({bwr.extension_tables[xt]['geocollection'] for xt in xts})
    new_ext = bwr.ExtensionTable(label)
    new_ext.register(geocollections=geocollections)
    new_ext.write(data)

# for xt in xts:
#     print("****" ,xt, "\n")
#     XT = bwr.extension_tables[xt]
#     for k,v in XT.items(): 
#         print(k, ":", v, "\n")

# In[6]:


CROPS = ['cereals', 'citrus', 'potatoe', 'rice']


# In[7]:


for crop in CROPS:
    xts = [xt for xt in bwr.extension_tables if crop in xt and "xt" not in xt]
    combine_xts(xts, f"{crop}-xt-all")


# In[8]:

def characterization_matrix_for_regionalized_lca(lca):
    return (
        lca.inv_mapping_matrix
        * lca.distribution_normalization_matrix
        * lca.distribution_matrix
        * lca.xtable_matrix
        * lca.geo_transform_normalization_matrix
        * lca.geo_transform_matrix
        * lca.reg_cf_matrix
    ).T

# In[9]:


matrix_dict = {}

for crop in CROPS:
    for month in range(1, 13):
        lca = bwr.ExtensionTablesLCA(
            demand={meal: 1},
            method=("Monthly water stress", str(month)),
            xtable=f'{crop}-xt-all'
        )
        lca.lci()
        lca.lcia() 
        matrix_dict[(crop, month)] = characterization_matrix_for_regionalized_lca(lca)


# In[10]:


def characterize_water(
    series,
    lca,
    matrix_dict,
    crop
) -> pd.DataFrame:
    amount = matrix_dict[
        (crop, series.date.month)
    ][
        lca.dicts.biosphere[series.flow], 
        lca.dicts.activity[series.activity]
    ] * series.amount
    return pd.DataFrame(
        {
            "date": [series.date],
            "amount": [amount],
            "flow": [series.flow],
            "activity": [series.activity],
        }
    )


# In[11]:


characterize_water_generic = partial(characterize_water, lca=lca, matrix_dict=matrix_dict)


# In[12]:


class RegionalizedGraphTraversal(GraphTraversal):
    @classmethod
    def get_characterized_biosphere(cls, lca: bc.LCA):
        return characterization_matrix_for_regionalized_lca(lca).multiply(lca.biosphere_matrix)


# In[13]:


CROP = "cereals"


# In[14]:



lca = bwr.ExtensionTablesLCA(
    demand={meal: 1},
    method=("Monthly water stress", "Average"),
    xtable=f'{crop}-xt-all'
)
lca.lci()
lca.lcia()


# In[15]:


tlca = TemporalisLCA(lca, graph_traversal=RegionalizedGraphTraversal)


# In[ ]:





# In[16]:


tl = tlca.build_timeline()

#%%

# for o in tl.data:
#     #print(o.distribution[1])
#     print(len(o.distribution[0]))
#     print(o.flow)
#     print(o.activity)
#     print("\n")

# In[17]:


tl.build_dataframe()


# In[ ]:


tl.df.plot(x="date", y="amount", kind="scatter")


# In[ ]:


characterize_water_specific = partial(characterize_water_generic, crop=CROP)


# In[ ]:


characterized_df = tl.characterize_dataframe(
    characterization_function=characterize_water_specific, 
    cumsum=True
)


# In[ ]:


characterized_df.plot(x="date", y="amount_sum")


# In[ ]:





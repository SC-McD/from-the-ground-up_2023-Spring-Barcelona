#!/usr/bin/env python
# coding: utf-8

# In[1]:


import bw2data as bd
import bw2regional as bwr
from bw_temporalis import TemporalDistribution as TD
import numpy as bp
from pathlib import Path
import fiona
import numpy as np
import os


# In[2]:


PROJECT_NAME = "Spain case study spatiotemporal"


# In[3]:


RESET = True


# In[4]:


if PROJECT_NAME in bd.projects and RESET:
    bd.projects.delete_project(PROJECT_NAME, True) 


# In[5]:


bd.projects.set_current(PROJECT_NAME)


# In[6]:


reg_data_dir = (Path.home() / "code/gh/from-the-ground-up_2023-Spring-Barcelona" / "regionalization" / "data").absolute()
assert reg_data_dir.is_dir()


# In[ ]:





# In[7]:


data_dir = (Path.home() / "code/gh/from-the-ground-up_2023-Spring-Barcelona" / "spatiotemporal" / "data").absolute()
assert data_dir.is_dir()


# Tell `bw2regional` about our maps.

# Data from Natural Earth Data. Needed to create another column named `city_id` with a string data type.

# In[8]:


bwr.geocollections['cities'] = {
    'filepath': str(reg_data_dir / 'cities.gpkg'),
    'field': 'city_id',
}


# In[9]:


bwr.geocollections['regions'] = {
    'filepath': str(reg_data_dir / 'regions.gpkg'),
    'field': 'name',
}


# In[10]:


bwr.geocollections['countries'] = {
    'filepath': str(reg_data_dir / 'countries.gpkg'),
    'field': 'NAME',
}


# In[11]:


bwr.geocollections['WaterGap'] = {
    'filepath': str(data_dir / 'wsi_annual_spain.gpkg'),
    'field': 'basin_id',
}


# Data from [Estimation of spatial distribution of irrigated crop areas in Europe for large-scale modelling applications](https://www.sciencedirect.com/science/article/pii/S0378377422000749?via%3Dihub#sec0060), via [Agri4Cast](https://agri4cast.jrc.ec.europa.eu/DataPortal/Index.aspx?o=).
# 
# Data also [available here](https://files.brightway.dev/europe_irrigated.gpkg).
# 
# GDAL commands to extract and process the rasters:
# 
# ```bash
# gdal_rasterize -a IR_citrus -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg citrus.p.tiff
# gdal_rasterize -a IR_potatoe -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg potatoe.p.tiff
# gdal_rasterize -a IR_rice -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg rice.p.tiff
# gdal_rasterize -a IR_cereals -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg cereals.p.tiff
# 
# gdalwarp -t_srs EPSG:4326 rice.p.tiff rice.tiff
# gdalwarp -t_srs EPSG:4326 potatoe.p.tiff potatoe.tiff
# gdalwarp -t_srs EPSG:4326 cereals.p.tiff cereals.tiff
# gdalwarp -t_srs EPSG:4326 citrus.p.tiff citrus.tiff
# ```

# In[12]:


CROPS = ['cereals', 'citrus', 'rice', 'potatoe']


# In[13]:
,

for crop in CROPS:
    bwr.geocollections[crop] = {'filepath': str(reg_data_dir / f'{crop}.tiff'), 'nodata': -999}


# In[14]:


bio = bd.Database("biosphere")
bio.register()


# In[15]:


water = bio.new_node(
    code="water",
    name="water",
    type="emission",
)
water.save()


# In[16]:


co2 = bio.new_node(
    code="co2",
    name="co2",
    type="emission",
)
co2.save()


# In[17]:


ch4 = bio.new_node(
    code="ch4",
    name="ch4",
    type="emission",
)
ch4.save()


# In[18]:


bio.set_geocollections()


# Just in case things go wrong later :)

# In[19]:


food = bd.Database("food")
food.register()


# In[20]:


lemon = food.new_node(
    code="lemon",
    name="lemon",
    location=('regions', 'Granada')
)
lemon.save()
lemon.new_edge(
    input=water,
    amount=5,
    type="biosphere",
    temporal_distribution=TD(
        np.array([-3, -2, -1, 0, 1], dtype="timedelta64[Y]"),
        np.ones(5)
    )
).save()
lemon.new_edge(
    input=co2,
    amount=0.2,
    type="biosphere",
    temporal_distribution=TD(
        np.array([-1, 0, 1], dtype="timedelta64[M]"),
        np.ones(3) * 2/3
    )
).save()


# In[21]:


mushroom = food.new_node(
    code="mushroom",
    name="mushroom",
    location=('countries', 'Portugal')
)
mushroom.save()
mushroom.new_edge(
    input=water,
    amount=0.5,
    type="biosphere",
    temporal_distribution=TD(
        np.array([-3, -2, -1], dtype="timedelta64[M]"),
        np.ones(3) * 0.5
    )    
).save()
mushroom.new_edge(
    input=ch4,
    amount=0.05,
    type="biosphere",
    temporal_distribution=TD(
        np.array([-3, -2, -1, 0], dtype="timedelta64[M]"),
        np.ones(4) * 0.0125
    )    
).save()


# In[22]:


cheese = food.new_node(
    code="cheese",
    name="cheese",
    location=('countries', 'Spain')
)
cheese.save()
cheese.new_edge(
    input=water,
    amount=25,
    type="biosphere",
    temporal_distribution=TD(
        np.linspace(-90, -10, 10).astype("timedelta64[D]"),
        np.ones(10) * 10/25
    )    
).save()


# In[23]:


rice = food.new_node(
    code="rice",
    name="rice",
    location=('regions', 'Valencia')
)
rice.save()
rice.new_edge(
    input=water,
    amount=10,
    type="biosphere",
).save()


# In[24]:


meal = food.new_node(
    code="meal",
    name="meal",
    location=('cities', '14')
)
meal.save()
meal.new_edge(
    input=water,
    amount=0.5,
    type="biosphere",
).save()
meal.new_edge(
    input=lemon,
    amount=0.25,
    type="technosphere",
).save()
meal.new_edge(
    input=rice,
    amount=1,
    type="technosphere",
).save()
meal.new_edge(
    input=mushroom,
    amount=0.5,
    type="technosphere",
).save()
meal.new_edge(
    input=cheese,
    amount=0.1,
    type="technosphere",
).save()


# In[25]:


meal = bd.get_node(name="meal")


# In[26]:


food.set_geocollections()


# See notebook X for details on the LCIA method

# In[27]:


# From https://www.sciencedirect.com/science/article/abs/pii/S0959652613007956
GLOBAL_CF = 0.44


# In[28]:


water_flows = [(bd.get_node(name="water"), 1)]


# In[29]:


def gpkg_reader(column):
    with fiona.Env():
        with fiona.open(data_dir / 'wsi_annual_spain.gpkg') as src:
            for feat in src:
                for obj, sign in water_flows:
                    yield (
                        obj.key,
                        feat["properties"][column]
                        * sign,  # Convert km3 to m3
                        ('WaterGap', feat["properties"]["basin_id"]),
                    )    


# In[30]:


water_stress = bd.Method(("Monthly water stress", "Site-generic"))
water_stress.register(geocollections=["WaterGap"])
water_stress.write([(water.key, GLOBAL_CF)])


# In[31]:


water_stress = bd.Method(("Monthly water stress", "Average"))
water_stress.register(geocollections=["WaterGap"])
water_stress.write(
    list(gpkg_reader('mean'))
)


# In[32]:


for month in range(1, 13):
    water_stress = bd.Method(("Monthly water stress", str(month)))
    water_stress.register(geocollections=["WaterGap"])
    water_stress.write(
        list(gpkg_reader(f'WSI_{month:02}'))
    )


# In[33]:


bwr.calculate_needed_intersections({meal: 1}, ("Monthly water stress", "Average"))


# In[34]:


inventory_geocollections = [
    'countries',
    'cities',
    'regions',
]


# In[35]:


for gc in inventory_geocollections:
    if f'{gc}-WaterGap' not in bwr.geocollections:
        bwr.remote.calculate_intersection(gc, 'WaterGap')


# In[36]:


for gc in inventory_geocollections:
    if f'{gc}-watergap' not in bwr.geocollections:
        bwr.remote.intersection_as_new_geocollection(gc, 'WaterGap', f'{gc}-WaterGap')


# In[ ]:


bwr.geocollections['popdensity'] = {'filepath': str(reg_data_dir / 'gpw_v4_population_density.tif')}


# In[ ]:


CROPS = ['cereals', 'citrus', 'rice', 'potatoe']


# In[ ]:


for crop in CROPS:
    for gc in inventory_geocollections:
        if f'{gc}-WaterGap - {crop}' not in bwr.extension_tables:
            bwr.raster_as_extension_table(f'{gc}-WaterGap', crop, engine='rasterstats')


# In[ ]:


for xt in bwr.extension_tables:
    bwr.calculate_needed_intersections({meal: 1}, ("Monthly water stress", "Average"), xt)


# %%

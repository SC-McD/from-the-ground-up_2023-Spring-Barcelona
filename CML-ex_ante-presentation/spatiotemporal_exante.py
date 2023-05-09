#!/usr/bin/env python
# coding: utf-8

#%% [1]: IMPORTS
import bw2data as bd
import bw2regional as bwr
from bw_temporalis import TemporalDistribution as TD

import numpy as bp
from pathlib import Path
import fiona
import numpy as np
import os

# for making a PFD of the inventory



# for processing the LCIA map
from bs4 import BeautifulSoup
from shapely.geometry import shape, mapping



# for the temporal calculations
from bw_temporalis import TemporalDistribution as TD, TemporalisLCA, Timeline
import bw2data as bd
import bw2calc as bc
import bw_temporalis as bwt
import numpy as np
import pandas as pd
from functools import partial
import bw2regional as bwr
from bw_graph_tools import NewNodeEachVisitGraphTraversal as GraphTraversal # bug workaround
from functools import partial

#%% [2]: SETUP PROJECT AND DIRS
PROJECT_NAME = "Spain case study spatiotemporal"
RESET = True
if PROJECT_NAME in bd.projects and RESET:
    bd.projects.delete_project(PROJECT_NAME, True) 

bd.projects.set_current(PROJECT_NAME)

# change these to match your paths
reg_data_dir = (Path.home() / "code/gh/from-the-ground-up_2023-Spring-Barcelona" / "regionalization" / "data").absolute()
assert reg_data_dir.is_dir()

data_dir = (Path.home() / "code/gh/from-the-ground-up_2023-Spring-Barcelona" / "spatiotemporal" / "data").absolute()
assert data_dir.is_dir()

#%% [3]: ESTABLISH GEOCOLLECTIONS

# Tell `bw2regional` about our maps.
# Data from Natural Earth Data. Needed to create another column named `city_id` with a string data type.

bwr.geocollections['cities'] = {
    'filepath': str(reg_data_dir / 'cities.gpkg'),
    'field': 'city_id',
}

bwr.geocollections['regions'] = {
    'filepath': str(reg_data_dir / 'regions.gpkg'),
    'field': 'name',
}

bwr.geocollections['countries'] = {
    'filepath': str(reg_data_dir / 'countries.gpkg'),
    'field': 'NAME',
}


bwr.geocollections['WaterGap'] = {
    'filepath': str(data_dir / 'wsi_annual_spain.gpkg'),
    'field': 'basin_id',
}

#%%  EXAMPLE OF HOW TO RASTERIZE THE GEOSPATIAL DATA
""" 
Data from [Estimation of spatial distribution of irrigated crop areas in Europe for large-scale modelling applications]

(https://www.sciencedirect.com/science/article/pii/S0378377422000749?via%3Dihub#sec0060), 

via [Agri4Cast](https://agri4cast.jrc.ec.europa.eu/DataPortal/Index.aspx?o=).

Data also [available here](https://files.brightway.dev/europe_irrigated.gpkg).

GDAL commands to extract and process the rasters:

```bash
gdal_rasterize -a IR_citrus -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg citrus.p.tiff
gdal_rasterize -a IR_potatoe -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg potatoe.p.tiff
gdal_rasterize -a IR_rice -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg rice.p.tiff
gdal_rasterize -a IR_cereals -init -999 -a_nodata -999 -ts 400 400 -of GTIFF irrigation.gpkg cereals.p.tiff

gdalwarp -t_srs EPSG:4326 rice.p.tiff rice.tiff
gdalwarp -t_srs EPSG:4326 potatoe.p.tiff potatoe.tiff
gdalwarp -t_srs EPSG:4326 cereals.p.tiff cereals.tiff
gdalwarp -t_srs EPSG:4326 citrus.p.tiff citrus.tiff
``` 
"""

CROPS = ['cereals', 'citrus', 'rice', 'potatoe']

for crop in CROPS:
    bwr.geocollections[crop] = {'filepath': str(reg_data_dir / f'{crop}.tiff'), 'nodata': -999}

#%% [4]: SETUP DATABASES

# biosphere with only water

bio = bd.Database("biosphere")
bio.register()

water = bio.new_node(
    code="water",
    name="water",
    type="emission",
)
water.save()

# technosphere with only rice and a meal
food = bd.Database("food")
food.register()

rice_Valencia = food.new_node(
    code="rice_Valencia",
    name="rice_Valencia",
    location=('regions', 'Valencia')
)
rice_Valencia.save()
rice_Valencia.new_edge(
    input=water,
    amount=12,
    type="biosphere",
    temporal_distribution=TD(
        amount=np.ones(12),
        date=np.linspace(0, 12, 12, dtype="timedelta64[M]", endpoint=False))
).save()

# make one in a different region
rice_Coimbra = food.new_node(
    code="rice_Coimbra",
    name="rice_Coimbra",
    location=('regions', 'Coimbra')
)
rice_Coimbra.save()

rice_Coimbra.new_edge(
    input=water,
    amount=12,
    type="biosphere",
    temporal_distribution=TD(
        amount=np.ones(12) ,
        date=np.linspace(0, 12, 12, dtype="timedelta64[M]", endpoint=False))
).save()


#%% [5]: SETUP A MEAL OF RICE AND WATER

meal_Valencia = food.new_node(
    code="meal_Valencia",
    name="meal_Valencia",
    location=('cities', '14')
)
meal_Valencia.save()
meal_Valencia.new_edge(
    input=water,
    amount=0.5,
    type="biosphere",
).save()
meal_Valencia.new_edge(
    input=rice_Valencia,
    amount=0.5,
    type="technosphere",
).save()

meal_Valencia = bd.get_node(name="meal_Valencia")

meal_Coimbra = food.new_node(
    code="meal_Coimbra",
    name="meal_Coimbra",
    location=('cities', '14')
)
meal_Coimbra.save()
meal_Coimbra.new_edge(
    input=water,
    amount=0.5,
    type="biosphere",
).save()
meal_Coimbra.new_edge(
    input=rice_Coimbra,
    amount=0.5,
    type="technosphere",
).save()
meal_Coimbra = bd.get_node(name="meal_Coimbra")

#%% [6] Set the geocollections for the databases

bio.set_geocollections()
food.set_geocollections()

#%% [7] PROCESS LCIA MAP
# # From https://www.sciencedirect.com/science/article/abs/pii/S0959652613007956

# GLOBAL_CF = 0.44  # end result

# # Change some column labels and filter out some columns
# def try_number(x):
#     try:
#         if "." in x:
#             return float(x)
#         else:
#             return int(x)
#     except:
#         return x


# remapping = {
#     'Wweigh_mWSI': "mean",
#     'WSI_01': 'WSI_01',
#     'WSI_02': 'WSI_02',
#     'WSI_03': 'WSI_03',
#     'WSI_04': 'WSI_04',
#     'WSI_05': 'WSI_05',
#     'WSI_06': 'WSI_06',
#     'WSI_07': 'WSI_07',
#     'WSI_08': 'WSI_08',
#     'WSI_09': 'WSI_09',
#     'WSI_10': 'WSI_10',
#     'WSI_11': 'WSI_11',
#     'WSI_12': 'WSI_12',
# }

# # Basin IDs are not unique, as there are somehow more than 10.000 `MultiPolygon` geometries (non-contiguous watersheds?).
# class BasinCounter:
#     def __init__(self):
#         self.data = {}

#     def __getitem__(self, key):
#         try:
#             _, index = self.data[key]
#             index += 1
#         except KeyError:
#             index = 1
#         self.data[key] = (key, index)
#         return f"{key}-{index}"

# bc = BasinCounter()

# # Data is stored inside an attribute called `description`, which is HTML (!). Even better, the data is inside a table inside another table in that HTML (!!).

# def parse_table(s):
#     return dict([
#         [try_number(td.string) for td in row.find_all("td")]
#         for row in s.table.table.find_all("tr")
#     ])

# def set_attributes_from_table(feat, description):
#     s = BeautifulSoup(description)
#     for key, value in parse_table(s).items():
#         try:
#             if key == "BAS34S_ID":
#                 value = bc[value]
#             feat['properties'][remapping[key]] = value
#         except KeyError:
#             pass
#     return feat

# # Finally ready to write the new GeoPackage
# yuck = '/home/stew/code/gh/from-the-ground-up_2023-Spring-Barcelona/spatiotemporal/data/wsi_annual_yuck.gpkg'

# with fiona.open(yuck) as src:
#     crs = src.crs
#     schema = {
#         'geometry': 'Polygon',
#         'properties': {
#             'mean': "float",
#             'basin_id': "str",
#             'WSI_01': 'float',
#             'WSI_02': 'float',
#             'WSI_03': 'float',
#             'WSI_04': 'float',
#             'WSI_05': 'float',
#             'WSI_06': 'float',
#             'WSI_07': 'float',
#             'WSI_08': 'float',
#             'WSI_09': 'float',
#             'WSI_10': 'float',
#             'WSI_11': 'float',
#             'WSI_12': 'float',
#         }
#     }

# wsi = '/home/stew/code/gh/from-the-ground-up_2023-Spring-Barcelona/spatiotemporal/data/wsi_annual.gpkg'

# with fiona.open(wsi, "w", driver="GPKG", 
#                 crs=crs, schema=schema) as dst:
#     for feat_orig in src:
#         if feat_orig.geometry['type'] == 'MultiPolygon':
#             # Unroll MultiPolygon to Polygon
#             geom = shape(feat_orig.geometry)
#             for polygon in shape(feat_orig.geometry).geoms:
#                 feat = {'geometry': mapping(polygon), 'properties': {}}
#                 set_attributes_from_table(feat, feat_orig.properties['description'])
#                 dst.write(feat)
#         else:
#             feat = {'geometry': feat_orig['geometry'], 'properties': {}}
#             set_attributes_from_table(feat, feat_orig.properties['description'])
#             dst.write(feat)





#%% [8]: WRITE LCIA METHODS

GLOBAL_CF = 0.44  # end result from processing the maps

water_flows = [(bd.get_node(name="water"), 1)]

# function to read the data from the geopackage
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

# Write a method for the site-generic water stress
water_stress = bd.Method(("Monthly water stress", "Site-generic"))
water_stress.register(geocollections=["WaterGap"])
water_stress.write([(water.key, GLOBAL_CF)])

# Write a method for the mean water stress
water_stress = bd.Method(("Monthly water stress", "Average"))
water_stress.register(geocollections=["WaterGap"])
water_stress.write(
    list(gpkg_reader('mean'))
)

# Write a method specific for each month
for month in range(1, 13):
    water_stress = bd.Method(("Monthly water stress", str(month)))
    water_stress.register(geocollections=["WaterGap"])
    water_stress.write(
        list(gpkg_reader(f'WSI_{month:02}'))
    )

#%% [9]: CALCULATE INTERSECTIONS

meal = meal_Coimbra

bwr.calculate_needed_intersections({meal: 1}, ("Monthly water stress", "Average"))

inventory_geocollections = [
    'countries',
    'cities',
    'regions',
]

for gc in inventory_geocollections:
    if f'{gc}-WaterGap' not in bwr.geocollections:
        bwr.remote.calculate_intersection(gc, 'WaterGap')

for gc in inventory_geocollections:
    if f'{gc}-watergap' not in bwr.geocollections:
        bwr.remote.intersection_as_new_geocollection(gc, 'WaterGap', f'{gc}-WaterGap')

bwr.geocollections['popdensity'] = {'filepath': str(reg_data_dir / 'gpw_v4_population_density.tif')}


# turn the map of irrigation into an extension table and calculate the intersections

CROPS = ['rice'] # 'cereals', 'citrus', 'potatoe'
for crop in CROPS:
    for gc in inventory_geocollections:
        if f'{gc}-WaterGap - {crop}' not in bwr.extension_tables:
            bwr.raster_as_extension_table(f'{gc}-WaterGap', crop, engine='rasterstats')

for xt in bwr.extension_tables:
    bwr.calculate_needed_intersections({meal: 1}, ("Monthly water stress", "Average"), xt)


#%% TEMPORAL CALCULATIONS

# see what is in there...
rice_Valencia = bd.get_node(name="rice_Valencia")
for x in rice_Valencia.biosphere():
    td = x["temporal_distribution"]
    print(x)
    print("\t", td)

# function to combine the extension tables
def combine_xts(xts: list, label: str):
    data = [elem for xt in xts for elem in bwr.ExtensionTable(xt).load()]

    geocollections = list({bwr.extension_tables[xt]['geocollection'] for xt in xts})
    new_ext = bwr.ExtensionTable(label)
    new_ext.register(geocollections=geocollections)
    new_ext.write(data)

CROPS = ['rice'] # 'cereals', 'citrus', 'potatoe', 

for crop in CROPS:
    xts = [xt for xt in bwr.extension_tables if crop in xt and "xt" not in xt]
    combine_xts(xts, f"{crop}-xt-all")

# %% DEFINE CHARACTERIZATION MATRICES FOR REGIONALIZED LCIA

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

matrix_dict = {}

act = meal
for crop in CROPS:
    for month in range(1, 13):
        lca = bwr.ExtensionTablesLCA(
            demand={act: 1},
            method=("Monthly water stress", str(month)),
            xtable=f'{crop}-xt-all'
        )
        lca.lci()
        lca.lcia() 
        matrix_dict[(crop, month)] = characterization_matrix_for_regionalized_lca(lca)

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

characterize_water_generic = partial(characterize_water, lca=lca, matrix_dict=matrix_dict)


# %% [10]: CALCULATE REGIONALISED LCA

class RegionalizedGraphTraversal(GraphTraversal):
    @classmethod
    def get_characterized_biosphere(cls, lca: bc.LCA):
        return characterization_matrix_for_regionalized_lca(lca).multiply(lca.biosphere_matrix)

# %% [11]: CALCULATE TEMPORALIS LCA

CROP = 'rice'
lca = bwr.ExtensionTablesLCA(
    demand={act: 1},
    method=("Monthly water stress", "Average"),
    xtable=f'{crop}-xt-all',
)
lca.lci()
lca.lcia()

tlca = TemporalisLCA(lca, graph_traversal=RegionalizedGraphTraversal)
tl = tlca.build_timeline()
tl.build_dataframe()

# %% [12]: PLOT THE RESULTS FOR THE WATER DEMAND OF A MEAL OF RICE
tl.df.plot(x="date", y="amount", 
    kind="scatter", 
    title="Water stress of a meal of rice from {}".format(act['name'].split("_")[1]), 
    ylabel="Water demand (m³)", 
    xlabel="Date",
)

import matplotlib.pyplot as plt
plt.xticks(ticks=tl.df.date, labels=[d.strftime("%b '%y") for d in tl.df.date], rotation=45)

plt.savefig("water_demand_{}.png".format(act['name']), dpi=300, bbox_inches="tight")
#%% 

characterize_water_specific = partial(characterize_water_generic, crop=CROP)
characterized_df = tl.characterize_dataframe(
    characterization_function=characterize_water_specific, 
    cumsum=True
)
#%%
c_df = characterized_df.copy()

fig = plt.figure()
plt.scatter(c_df["date"], c_df["amount"], label="Stress by month")
plt.plot(c_df["date"], c_df["amount_sum"], label="Cumulative stress", color="black", linestyle="--")

plt.title("Water stress of a meal of rice from {}".format(act['name'].split("_")[1]))
plt.ylabel("Water stress (unit?)")
plt.xlabel("Date")
plt.xticks(ticks=c_df.date, labels=[d.strftime("%b '%y") for d in c_df.date], rotation=45)
plt.legend()
plt.ylim(0, 3.5)


fig.savefig("water_stress_{}.png".format(act['name']), dpi=300, bbox_inches="tight")

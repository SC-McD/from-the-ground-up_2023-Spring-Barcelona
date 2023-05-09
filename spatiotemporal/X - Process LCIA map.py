#!/usr/bin/env python
# coding: utf-8

# # Processing the monthly water stress index maps into a sange geospatial format
# 
# Data from [Stephan Pfister, ETHZ](https://esd.ifu.ethz.ch/downloads/monthly-water-scarcity-assessment---water-footprinting.html).
# 
# Many Bothans died to bring us this information.
# 
# First converted from `KMZ` to `GeoPackage` with GDAL and extracted the (only) layer `WSI_weigh.ann.avg`:
# 
# ```bash
# ogr2ogr wsi_annual_yuck.gpkg ifu-esd-monthly_annual_WSI.kmz WSI_weigh.ann.avg
# ```

# In[ ]:


import fiona
from bs4 import BeautifulSoup
from shapely.geometry import shape, mapping


# Values stored as string, convert to `int` or `float` if possible

# In[ ]:


def try_number(x):
    try:
        if "." in x:
            return float(x)
        else:
            return int(x)
    except:
        return x


# Change some column labels and filter out some columns

# In[ ]:


remapping = {
    'Wweigh_mWSI': "mean",
    'WSI_01': 'WSI_01',
    'WSI_02': 'WSI_02',
    'WSI_03': 'WSI_03',
    'WSI_04': 'WSI_04',
    'WSI_05': 'WSI_05',
    'WSI_06': 'WSI_06',
    'WSI_07': 'WSI_07',
    'WSI_08': 'WSI_08',
    'WSI_09': 'WSI_09',
    'WSI_10': 'WSI_10',
    'WSI_11': 'WSI_11',
    'WSI_12': 'WSI_12',
}


# Basin IDs are not unique, as there are somehow more than 10.000 `MultiPolygon` geometries (non-contiguous watersheds?).

# In[ ]:


class BasinCounter:
    def __init__(self):
        self.data = {}

    def __getitem__(self, key):
        try:
            _, index = self.data[key]
            index += 1
        except KeyError:
            index = 1
        self.data[key] = (key, index)
        return f"{key}-{index}"


bc = BasinCounter()


# Data is stored inside an attribute called `description`, which is HTML (!). Even better, the data is inside a table inside another table in that HTML (!!).

# In[ ]:


def parse_table(s):
    return dict([
        [try_number(td.string) for td in row.find_all("td")]
        for row in s.table.table.find_all("tr")
    ])

def set_attributes_from_table(feat, description):
    s = BeautifulSoup(description)
    for key, value in parse_table(s).items():
        try:
            if key == "BAS34S_ID":
                value = bc[value]
            feat['properties'][remapping[key]] = value
        except KeyError:
            pass
    return feat


# Finally ready to write the new GeoPackage

# In[ ]:


with fiona.open("wsi_annual_yuck.gpkg") as src:
    crs = src.crs
    schema = {
        'geometry': 'Polygon',
        'properties': {
            'mean': "float",
            'basin_id': "str",
            'WSI_01': 'float',
            'WSI_02': 'float',
            'WSI_03': 'float',
            'WSI_04': 'float',
            'WSI_05': 'float',
            'WSI_06': 'float',
            'WSI_07': 'float',
            'WSI_08': 'float',
            'WSI_09': 'float',
            'WSI_10': 'float',
            'WSI_11': 'float',
            'WSI_12': 'float',
        }
    }

    with fiona.open("wsi_annual.gpkg", "w", driver="GPKG", 
                    crs=crs, schema=schema) as dst:
        for feat_orig in src:
            if feat_orig.geometry['type'] == 'MultiPolygon':
                # Unroll MultiPolygon to Polygon
                geom = shape(feat_orig.geometry)
                for polygon in shape(feat_orig.geometry).geoms:
                    feat = {'geometry': mapping(polygon), 'properties': {}}
                    set_attributes_from_table(feat, feat_orig.properties['description'])
                    dst.write(feat)
            else:
                feat = {'geometry': feat_orig['geometry'], 'properties': {}}
                set_attributes_from_table(feat, feat_orig.properties['description'])
                dst.write(feat)



#%%
import graphviz as gv

#%% add nodes

nodes = []

water = dict(
    database="biosphere",
    code="water",
    name="water",
    type="emission",
    unit="m³",
)
nodes.append(water)

rice = dict(
    database="technosphere",
    code="rice",
    name="rice",
    type="process",
    unit="kg",
)
nodes.append(rice)

meal = dict(
    database="technosphere",
    code="meal",
    name="meal",
    type="process",
    unit="kg",
)
nodes.append(meal)

# add edges

edges = []

water_to_rice = dict(
    input=water,
    output=rice,
    type="biosphere",
    amount=6,
    unit="m³",
)
edges.append(water_to_rice)

rice_to_meal = dict(
    input=rice,
    output=meal,
    type="technosphere",
    amount=1,
    unit="kg",
)
edges.append(rice_to_meal)


#%% make graph

g = gv.Digraph(
                filename="PFD_meal-of-rice", 
                format='svg',
                graph_attr={'rankdir':'LR',
                            'pad': '0.1',
                }) 

for node in nodes:
    g.node(node['code'], label=node['name'], shape='box')

    if node['type'] == 'emission':
        g.node(node['code'], shape='ellipse', style='filled', fillcolor='skyblue', label='Water')
    
    if node['name'] == 'meal':  
        g.node(node['code'], shape='box', style='filled', fillcolor='forestgreen', fontcolor='white', label='Delicious meal')

    if node['name'] == 'rice':  
        g.node(node['code'], shape='box', style='filled', fillcolor='orange', fontcolor='black', label='Rice')

for edge in edges:
    g.edge(edge['input']['code'], edge['output']['code'], label=str(round(edge['amount'],2)) + ' ' + edge['unit'],
    penwidth=str(0.1+(edge['amount'])**0.5))

g.render(view=True)

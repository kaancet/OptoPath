import numpy as np 
import pandas as pd
from scipy.stats import norm

from bokeh.io import show,curdoc
from bokeh.plotting import figure
from bokeh.palettes import Set1
from bokeh.layouts import row, column
from bokeh.models import Plot, Segment, ColumnDataSource, Select, RadioButtonGroup, CheckboxButtonGroup, MultiSelect, RangeSlider, Button, Slider, DataTable, Segment, Div, Tabs, Panel, TableColumn, PreText, FileInput, HoverTool

from opticalElement import OpticalElement

#####################################
# GLOBAL VARIABLES AND DATA SOURCES #
#####################################
# Color palette to iterate over with every new component added
clr = Set1[9]

# Measured knob powers to be used in 
knob_power_lookup = {}

# csv data paths for components
component_path_lookup = {'Thorlabs 450/10' : 'csv_data/thorlabs/FB450-10_Spectrum.csv',
                         'Thorlabs 450 LP' : 'csv_data/thorlabs/FEL0450_Spectrum.csv',
                         'Semrock 468 SP'  : 'csv_data/semrock/FF01-468_SP_Spectrum.csv',
                         'Semrock 460/14'  : 'csv_data/semrock/FF01-460-14_Spectrum.csv',
                         'Semrock 442 LP'  : 'csv_data/semrock/BLP01-442R_Spectrum.csv',
                         'Semrock 430 LP'  : 'csv_data/semrock/FF01-430_LP_Spectrum.csv',
                         'Fiber'           : 'Fiber'} 

laser_path_lookup = {'445nm Blue'  : 'csv_data/laser/no_filter_laser.csv',
                     '540nm Green' : 'csv_data/laser/single_filter_laser.csv'}

def get_laser_data(laser_name):
    laser_path = laser_path_lookup[laser_name]
    laser_data = pd.read_csv(laser_path,sep='\t')
    # clean and normalize
    laser_data['Counts'] = laser_data['Counts'].apply(lambda x: 0 if x<0 else x)

    laser_data['max_norm_counts'] = (laser_data['Counts'] / np.max(laser_data['Counts'],axis=None))
    laser_data['sum_norm_counts'] = (laser_data['Counts'] / np.sum(laser_data['Counts'],axis=None))
    return laser_data

comps = [k for k in component_path_lookup.keys()]

# global sync stuff
active_components = {}
component_keys = {}
component_ctr = 1
the_laser = get_laser_data('445nm Blue')
the_distance = 1
the_power = 0

# init sources
component_specs = {'Wavelength':[],
                    'Transmission':[],
                    'od':[],
                    'color':[],
                    'name': []}

optical_path = {'x':[0],
                'y':[0],
                'x1':[0],
                'y1':[0],
                'color':['#e885fc'],
                'beam_w':[0.5],
                'name':['Sample']}

sources = {}
sources['spec_src'] = ColumnDataSource(data = component_specs)
sources['transmission_src'] = ColumnDataSource(data = component_specs)
sources['od_src'] = ColumnDataSource(data = component_specs)
sources['laser_src'] = ColumnDataSource(data = the_laser.to_dict(orient='list'))
sources['optical_path_src'] = ColumnDataSource(data = optical_path)
sources['power_src'] = ColumnDataSource(data = the_laser.to_dict(orient='list'))

#########
# UI/UX #
#########
columns = [TableColumn(field='Wavelength',title='Wavelength'),
           TableColumn(field='Transmission',title='Transmission'),
           TableColumn(field='od',title='Optical Density')]

# controller widgets
laser_selector = RadioButtonGroup(labels=[k for k in laser_path_lookup.keys()],active=0)
distance_slider = Slider(start=1,end=20,value=the_distance,step=1,title='Distance(mm)')
knob_slider = Slider(start=0,end=10,step=0.1,value=0,title='Knob Value')
component_select = Select(title='Available Components',options=comps,value=comps[0]) #this gives the value as a string name
add_component = Button(label='Add Component',button_type='success')
remove_component = Button(label='Remove Component',button_type='warning')

# data showing stuff
component_list = MultiSelect(options=list(component_keys.values())) #this gives the value as a string id (0,1,2,...)
selected_component_data = DataTable(source=sources['spec_src'],columns=columns,width=400, height=250)
power_div = Div(text="""<h2> Sample at {0} mm:<b>{1} mW/mm²</b></h2>""".format(the_distance,the_power))
log_text = PreText(text=""" """,width=400,height=300)

# optical path plot
path_plot = figure(plot_width=700,plot_height=200,toolbar_location='below')
# light source
path_plot.rect(x=-1,y=0,width=2,height=1,fill_color='#b0b0b0')
# light
path_plot.segment(x0=0,y0=0,x1='x1',y1=0,line_color="#138bf4",line_width='beam_w',alpha=0.6,source=sources['optical_path_src'])
# sample
path_plot.segment(x0='x',y0='y',x1='x1',y1='y1',line_color='color',line_width=3,source=sources['optical_path_src'])
path_plot.axis.visible = False
path_plot.grid.visible = False

# transmission/od plot
transmission_plot = figure(plot_width=700,plot_height=300,toolbar_location='below')
transmission_plot.line(x='Wavelength',y='max_norm_counts',line_width=3,line_color='#0000ff',source=sources['laser_src'])
transmission_plot.xaxis.axis_label = 'Wavelength(nm)'
transmission_plot.yaxis.axis_label = 'Transmission'
od_plot = figure(plot_width=700,plot_height=300,toolbar_location='below')
od_plot.xaxis.axis_label = 'Wavelength(nm)'
od_plot.yaxis.axis_label = 'Optical Density'

tab1 = Panel(child=transmission_plot,title='Transmission')
tab2 = Panel(child=od_plot,title='Optical Density')

#power plot
power_plot = figure(plot_width=500,plot_height=500,toolbar_location='below')
power_plot.line(x='Wavelength',y='sum_norm_counts',line_width=3,line_color='#0f8bdd',source=sources['power_src'])
power_plot.xaxis.axis_label = 'Wavelength(nm)'
power_plot.yaxis.axis_label = 'Relative Power'

# add hover tools
transmission_plot.add_tools(HoverTool(tooltips=[('Name', '@name'),
                                                ('Transmission','$y'),
                                                ('lambda(nm)','$x')],
                                      mode='mouse'))

od_plot.add_tools(HoverTool(tooltips=[('name', '@name'),
                                      ('OD','$y'),
                                      ('lambda(nm)','$x')],
                            mode='mouse'))

path_plot.add_tools(HoverTool(tooltips=[('name', '@name')],
                              mode='mouse'))  

power_plot.add_tools(HoverTool(tooltips=[('Power','$y'),
                                         ('Wavelength','$x')],
                               mode='mouse'))                  


###########################
# CALLBACKS AND FUNCTIONS #
###########################
def calc_power(power_frame):
    energy_arr = 1.2398 / power_frame['Wavelength'].to_numpy()
    return float(np.sum(energy_arr * power_frame['sum_norm_counts'],axis=None))

def update_plots_and_propagate_light():
    global the_laser
    P_temp = the_laser

    #clear plot sources
    sources['transmission_src'].data = {'Wavelength':[[]],
                                        'Transmission':[[]],
                                        'od':[[]],
                                        'color':[[]],
                                        'name':[[]]}

    sources['od_src'].data = {'Wavelength':[[]],
                              'Transmission':[[]],
                              'od':[[]],
                              'color':[[]],
                              'name':[[]]}

    sources['optical_path_src'].data = {'x':[0],
                                        'y':[0],
                                        'x1':[0],
                                        'y1':[0],
                                        'color':['#e885fc'],
                                        'beam_w':[float(knob_slider.value)],
                                        'name':['Sample']}

    # update plot sources and propagate light through existing components
    for comp in active_components.values():
        for k in sources['transmission_src'].data.keys():
            if k == 'color':
                sources['transmission_src'].data['color'].append(comp.color)
                sources['od_src'].data['color'].append(comp.color)
            elif k == 'name':
                sources['transmission_src'].data['name'].append(comp.name)
                sources['od_src'].data['name'].append(comp.name)
            else:
                sources['transmission_src'].data[k].append(comp.data[k].tolist())
                sources['od_src'].data[k].append(comp.data[k].tolist())
        for g in comp.shape_glyph:
            path_plot.add_glyph(source_or_glyph=comp.shape_source,glyph=g)

        # propagate the_laser here with all the wavelengths
        P_temp = comp.propagate(P_temp)

    # propagate distance
    P_temp['sum_norm_counts'] = P_temp['sum_norm_counts'].apply(lambda x: x * (1/(the_distance**2)))

    sources['optical_path_src'].data = {'x':[component_ctr+the_distance],
                                        'y':[-1],
                                        'x1':[component_ctr+the_distance],
                                        'y1':[1],
                                        'color':['#e885fc'],
                                        'beam_w':[float(knob_slider.value)],
                                        'name':['Sample']}

    sources['power_src'].data = P_temp.to_dict(orient='list')

    the_power = calc_power(P_temp)
    # Update plots and UI stuff
    power_div.text = """<h1>Power on sample at {0} mm: <b><br/>{1} mW/mm²</b></h1>""".format(the_distance,the_power)
        
    transmission_plot.multi_line(xs='Wavelength',ys='Transmission',line_color='color',line_dash='dashed',source=sources['transmission_src'])
    od_plot.multi_line(xs='Wavelength',ys='od',line_color='color',source=sources['od_src'])

    path_plot.segment(x0='x',x1='x1',y0='y',y1='y1',line_width=3,line_color='color',source=sources['optical_path_src'])

def distance_slider_change(attr,old,new):
    the_distance = int(distance_slider.value)
    sources['optical_path_src'].data['x'] = [component_ctr+the_distance-1]
    sources['optical_path_src'].data['x1'] = [component_ctr+the_distance-1]
    global the_laser
    P_temp = the_laser.copy()
    P_temp['sum_norm_counts'] = P_temp['sum_norm_counts'].apply(lambda x: x * (1/(the_distance**2)))
    the_power = calc_power(P_temp)
    power_div.text = """<h1>Power on sample at {0} mm: <b><br/>{1} mW/mm²</b></h1>""".format(the_distance,the_power)
    log_text.text = 'Distance set to {0}\n'.format(the_distance)
    
def knob_slider_change(attr,old,new):
    sources['optical_path_src'].data['beam_w'] = [float(knob_slider.value)]
    log_text.text = 'Knob value set to {0}\n'.format(knob_slider.value)
    
# Buttons
def laser_radio_button(attr):
    laser_keys = list(laser_path_lookup.keys())
    laser_name = laser_keys[int(laser_selector.active)]
    global the_laser
    the_laser = get_laser_data(laser_name)
    sources['laser_src'].data = the_laser.to_dict(orient='list')
    log_text.text = 'Laser changed {0}\n'.format(laser_name)
    
def add_button():
    global component_ctr
    selected = component_select.value 
    log_text.text = 'Added {0}\n'.format(selected)

    # add the OpticalElement object to the dictionary
    key = '{0}_{1}'.format(selected,component_ctr)
    active_components[key] = OpticalElement(name=selected,pos=component_ctr,
                                            csv_path=component_path_lookup[selected],
                                            color=clr[len(clr)%component_ctr])
    # add key 
    component_keys[str(component_ctr)] = (str(component_ctr),key)
    # update the shown component list
    component_list.options = list(component_keys.values())
    component_ctr += 1
    
    update_plots_and_propagate_light()
    
def remove_button():
    selected = component_list.value
    if len(selected):
        global component_ctr
        for comp_id in selected:
            comp_name = component_keys[comp_id][1]
            comp = active_components[comp_name]
            comp.remove_shape()
            active_components.pop(comp_name)
            component_keys.pop(comp_id)
            log_text.text = 'Removed {0}\n'.format(comp_name)
            component_ctr -= 1
        
        component_list.options = list(component_keys.values())
        update_plots_and_propagate_light()

    print(component_list)

def multiselect_select(attr,old,new):
    selected = component_list.value
    # always show the first one
    selected = selected[0]

    selected_data = active_components[component_keys[selected][1]].data
    temp = {}
    for c in selected_data.columns:
        temp[c] = selected_data[c].tolist()
    sources['spec_src'].data = temp
    print(component_list.value,flush=True)

# bind callbacks
laser_selector.on_click(laser_radio_button)
distance_slider.on_change('value',distance_slider_change)
knob_slider.on_change('value',knob_slider_change)
component_list.on_change('value',multiselect_select)
add_component.on_click(add_button)
remove_component.on_click(remove_button)

##############
# SET LAYOUT #
##############
layout = column(row(column(laser_selector,
                           row(column(component_select,add_component), # can add log_text in this column
                               column(component_list,remove_component)), 
                           distance_slider,knob_slider),
                           selected_component_data),
                row(column(path_plot,Tabs(tabs=[tab1,tab2])),
                    column(power_div,power_plot)))

curdoc().add_root(layout)


# elif self.name == 'Distance':
#     transmission = np.ones_like(spectra) * 1
#     od = np.log10(1/transmission)
#     data = np.hstack((spectra.reshape(-1,1),transmission.reshape(-1,1),od.reshape(-1,1)))
#     self.data = pd.DataFrame(data=data, columns=['Wavelength','Transmission','od'])
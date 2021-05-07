import pandas as pd
import numpy as np
from bokeh.models import ColumnDataSource, Segment, Ellipse

from scipy.interpolate import interp1d


class OpticalElement:
    def __init__(self,name,pos,csv_path,**kwargs):
        self.name = name
        if not isinstance(pos,list):
            self.pos = {'x':pos, 'y':-0.5}
        else:
            self.pos = {'x':pos[0], 'y':pos[1]}

        self.make_data(csv_path)
        self.set_lambda_range()
        
        self.shape = {'w':1, 'h':1, 'r':0.25}
        self.color = kwargs.get('color','#336644')
        self.make_shape()

    def make_data(self,path=None):
        spectra = np.arange(300,1200,0.2)
        if self.name == 'Fiber':
            # assume no loss for now
            transmission = np.ones_like(spectra) * 0.98
            od = np.log10(1/transmission)
            data = np.hstack((spectra.reshape(-1,1),transmission.reshape(-1,1),od.reshape(-1,1)))
            self.data = pd.DataFrame(data=data, columns=['Wavelength','Transmission','od'])

        if 'thorlabs' in path:
            temp = pd.read_csv(path,sep = '\t')
            temp['Transmission'] = temp['Transmission'].apply(lambda x: x/100)
            trans = interp1d(temp['Wavelength'],temp['Transmission'],kind='cubic')
            od = interp1d(temp['Wavelength'],temp['od'],kind='cubic')
            
            data = np.hstack((spectra.reshape(-1,1), trans(spectra).reshape(-1,1), od(spectra).reshape(-1,1)))
            self.data = pd.DataFrame(data=data, columns=['Wavelength','Transmission','od'])
        elif 'semrock' in path:
            self.data= pd.read_csv(path, sep='\t', header=4)
            self.data['od'] = self.data['Transmission'].apply(lambda x: np.log10(1/x))

    def propagate(self,P_in):
        P_out = P_in.copy()
        # P_in is a dataframe with lambda and 'count' values
        lambda_max = np.max(P_out['Wavelength'],axis=None)
        lambda_min = np.min(P_out['Wavelength'],axis=None)

        lambda_slice = self.data[(self.data['Wavelength'] >= lambda_min) & (self.data['Wavelength'] <= lambda_max)]
        lambda_arr = lambda_slice['Wavelength'].to_numpy()
        trans_arr =  lambda_slice['Transmission'].to_numpy()
        od_arr = lambda_slice['od'].to_numpy()

        # pad with a zeros if laser lambda range is bigger than component range
        if lambda_max > np.max(self.data['Wavelength']):
            lambda_arr = np.append(lambda_arr,lambda_max)
            trans_arr = np.append(trans_arr,0)
            od_arr = np.append(od_arr,0)
        
        if lambda_min < np.min(self.data['Wavelength']):
            lambda_arr = np.insert(lambda_arr,0,lambda_min)
            trans_arr = np.insert(trans_arr,0,0)
            od_arr = np.insert(od_arr,0,0)

        # interpolate
        trans = interp1d(lambda_arr,trans_arr,kind='cubic',fill_value='extrapolate')
        od = interp1d(lambda_arr,od_arr,kind='cubic',fill_value='extrapolate')

        if self.name == 'Fiber':
            P_out['sum_norm_counts'] = P_in['sum_norm_counts'].to_numpy() * np.power(10,-(L*od(P_in['Wavelength'].to_numpy())))
        else:
            P_out['sum_norm_counts'] = P_in['sum_norm_counts'].to_numpy() * np.power(10,-od(P_in['Wavelength'].to_numpy()))



        return P_out

    def make_shape(self):
        glyphs = []
        if self.name == 'Fiber':
            # make fiber shape _O_
            src = ColumnDataSource(data = {'x' : [self.pos['x'] - self.shape['w']/2],
                                           'y' : [self.pos['y'] + self.shape['h']/2],
                                           'x1': [self.pos['x'] + self.shape['w']/2],
                                           'y1': [self.pos['y'] + self.shape['h']/2],
                                           'loop_x' : [self.pos['x']],
                                           'loop_y' : [self.pos['y'] + self.shape['h']/2 + self.shape['r']],
                                           'loop_size' : [self.shape['r']*2],
                                           'color' : [self.color],
                                           'name'  : [self.name]
                                           }) 
            glyphs.append(Segment(x0='x',
                                  y0='y',
                                  x1='x1',
                                  y1='y1',
                                  line_color='color',
                                  line_width=3))
            glyphs.append(Ellipse(x='loop_x',
                                  y='loop_y',
                                  width='loop_size',
                                  height='loop_size',
                                  line_color='color',
                                  fill_alpha=0,
                                  line_width=3))
        else:
            src = ColumnDataSource(data = {'x':[self.pos['x']],
                                           'y':[self.pos['y']],
                                           'x1':[self.pos['x']],
                                           'y1':[self.pos['y'] + self.shape['h']],
                                           'color':[self.color],
                                           'name':[self.name]})
            # make filter shape |
            glyphs.append(Segment(x0='x',
                                    y0='y',
                                    x1='x1',
                                    y1='y1',
                                    line_color='color',
                                    line_dash='solid',
                                    line_width=3))
        self.is_active = True
        self.shape_source = src  
        self.shape_glyph = glyphs

    def remove_shape(self):
        # update glyphs
        if self.name == 'Fiber':
            new_src = {'x' : [0],
                       'y' : [0],
                       'x1': [0],
                       'y1': [0],
                       'loop_x' : [0],
                       'loop_y' : [0],
                       'loop_size' : [0]}
        else:
            new_src = {'x':[0],
                       'y':[0],
                       'x1':[0],
                       'y1':[0]}
        self.is_active = False
        self.shape_source.data = new_src

    def move_shape(self,new_pos):
        """ Moves the shape bu updating the pos dict and then filling the columndatasource for glyphs"""
        if not isinstance(new_pos,list):
            self.pos = {'x':new_pos, 'y':0}
        else:
            self.pos = {'x':new_pos[0], 'y':new_pos[1]}

        # update glyphs
        if self.name == 'Fiber':
            new_src = {'x' : [self.pos['x']],
                       'y' : [self.pos['y']],
                       'x1': [self.pos['x'] + self.shape['w']],
                       'y1': [self.pos['y'] + self.shape['h']],
                       'loop_x' : [self.shape['w']/2],
                       'loop_y' : [self.shape['h']/2 + self.shape['r']],
                       'loop_size' : [self.shape['r']*2]}
        else:
            new_src = {'x':[self.pos['x']],
                       'y':[self.pos['y']],
                       'x1':[self.pos['x'] + self.shape['w']],
                       'y1':[self.pos['y'] + self.shape['h']]}
        self.shape_source.data = new_src

    def set_lambda_range(self,wavelength=None):
        """ Get the current object properties dependig on the wavelength range"""
        if wavelength is not None: 
            self.lambda_range = self.data[(self.data['Wavelength'] >= wavelength[0]) & (self.data['Wavelength'] <= wavelength[1])]
        else:
            self.lambda_range = np.arange(300,1200,0.2)
        
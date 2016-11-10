from gunviolence import app
from flask import Flask, render_template, url_for, jsonify
from werkzeug.serving import run_simple
from ConfigUtil import config
from ChicagoData import comm
import pandas as pd
import numpy as np
import random

def gen_hex_colour_code():
   return ''.join([random.choice('0123456789ABCDEF') for x in range(6)])


key=config['GOOGLE_MAPS_KEY']

map_dict = {
            'identifier': 'view-side',
            'zoom': 11,
            'maptype': 'ROADMAP',
            'zoom_control': True,
            'scroll_wheel': False,
            'fullscreen_control': False,
            'rorate_control': False,
            'maptype_control': False,
            'streetview_control': False,
            'scale_control': True,
            'style': 'height:800px;width:600px;margin:0;'}

@app.route('/')
def main_page():
	return render_template('main_page.html')



@app.route('/<string:city>')
def city(city, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    return render_template('city.html', date_dropdown=[d for d in enumerate(comm.date_list)], api_key=key, city=city)


@app.route('/<string:city>/<string:dt_filter>')
def monthly_data(city, dt_filter, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    if dt_filter!='0':
        cols = set(comm.data.columns) - set(comm.date_list) 
        cols |= set([dt_filter])
        comm_data = comm.geom_to_list(comm.data[list(cols)])
        comm_data.loc[:, dt_filter] = comm_data[dt_filter].fillna(0)
        comm_data.loc[:, 'norm'] = np.linalg.norm(comm_data[dt_filter].fillna(0))
        comm_data.loc[:, 'fill_opacity'] = comm_data[dt_filter]/comm_data['norm']
    else: 
        comm_data=pd.DataFrame([])
    polyargs = {}
    polyargs['stroke_color'] = '#FF0000' 
    polyargs['fill_color'] = '#FF0000' 
    polyargs['stroke_opacity'] = 1
    polyargs['stroke_weight'] = .2

    return jsonify({'selected_dt': dt_filter, 'map_dict': map_dict, 'polyargs': polyargs, 'results': comm_data.to_dict()})



if __name__ == '__main__':
    run_simple('localhost', 5000, app,
               use_reloader=True, use_debugger=True, use_evalex=True)

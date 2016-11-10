from gunviolence import app
from flask import Flask, render_template, url_for, jsonify
from werkzeug.serving import run_simple
from ConfigUtil import config
from ChicagoData import crime_dict
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


@app.route('/city/<string:city>')
def city(city, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    return render_template('city.html', date_dropdown=crime_dict['community'].date_list, api_key=key, city=city)


@app.route('/<string:api_endpoint>/<string:city>/<string:dt_filter>')
def monthlty_data(api_endpoint, city, dt_filter, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    crime_obj = crime_dict[api_endpoint]
    if dt_filter!='0':
        cols = set(crime_obj.data.columns) - set(crime_obj.date_list) 
        cols |= set([dt_filter])
        crime_data = crime_obj.geom_to_list(crime_obj.data[list(cols)])
        crime_data.loc[:, dt_filter] = crime_data[dt_filter].fillna(0)
        crime_data = crime_data[crime_data[dt_filter]>0].reset_index(drop=True)
        crime_data.loc[:, 'norm'] = np.linalg.norm(crime_data[dt_filter].fillna(0))
        crime_data.loc[:, 'fill_opacity'] = crime_data[dt_filter]/crime_data['norm']
    else: 
        crime_data=pd.DataFrame([])
    polyargs = {}
    polyargs['stroke_color'] = '#FF0000' 
    polyargs['fill_color'] = '#FF0000' 
    polyargs['stroke_opacity'] = 1
    polyargs['stroke_weight'] = .2
    return jsonify({'selected_dt': dt_filter, 'map_dict': map_dict, 'polyargs': polyargs, 'results': crime_data.to_dict()})


if __name__ == '__main__':
    run_simple('localhost', 5000, app,
               use_reloader=True, use_debugger=True, use_evalex=True)

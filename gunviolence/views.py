from gunviolence import app
from flask import Flask, render_template, url_for, jsonify
from werkzeug.serving import run_simple
from ConfigUtil import config
from gunviolence.ChicagoData import crime_dict
import pandas as pd
import numpy as np
import random
import json

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
            'style': 'height:800px;width:800px;margin:0;'}

@app.route('/')
def main_page():
	return render_template('main_page.html')


@app.route('/city/<string:city>')
def city(city):
    return render_template('city.html', date_dropdown=crime_dict['community'].date_list, api_key=key, city=city)

@app.route('/trends/<string:city>')
def trends(city):
    data = crime_dict['trends'].data.set_index('CITY')
    data.index = [i.lower() for i in data.index]
    return jsonify(data.T.to_dict())

@app.route('/<string:api_endpoint>/<string:city>/<string:dt_filter>')
def monthlty_data(api_endpoint, city, dt_filter, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    crime_obj = crime_dict[api_endpoint]
    filter_zeros = True
    if api_endpoint=="community":
        filter_zeros = False
    if dt_filter!='0':
        norm_data = crime_obj.norm_data(dt_filter, filter_zeros)
        crime_data = crime_obj.geom_to_list(norm_data)
        cols = (set(crime_data.columns) - set(crime_obj.date_list)) | set([dt_filter])
        crime_data = crime_data[list(cols)]    
    else: 
        crime_data=pd.DataFrame([])

    polyargs = {}
    polyargs['stroke_color'] = '#FFFFFF' 
    polyargs['fill_color'] = '#FF0000' 
    polyargs['stroke_opacity'] = 1
    polyargs['stroke_weight'] = .5
    return jsonify({'selected_dt': dt_filter, 'map_dict': map_dict, 'polyargs': polyargs, 'results': crime_data.to_dict()})

@app.route('/community_trends/<string:city>/<int:community_id>')
def community_data(city, community_id):
    crime_obj = crime_dict["community"]
    filter_zeros = False
    crime_data = crime_obj.geom_to_list(crime_obj.data).fillna(0)
    crime_data = crime_data[crime_data['Community Area']==community_id]
    results = crime_data[crime_obj.date_list].reset_index(drop=True).ix[0]
    meta_cols = set(crime_data.columns) - set(crime_obj.date_list)
    meta = crime_data[list(meta_cols)].reset_index(drop=True).ix[0]
    return jsonify({'meta': meta.to_dict(), 'results': results.to_dict()})


@app.route('/census_correlation/<string:city>')
def census_scatter(city):
    crime_obj = crime_dict["census_correlation"]
    crime_data = crime_obj.data[['COMMUNITY', 'Community Area']]
    crime_data['avg_annual_crimes'] = crime_obj.data[crime_obj.date_list].mean(axis=1)
    census_extended = crime_obj.read_census_extended()
    census_data = crime_data.merge(census_extended, left_on='COMMUNITY', right_on='GEOG').fillna(0)
    return jsonify({'results': census_data.to_dict()})

@app.route('/census/<string:city>')
def community(city):
    crime_obj = crime_dict['community']
    data = crime_obj.data
    crime_data = crime_obj.geom_to_list(data)
    community_meta = crime_obj.communities(crime_data)
    return jsonify(community_meta.T.to_dict())



if __name__ == '__main__':
    run_simple('localhost', 5000, app,
               use_reloader=True, use_debugger=True, use_evalex=True)

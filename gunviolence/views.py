from gunviolence import app
from flask import Flask, render_template, url_for, jsonify
from werkzeug.serving import run_simple
from ConfigUtil import config
from gunviolence.NewYorkData import PivotData as NewYorkPivot
from gunviolence.ChicagoData import PivotData as ChicagoPivot
from gunviolence.NewYorkData import NewYorkData
from gunviolence.ChicagoData import ChicagoData
import pandas as pd
import numpy as np
import random
import json
from runserver import args

print args
# crime_dict = {}
# crime_dict['chicago'] = crime_dict_chicago(args)
# crime_dict['new_york'] = crime_dict_newyork(args)


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
    csv = 'community_pivot.csv'
    fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
    crime_obj = crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) 
    return render_template('city.html', date_dropdown=crime_obj.date_list, api_key=key, city=city)

@app.route('/trends/<string:city>')
def trends(city):
    csv = 'trend.csv'
    fields = ['CITY']
    crime_obj = crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) 
    # data = crime_dict[city]['trends'].data.set_index('CITY')
    data = crime_obj.data.set_index('CITY')
    data.index = [i.lower() for i in data.index]
    return jsonify(data.T.to_dict())

@app.route('/<string:api_endpoint>/<string:city>/<string:dt_filter>')
def monthlty_data(api_endpoint, city, dt_filter, map_dict=map_dict):
    map_dict['center'] = tuple(config['center'][city])
    # crime_obj = crime_dict[city][api_endpoint]
    if api_endpoint=='crime_location':
        csv = 'crime_location.csv'
        fields = ['Primary Type', 'Location Description']
    elif api_endpoint=='heatmap':
        csv = 'heatmap.csv'
        fields = ['Latitude', 'Longitude']
    elif api_endpoint=='incident_marker':
        csv = 'incident_marker.csv'
        fields = ['Latitude', 'Longitude', 'Location', 'Primary Type']
    elif api_endpoint=='community_marker':
        csv = 'community_marker.csv'
        fields = ['Latitude', 'Longitude', 'Community Area', 'Primary Type']
    elif api_endpoint=='district_marker':
        csv = 'district_marker.csv'
        fields = ['Latitude', 'Longitude', 'DIST_NUM', 'Primary Type']
    elif api_endpoint=='beat_marker':
        csv = 'beat_marker.csv'
        fields = ['Latitude', 'Longitude', 'BEAT_NUM', 'Primary Type']
    elif api_endpoint=='city_marker':
        csv = 'city_marker.csv'
        fields = ['Latitude', 'Longitude', 'CITY', 'Primary Type']
    elif api_endpoint=='crime_description':
        csv = 'crime_description.csv'
        fields = ['Primary Type', 'Description']
    elif api_endpoint=='community':
        csv = 'community_pivot.csv'
        fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
    elif api_endpoint=='precinct_marker':
        csv = 'precinct_pivot.csv'
        fields = ['Precinct', 'the_geom_precinct']
    crime_obj = crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) 
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

@app.route('/community_trends/<string:city>/<string:community_id>')
def community_data(city, community_id):
    csv = 'community_pivot.csv'
    fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
    crime_obj = crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) 
    # crime_obj = crime_dict[city]["community"]
    filter_zeros = False
    crime_data = crime_obj.geom_to_list(crime_obj.data).fillna(0)
    if city==chicago:
        community_id=int(community_id)
    crime_data = crime_data[crime_data['Community Area']==community_id]
    results = crime_data[crime_obj.date_list].reset_index(drop=True).ix[0]
    meta_cols = set(crime_data.columns) - set(crime_obj.date_list)
    meta = crime_data[list(meta_cols)].reset_index(drop=True).ix[0]
    return jsonify({'meta': meta.to_dict(), 'results': results.to_dict()})


@app.route('/census_correlation/<string:city>')
def census_scatter(city):
    csv='census_correlation.csv'
    fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
    crime_obj = crimes(city, '%Y', fields,  ['WEAPON_FLAG', 1], ['Year', [2010, 2011, 2012, 2013, 2014]], csv=csv) 
    # crime_obj = crime_dict[city]["census_correlation"]
    crime_data = crime_obj.data[['COMMUNITY', 'Community Area']]
    crime_data['avg_annual_crimes'] = crime_obj.data[crime_obj.date_list].mean(axis=1)
    census_extended = crime_obj.read_census_extended().dropna(axis=1)
    if city=='chicago':
        right_on='GEOG'
    elif city=='new_york':
        right_on='GeogName'
    census_data = crime_data.merge(census_extended, left_on='COMMUNITY', right_on=right_on).fillna(0)
    return jsonify({'results': census_data.to_dict()})

@app.route('/census/<string:city>')
def community(city):
    csv = 'community_pivot.csv'
    fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
    crime_obj = crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) #crime_dict[city]['community']
    data = crime_obj.data
    for d in data.columns:
        print d
    print 'neighborhood\n', data
    crime_data = crime_obj.geom_to_list(data)
    community_meta = crime_obj.communities(crime_data)
    return jsonify(community_meta.T.to_dict())

def cityPivot(city):
    if city=='chicago':
        return ChicagoPivot
    elif city=='new_york':
        return NewYorkPivot

def cityData(city):
    if city=='chicago':
        return ChicagoData()
    elif city=='new_york':
        return NewYorkData()

def crimes(city, dt_format,  pivot_cols, *args, **kwargs):
    nd = cityData(city)
    pivot_cols = nd._set_list(pivot_cols)
    kwargs.setdefault('repull', False)
    PivotData = cityPivot(city)
    if 'csv' in kwargs:
        filepath = nd.DATA_PATH + kwargs['csv']
        data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
        print '%s saved to csv' % filepath
    if 'pickle' in kwargs:
        filepath = nd.DATA_PATH + kwargs['pickle']
        if (not kwargs['repull']) and os.path.isfile(filepath):
            f = open(filepath, 'rb')
            data_obj = cPickle.load(f)
            f.close()
            print '%s pickle loaded' % filepath 
        else:
            data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
            f = open(filepath, 'wb')
            data_obj.df = pd.DataFrame([]) 
            cPickle.dump(data_obj, f, protocol=cPickle.HIGHEST_PROTOCOL)
            f.close()
            print '%s pickled' % filepath
    return data_obj

if __name__ == '__main__':
    run_simple('localhost', 5000, app,
               use_reloader=True, use_debugger=True, use_evalex=True)

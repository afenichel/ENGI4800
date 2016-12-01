import pandas as pd
import numpy as np
import os
from datetime import datetime
import numbers
import requests
import re
from sklearn.linear_model import LinearRegression
from statsmodels.api import OLS
import cPickle
from sklearn.cluster import DBSCAN
import requests
import json
from matplotlib.path import Path
from matplotlib import colors, cm


class BaltimoreData():
	def __init__(self, *args):
		self.DATA_PATH =  os.path.join(os.path.dirname(__file__), "data/baltimore/")
		self.NEIGHBORHOOD_URL =  "http://catalog.civicdashboards.com/dataset/e90d8498-44dd-4390-9bb9-5a53e85221eb/resource/6045d7d0-263e-416c-80fe-af1fb9f30650/download/3327ba9ba6f54cfdb9a5ef18244ae710temp.geojson"
		self.CSV_FILE = self.DATA_PATH + "Baltimore_Complaint_Data.csv"
		self.df = pd.DataFrame()
		self.meta = dict()
		self.args = args

	def filter_df(self, df):
		for arg in self.args:
			assert len(arg)==2, "Filter must define field and filter values"
			assert arg[0] in df.columns
			key = arg[0]
			val = self._set_list(arg[1])
			df = df[df[key].isin(val)].reset_index(drop=True)
		return df

	def initData(self, **kwargs):
		if 'download_data' in kwargs:
			if kwargs['download_data']:
				self.pull_data()

		if 'download_metadata' in kwargs:
			if kwargs['download_metadata']:
				self.pull_metadata()

		if 'limit' in kwargs:
			if kwargs['limit']:
				limit = kwargs['limit']
		else:
			limit = None

		if 'repull' in kwargs:
			if kwargs['repull']: 
				self.read_data(limit=limit)
				self._apply_weapons_flag()
				self.read_meta()
				self.merge_meta()
				self.df['CITY'] = 'Baltimore'
		return self

	def _split_latlng(self):
		Lat_Lng = self.df['Location'].str.replace('\(|\)', '').str.split(', ')
		self.df['Latitude'] = Lat_Lng.map(lambda x: x[0])
		self.df['Longitude'] = Lat_Lng.map(lambda x: x[1])
		return self

	def read_data(self, limit=None):
		self.df = pd.read_csv(self.CSV_FILE, nrows=limit)
		self.df.rename(columns={'Location': 'Address', 'CrimeDate': 'Date', 'Neighborhood': 'Community Area',  'Inside/Outside': 'Location Description', 'Location 1': 'Location', 'District': 'DIST_NUM', 'Description': 'Primary Type', 'Weapon': 'Description'}, inplace=True)
		self.df = self.df[self.df.Location.notnull()].reset_index(drop=True)
		self.df['COMMUNITY'] = self.df['Community Area'].str.upper()
		self._split_latlng()
		return self	

	def read_meta(self):
		self.meta['census'] = self._read_census()
		self.meta['district'] = self._read_BNIAneighborhood()
		self.meta['ward'] = self._read_ward()
		self.meta['community'] = self._read_neighborhood()

	def _read_census(self):
		demo_census = self._read_demo_census()
		action_census = self._read_action_census()
		census = demo_census.merge(action_census, on='DIST_NUM')
		return census

	def _read_BNIAneighborhood(self):
		BNIAneighborhood = pd.read_csv(self.DATA_PATH + 'BNIA_neighborhood.csv').rename(columns={'CSA2010': 'DIST_NUM'})
		return BNIAneighborhood

	def _read_neighborhood(self):
		neighborhood = pd.read_csv(self.DATA_PATH + 'neighborhood.csv').rename(columns={'NBRDESC': 'COMMUNITY', 'LABEL': 'Community Area', 'the_geom': 'the_geom_community'})
		return neighborhood

	def _read_ward(self):
		ward = pd.read_csv(self.DATA_PATH + 'ward.csv').rename(columns={'NAME_1': 'Ward'})
		return ward
	
	def _read_demo_census(self):
		census_demo = pd.read_csv(self.DATA_PATH + 'BNIA_census_data.csv').rename(columns={'CSA2010': 'DIST_NUM'})
		return census_demo
	
	def _read_action_census(self):
		census_action = pd.read_csv(self.DATA_PATH + 'BNIA_action_data.csv').rename(columns={'CSA2010': 'DIST_NUM'})
		return census_action

	def pull_data(self):
		os.system("curl 'https://data.baltimorecity.gov/api/views/v9wg-c9g7/rows.csv?accessType=DOWNLOAD' -o '%sBaltimore_Complaint_Data.csv'" % self.DATA_PATH)
		return self

	def merge_meta(self):
		self.df = self.df.merge(self.meta['community'], how='left', on=['Community Area', 'COMMUNITY'], suffixes=('', '_community'))
		return self

	def pull_metadata(self):
		os.system("curl 'https://data.baltimorecity.gov/api/views/t7sb-aegk/rows.csv?accessType=DOWNLOAD' -o '%sBNIA_census_data.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.baltimorecity.gov/api/views/ipje-efsv/rows.csv?accessType=DOWNLOAD' -o '%sBNIA_action_data.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.baltimorecity.gov/api/views/5j2q-jsy4/rows.csv?accessType=DOWNLOAD' -o '%sward.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.baltimorecity.gov/api/views/i49u-94ea/rows.csv?accessType=DOWNLOAD' -o '%sBNIA_neighborhood.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.baltimorecity.gov/api/views/h3fx-54q3/rows.csv?accessType=DOWNLOAD' -o '%sneighborhood.csv'" % self.DATA_PATH)
		return self


	def get_neighborhood_name(self, df):
		df = self._get_area_name(df, 'community', 'Community Area')
		df['Community Area Number'] = df['Community Area']
		return df
	
	def get_ward_name(self, df):
		df = self._get_area_name(df, 'ward', 'Ward')
		return df

	def get_district_name(self, df):
		df = self._get_area_name(df, 'district', 'DIST_NUM')
		return df

	def _get_area_name(self, df, meta_key, col):
		area_data = self.meta[meta_key].copy()
		area_data = self.geom_to_list(area_data)
		for c in area_data.columns: 
			if re.match('the_geom.*', c):
				self.meta[meta_key]['path'] = area_data[c].map(lambda x: Path(x))
		df[col] = df.index.map(lambda x: self._match_neighborhood(x, df, meta_key, col))
		df[col] = df[col].map(lambda x: x[0] if len(x)>0 else np.nan)
		df = df.merge(self.meta[meta_key], how='left', on=col, suffixes=('_%s' % meta_key, ''))
		df.rename(columns={'the_geom': 'the_geom_%s' % meta_key}, inplace=True)
		return df[df[col].notnull()]

	def _match_neighborhood(self, x, df, meta_key, col):
		lat = float(df.ix[x]['Latitude'])
		lng = float(df.ix[x]['Longitude'])
		area_data = self.meta[meta_key].copy()
		if meta_key=='community':
			area_data['use_flag'] = area_data['COMMUNITY'].map(lambda x: 1 if not re.match('park-cemetery-etc.*|airport', x.lower()) else 0)
			area_data = area_data[area_data.use_flag==1]
		return [row[col] for i, row in area_data.iterrows() if row['path'].contains_point([lat, lng])]


	def read_census_extended(self, values=None):
		census = pd.read_csv("gunviolence/data/chicago/CMAP_census_data.csv")
		census['GEOG'] = census['GEOG'].map(lambda x: x.upper())
		census_key = pd.read_csv("gunviolence/data/chicago/census_lookup.csv")
		col_filter = []
		col_levels = []
		for c in census.columns:
			col = census_key[census_key.Code==c][['Category', 'Variable', 'Code']].values
			if len(col)==1:
				col = list(col[0])
				col = [i.replace('GEOG', 'COMMUNITY AREA NAME') for i in col if isinstance(i, basestring)]
				col_filter.append(c)
				col_levels.append(tuple(col))
		census = census[col_filter]
		census.columns = pd.MultiIndex.from_tuples(col_levels, names=['Category', 'Variable', 'Code'])
		census_extended = census.T.reset_index(drop=False)
		census_extended.index = ['%s: %s' % (row['Category'], row['Variable']) if row['Category'] not in ('COMMUNITY AREA NAME') else row['Category'] for i, row in census_extended.iterrows()]
		census_extended.drop(['Code', 'Category', 'Variable'], axis=1, inplace=True)
		return census_extended.T

	@classmethod
	def geom_to_list(cls, df):
		for c in df.columns: 
			if re.match('the_geom.*', c):
				df[c] = df[c].map(lambda x: cls._parse_geom(x))
		return df


	@staticmethod
	def _parse_geom(coords):
		if isinstance(coords, basestring):
			if str(coords) != '0':
				coord_sets = re.match("MULTIPOLYGON \(\(\((.*)\)\)\)", coords).group(1)
				coord_strings = [re.sub("\(|\)", "", c).split(" ") for c in coord_sets.split(", ")]
				coord_list = tuple([(float(c[1]), float(c[0])) for c in coord_strings])
			else:
				coord_list = tuple([])
		elif isinstance(coords, (list, tuple)):
			coord_list = tuple(coords)
		return coord_list

	@classmethod
	def communities(cls, df):
		community = dict()
		census = cls._read_census()
		
		if set(['the_geom_community', 'Community Area']) < set(df.columns):
			for index1, row1 in df.iterrows():
				for index2, row2 in df.iterrows():
					community.setdefault(row1['Community Area'], {})
					community.setdefault(row2['Community Area'], {})
					if index1 > index2:
						geom1 = row1['the_geom_community']
						geom2 = row2['the_geom_community']
						boundary_intersect = set(geom1) & set(geom2)
						if len(boundary_intersect) > 0:
							community[row1['Community Area']].setdefault('adj_list', []).append(row2['Community Area'])
							community[row2['Community Area']].setdefault('adj_list', []).append(row1['Community Area'])
		
		community = pd.DataFrame(community).T
		community.columns = pd.MultiIndex.from_tuples([tuple(['adj_list']*6)], names=['Code', 'Category', 'Variable', 'CodeType', 'Unit of Analysis', 'Heading'])
		return pd.DataFrame(community).join(census).fillna(-1)
		

	@staticmethod
	def _set_list(f):
		if not isinstance(f, list):
			if isinstance(f, (basestring, numbers.Integral)):
				return [f]
			else:
				return list(f)
		else:
			return f		

	def _model(self, X, y):
		model = OLS(y, X)
		result = model.fit()
		print result.summary()
		return result

	def _apply_weapons_flag(self):
		indexes = []
		self.df['WEAPON_FLAG'] = 0
		for i, row in self.df.iterrows():
			if row['Description']:
				if 'FIREARM' in str(row['Description']) or 'FIREARM' in str(row['Primary Type']):
					indexes.append(i)
		self.df.loc[indexes, 'WEAPON_FLAG'] = 1
		return self



class PivotData(BaltimoreData):
	def __init__(self, fields, dt_format, *args, **kwargs):
		BaltimoreData.__init__(self, *args)
		kwargs.setdefault('repull', False)
		self.fields = self._set_list(fields)
		self.dt_format = dt_format
		if 'csv' in kwargs:
			self.csv = self.DATA_PATH + kwargs['csv']
		else:
			self.csv = ""

		if not kwargs['repull'] and os.path.isfile(self.csv):
			self.initData(**kwargs)
			self._data = pd.read_csv(self.csv)
		else:
			self.initData(**kwargs)
			self.pivot()


	def pivot(self):
		data = self.df.copy()
		data['Year'] = data['Date'].map(lambda x: datetime.strptime(x, '%m/%d/%Y').year)
		data = self.filter_df(data)
		if 'DIST_NUM' in self.fields:
			data = self.get_district_name(data)
		if 'Ward' in self.fields:
			data = self.get_ward_name(data)
		sep = '---'
		data['Period'] = data['Date'].map(lambda x: datetime.strptime(x, '%m/%d/%Y').strftime(self.dt_format))
		counts = data.fillna(0).groupby(['Period']+self.fields, as_index=False).count()
		counts = counts.iloc[:, 0:len(self.fields)+2]
		counts.columns = ['Period']+self.fields+['count']
		for i, f in enumerate(self.fields):
			field_counts = counts[f].map(lambda x: str(x))
			if i==0:
				counts['fields'] = field_counts
			else:
				counts['fields'] += sep+field_counts

		pivot = counts.pivot('fields', 'Period', 'count')
		pivot_split = pivot.reset_index().fields.str.split(sep, expand=True)
		pivot_rename = pivot_split.rename(columns={int(k): v for k, v in enumerate(self.fields)})
		self._data = pivot_rename.merge(pivot.reset_index(drop=True), left_index=True, right_index=True)
		if self.csv:
			self._data.to_csv(self.csv, index=False)
		return self

	def _date_cols(self):
		return set(self._data.columns) - set(self.fields)

	def norm_data(self, dt_filter, filter_zero=True):
		data = self.data.copy()
		data.loc[:, self.date_list] = data.loc[:, self.date_list].fillna(0)
		norm = np.linalg.norm(data.loc[:, self.date_list].fillna(0))
		data.loc[:, 'fill_opacity'] = data[dt_filter]/norm
		data.loc[:, 'fill_opacity'] = data.loc[:, 'fill_opacity'] / max(data.loc[:, 'fill_opacity'] )
		if filter_zero:
			data = data[data[dt_filter]>0].reset_index(drop=True)
		return data

	def color_data(self, dt_filter, filter_zero=True):
		h = cm.get_cmap('RdYlGn')
		data = self.norm_data(dt_filter, filter_zero)
		data.loc[:, 'fill_color'] = data.loc[:, 'fill_opacity'].map(lambda x: colors.rgb2hex(h(1.0-x)).upper())
		return data
	
	@property
	def data(self):
		return self._data

	@property
	def date_list(self):
		dt_list = list(self._date_cols())
		dt_list.sort()
		return dt_list


if __name__=="__main__":
	csv = 'community_pivot.csv'
	fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv

	csv = 'ward_marker.csv'
	fields = ['Latitude', 'Longitude', 'Ward', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv

	csv = 'community_marker.csv'
	fields = ['Latitude', 'Longitude', 'Community Area', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'incident_marker.csv'
	fields = ['Latitude', 'Longitude', 'Location', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'heatmap.csv'
	fields = ['Latitude', 'Longitude']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'census_correlation.csv'
	fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	p = PivotData(fields, '%Y', ['WEAPON_FLAG', 1], ['Year', [2010, 2011, 2012, 2013, 2014]], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'trends.csv'
	fields = ['CITY']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'crime_location.csv'
	fields = ['Primary Type', 'Location Description']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'district_marker.csv'
	fields = ['Latitude', 'Longitude', 'DIST_NUM', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'city_marker.csv'
	fields = ['Latitude', 'Longitude', 'CITY', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	
	csv = 'crime_description.csv'
	fields = ['Primary Type', 'Description']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	print '%s done' % csv
	

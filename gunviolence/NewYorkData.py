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


class NewYorkData():
	def __init__(self, *args):
		self.DATA_PATH =  os.path.join(os.path.dirname(__file__), "data/new_york/")
		self.NEIGHBORHOOD_URL =  "http://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/nynta/FeatureServer/0/query?where=1=1&outFields=*&outSR=4326&f=geojson"
		self.CSV_FILE = self.DATA_PATH + "NYPD_Complaint_data.csv"
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

		self.read_data(limit=limit)
		self._apply_weapons_flag()
		self.read_meta()
		# self.merge_meta()
		self.df['CITY'] = 'New York'
		return self

	def read_data(self, limit=None):
		self.df = pd.read_csv(self.CSV_FILE, nrows=limit, dtype={'CMPLNT_NUM': str, 'KY_CD': str, 'PD_CD': str, 'ADDR_PCT_CD': str, 'PARKS_NM': str, 'X_COORD_CD': str, 'Y_COORD_CD': str, 'Latitude': str, 'Longitude': str})
		self.df.rename(columns={'RPT_DT': 'Date', 'PREM_TYP_DESC': 'Location Description', 'Lat_Lon': 'Location', 'BORO_NM': 'DIST_NUM', 'OFNS_DESC': 'Primary Type', 'PD_DESC': 'Description'}, inplace=True)
		self.df = self.df[self.df.Location.notnull()]
		return self	

	def read_meta(self):
		self.meta['economic_census'] = self._read_economic_census()
		self.meta['demo_census'] = self._read_demo_census()
		self.meta['precinct'] = self._read_precinct()
		self.meta['community'] = self._read_neighborhood()
	
	def _read_neighborhood(self):
		precinct = pd.read_csv(self.DATA_PATH + 'tabulation_areas.csv').rename(columns={'NTAName': 'COMMUNITY', 'NTACode': 'Community Area'})
		return precinct

	def _read_precinct(self):
		precinct = pd.read_csv(self.DATA_PATH + 'precinct.csv')
		return precinct
	
	def _read_economic_census(self):
		census_econ = pd.read_csv(self.DATA_PATH + 'economic_census_data.csv')
		return census_econ
		
	def _read_demo_census(self):
		census_demo = pd.read_csv(self.DATA_PATH + 'demo_census_data.csv')
		return census_demo

	def pull_data(self):
		os.system("curl 'https://data.cityofnewyork.us/api/views/4ax6-n4rg/rows.csv?accessType=DOWNLOAD' -o '%sNYPD_Complaint_Data_Historic.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofnewyork.us/api/views/5uac-w243/rows.csv?accessType=DOWNLOAD' -o '%sNYPD_Complaint_Data_Current_YTD.csv'" % self.DATA_PATH)
		os.system("cat '{0}NYPD_Complaint_Data_Historic.csv' {0}NYPD_Complaint_Data_Current_YTD.csv > {0}NYPD_Complaint_data.csv" .format(self.DATA_PATH))
		return self

	def merge_meta(self):
		# self.df = self.df.merge(self.meta['precinct'], how='left', left_on='District', right_on='DIST_NUM', suffixes=('', '_district'))
		# self.df = self.df.merge(self.meta['community'], how='left', left_on='Community Area', right_on='AREA_NUMBE', suffixes=('', '_community'))		
		# self.df = self.df.merge(self.meta['demo_census'], how='left', left_on='District', right_on='DIST_NUM', suffixes=('', '_district'))
		# self.df = self.df.merge(self.meta['economic_census'], how='left', left_on='Community Area', right_on='Community Area Number')
		# self.df['the_geom_district'] = self.df['the_geom']
		return self

	def pull_metadata(self):
		os.system("curel 'https://data.cityofnewyork.us/api/views/q2z5-ai38/rows.csv?accessType=DOWNLOAD' -o %stabulation_areas.csv" % self.DATA_PATH)
		os.system("curl 'https://data.cityofnewyork.us/api/views/kmub-vria/rows.csv?accessType=DOWNLOAD' -o '%sprecinct.csv" % self.DATA_PATH)
		os.system("curl 'http://catalog.civicdashboards.com/dataset/273b1ac5-4f00-438d-ab93-37dc41dd6450/resource/671ebb5a-672e-4005-9712-45310afd4308/download/eco2013acs5yrntadata.csv' -o '%seconomic_census_data.csv'" % self.DATA_PATH)
		os.system("curl 'http://catalog.civicdashboards.com/dataset/efabb263-311f-47fe-b63a-09b56e44105a/resource/407919f3-6013-4635-af11-b51bd6adadff/download/dem2013acs5yrntadata.csv' -o '%sdemo_census_data.csv'" % self.DATA_PATH)
		return self


	def _pull_geom(self):
		results = requests.get(self.NEIGHBORHOOD_URL)
		j = json.loads(results.content)
		neighborhood_data = []
		for n in j['features']:
			neighborhood_dict = n['properties']
			if not re.match('park-cemetery-etc.*|Airport', neighborhood_dict['NTAName']):
				if len(n['geometry']['coordinates'])>1:
					geom = []
					for p in n['geometry']['coordinates']:
						if len(p)==1:
							geom += p[0]
						else:
							geom += p
					n['geometry']['coordinates'] = [geom]
				neighborhood_dict['the_geom_community'] = [(k[1], k[0]) for i in n['geometry']['coordinates'] for k in i]
				neighborhood_data.append(neighborhood_dict)
		return pd.DataFrame(neighborhood_data).rename(columns={'NTAName': 'COMMUNITY', 'NTACode': 'Community Area'})

	def get_neighborhood_name(self, df):
		df = self._get_area_name(df, 'community', 'Community Area')
		df['Community Area Number'] = df['Community Area']
		return df
	
	def get_precinct_name(self, df):
		df = self._get_area_name(df, 'precinct', 'Precinct')
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
			area_data['use_flag'] = area_data['COMMUNITY'].map(lambda x: 1 if not re.match('park-cemetery-etc.*|Airport', x) else 0)
			area_data = area_data[area_data.use_flag==1]
		return [row[col] for i, row in area_data.iterrows() if row['path'].contains_point([lat, lng])]

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


	@staticmethod
	def communities(df):
		community = dict()
		community.setdefault('All', {})

		econ_census = pd.read_csv("gunviolence/data/new_york/economic_census_data.csv")
		demo_census = pd.read_csv("gunviolence/data/new_york/demo_census_data.csv")
		census = econ_census.merge(demo_census, on='GeoID').rename(columns={'GeoID': 'Community Area Number'}).set_index('Community Area Number')

		if set(['the_geom_community', 'Community Area']) < set(df.columns):
			for index1, row1 in df.iterrows():
				community['All'].setdefault('adj_list', []).append(row1['Community Area'])
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
				if 'WEAPON' in str(row['Description']) or 'WEAPON' in str(row['Primary Type']):
					indexes.append(i)
		self.df.loc[indexes, 'WEAPON_FLAG'] = 1
		return self



class PivotData(NewYorkData):
	def __init__(self, fields, dt_format, *args, **kwargs):
		NewYorkData.__init__(self, *args)
		kwargs.setdefault('repull', False)
		self.fields = self._set_list(fields)
		self.dt_format = dt_format
		if 'csv' in kwargs:
			self.csv = self.DATA_PATH + kwargs['csv']
		else:
			self.csv = ""

		if not kwargs['repull'] and os.path.isfile(self.csv):
			self._data = pd.read_csv(self.csv)
		else:
			self.initData(**kwargs)
			self.pivot()

	def pivot(self):
		data = self.df.copy()
		data = self.filter_df(data)
		if ('COMMUNITY' in self.fields) or ('Community Area' in self.fields) or ('Community Area Number' in self.fields):
			data = self.get_neighborhood_name(data)
		if 'Precinct' in self.fields:
			data = self.get_precinct_name(data)
		sep = '---'
		data['Period'] = data['Date'].map(lambda x: datetime.strptime(x, '%m/%d/%Y').strftime(self.dt_format))
		print data
		for c in data.columns:
			print c
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
		data.loc[:, dt_filter] = data[dt_filter].fillna(0)
		if filter_zero:
			data = data[data[dt_filter]>0].reset_index(drop=True)
		norm = np.linalg.norm(data[dt_filter].fillna(0))
		data.loc[:, 'fill_opacity'] = data[dt_filter]/norm
		data.loc[:, 'fill_opacity'] = data.loc[:, 'fill_opacity'] / max(data.loc[:, 'fill_opacity'] )
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

	csv = 'community_marker.csv'
	fields = ['Latitude', 'Longitude', 'Community Area', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	# csv = 'precinct_marker.csv'
	# fields = ['Latitude', 'Longitude', 'Precinct', 'Primary Type']
	# p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv)

	# csv = 'heatmap.csv'
	# fields = ['Latitude', 'Longitude']
	# p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv)

	# csv = 'incident_marker.csv'
	# fields = ['Latitude', 'Longitude', 'Location', 'Primary Type']
	# p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv)

	csv = 'census_correlation.csv'
	fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	p = PivotData(fields, '%Y', ['WEAPON_FLAG', 1], csv=csv, repull=True)

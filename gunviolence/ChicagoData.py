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
from runserver import args



class ChicagoData():
	def __init__(self, *args):
		self.DATA_PATH =  os.path.join(os.path.dirname(__file__), "data/")
		self.CSV_FILE = self.DATA_PATH + "Crimes_-_2010_to_present.csv"
		self.df = pd.DataFrame()
		self.meta = dict()
		self.gun_fbi_codes = ['01A', '2', '3', '04B', '04A', '15']
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

		if 'download_fbi' in kwargs:
			if kwargs['download_fbi']:
				self.pull_fbi_codes()

		if 'limit' in kwargs:
			if kwargs['limit']:
				limit = kwargs['limit']
		else:
			limit = None

		self.read_data(limit=limit)
		self._apply_weapons_flag()
		self.read_meta()
		self.merge_meta()
		return self

	def read_data(self, limit=None):
		self.df = pd.read_csv(self.CSV_FILE, nrows=limit)
		return self	

	def read_meta(self):
		self.meta['district'] = self._read_district()
		self.meta['community'] = self._read_community()
		self.meta['beat'] = self._read_beat()
		self.meta['census'] = self._read_census()
		self.meta['fbi'] = self._read_fbi()
		
	def _read_community(self):
		community = pd.read_csv(self.DATA_PATH + 'community_areas.csv')
		return community
		
	def _read_beat(self):
		beat = pd.read_csv(self.DATA_PATH + 'police_beat.csv')
		return beat
		
	def _read_district(self):
		police_district = pd.read_csv(self.DATA_PATH + 'police_districts.csv')
		return police_district
		
	def _read_census(self):
		census = pd.read_csv(self.DATA_PATH + 'census_data.csv')
		return census[~np.isnan(census['Community Area Number'])]

	def _read_fbi(self):
		fbi = pd.read_csv(self.DATA_PATH + 'fbi.csv')
		return fbi

	def pull_fbi_codes(self):
		url = "http://gis.chicagopolice.org/clearmap_crime_sums/crime_types.html"
		response = requests.get(url)
		content = response.content
		codes = re.findall("\r\n\t+.+<br>|\r\n\t+.+</td>", content)
		regex = '.*</span><span class="crimetype"><a href="#.*">(.+).*\((.+)\)</a>.*'
		special_codes = [re.match(regex, c.replace(' (Index)', '').replace("\r", "").replace("\t", "").replace("\n", "")).groups() for c in codes if '</span><span class="crimetype"><a href=' in c]
		special_codes_ordered = [(c[1], c[0]) for c in special_codes]
		codes_clean = [re.sub('<td.*\"\d+\">|</[a-zA-Z]+>|<br>', "", c.replace("\r", "").replace("\t", "").replace("\n", "")) for c in codes]
		codes_split = [tuple(c.split(' ', 1)) for c in codes_clean if re.match("^\d", c)]
		pd.DataFrame(codes_split+special_codes_ordered, columns=['CODE', 'FBI DESCRIPTION']).to_csv(self.DATA_PATH + 'fbi.csv')
		return self

	def pull_data(self):
		os.system("curl 'https://data.cityofchicago.org/api/views/diig-85pa/rows.csv?accessType=DOWNLOAD' -o '%sCrimes_-_2010_to_present.csv'" % self.DATA_PATH)
		return self

	def merge_meta(self):
		self.df = self.df.merge(self.meta['district'], how='left', left_on='District', right_on='DIST_NUM', suffixes=('', '_district'))
		self.df = self.df.merge(self.meta['community'], how='left', left_on='Community Area', right_on='AREA_NUMBE', suffixes=('', '_community'))
		self.df = self.df.merge(self.meta['beat'], how='left', left_on='Beat', right_on='BEAT_NUM', suffixes=('', '_beat'))
		self.df = self.df.merge(self.meta['census'], how='left', left_on='Community Area', right_on='Community Area Number')
		self.df = self.df.merge(self.meta['fbi'], how='left', left_on='FBI Code', right_on='CODE')
		self.df['the_geom_district'] = self.df['the_geom']
		return self

	def pull_metadata(self):
		os.system("curl 'https://data.cityofchicago.org/api/views/z8bn-74gv/rows.csv?accessType=DOWNLOAD' -o '%spolice_stations.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofchicago.org/api/views/c7ck-438e/rows.csv?accessType=DOWNLOAD' -o '%sIUCR.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofchicago.org/api/views/n9it-hstw/rows.csv?accessType=DOWNLOAD' -o '%spolice_beat.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofchicago.org/api/views/24zt-jpfn/rows.csv?accessType=DOWNLOAD' -o '%spolice_districts.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofchicago.org/api/views/k9yb-bpqx/rows.csv?accessType=DOWNLOAD' -o '%swards.csv'" % self.DATA_PATH)
		os.system("curl 'https://data.cityofchicago.org/api/views/igwz-8jzy/rows.csv?accessType=DOWNLOAD' -o '%scommunity_areas.csv'" % self.DATA_PATH)		
		os.system("curl 'https://data.cityofchicago.org/api/views/kn9c-c2s2/rows.csv?accessType=DOWNLOAD' -o '%scensus_data.csv'" % self.DATA_PATH)
		return self



	@classmethod
	def geom_to_list(cls, df):
		for c in df.columns: 
			if re.match('the_geom.*', c):
				df[c] = df[c].map(lambda x: cls._parse_geom(x))
		return df


	@staticmethod
	def _parse_geom(coords):
		if isinstance(coords, basestring):
			coord_sets = re.match("MULTIPOLYGON \(\(\((.*)\)\)\)", coords).group(1)
			coord_strings = [re.sub("\(|\)", "", c).split(" ") for c in coord_sets.split(", ")]
			coord_list = tuple([(float(c[1]), float(c[0])) for c in coord_strings])
		elif isinstance(coords, (list, tuple)):
			coord_list = tuple(coords)
		return coord_list


	@staticmethod
	def communities(df):
		community = dict()
		community.setdefault('All', {})

		census = pd.read_csv("gunviolence/data/census_data.csv")
		census['Community Area Number'] = census['Community Area Number'].fillna('All')
		census = census.set_index('Community Area Number')
		census.index = [str(idx) for idx in census.index]

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
		
		return pd.DataFrame(community).T.join(census).fillna(-1)
		

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
			if re.match('.*GUN.*|.*FIREARM.*|.*(?<!NO )WEAPON.*|WEAPON.*', row['Description']) or row['Primary Type']=='WEAPONS VIOLATION':
				indexes.append(i)
		self.df.loc[indexes, 'WEAPON_FLAG'] = 1
		return self



class PivotData(ChicagoData):
	def __init__(self, fields, dt_format, *args, **kwargs):
		ChicagoData.__init__(self, *args)
		kwargs.setdefault('repull', False)
		self.fields = self._set_list(fields)
		self.dt_format = dt_format
		if 'csv' in kwargs:
			self.csv = self.DATA_PATH + kwargs['csv']

		if not kwargs['repull'] and self.csv and os.path.isfile(self.csv):
			self._data = pd.read_csv(self.csv)
		else:
			self.initData(**kwargs)
			self.pivot()

	def pivot(self):
		data = self.df.copy()
		data = self.filter_df(data)
		sep = '---'

		data['Period'] = data['Date'].map(lambda x: datetime.strptime(x, '%m/%d/%Y %I:%M:%S %p').strftime(self.dt_format))
		counts = data.groupby(['Period']+self.fields, as_index=False).count().iloc[:, 0:len(self.fields)+2] 
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
		data.loc[:, 'norm'] = np.linalg.norm(data[dt_filter].fillna(0))
		data.loc[:, 'fill_opacity'] = data[dt_filter]/data['norm']
		data.loc[:, 'fill_opacity'] = data.loc[:, 'fill_opacity'] / max(data.loc[:, 'fill_opacity'] )
		return data

	def clusters(self):
		kms_per_radian = 6371.0088
		epsilon = 1.5 / kms_per_radian
		db = DBSCAN(eps=epsilon, min_samples=1, algorithm='ball_tree', metric='haversine')
		for d in self.date_list:
			data = self._data[self._data[d]>0][['Longitude', 'Latitude']]
			print 'DATA\n', data
			db.fit(np.radians(data))
			cluster_labels = db.labels_
			num_clusters = len(set(cluster_labels))
			for n in set(cluster_labels(num_clusters)):
				print n
			print cluster_labels


	def get_geo_midpoints(self):
		# http://www.geomidpoint.com/calculation.html
		data = self._data.fillna(0)
		groupby_cols = list(set(data.columns) - set(self.date_list) - set(['Longitude', 'Latitude']))
		if (set(['Longitude', 'Latitude']) < set(data.columns)) and (len(groupby_cols) > 0):
			lat = data['Latitude'].map(lambda x: float(x))
			lng = data['Longitude'].map(lambda x: float(x))
			lat = lat*np.pi/180.
			lng = lng*np.pi/180.
			for d in self.date_list:
				data[d + '_X'] = np.cos(lat) * np.cos(lng) * data[d]
				data[d + '_Y'] = np.cos(lat) * np.sin(lng) * data[d]
				data[d + '_Z'] = np.sin(lat) * data[d]
				data = data.groupby(groupby_cols, as_index=False).sum()
				X = data[d + '_X']/data[d]
				Y = data[d + '_Y']/data[d]
				Z = data[d + '_Z']/data[d]
				data[d + '_Lng'] = np.arctan2(Y, X) * 180./np.pi
				Hyp = np.sqrt(X * X + Y * Y)
				data[d + '_Lat'] = np.arctan2(Z, Hyp) * 180./np.pi
			Lat = data[groupby_cols + [d + '_Lat' for d in self.date_list]].fillna(0)
			Lat.columns = groupby_cols + self.date_list
			Lng = data[groupby_cols + [d + '_Lng' for d in self.date_list]].fillna(0)
			Lng.columns = groupby_cols + self.date_list
			return Lat, Lng
		else:
			return pd.DataFrame([], columns=[groupby_cols + self.date_list]), pd.DataFrame([], columns=[groupby_cols + self.date_list])

	def get_midpoint_counts(self):
		data = self._data.fillna(0)
		groupby_cols = list(set(data.columns) - set(self.date_list) - set(['Longitude', 'Latitude']))
		return self._data.groupby(groupby_cols, as_index=False).sum()

	@property
	def Lat_midpoints(self):
		return self.get_geo_midpoints()[0]

	@property
	def Lng_midpoints(self):
		return self.get_geo_midpoints()[1]

	@property
	def count_midpoints(self):
		return self.get_midpoint_counts()
	
	@property
	def data(self):
		return self._data

	@property
	def date_list(self):
		dt_list = list(self._date_cols())
		dt_list.sort()
		return dt_list



def community_crimes(dt_format, *args, **kwargs):
	kwargs['pickle'] = 'community_pivot.obj'
	data_obj = crimes(dt_format, ['Community Area', 'COMMUNITY', 'the_geom_community'],  *args, **kwargs)
	return data_obj

def heatmap_crimes(dt_format, *args, **kwargs):
	kwargs['csv'] = 'heatmap.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude'],  *args, **kwargs)
	return data_obj

def district_markers(dt_format, *args, **kwargs):
	kwargs['pickle'] = 'district_marker.obj'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'DIST_NUM', 'Primary Type'], *args, **kwargs)
	return data_obj

def community_markers(dt_format, *args, **kwargs):
	kwargs['pickle'] = 'community_marker.obj'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'Community Area', 'Primary Type'], *args, **kwargs)
	return data_obj

def beat_markers(dt_format, *args, **kwargs):
	kwargs['pickle'] = 'beat_marker.obj'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'BEAT_NUM', 'Primary Type'], 'beat_marker.obj', *args, **kwargs)
	return data_obj

def incident_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'incident_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'Location', 'Primary Type'], *args, **kwargs)
	return data_obj

def crimes(dt_format,  pivot_cols, *args, **kwargs):
	cd = ChicagoData()
	pivot_cols = cd._set_list(pivot_cols)
	kwargs.setdefault('repull', False)
	if 'csv' in kwargs:
		filepath = cd.DATA_PATH + kwargs['csv']
		data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
	if 'pickle' in kwargs:
		filepath = cd.DATA_PATH + kwargs['pickle']
		if (not kwargs['repull']) and os.path.isfile(filepath):
			f = open(filepath, 'rb')
			data_obj = cPickle.load(f)
			f.close()
		else:
			data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
			f = open(filepath, 'wb')
			data_obj.df = pd.DataFrame([]) 
			cPickle.dump(data_obj, f, protocol=cPickle.HIGHEST_PROTOCOL)
			print '%s pickled' % filename
			f.close()
	return data_obj


crime_dict={}
crime_dict['incident_marker'] = incident_markers('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['heatmap'] = heatmap_crimes('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['community'] = community_crimes('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['district_marker'] = district_markers('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['community_marker'] = community_markers('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['beat_marker'] = beat_markers('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)



if __name__=="__main__":
	pass
	
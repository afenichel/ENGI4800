import pandas as pd
import numpy as np
import os
from datetime import datetime
import numbers
import requests
import re
import cPickle
from sklearn.cluster import DBSCAN
from matplotlib import colors, cm
from statsmodels.api import OLS



class ChicagoData():
	def __init__(self, *args):
		self.DATA_PATH =  os.path.join(os.path.dirname(__file__), "data/chicago/")
		self.CSV_FILE = self.DATA_PATH + "Crimes_2010-2016.csv"
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

		if 'repull' in kwargs:
			if kwargs['repull']:
				self.read_data(limit=limit)
				self._apply_weapons_flag()
				self.read_meta()
				self.merge_meta()
				self.df['CITY'] = 'Chicago'
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
		os.system("curl 'https://data.cityofchicago.org/api/views/h8e4-zn48/rows.csv?accessType=DOWNLOAD' -o '%sCrimes_2010-2016.csv'" % self.DATA_PATH)
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
		# CODE LOOKUP: https://datahub.cmap.illinois.gov/dataset/1d2dd970-f0a6-4736-96a1-3caeb431f5e4/resource/d23fc5b1-0bb5-4bcc-bf70-688201534833/download/CDSFieldDescriptions.pdf
		os.system("curl 'https://datahub.cmap.illinois.gov/dataset/1d2dd970-f0a6-4736-96a1-3caeb431f5e4/resource/8c4e096e-c90c-4bef-9cf1-9028d094296e/download/ReferenceCCA20102014.csv' -o '%sCMAP_census_data.csv'" % self.DATA_PATH)
		return self

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

		census = pd.read_csv("gunviolence/data/chicago/census_data.csv")
		census['Community Area Number'] = census['Community Area Number'].fillna('All')
		census = census.set_index('Community Area Number')
		census.index = [str(int(idx)) if idx!="All" else idx for idx in census.index]

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
		community.index =  [str(int(idx)) if idx!="All" else idx for idx in community.index]
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

	def clusters(self):
		kms_per_radian = 6371.0088
		epsilon = 1.5 / kms_per_radian
		db = DBSCAN(eps=epsilon, min_samples=1, algorithm='ball_tree', metric='haversine')
		for d in self.date_list:
			data = self._data[self._data[d]>0][['Longitude', 'Latitude']]
			db.fit(np.radians(data))
			cluster_labels = db.labels_
			num_clusters = len(set(cluster_labels))
	
	@property
	def data(self):
		return self._data

	@property
	def date_list(self):
		dt_list = list(self._date_cols())
		dt_list.sort()
		return dt_list

	def _add_percentage(self, census):
		for c in census.columns:
			if 'Age Cohorts' in c or 'Race and Ethnicity' in c: 
				total_pop = 'General Population: Total Population'
				if c!=total_pop:
					census['%s - Percent' % c] = census[c]/census[total_pop]
			elif 'Employment Status' in c or 'Mode of Travel to Work' in c: 
				total_employment = 'Employment Status: Population 16+ (Labor)'
				if c!=total_employment:
					census['%s - Percent' % c] = census[c]/census[total_employment]
			elif 'Educational Attainment' in c: 
				education = 'Educational Attainment: Population 25+ (Education)'
				if c!=education:
					census['%s - Percent' % c] = census[c]/census[education]
			elif 'Household Income' in c: 
				household = 'General Population: Total Households'
				if c=='Household Income: Median Income 2010-2014 American Community':
					census[c] = census[c]
				elif c!=household:
					census['%s - Percent' % c] = census[c]/census[household]
			elif 'Housing and Tenure' in c or 'Housing Type' in c or 'Housing Size' in c or 'Housing Age' in c: 
				housing_unit = 'Housing: Housing Unit total'
				if c!=housing_unit:
					census['%s - Percent' % c] = census[c]/census[housing_unit]
			elif 'General Population: Total Population' in c: 
				sq_footage = 'SHAPE_AREA'
				if c!= sq_footage:
					census['Population Density'] = census[c]/census[sq_footage]
			elif 'General Population: Total Population' in c:
				pop_change = 'Population: 2010 Census'
				if c!= pop_change:
					census['Population Growth - Percent'] = census[c]/census[pop_change]
		return census

def community_crimes(dt_format, *args, **kwargs):
	data_obj = crimes(dt_format, ['Community Area', 'COMMUNITY', 'the_geom_community'],  *args, **kwargs)
	return data_obj

def heatmap_crimes(dt_format, *args, **kwargs):
	kwargs['csv'] = 'heatmap.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude'],  *args, **kwargs)
	return data_obj

def district_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'district_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'DIST_NUM', 'Primary Type'], *args, **kwargs)
	return data_obj

def community_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'community_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'Community Area', 'Primary Type'], *args, **kwargs)
	return data_obj

def beat_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'beat_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'BEAT_NUM', 'Primary Type'], *args, **kwargs)
	return data_obj

def incident_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'incident_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'Location', 'Primary Type'], *args, **kwargs)
	return data_obj

def city_markers(dt_format, *args, **kwargs):
	kwargs['csv'] = 'city_marker.csv'
	data_obj = crimes(dt_format, ['Latitude', 'Longitude', 'CITY', 'Primary Type'], *args, **kwargs)
	return data_obj

def crime_descriptions(dt_format, *args, **kwargs):
	kwargs['csv'] = 'crime_description.csv'
	data_obj = crimes(dt_format, ['Primary Type', 'Description'], *args, **kwargs)
	return data_obj

def crime_locations(dt_format, *args, **kwargs):
	kwargs['csv'] = 'crime_location.csv'
	data_obj = crimes(dt_format, ['Primary Type', 'Location Description'], *args, **kwargs)
	return data_obj

def trends(dt_format, *args, **kwargs):
	kwargs['csv'] = 'trend.csv'
	data_obj = crimes(dt_format, ['CITY'], *args, **kwargs)
	return data_obj

def crimes(dt_format,  pivot_cols, *args, **kwargs):
	cd = ChicagoData()
	pivot_cols = cd._set_list(pivot_cols)
	kwargs.setdefault('repull', False)
	if 'csv' in kwargs:
		filepath = cd.DATA_PATH + kwargs['csv']
		data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
		print '%s saved to csv' % filepath
	if 'pickle' in kwargs:
		filepath = cd.DATA_PATH + kwargs['pickle']
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

		
if __name__=="__main__":
	csv = 'community_pivot.csv'
	fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	csv = 'beat_marker.csv'
	fields = ['Latitude', 'Longitude', 'BEAT_NUM', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	
	csv = 'community_marker.csv'
	fields = ['Latitude', 'Longitude', 'Community Area', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	csv = 'incident_marker.csv'
	fields = ['Latitude', 'Longitude', 'Location', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	
	csv = 'heatmap.csv'
	fields = ['Latitude', 'Longitude']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	
	csv = 'census_correlation.csv'
	fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	p = PivotData(fields, '%Y', ['WEAPON_FLAG', 1], ['Year', [2010, 2011, 2012, 2013, 2014]], csv=csv, repull=True)

	csv = 'trends.csv'
	fields = ['CITY']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	
	csv = 'crime_location.csv'
	fields = ['Primary Type', 'Location Description']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	csv = 'district_marker.csv'
	fields = ['Latitude', 'Longitude', 'DIST_NUM', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	csv = 'city_marker.csv'
	fields = ['Latitude', 'Longitude', 'CITY', 'Primary Type']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)

	csv = 'crime_description.csv'
	fields = ['Primary Type', 'Description']
	p = PivotData(fields, '%Y-%m', ['WEAPON_FLAG', 1], csv=csv, repull=True)
	

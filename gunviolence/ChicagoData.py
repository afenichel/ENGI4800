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
		self.meta['community'] = self._read_community()
		self.meta['beat'] = self._read_beat()
		self.meta['district'] = self._read_district()
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
		self.df = self.df.merge(self.meta['beat'], how='left', left_on='Beat', right_on='BEAT_NUM', suffixes=('', '_beat'))
		self.df = self.df.merge(self.meta['community'], how='left', left_on='Community Area', right_on='AREA_NUMBE', suffixes=('', '_community'))
		self.df = self.df.merge(self.meta['census'], how='left', left_on='Community Area', right_on='Community Area Number')
		self.df = self.df.merge(self.meta['fbi'], how='left', left_on='FBI Code', right_on='CODE')
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
		coord_sets = re.match("MULTIPOLYGON \(\(\((.*)\)\)\)", coords).group(1)
		coord_strings = [re.sub("\(|\)", "", c).split(" ") for c in coord_sets.split(", ")]
		coord_list = tuple([(float(c[1]), float(c[0])) for c in coord_strings])
		return coord_list
		

	@staticmethod
	def _set_list(f):
		if not isinstance(f, list):
			if isinstance(f, (basestring, numbers.Integral)):
				return [f]
			else:
				return list(f)
		else:
			return f

	

	def regression(self):
		data = self.df
		data_filtered = data[data['Primary Type']=='WEAPONS VIOLATION']
		c = list(self.meta['census'].columns)
		c.remove('Community Area Number')
		c.remove('COMMUNITY AREA NAME')
		c.append('COMMUNITY')
		c.append('SHAPE_AREA')
		c.append('Location Description')
		c.append('Year')
		data_mat = data_filtered[c+['Primary Type']].groupby(c, as_index=False).count()
		
		year =pd.get_dummies(data_mat['Year'])
		loc =pd.get_dummies(data_mat['Location Description'])
		community =pd.get_dummies(data_mat['COMMUNITY'])

		mat = data_mat.join(year).join(loc).join(community).drop('Year', axis=1).drop('Location Description', axis=1).drop('COMMUNITY', axis=1)
		X = mat[[c for c in mat.columns if c!='Primary Type']]
		y = mat['Primary Type']
		
		significant_cols = list()

		print '----------INDIVIDUAL REGRESSION----------'
		for c in X:
			print c
			result = self._model(X[c], y)
			significant_cols += list(result.pvalues[result.pvalues<0.05].axes[0])

		print '----------TOTAL REGRESSIONION----------'
		result = self._model(X, y)

		result = self._model(X[significant_cols], y)
		

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
		self.initData(**kwargs)
		self.fields = self._set_list(fields)
		self.dt_format = dt_format
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
		return self

	def _date_cols(self):
		return set(self._data.columns) - set(self.fields)

	@property
	def data(self):
		return self._data

	@property
	def date_list(self):
		dt_list = list(self._date_cols())
		dt_list.sort()
		return dt_list


def community_crimes(dt_format, *args, **kwargs):
	data_obj = crimes(dt_format, ['Community Area', 'COMMUNITY', 'the_geom_community'], 'community_pivot.obj', *args, **kwargs)
	return data_obj

def heatmap_crimes(dt_format, *args, **kwargs):
	data_obj = crimes(dt_format, ['Latitude', 'Longitude'], 'heatmap.obj', *args, **kwargs)
	return data_obj

def crimes(dt_format,  pivot_cols, filename, *args, **kwargs):
	cd = ChicagoData()
	pivot_cols = cd._set_list(pivot_cols)
	filepath = cd.DATA_PATH + filename
	kwargs.setdefault('repull', False)
	if (not kwargs['repull']) and os.path.isfile(filepath):
		f = open(filepath, 'rb')
		data_obj = cPickle.load(f)
	else:
		f = open(filepath, 'wb')
		data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
		data_obj.df = pd.DataFrame([]) 
		cPickle.dump(data_obj, f, protocol=cPickle.HIGHEST_PROTOCOL)
	f.close()
	return data_obj

print 'args', args
crime_dict={}
crime_dict['community'] = community_crimes('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)
crime_dict['heatmap'] = heatmap_crimes('%Y-%m', ['WEAPON_FLAG', 1], repull=args.repull)





if __name__=="__main__":
	pass
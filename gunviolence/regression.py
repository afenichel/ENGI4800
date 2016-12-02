from ChicagoData import *
from sklearn.model_selection import cross_val_predict
from sklearn.feature_selection import SelectKBest 
from sklearn.feature_selection import chi2
from sklearn.linear_model import LinearRegression
from statsmodels.api import OLS
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, r2_score, explained_variance_score
import matplotlib.pyplot as plt
from datetime import datetime
from dateutil.relativedelta import relativedelta


class Regression():
	def __init__(self, *args):
		pass

	def _model(self, X, y):
		model = OLS(y, X)
		result = model.fit()
		print result.summary()
		return result


	def regression(self, time_model=True, model_by="sk"):
		mat = self.census_scatter(time_model=time_model)
		# X = mat[[c for c in mat.columns if c not in ('COMMUNITY', 'COMMUNITY AREA NAME', 'Community Area', 'Avg. Annual Crimes', 'General Population: Population Change, 2000-10', 'Population: 2000 Census', 'Population: 2000 Census', 'SHAPE_AREA')]]
		if time_model:
			X = mat[self.dummy_cols + ['Crimes_lag1month']]
			y = mat['Crimes']
			i = 'time_series'
		else:
			X = mat[[c for c in mat.columns if 'Pct' in c or c=='Population Density']]
			y = mat['Avg. Annual Crimes']
			i = 'census'

		significant_cols = list()

		fig, ax = plt.subplots(2)
		kf = KFold(n_splits=5)
		best_cols = dict()
		acc = np.zeros((len(X.columns), len(y)))
		for n_features in range(1, len(X.columns)+1):
			SK = SelectKBest(chi2, k=n_features)
			SK.fit(X.values, y.values.astype(int))
			cols = X.columns[np.argsort(SK.scores_)[::-1][0:n_features]]
			best_cols[n_features] = cols
			for fold, (train, test) in enumerate(kf.split(np.arange(len(y)))):
				Xtrain = X[cols].values[train]
				ytrain = y.values[train].astype(int)
				Xtest = X[cols].values[test]
				ytest = y.values[test].astype(int)
				if model_by=="sk":
					LR = LinearRegression()
					LR.fit(Xtrain, ytrain)
					mse = mean_squared_error(ytest, LR.predict(Xtest))
				elif model_by=="sm":
					model = OLS(ytrain, Xtrain)
					result = model.fit()
					mse = result.mse_total 

				
				acc[n_features-1, fold] = mse

				if n_features == 13:
					if model_by=="sk":
						predicted = LR.predict(Xtest)
					elif model_by=="sm":
						predicted = np.zeros(len(ytest))
						for i, x in enumerate(Xtest):
							p = model.predict(result.params, exog=x)
							predicted[i] = p 
					ax[0].scatter(ytest, predicted)
					a =[ytest.min(), ytest.max()]
					ax[0].plot(a, a, 'k--', lw=4)
					ax[0].set_xlabel('Measured')
					ax[0].set_ylabel('Predicted')
		
		avg_acc = np.mean(acc, axis=1)
		print avg_acc
		print len(avg_acc)
		print np.argmin(avg_acc)+1
		ax[1].plot(np.arange(1, len(avg_acc)+1), avg_acc, 'g.')
		fig.savefig('img_%s.png' % i)
		plt.close()


		cols = list(best_cols[np.argmin(avg_acc)+1])
		cols.sort()
		if model_by=="sk":
			LR.fit(X[cols].values, y.values.astype(int))
			print '-------------LINEAR REGRESSION-------------'		
			print "R^2:  %s" % LR.score(X[cols].values, y.values.astype(int))
			print "MSE:  %s" % mean_squared_error(y.values.astype(int), LR.predict(X[cols].values))
			print 'variable:%scoefficients:\n%s' % (' '*(70-len('variable:')), '\n'.join(['%s%s%s' % (n, ' '*(70-len(n)), c) for n, c in zip(cols, LR.coef_)]))

		elif model_by=="sm":
			model = OLS(y.values.astype(int), X[cols])
			result = model.fit()
			print result.summary()


	def crimes(self, city, dt_format,  pivot_cols, *args, **kwargs):
		nd = ChicagoData()
		pivot_cols = nd._set_list(pivot_cols)
		kwargs.setdefault('repull', False)
		if 'csv' in kwargs:
			filepath = nd.DATA_PATH + kwargs['csv']
			data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
			print '%s saved to csv' % filepath
		return data_obj

	def census_scatter(self, city='chicago', values=None, time_model=True):
		fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
		
		csv='census_correlation.csv'
		census_obj = self.crimes(city, '%Y', fields,  ['WEAPON_FLAG', 1], ['Year', [2010, 2011, 2012, 2013, 2014]], csv=csv) 
		census_data = census_obj.data[['COMMUNITY', 'Community Area']]
		census_data['Avg. Annual Crimes'] = census_obj.data[census_obj.date_list].mean(axis=1)
	   
		csv='community_pivot.csv'
		community_obj = self.crimes(city, '%Y-%m', fields,  ['WEAPON_FLAG', 1], csv=csv) 
		community_data = community_obj.data
		
		census_extended = census_obj.read_census_extended(values=values)
		census_data = census_data.merge(census_extended, left_on='COMMUNITY', right_on='COMMUNITY AREA NAME').fillna(0)
		census_area = census_obj._read_community()[['COMMUNITY', 'SHAPE_AREA']]
		census_data = census_data.merge(census_area, on='COMMUNITY')

		if time_model:
			data = census_data.merge(community_data[['COMMUNITY'] + community_obj.date_list], on='COMMUNITY')
			data = pd.melt(data, id_vars = list(census_data.columns), value_vars = community_obj.date_list)
			data.rename(columns={'variable': 'MonthYear', 'value': 'Crimes'}, inplace=True)
			data['Crimes'] = data['Crimes'].fillna(0)

			lag = data[['MonthYear', 'COMMUNITY', 'Crimes']]
			lag['LastMonthYear'] = lag['MonthYear'].map(lambda x: (datetime.strptime(x, '%Y-%m') - relativedelta(months=1)).strftime('%Y-%m'))
			data = data.merge(lag, left_on=['MonthYear', 'COMMUNITY'], right_on=['LastMonthYear', 'COMMUNITY'], suffixes=('', '_lag1month'))
			data['Month'] = data['MonthYear'].str.split('-').map(lambda x: x[1])
			data['Season'] = data['Month'].map(lambda x: 'Season'+str((int(x)-1)/3))

			month_dummies = pd.get_dummies(data['Month'])
			season_dummies = pd.get_dummies(data['Season'])

			self.dummy_cols = list(month_dummies.columns) + list(season_dummies.columns)
			data = data.join(month_dummies).join(season_dummies)
		else:
			data = census_data
		return self._add_percentage(data)



	def _add_percentage(self, census):
		for c in census.columns:
			if 'Age Cohorts' in c or 'Race and Ethnicity' in c: 
				total_pop = 'General Population: Total Population'
				if c!=total_pop:
					census['%s Pct' % c] = census[c]/census[total_pop]
			elif 'Employment Status' in c or 'Mode of Travel to Work' in c: 
				total_employment = 'Employment Status: Population 16+ (Labor)'
				if c!=total_employment:
					census['%s Pct' % c] = census[c]/census[total_employment]
			elif 'Educational Attainment' in c: 
				education = 'Educational Attainment: Population 25+ (Education)'
				if c!=education:
					census['%s Pct' % c] = census[c]/census[education]
			elif 'Household Income' in c: 
				household = 'General Population: Total Households'
				if c=='Household Income: Median Income 2010-2014 American Community':
					census['%s Pct' % c] = census[c]
				elif c!=household:
					census['%s Pct' % c] = census[c]/census[household]
			elif 'Housing and Tenure' in c or 'Housing Type' in c or 'Housing Size' in c or 'Housing Age' in c: 
				housing_unit = 'Housing: Housing Unit total'
				if c!=housing_unit:
					census['%s Pct' % c] = census[c]/census[housing_unit]
			elif 'General Population: Total Population' in c: 
				sq_footage = 'SHAPE_AREA'
				if c!= sq_footage:
					census['Population Density'] = census[c]/census[sq_footage]
			elif 'General Population: Total Population' in c:
				pop_change = 'Population: 2010 Census'
				if c!= pop_change:
					census['Population Growth Pct'] = census[c]/census[pop_change]
		return census

	def box_plot(self, city='chicago'):
		csv = 'crime_location.csv'
		fields = ['Primary Type', 'Location Description']
		location_obj = self.crimes(city, '%Y', fields,  ['WEAPON_FLAG', 1], csv=csv) 
		location_data = location_obj.data.fillna(0)
		location_data = location_data.groupby('Location Description').sum()
		location_data = location_data[location_data['2016-10']>10].sort_values('2016-10', ascending=False).applymap(lambda x: int(x))
		fig, ax = plt.subplots(1)
		ax.boxplot(location_data.values.T)
		ax.set_xticklabels(list(location_data.index), rotation='vertical')
		# plt.show()
		fig.savefig('location_box.png')

if __name__=="__main__":
	R = Regression()
	# census = R.census_scatter()
	# print census
	# census = R.regression(True)
	# census = R.regression(time_model=False)
	# census = R.regression(time_model=False, model_by="sm")
	R.box_plot()
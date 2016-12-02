from ChicagoData import *
from sklearn.model_selection import cross_val_predict
from sklearn.feature_selection import SelectKBest 
from sklearn.feature_selection import chi2
from sklearn.linear_model import LinearRegression
from statsmodels.api import OLS
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt

class Regression():
	def __init__(self, *args):
		pass

	def _model(self, X, y):
		model = OLS(y, X)
		result = model.fit()
		print result.summary()
		return result


	def regression(self):
		mat = self.census_scatter()
		X = mat[[c for c in mat.columns if c not in ('COMMUNITY', 'COMMUNITY AREA NAME', 'Community Area', 'Avg. Annual Crimes', 'General Population: Population Change, 2000-10', 'SHAPE_AREA')]]
		y = mat['Avg. Annual Crimes']
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
				LR = LinearRegression()
				LR.fit(Xtrain, ytrain)
				acc[n_features-1, fold] = mean_squared_error(ytest, LR.predict(Xtest))

				if n_features == 19:
					predicted = LR.predict(Xtest)
					ax[0].scatter(ytest, predicted)
					a =[ytest.min(), ytest.max()]
					ax[0].plot(a, a, 'k--', lw=4)
					ax[0].set_xlabel('Measured')
					ax[0].set_ylabel('Predicted')
		
		avg_acc = np.mean(acc, axis=1)
		print avg_acc
		print len(avg_acc)
		ax[1].plot(np.arange(1, len(avg_acc)+1), avg_acc, 'g.')
		cols = best_cols[np.argmin(avg_acc)+1]
		LR.fit(X[cols].values, y.values.astype(int))
		plt.show()

		print '----------TOTAL REGRESSION----------'
		

		# result = self._model(X[significant_cols], y)



	def crimes(city, dt_format,  pivot_cols, *args, **kwargs):
	    nd = ChicagoData()
	    pivot_cols = nd._set_list(pivot_cols)
	    kwargs.setdefault('repull', False)
	    if 'csv' in kwargs:
	        filepath = nd.DATA_PATH + kwargs['csv']
	        data_obj = PivotData(pivot_cols, dt_format, *args, **kwargs)
	        print '%s saved to csv' % filepath
	    return data_obj

	def census_scatter(self, city='chicago', values=None):
	    csv='census_correlation.csv'
	    fields = ['Community Area', 'COMMUNITY', 'the_geom_community']
	    crime_obj = self.crimes(city, '%Y', fields,  ['WEAPON_FLAG', 1], ['Year', [2010, 2011, 2012, 2013, 2014]], csv=csv) 
	    crime_data = crime_obj.data[['COMMUNITY', 'Community Area']]
	    crime_data['Avg. Annual Crimes'] = crime_obj.data[crime_obj.date_list].mean(axis=1)
	    census_extended = crime_obj.read_census_extended(values=values)
	    census_data = crime_data.merge(census_extended, left_on='COMMUNITY', right_on='COMMUNITY AREA NAME').fillna(0)
	    community_area = crime_obj._read_community()[['COMMUNITY', 'SHAPE_AREA']]
	    census_data = census_data.merge(community_area, on='COMMUNITY')
	    return self._add_percentage(census_data)

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
				if c!=household:
					census['%s Pct' % c] = census[c]/census[household]
			elif 'Housing and Tenure' in c or 'Housing Type' in c or 'Housing Size' in c or 'Housing Age' in c: 
				housing_unit = 'Housing: Housing Unit total'
				if c!=housing_unit:
					census['%s Pct' % c] = census[c]/census[housing_unit]
			elif 'General Population: Total Population' in c: 
				sq_footage = 'SHAPE_AREA'
				if c!= sq_footage:
					census['Population Density'] = census[c]/census[sq_footage]
		return census

		
		
if __name__=="__main__":
	R = Regression()
	census = R.regression()

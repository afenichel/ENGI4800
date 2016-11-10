from gunviolence import app
import argparse

def main():
	app.run(debug=True)


def parse_args():
	parser = argparse.ArgumentParser(description="Chicago_Data")
												
	parser.add_argument("-download_data",  action="store_true",
						help="use to download csv data file")

	parser.add_argument("-download_metadata",  action="store_true",
						help="use to download csv meta data files")
	
	parser.add_argument("-download_fbi",  action="store_true",
						help="pull and parse fbi code data to csv")
												
	parser.add_argument("-repull",  action="store_true",
						help="repull pivot data object")
	
	parser.add_argument("-limit",  metavar='limit', type = int, default=None,
							help="limit size of data for faster testing of code")

	args = parser.parse_args()
	return args

args = parse_args()

if __name__=="__main__":
	main()
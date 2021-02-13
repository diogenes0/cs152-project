import requests
import json
from datetime import datetime

def generate_query(term, limit, site, start, end):
	start_time = start.strftime("%Y-%m-%dT%H:%M:%S.%f")
	end_time = end.strftime("%Y-%m-%dT%H:%M:%S.%f")
	return "https://api.smat-app.com/content?term={}&limit={}&site={}&since={}&until={}&esquery=false".format(term, limit, site, start_time, end_time)

def main():
	url = generate_query("storm", 10, "reddit", datetime(2020, 1, 1), datetime(2021, 1, 1))
	r = requests.get(url)
	if not r.ok:
		print("Request failed with code {}".format(r.status_code))
	posts = json.loads(r.content)
	print(posts)

if __name__ == "__main__":
	main()

from datetime import date
from datetime import datetime
import pandas as pd
import requests as rq
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
def etl_process():
    listens = pd.read_csv("Ewaoluwa.csv")
    API_KEY=os.getenv("API_KEY")
    USER_AGENT = 'Ewaoluwa'
    user='ewaoluwa'
    unix_time = int(listens.iloc[0]['unix_time'])
    

    def lastfmlookup(payload):
        headers= {'user-agent': USER_AGENT}
        url = 'https://ws.audioscrobbler.com/2.0/'
        payload['limit'] = 200
        payload['user']= user
        payload['api_key'] = API_KEY
        payload['format'] = 'json'
        
        response= rq.get(url,headers=headers, params=payload)
        return response

    responses= []

    page=1
    total_pages= 9999

    while page <= total_pages:
        payload= {
            'method': 'user.getrecenttracks',
            'limit': 200,
            'user':user,
            'page' : page,
            'from' : unix_time
        }

        print("Requesting page {}/{}".format(page, total_pages))
        
        response = lastfmlookup(payload)
        
        page = int(response.json()['recenttracks']['@attr']['page'])
        total_pages = int(response.json()['recenttracks']['@attr']['totalPages'])
        responses.append(response)
        page +=1
    frames = [pd.DataFrame(r.json()['recenttracks']['track']) for r in responses]
    tracks = pd.concat(frames)
    #transformation
    tracks=tracks.drop(['mbid','streamable'], axis=1)
    tracks['unix_time'] = tracks['date'].apply(lambda x: x['uts'])
    tracks['date'] = tracks['date'].apply(lambda x: x['#text'])
    tracks['date'] = tracks['date'].apply(lambda x: datetime.strptime(x, '%d %b %Y, %H:%M'))
    import ast
    def extract_medium_link(row):
        try:
            row_list = ast.literal_eval(row)
            for item in row_list:
                if item[size] == 'medium':
                    return item['#text']
        except (ValueError, SyntaxError):
            pass  # Handle the case where the data can't be parsed
        
        return None  # Return None if a medium-sized image is not found

    tracks['image'] = tracks['image'].apply(extract_medium_link)

    tracks['artist']= tracks['artist'].apply(lambda x: x['#text'])
    tracks['album']= tracks['album'].apply(lambda x: x['#text'])
    tracks=tracks.rename(columns={'name':'song_title'})
    full_tracks=pd.concat([tracks,listens], ignore_index=True)
    csv_file = 'Ewaoluwatoday.csv'
    full_tracks.to_csv( csv_file, index=False)
    
    return full_tracks, csv_file
full_tracks, csv_file=etl_process()

def github_write(full_tracks,csv_file):
    from github import Github
    REPO_KEY=os.getenv("REPO_KEY")
    g = Github(REPO_KEY)
    
    csv_data = full_tracks.to_csv(index=False)
    timestamp=datetime.now()
    filename=f"result_{timestamp.isoformat()}.csv"
    repo = g.get_repo('EwaoluwaO/MusicHistoryPipeline')
    
    repo.create_file(filename, 'upload csv', csv_data, branch='main')
github_write(full_tracks, csv_file)

Create `.env` file
---
API_KEY = os.getenv("LASTFM_API_KEY")
USERNAME = os.getenv("LASTFM_USERNAME")

When you clone this repo you want to create your own personal `.env` file. Paste the 2 lines above inside the new `.env` file and replace the quoted paramaters with your API credentials

To get the API credentials go here `https://www.last.fm/api/account/create`, use the same email that you created your last.fm account with to create the api account (Should receive the codes isntantly after)

Running `test.py`
---
To run `test.py` make sure all the dependencies in `requirements.txt` are installed. To install them as easy as possible activate a virtual environment, then inside teh virtual environment type in the command `pip -r requirements.txt`

Now the code should be able to run, and print our your most scrobbled track.





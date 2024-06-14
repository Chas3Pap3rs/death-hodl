Chase Poulton

* A crypto trading simulator that grants registered users $100k balance to purchase cryptocurrencies. Users can get points for referrals that they can trade for dollars to their portfolio. Death Hodl utilizes the coingecko api for pulling real crypto data. 
    - deathhodl.com (coming soon)

* Installation instructions: To run on your own local machine, be sure to install all the requirements listed in the requirements.txt file: pip install -r requirements in your virtual environment. Once you have installed all the requirements in your virtual environment run: python manage.py runserver to view and interact with Death Hodl. Enjoy!

* Additional information: This app utilizes the FREE coingecko api, this limits the amount of calls that can be made. This app handles too many requests by not showing current prices or market data, if you see prices listed as 0, or no chart renders (on the charts page), then you have made too many api calls too fast. Future error handling is planned to inform the user better of these instances. I am also considering purchasing the Analyst API Plan which should eliminate these adverse experiences for the user. 

* Tech Used: HTML, CSS, JS, Python, Django, Pandas, Bootstrap, CDN Fonts, Font Awesome, Chart.js, jQuery, Popper, CoinGecko API, SQLite3

* Ideas for future improvement (minimum of 3)
    1. Fix deployment issues on VPS, get the live site working, and upgrade API access to allow for more calls
    2. Interactive charts with more viewing options
    3. Add Stocks
    4. Add comparable/realistic broker fees for trades
    5. Add trade history to portfolio or give it its own page


* User stories:
    1. As Max, I want to refer my friends, so we can enjoy learning/practicing crypto investing together.
    2. As Grim, I want to view historical price charts so that I can make an educated decision about which crypto. 
    3. As Renee, I want to check the top 100 crypto's so that I can get some insight on what coins/tokens are trending.


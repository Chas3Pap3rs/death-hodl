import json
import requests
import pandas as pd
from requests import Request, Session
from decimal import Decimal
from django.contrib import auth, messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.defaultfilters import slugify
from django.utils.http import urlsafe_base64_decode
from django.urls import reverse

from .forms import CustomUserCreationForm
from .models import Cryptocurrency, Portfolio, Profile, Referal, User

from plotly.graph_objs import Candlestick


def login_view(request):
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=raw_password)
            if user is not None:
                login(request, user)
                return redirect('portfolio')
        else:
            messages.error(request, "Invalid username or password.", extra_tags='danger')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


@login_required(login_url="login")
def logout_view(request):
    logout(request)
    messages.success(request, 'You have successfully logged out!')
    return redirect('home')

def signup_view(request):
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')
    
    if request.method == 'POST':
            form = CustomUserCreationForm(request.POST)
            
            if form.is_valid():
                user = form.save(commit=False)
                user.password = make_password(form.cleaned_data['password1'])
                user.email = form.cleaned_data['email']
                user.save()
                # Create new portfolio for user with initial cash balance and portfolio value
                Portfolio.objects.create(user=user, cash_balance=Decimal('100000.00'), crypto_value=Decimal('0.00'))
                messages.success(request, 'You have successfully signed up!', extra_tags='success')
                return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


# block access to signup page if user is already logged in
def signup_with_referrer_view(request, referral_code):
    
    # check if user is already logged in
    if request.user.is_authenticated:
        return redirect('portfolio')
            
    try:
        # get the User Profile of the referrer
        referrer = User.objects.get(profile__referral_code=referral_code)
    except User.DoesNotExist:
        # show error message if referrer does not exist
        return HttpResponse("Referrer does not exist")

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password1'])
            user.email = form.cleaned_data['email']
            user.save()
            # Create new portfolio for user with initial cash balance and portfolio value
            Portfolio.objects.create(user=user, cash_balance=Decimal('100000.00'), crypto_value=Decimal('0.00'))
            # create a referral instance
            referral = Referal.objects.create(user=user, referrer=referrer)
            referral.save()

            if referrer is not None:
                referrer.profile.bonus += 100  # add referral bonus to referrer
                referrer.profile.save()
                messages.success(request, f'{referrer.username} recieved a bonus of 100 points from you because you signed up using their referral link!')

            
            messages.success(request, 'You have successfully signed up!')
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'signup.html', {'form': form, 'referrer': referrer})



@login_required(login_url="login")
def portfolio_view(request):
    # get the current logged in user
    current_user = request.user

    # get the referal code of the current user
    referral_code = current_user.profile.referral_code

    # get a list of all users who have the current user as their referrer
    referrals = Referal.objects.filter(referrer=current_user)

    # get total bonus earned by the current user
    total_bonus = current_user.profile.bonus

    # get the list of cryptocurrencies owned by the current user
    user_cryptocurrencies = Cryptocurrency.objects.filter(user=current_user)

    if user_portfolio := Portfolio.objects.filter(user=current_user).first():
      portfolio = Portfolio.objects.get(user=current_user)

      context = {
          'current_user': current_user,
          'referral_code': referral_code,
          'user_cryptocurrencies': user_cryptocurrencies,
          'portfolio': portfolio,  # Changed 'user_portfolio' to 'portfolio'
          'referrals': referrals, 
          'total_bonus': total_bonus,
          'total_value': portfolio.total_value,  # Changed 'new_portfolio_value' to 'total_value'
      }

    else:
    
      context = {
            'current_user': current_user,
            'referral_code': referral_code,
            'user_cryptocurrencies': user_cryptocurrencies,
            'user_portfolio': user_portfolio,
            'referrals': referrals, 
            'total_bonus': total_bonus,

        }
    return render(request, 'portfolio.html', context)


def home_view(request):
    # get the top crypto currencies by market cap
    top_crypto_url_global = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=USD&order=market_cap_desc&per_page=&page=1&sparkline=true'
    # top_crypto_url_global = 'https://api.binance.us'
    top_crypto_data_global = requests.get(top_crypto_url_global).json()

    # check if user is logged in    
    if request.user.is_authenticated:
        
        # get user's crypto currencies
        user_cryptocurrencies = Cryptocurrency.objects.filter(user=request.user)
        user_portfolio = Portfolio.objects.filter(user=request.user).first()
        
        # get the prices and price changes for user's cryptocurrencies
        names = [crypto.name for crypto in user_cryptocurrencies]
        symbols = [crypto.symbol for crypto in user_cryptocurrencies]
        ids = [crypto.id_from_api for crypto in user_cryptocurrencies]
        prices=[]
        
        # NOTE: Only showing the price change for the last 24 hours for now and not the percentage change to reduce the number of api calls. Only 10-20 api calls per minute are allowed for free users. Otherwise, I could have used the /coins/{id}/market_chart?vs_currency=usd&days=1 endpoint to get the price change for the last 24 hours and calculate the percentage change from that.
        for crytpo_id in ids:  
            prices_url = f'https://api.coingecko.com/api/v3/simple/price?ids={crytpo_id}&vs_currencies=usd&include_24hr_change=true'
            prices_data = requests.get(prices_url).json()

            price_change = prices_data[crytpo_id]['usd_24h_change']
            prices.append(price_change)
            
        # make a dictionary out of the names and prices
        crypto_price_changes = dict(zip(names, prices))
            
        context = {
            'top_crypto_data_global': top_crypto_data_global,
            'user_cryptocurrencies': user_cryptocurrencies,
            'user_portfolio': user_portfolio,
            'crypto_price_changes': crypto_price_changes,
        }
        
    else:
        context = {'top_crypto_data_global': top_crypto_data_global}    
    return render(request, 'home.html', context)


@login_required(login_url="login")
def buy_view(request):
    if request.method == 'POST':
        pass
    elif request.method == 'GET':  # Correct indentation (one level less)
        # Handle GET requests for displaying search results
        search_query = request.GET.get('search_query')  # Access query string parameter
        if not search_query:
            return HttpResponse('No crypto currency found based on your search query.')

        api_url = f'https://api.coingecko.com/api/v3/search?query={search_query}'
        response = requests.get(api_url)
        search_results = response.json()
        try:
            data = search_results['coins'][0]
        except IndexError:
            return HttpResponse('No crypto currency found based on your search query.')

        coin_id = data['id']
        image = data['large']
        symbol = data['symbol']
        market_cap = data['market_cap_rank']

        # check if the crypto currency is already in the users portfolio and pass that information to the template
        current_user = request.user
        is_already_in_portfolio = False
        if current_user.is_authenticated:
            user_cryptocurrencies = Cryptocurrency.objects.filter(user=current_user)
            for cryptocurrency in user_cryptocurrencies:
                if cryptocurrency.name.lower() == coin_id.lower():
                    is_already_in_portfolio = True
                    break  # Exit the loop after finding a match

        context = {
            'data': data,
            'coin_id': coin_id,
            'image': image,
            'symbol': symbol,
            'market_cap': market_cap,
            'is_already_in_portfolio': is_already_in_portfolio,
        }
        return render(request, 'buy.html', context)

    else:
        return HttpResponseNotAllowed(['GET', 'POST'])  # Explicitly allow both methods
    
@login_required(login_url="login")
def sell_view(request, pk):
    if request.method != 'POST':
        return HttpResponse('Need a crypto currency to sell. Go back to the portfolio page and enter a sell amount.')

    sell_amount_str = request.POST.get('sell_amount')
    if sell_amount_str is None:
        sell_amount = 0.0
    else:
        sell_amount = float(sell_amount_str)

    crypto_currency = Cryptocurrency.objects.get(pk=pk)
    if crypto_currency.quantity < sell_amount:
        messages.error(request, f"Insufficient quantity of {crypto_currency.name}. You only have {crypto_currency.quantity}.")
        return redirect('portfolio')

    total_earned = sell_amount * crypto_currency.current_price
    crypto_currency.quantity -= sell_amount
    crypto_currency.save()

    portfolio = Portfolio.objects.get(user=request.user)
    portfolio.cash_balance += total_earned
    portfolio.crypto_value -= total_earned
    portfolio.total_value = portfolio.cash_balance + portfolio.crypto_value
    portfolio.save()

    messages.success(request, f"{sell_amount} {crypto_currency.symbol} has been sold for ${total_earned:.2f}.")
    return redirect('portfolio')

    
# @login_required(login_url="login")
# def add_to_portfolio_view(request):
#     if request.method != 'POST':
#         return HttpResponse('Need a crypto currency to add to your portfolio. Go back to the home page and search for a crypto currency.')
    
#     # get values from the form
#     coin_id = request.POST.get('id')
#     quantity = request.POST.get('quantity')
#     print(coin_id)
    
#     # get the crypto currency data from the coingecko api based on the coin id
#     api_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
#     response = requests.get(api_url)
#     data = response.json()
#     print(data)
#     # store the name, symbol, current price, and market cap rank of the crypto currency
#     user = request.user
#     name = data['name']
#     id_from_api = data['id']
#     symbol = data['symbol']
#     current_price = data['market_data']['current_price']['usd']

#     try:
#         # save the crypto currency to the database
#         crypto_currency = Cryptocurrency.objects.create(
#             user = user,
#             name= name,
#             id_from_api= id_from_api,
#             symbol= symbol,
#             quantity= quantity,
#             current_price=current_price,
#         )
#     except IntegrityError:
#         crypto_currency = Cryptocurrency.objects.get(user=user, name=name)
#         crypto_currency.quantity += int(quantity)


#     crypto_currency.save()

#     # calculate the total value of the crypto currency
#     total_value = int(quantity) * int(current_price)

#     # save the total value of the crypto currency to the database in the portfolio model
#     # check if the user already has a portfolio
#     if Portfolio.objects.filter(user=user).exists():
#         portfolio = Portfolio.objects.get(user=user)
#         portfolio.total_value += total_value
#     else: 
#         portfolio = Portfolio(user=user, total_value=total_value)     

#     portfolio.save()
#     messages.success(request, f'{name} has been added to your portfolio.')

#     # if all the above steps are successful, redirect the user to the portfolio page
#     return redirect('portfolio') 
  
@login_required(login_url="login")
def add_to_portfolio_view(request):
  if request.method != 'POST':
    return HttpResponse('Need a crypto currency to add to your portfolio. Go back to the home page and search for a crypto currency.')

  # Get values from the form (changed to buy amount)
  coin_id = request.POST.get('id')
  buy_amount_str = request.POST.get('buy_amount')

  # Check if buy_amount is provided, if not set it to 0
  if buy_amount_str is None:
      buy_amount = 0.0  # Or set a default value as needed
  else:
      buy_amount = float(buy_amount_str)

  # Get crypto data from API
  api_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
  response = requests.get(api_url)
  data = response.json()
  current_price = data['market_data']['current_price']['usd']

  user = request.user
  existing_cryptocurrency = Cryptocurrency.objects.filter(user=user, name=data['name']).first()

    # Check for existing cryptocurrency and update quantity if found
  if existing_cryptocurrency:
      quantity = buy_amount / float(current_price)
      # existing_cryptocurrency.quantity += quantity
      existing_cryptocurrency.quantity += Decimal(str(quantity))
      existing_cryptocurrency.save()
      messages.success(request, f'{existing_cryptocurrency.name} quantity has been updated in your portfolio.')
      return redirect('portfolio')

  # Calculate quantity based on buy amount and price (only if new)
  quantity = buy_amount / float(current_price)

   # Get user's portfolio
  portfolio, _ = Portfolio.objects.get_or_create(user=user)

  # Check if user has enough cash balance
  if portfolio.cash_balance < buy_amount:
    messages.error(request, "Insufficient funds. Please enter a lower amount.")
    return redirect('buy')

  # Save cryptocurrency to database
  crypto_currency, created = Cryptocurrency.objects.get_or_create(
      user=user,
      name=data['name'],
      id_from_api=data['id'],
      symbol=data['symbol'],
      current_price=current_price,
  )
  if created:
    crypto_currency.quantity = quantity
  else:
    crypto_currency.quantity += quantity
  crypto_currency.save()

  # Update user cash balance and portfolio value
  portfolio.cash_balance -= buy_amount
  portfolio.crypto_value += crypto_value
  portfolio.total_value = portfolio.cash_balance + portfolio.crypto_value
  portfolio.save()

  messages.success(request, f'{crypto_currency.name} has been added to your portfolio.')
  return redirect('portfolio')



@login_required(login_url="login")
def delete_from_portfolio_view(request, pk):
  # Get the current logged in user
  user = request.user

  # Get the sell quantity from the form
  sell_quantity = float(request.POST.get('sell_quantity'))

  # Get the cryptocurrency object from the database
  crypto_currency = Cryptocurrency.objects.get(pk=pk)

  # Check if user has sufficient quantity to sell
  if crypto_currency.quantity < sell_quantity:
      messages.error(request, f"Insufficient quantity of {crypto_currency.name}. You only have {crypto_currency.quantity}.")
      return redirect('portfolio')

  # Get current price from existing logic (assuming it's retrieved before)
  current_price = crypto_currency.current_price

  # Calculate total earned amount from selling
  total_earned = sell_quantity * current_price

  # Update cryptocurrency quantity
  crypto_currency.quantity -= sell_quantity
  crypto_currency.save()

  # Get user's portfolio
  portfolio = Portfolio.objects.get(user=user)

 # Update user cash balance
  portfolio.cash_balance += total_earned
  portfolio.crypto_value -= (crypto_currency.quantity + sell_quantity) * current_price + remaining_value
  portfolio.total_value = portfolio.cash_balance + portfolio.crypto_value
  portfolio.save()

  # Update portfolio total value (considering remaining quantity)
  remaining_value = crypto_currency.quantity * current_price
  portfolio.crypto_value -= (crypto_currency.quantity + sell_quantity) * current_price + remaining_value
  portfolio.save()

  messages.success(request, f"{sell_quantity} {crypto_currency.symbol} has been sold for ${total_earned:.2f}.")
  return redirect('portfolio')


# @login_required(login_url="login")      
# def delete_from_portfolio_view(request, pk):
#     # get the current logged in user
#     user = request.user
    
#     # get the crypto currency object from the database
#     crypto_currency = Cryptocurrency.objects.get(pk=pk)
    
#     # delete the crypto currency from the database
#     crypto_currency.delete()
    
#     # update the total value of the portfolio
#     portfolio = Portfolio.objects.get(user=user)
    
#     # get all the crypto currencies in the portfolio and recalculate the total value of the portfolio
#     user_cryptocurrencies = Cryptocurrency.objects.filter(user=user)
#     for cryptocurrency in user_cryptocurrencies:
#         total_value = cryptocurrency.quantity * cryptocurrency.current_price
#         portfolio.total_value += total_value
    
#     portfolio.save()    

#     # send an alert to the user that the crypto currency has been deleted from the portfolio
#     messages.warning(request, f'{crypto_currency.name} has been deleted from your portfolio.')
    
#     return redirect('portfolio')


def reset_portfolio_view(request):
    # Delete all of the user's crypto holdings
    Cryptocurrency.objects.filter(user=request.user).delete()

    # Get the user's portfolio
    portfolio = Portfolio.objects.get(user=request.user)

    # Reset the user's cash balance and crypto value to their initial values
    portfolio.cash_balance = Decimal('100000.00')
    portfolio.crypto_value = Decimal('0.00')
    portfolio.save()

    messages.success(request, 'Your portfolio has been reset.')
    return redirect('portfolio')


@login_required(login_url="login")
def delete_account_view(request):
    user = request.user

    # Delete user's related objects
    Portfolio.objects.filter(user=user).delete()
    Cryptocurrency.objects.filter(user=user).delete()
    Referal.objects.filter(user=user).delete()
    Profile.objects.filter(user=user).delete()

    # Delete user
    user.delete()

    messages.success(request, 'Your account has been deleted.')
    return redirect('home')








def crypto_chart(request):
  # Available cryptocurrencies (replace with your actual choices)
  crypto_choices = [
      ("bitcoin", "Bitcoin (BTC)"),
      ("ethereum", "Ethereum (ETH)"),
      ("bnb", "Binance Coin (BNB)"),
  ]

  # If form is submitted, process data
  if request.method == 'POST':
    cryptocurrency = request.POST.get('cryptocurrency')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')

    # API call with error handling
    try:
      url = f"https://api.coingecko.com/api/v3/coins/{cryptocurrency}/ohlcv/daily?from={start_date}&to={end_date}"
      response = requests.get(url)
      response.raise_for_status()  # Raise exception for non-200 status codes

      # Parse JSON data
      data = response.json()
      timestamps, prices = zip(*data)

      # Convert timestamps to datetime objects
      df = pd.DataFrame({'timestamp': timestamps, 'price': prices})
      df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

      # Create candlestick chart with Plotly
      candlestick = Candlestick(
          x=df['timestamp'],
          open=df['price'].iloc[:-1],  # Open price uses previous day's close
          high=df['price'],
          low=df['price'],
          close=df['price'].iloc[1:],  # Close price uses next day's close
      )

      # Layout options (customize as needed)
      layout = {
          'title': f"{cryptocurrency.upper()} Price Chart",
          'xaxis_title': 'Date',
          'yaxis_title': 'Price (USD)',
          'xaxis_rangeslider_visible': False,
      }

      # Generate chart as a div using Plotly offline capabilities
      plot_div = plot({'data': [candlestick], 'layout': layout}, output_type='div', include_plotlyjs=False)

    except requests.exceptions.RequestException as e:
      error_message = f"An error occurred fetching data: {e}"
      plot_div = None

  else:
    # Initial form rendering
    cryptocurrency = None
    start_date = None
    end_date = None
    plot_div = None
    error_message = None

  return render(request, 'charts.html', {
      'crypto_choices': crypto_choices,
      'cryptocurrency': cryptocurrency,
      'start_date': start_date,
      'end_date': end_date,
      'plot_div': plot_div,
      'error_message': error_message,
  })


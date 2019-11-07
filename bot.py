import json
import time
import ccxt
import requests
from time import sleep
from functools import wraps
from datetime import datetime, timedelta
from telegram.ext import Updater, CommandHandler


def get_config():
    with open("config.json", "r") as read_file:
        config = json.load(read_file)
        return config


def write_config(config):
    with open("config.json", "w") as write_file:
        json.dump(config, write_file, indent=1)


def get_telegram_config():
    telegram_chat_id = get_config()["telegram_chat_id"]
    telegram_bot_key = get_config()["telegram_bot_key"]
    return telegram_chat_id, telegram_bot_key


def get_api_config(account_name):
    for i in get_config()["exchange_api_data"]:
        if i["name"] == account_name:
            key = i["key"]
            secret = i["secret"]
            return key, secret


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        chat_id = int(get_telegram_config()[0])
        if user_id != chat_id:
            # print("Unauthorized access denied for {}.".format(user_id))
            context.bot.send_message(
                chat_id=chat_id,
                text=("Unauthorized access denied for {}.".format(user_id)),
            )
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def exchange(account_name):
    try:
        key = get_api_config(account_name)[0]
        secret = get_api_config(account_name)[1]
        exchange = ccxt.binance(
            {"apiKey": key, "secret": secret, "enableRateLimit": True}
        )
        return exchange

    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))


def usd_price(coin, amount, account_name):
    price = exchange(account_name).fetch_ticker(f"{coin.upper()}/USDC")["last"]
    return price * amount


def number_for_human(number):
    x_str = str(number)
    if "e-0" in x_str:
        return "%.08f" % number  # str
    else:
        return str(number)[:9]  # str

@restricted
def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="For showing all commands type /help",
    )


@restricted
def help(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="/balance\n\n/accounts\n\n/price\n\n/trade\n\n/orders\n\n/cancel_order",
    )


@restricted
def show_all_accounts_names(update, context):
    for i in get_config()["exchange_api_data"]:
        context.bot.send_message(chat_id=update.effective_chat.id,text=i["name"])


@restricted
def fetch_balance(update, context):
    try:
        if len(" ".join(context.args)) == 0:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="/balance <account_name> <coin>\n\nAn example (Balance XRP on account 1): \n/balance account_1 xrp",
                    )
        else:
            account_name = context.args[0]
            coin = context.args[1]

            balance = exchange(account_name).fetch_balance()
            balance = balance[coin.upper()]["free"]

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{balance} {coin.upper()} ~ {round(usd_price(coin, balance, account_name))} USDC",
            )

    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))


@restricted
def get_price(update, context):
    try:
        if len(" ".join(context.args)) == 0:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="/price <account_name> <coin_1> <coin_2>\n\nAn example (Price XRP/BTC): \n/price account_1 xrp btc",
                    )
        else:
            account_name = context.args[0]
            coin_1 = context.args[1].upper()
            coin_2 = context.args[2].upper()
            price = exchange(account_name).fetch_ticker(f"{coin_1}/{coin_2}")["last"]
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{number_for_human(price)}",
            )

    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))


@restricted
def trade(update, context):
    try:
        if len(" ".join(context.args)) == 0:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="/trade <account_name> <buy/sell> <coin_1> <coin_2> <amount> <price>\n\nAn example (Sell XRP/BTC): \n/trade account_1 sell xrp btc 100 0.00003154",
                    )
        else:
            account_name = context.args[0]
            side = context.args[1]  # "buy" or "sell"
            coin_1 = context.args[2].upper()
            coin_2 = context.args[3].upper()
            amount = float(context.args[4])
            price = float(context.args[5])
            symbol = f"{coin_1}/{coin_2}"
            type = "limit"  # "market" or "limit"
            params = {}
            order = (symbol, type, side, amount, price, params)
            order = exchange(account_name).create_order(symbol, type, side, amount, price, params)

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=order,
            )

    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))


@restricted
def show_orders(update, context):
    try:
        if len(" ".join(context.args)) == 0:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="/orders <account_name> <coin_1> <coin_2>\n\nAn example (Open orders XRP/BTC): \n/orders account_1 xrp btc",
                    )
        else:
            account_name = context.args[0]
            coin_1 = context.args[1].upper()
            coin_2 = context.args[2].upper()
            orders = exchange(account_name).fetch_open_orders(f"{coin_1}/{coin_2}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=orders,
            )

    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))


@restricted
def cancel_order(update, context):
    try:
        if len(" ".join(context.args)) == 0:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="/cancel_order <account_name> <order_id> <coin_1> <coin_2>\n\nAn example: \n/cancel_order account_1 257880697 xrp btc",
                    )
        else:
            account_name = context.args[0]
            order_id = int(context.args[1])
            coin_1 = context.args[2].upper()
            coin_2 = context.args[3].upper()
            order = exchange(account_name).cancel_order(order_id, f"{coin_1}/{coin_2}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=order,
            )


    except ccxt.NetworkError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except ccxt.ExchangeError as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))
    except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))




if __name__ == "__main__":

    updater = Updater(get_telegram_config()[1], use_context=True)
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("help", help))
    updater.dispatcher.add_handler(CommandHandler("balance", fetch_balance))
    updater.dispatcher.add_handler(CommandHandler("accounts", show_all_accounts_names))
    updater.dispatcher.add_handler(CommandHandler("price", get_price))
    updater.dispatcher.add_handler(CommandHandler("trade", trade))
    updater.dispatcher.add_handler(CommandHandler("orders", show_orders))
    updater.dispatcher.add_handler(CommandHandler("cancel_order", cancel_order))

    updater.start_polling()
    updater.idle()

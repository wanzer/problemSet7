from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    total = db.execute("SELECT * FROM users WHERE id = :id", id = str(session["user_id"]))[0]["cash"]
    try:
        data = db.execute("SELECT * FROM :id", id =str(session["user_id"]))
    except:
        data = None
    else:
        data = db.execute("SELECT * FROM :id", id =str(session["user_id"]))
    if data:
        gainData = [{'symbol':i['symbol'], 'name': i['name'], 'shares':i['shares'], 'price': i['price'], 'total': i['total'] } for i in data]
        uniqueChar = list({i['symbol'] for i in gainData})
        sharesAmount=[]
        for i in uniqueChar:
            sharesAmount.append([j['shares'] for j in gainData if j['symbol'] == i])
        sharesAmount = [sum(i) for i in sharesAmount]
        amountTotal = []
        for i in uniqueChar:
            amountTotal.append([j['total'] for j in gainData if j['symbol'] == i])
        amountTotal = [sum(i) for i in amountTotal]
        name = []
        price = []
        for i in uniqueChar:
            name.append([j['name'] for j in gainData if j['symbol'] == i])
        name = [i[0] for i in name]
        for i in uniqueChar:
            price.append([j['price'] for j in gainData if j['symbol'] == i])
        price = [i[0] for i in price]
        gainData = list(zip(uniqueChar, name, sharesAmount, price, amountTotal))
        gainData = [i for i in gainData if i[2]>0]
    else:
        gainData = None
    return render_template("index.html", data = gainData, total = total)    
    

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "GET":
         return render_template("buy.html")
    else:
        if (len(lookup(request.form.get("quote")))<3):
             return apology("Wrong quote!")
        elif(request.form.get("quote")==None):
             return apology("Quote must be given")
        elif(int(request.form.get("shares"))<0):
            return apology("Shares quantity must be positive!")
        price = int(lookup(request.form.get("quote"))["price"])
        total = price * int(request.form.get("shares"))
        rows = db.execute("SELECT * FROM users WHERE id = :id", id = str(session["user_id"]))
        if rows[0]['cash']<total:
            return apology("You have not enought money!")
        else:
            db.execute("UPDATE users SET cash = :newCash WHERE id = :id", newCash = rows[0]['cash'] - total,
            id = str(session["user_id"]))
            try:
                len(db.execute("SELECT * FROM :id", id = str(session["user_id"])))
            except:
                db.execute("CREATE TABLE :id (symbol TEXT, name TEXT, shares INTEGER, price NUMERIC, total INTEGER, datetime DATE DEFAULT (datetime('now','localtime')), id INTEGER)",
                id = str(session["user_id"]))
                db.execute("INSERT INTO :id (symbol, name, shares, price, total) VALUES(:symbol, :name, :shares, :price, :total)", 
                id = str(session["user_id"]), symbol = request.form.get("quote"), name = lookup(request.form.get("quote"))["name"], 
                shares = int(request.form.get("shares")), price = price, total = total)
            else:
                db.execute("INSERT INTO :id (symbol, name, shares, price, total) VALUES(:symbol, :name, :shares, :price, :total)", 
                id = str(session["user_id"]), symbol = request.form.get("quote"), name = lookup(request.form.get("quote"))["name"], 
                shares = int(request.form.get("shares")),  price = price, total = total)
            return redirect(url_for("index", buy = 1))    
    

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    data = db.execute("SELECT * FROM :id", id =str(session["user_id"]))
    data = [[i['symbol'], i['shares'], i['price'], i['datetime']] for i in data]
    return render_template("history.html", data = data)
    

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
         return render_template("quote.html")
    else:
        return render_template("quoted.html", name = lookup(request.form.get("quote"))['name'],
        price = usd(lookup(request.form.get("quote"))['price']))
   

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "GET":
          return render_template("register.html")
    else:
        if request.form.get("username") == "":
            return apology("Username must be fill in.")
        elif request.form.get("password") == "" or request.form.get("password_confirm") == "":
            return apology("Password must be fill in.")
        elif request.form.get("password") != request.form.get("password_confirm"):
             return apology("Password don't match!")
        try:
            db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        except:
             hash = pwd_context.encrypt(request.form.get("password"))
             db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"),hash = hash)
            
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows) == 1:
            return apology("User already exists.")
        else:
            hash = pwd_context.encrypt(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash = hash)
            return redirect(url_for("index"))
    
    
    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        if (len(lookup(request.form.get("quote")))<3):
            return apology("Wrong quote!")
        elif(request.form.get("quote")==None):
            return apology("Quote must be given")
        elif(int(request.form.get("shares"))<0):
            return apology("Shares quantity must be possitive!")
        try:
            db.execute("SELECT * FROM :id WHERE symbol = :symbol", id = str(session["user_id"]), symbol = request.form.get("quote"))
        except:
            db.execute("CREATE TABLE :id (symbol TEXT, name TEXT, shares INTEGER, price NUMERIC, total INTEGER, datetime DATE DEFAULT (datetime('now','localtime')), id INTEGER)", 
            id = str(session["user_id"]))
            
        amountShares = db.execute("SELECT * FROM :id WHERE symbol = :symbol", id = str(session["user_id"]), symbol = request.form.get("quote"))
        amountShares = [i['shares'] for i in amountShares]
        amountShares = sum(amountShares)
        if amountShares < int(request.form.get("shares")):
            return apology("You have shares less than you want to sell")
        price = int(lookup(request.form.get("quote"))["price"])
        total = price * int(request.form.get("shares"))
        rows = db.execute("SELECT * FROM users WHERE id = :id", id = str(session["user_id"]))
        db.execute("UPDATE users SET cash = :extraCash WHERE id = :id", extraCash = rows[0]['cash'] + total, id = str(session["user_id"]))
        try:
            len(db.execute("SELECT * FROM :id", id = str(session["user_id"])))
        except:
            db.execute("CREATE TABLE :id (symbol TEXT, name TEXT, shares INTEGER, price NUMERIC, total INTEGER, datetime DATE DEFAULT (datetime('now','localtime')), id INTEGER)", 
            id = str(session["user_id"]))
        else:
             db.execute("INSERT INTO :id (symbol, name, shares, price, total) VALUES(:symbol, :name, :shares, :price, :total)",
             id = str(session["user_id"]), 
             symbol = request.form.get("quote"), name = lookup(request.form.get("quote"))["name"],
             shares =- int(request.form.get("shares")),
             price = price, total = total)
             
    return redirect(url_for("index", sell = 1))
    
@app.route("/addMoreCash", methods=["GET", "POST"])
@login_required
def addMoreCash():
    """add some additional money"""
    if request.method == "POST":
        if int(request.form.get("cash"))<0:
            return apology("Insert possitive value")
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", id =str(session["user_id"]), cash = 
        db.execute("SELECT * FROM users WHERE id = :id", id = str(session["user_id"]))[0]['cash'] + int(request.form.get("cash")))
    else:
        return render_template("addMoreCash.html")
    return redirect(url_for("index"))   

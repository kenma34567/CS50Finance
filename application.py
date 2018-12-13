import os

from cs50 import SQL
#import sqlite3 as lite
from flask import Flask, flash, redirect, render_template, request, session
#from flask_session.__init__ import Session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    r = db.execute("SELECT companyName as Name, latestPrice as Price, Symbol, SUM(Shares) as Shares, SUM(Total) as Total FROM Buy WHERE Buyer = :id GROUP BY Name HAVING SUM(Shares) > 0",
    id=session["user_id"])
    Cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    Cash = Cash_db[0]["cash"]
    return render_template("index.html", stocks = r, Cash = Cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        # Lookup and return name = 0, price = 1, symbol=2
        qlist = []
        symbol = request.form.get("symbol")
        qlist= lookup(symbol)
        if qlist is None:
            return apology("No such Stock", 400)

        # shares = empty
        elif request.form.get("shares") == None:
            return apology("Please input shares")
        else:
            shares = int(request.form.get("shares"))
            rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
            cr = rows[0]["cash"]
            if qlist[1] * shares > cr:
                return apology("Not enough cash")

            # Insert record to DB if no error
            cr -= qlist[1] * shares
            db.execute("UPDATE users SET cash = :cr WHERE id = :id", cr = cr, id = session["user_id"])
            db.execute("INSERT INTO Buy (companyName, latestPrice, Buyer, Symbol, Shares, Total) VALUES(:name, :price, :buyer, :symbol, :shares, :total)",
            name = qlist[0], price=qlist[1], buyer=session["user_id"], symbol=qlist[2], shares=shares, total=qlist[1] * shares)
            return index()
        return apology("GG")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    r = db.execute("SELECT companyName as Name, latestPrice as Price, Symbol, Shares as Shares, Total, Time FROM Buy WHERE Buyer = :id ORDER BY Time DESC",
    id=session["user_id"])

    return render_template("history.html", stocks = r)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Change password"""
    if request.method == "POST":

        # Ensure password was submitted
        if not request.form.get("oldpassword"):
            return apology("must provide Old password", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("Please confirm", 403)

        # Get old hash from DB
        old_pass_db = db.execute("SELECT hash FROM users WHERE id=:id", id=session["user_id"])
        old_pass = old_pass_db[0]["hash"]
        print(old_pass)

        # Check if oldpassword = old_pass
        if (not check_password_hash(old_pass, request.form.get("oldpassword"))):
            return apology("You FAKE")

        # Check if password = confirmation
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Confirmation does not match", 403)

        # Generate hash of password
        hash = generate_password_hash(request.form.get("password"))

        # Insert record to DB if no error
        db.execute("UPDATE users SET hash = :hash WHERE id = :id",
        hash=hash, id=session["user_id"])

        # Return success page
        return render_template("successReg.html")
    else:
        return render_template("settings.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        # Ensure quote was submitted
        if not request.form.get("symbol"):
            return apology("Please provide symbol", 400)

        # Lookup and return name = 0, price = 1, symbol=2
        qlist = []
        symbol = request.form.get("symbol")
        qlist= lookup(symbol)

        if (qlist == None):
            return apology("No such symbol", 400)
        return render_template("quoted.html", name = qlist[0], sym = qlist[2], price = qlist[1])
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Please provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("Please confirm", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
        username=request.form.get("username"))

        # Ensure username does not already exist
        if len(rows) > 0:
            return apology("username already exists", 400)

        # Check if password = confirmation
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Confirmation does not match", 400)

        # Generate hash of password
        hash = generate_password_hash(request.form.get("password"))

        # Insert record to DB if no error
        db.execute("INSERT INTO users (username, hash, cash) VALUES(:username, :hash, 10000)",
        username=request.form.get("username"), hash=hash)

        # Return success page
        return render_template("successReg.html")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    r = db.execute("SELECT Symbol FROM Buy WHERE Buyer = :id GROUP BY Symbol", id=session["user_id"])
    if request.method == "POST":

        #If symbol / shares = empty
        if not request.form.get("symbol"):
            return apology("Choose a symbol")
        if not request.form.get("shares"):
            return apology("Choose shares")

        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        #Get data
        owned_shares_db = db.execute("SELECT Shares FROM Buy WHERE Buyer =:id AND Symbol = :symbol1", id=session["user_id"], symbol1=symbol)
        owned_shares = owned_shares_db[0]["Shares"]
        Price_db = db.execute("SELECT latestPrice FROM Buy WHERE Symbol = :symbol1", symbol1=symbol)
        Price = Price_db[0]["latestPrice"]
        owned_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        owned_cash = owned_cash_db[0]["cash"]
        # Lookup and return name = 0, price = 1, symbol=2
        qlist = []
        qlist= lookup(symbol)

        #If shares > owned_shares
        if shares > owned_shares:
           return apology("You don't own this much shares")
        #return apology(f"{owned_shares}, {shares}")

        #Success
        db.execute("INSERT INTO Buy (companyName, latestPrice, Buyer, Symbol, Shares, Total) VALUES(:name, :price, :buyer, :symbol1, :shar, :total)",
        name=qlist[0],
        price=qlist[1],
        buyer=session["user_id"],
        symbol1=symbol,
        shar=-shares,
        total=qlist[1]*shares)
        db.execute("UPDATE users SET cash = :cr WHERE id = :id",
        cr=owned_cash-(Price*(-shares)), id=session["user_id"])
        return render_template("successReg.html")
    return render_template("sell.html", stocks = r)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

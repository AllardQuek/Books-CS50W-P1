import os
import requests

from flask import Flask, session, render_template, request, redirect, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    # session["user_id"] = user.id ERROR: user in user.id is not defined.
    return render_template("index.html")

@app.route("/register", methods=["POST", "GET"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check if username already exists: flights = db.execute("SELECT * FROM flights").fetchall(), the following DOESN'T WORK..?: does request.form.get return a string?? YES
        # Does db.execute fetchall return a list of strings? ('Charlie',) it returns a LIST of 0 or more dict objects, which are keys and values representing a table’s fields and cells, respectively.
        #allusers = db.execute("SELECT username FROM users").fetchall()
        # if username in allusers:
        if db.execute("SELECT username from users WHERE username = :username", {"username": username}).rowcount >= 1:
            return render_template("error.html", message="This username already exists. Sorry!")

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username": username, "password": password})
        db.commit()
        return render_template("register.html")

        #try: # The way to handle any possibility of error, instead of having "my whole website crash".
            #flight_id = int(request.form.get("flight_id")) #int should not be necessary. #Error occurs when the info extracted is a string for example, and thus cannot be converted into int.
        #except ValueError:
            #return render_template("error.html", message="Invalid flight number.")

    # Else if register route accessed via GET request
    return redirect("/")

@app.route("/search", methods=["POST", "GET"])
def search():
    # if accessed via login home page
    if request.method == "POST":
        # Forget any user_id
        session.clear()

        # Validate user input
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Provide username/password")

        # Check for match in db; need to specify .first() OR .fetchall(), unlike psets in CS50
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchall()
        # print (rows)

        # if username doesn't exist, or password wrong
        if len(rows) != 1 or request.form.get("password") != rows[0]["password"]:
            return render_template("error.html", message="Wrong username/password")

        # Remember which uesr logged in, store id inside session["user_id"]
        session["user_id"] = rows[0]["id"]
        return render_template("search.html")

    if request.method == "GET":
        if session["user_id"]:
            return render_template("search.html")

        else:
            return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/searchresults", methods=["POST"])
def searchresults():

    # If user did not provide any input
    if not request.form.get("query"):
        return render_template("error.html", message="Please enter a query"), 400

    select = request.form.get("select")
    query = request.form.get("query")
    print(select)

    # Note must use || as + operator is not unique and does not work AND note single quotes
    # OR if sqltitle = "%" + title + "%"
    # THEN rows = db.execute("SELECT * FROM books WHERE title LIKE :title", {"title": sqltitle}).fetchall()
    if select == "isbn":
        int_query = int(query)
        rows = db.execute("SELECT * FROM books WHERE (isbn LIKE '%' || :isbn || '%')", {"isbn": int_query}).fetchall()

    elif select == "title":
        rows = db.execute("SELECT * FROM books WHERE (title LIKE '%' || :title || '%')", {"title": query}).fetchall()
    else:
        rows = db.execute("SELECT * FROM books WHERE (author LIKE '%' || :author || '%')", {"author": query}).fetchall()
        print(rows)

    if not rows:
        return render_template("error.html", message="No matching books were found!")

    return render_template("searchresults.html", results = rows)


@app.route("/bookpage")
def bookpage():
    # TODO: implement variable url

    # Book details: title/author/year/isbn/reviews
    # main_details = db.execute("SELECT * FROM books WHERE title = :title", {"title": title}).fetchall()
    # review_details = db.execute("SELECT review FROM reviews WHERE title = :title", {"title": title }).fetchall()

    # Goodreads reviews (using API?)

    # Submit review
    return render_template("bookpage.html")

@app.route("/submitreview", methods=["POST"])
def submitreview():

    return redirect("/bookpage")


@app.route("/api/<int:isbn>")
def api(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "KEY", "isbns": "9781632168146"})
    print(res.json())

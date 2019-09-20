import os
import requests
import datetime

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

        # Does db.execute fetchall return a list of strings? It returns [('Apple',), ('Allard',)] which is a LIST of 0 or more dict objects, which are keys and values representing a table’s fields and cells, respectively.
        # type of result is <class 'sqlalchemy.engine.result.RowProxy'>, which cannot be compared to string returned via request.form.get

        if db.execute("SELECT username from users WHERE username = :username", {"username": username}).rowcount >= 1:
            return render_template("error.html", message="This username already exists. Sorry!")

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username": username, "password": password})
        db.commit()
        return render_template("register.html")

    # Else if method is GET
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/search", methods=["POST", "GET"])
def search():
    # If accessed via login home page
    if request.method == "POST":
        # Forget any user_id
        session.clear()

        # Validate user input
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("error.html", message="Provide username/password")

        # Check for match in db; need to specify .first() OR .fetchall(), unlike psets in CS50
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": request.form.get("username")}).fetchall()

        # If username doesn't exist, or password wrong
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



@app.route("/searchresults", methods=["POST"])
def searchresults():
    # If no input provided
    if not request.form.get("query"):
        return render_template("error.html", message="Please enter a query"), 400

    select = request.form.get("select")
    query = request.form.get("query")

    # Note must use || as + operator is not unique and does not work AND note single quotes
    # OR if sqltitle = "%" + title + "%"
    # THEN rows = db.execute("SELECT * FROM books WHERE title LIKE :title", {"title": sqltitle}).fetchall()

    if select == "isbn":
        try:
            int_query = int(query)
            results = db.execute("SELECT * FROM books WHERE (isbn LIKE '%' || :isbn || '%')", {"isbn": int_query}).fetchall()
        except:
            return render_template("error.html", message="Please fill in properly")

    elif select == "title":
        results = db.execute("SELECT * FROM books WHERE (title LIKE '%' || :title || '%')", {"title": query}).fetchall()

    else:
        results = db.execute("SELECT * FROM books WHERE (author LIKE '%' || :author || '%')", {"author": query}).fetchall()

    if not results:
        return render_template("error.html", message="No matching books were found!")

    return render_template("searchresults.html", results = results)


@app.route("/bookpage/<isbn>")
def bookpage(isbn):
# bookpage function needs to take an argument isbn lest it would not expect a keyword argument

    # Make sure book with isbn exists
    row = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if row is None:
        return render_template("error.html", message="No such book!"), 400

    reviews = db.execute("SELECT review, username, datetime, rating FROM reviews WHERE isbn = :isbn", {"isbn": isbn }).fetchall()

    # Goodreads reviews data using API
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "rp5fatbknRT7djHIMLasw", "isbns": isbn})
    ratings_count = res.json()['books'][0]['work_ratings_count']
    average_rating = res.json()['books'][0]['average_rating']


    return render_template("bookpage.html", row=row, reviews=reviews, ratings_count=ratings_count, average_rating=average_rating)

@app.route("/bookpage/<isbn>/submitreview", methods=["POST"])
def submitreview(isbn):

    # fetchone is important lest ResultProxy object returned instead of RowProxy which has attribute title
    user = db.execute("SELECT username FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()
    book = db.execute("SELECT title FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    # Check if user has already submitted a review
    if db.execute("SELECT review FROM reviews WHERE title = :title AND username = :username", {"title": book.title, "username": user.username}).rowcount >= 1:
        return render_template("error.html", message="Sorry, you may only submit one review!")

    try:
        review = request.form.get("review")
        rating = int(request.form.get("rating"))
    except:
        return render_template("error.html", message="No review!")

    db.execute("INSERT INTO reviews (isbn, title, review, username, datetime, rating) VALUES (:isbn, :title, :review, :username, to_char(current_timestamp, 'DD-MM-YYYY HH12:MI:SS'), :rating)", {"isbn": isbn, "title": book.title, "review": review, "username":user.username, "rating": rating})
    db.commit()

    return redirect(f"/bookpage/{isbn}")


@app.route("/api/<int:isbn>")
def api(isbn):

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "rp5fatbknRT7djHIMLasw", "isbns": isbn})
    if not res:
        return render_template("error.html", message="isbn number does not exist!"), 404

    return render_template("api.html", res=res.json())

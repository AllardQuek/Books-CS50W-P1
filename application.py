import os
import requests
import datetime

from flask import Flask, session, render_template, request, redirect, flash, jsonify
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

        if db.execute("SELECT username from users WHERE username = :username", {"username": username}).rowcount >= 1:
            return render_template("error.html", message="This username already exists. Sorry!")

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username": username, "password": password})
        try:
            db.commit()
        except:
            return render_template("error.html", message="Could not insert data"), 500

        # Set session["user_id"] value to user's id
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchall()
        session["user_id"] = rows[0]["id"]

        return render_template("search.html")

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

    # Use || instead of + operator which is not unique, and use single quotes:
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
# Function needs to take an argument isbn lest it would not expect a keyword argument

    row = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    reviews = db.execute("SELECT review, username, datetime, rating FROM reviews WHERE isbn = :isbn", {"isbn": isbn }).fetchall()

    # Goodreads review data using API
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "rp5fatbknRT7djHIMLasw", "isbns": isbn})
    ratings_count = res.json()['books'][0]['work_ratings_count']
    average_rating = res.json()['books'][0]['average_rating']

    return render_template("bookpage.html", row=row, reviews=reviews, ratings_count=ratings_count, average_rating=average_rating)


@app.route("/bookpage/<isbn>/submitreview", methods=["POST"])
def submitreview(isbn):

    # Need fetchone() lest ResultProxy object which has no attribute title is returned instead of RowProxy
    user = db.execute("SELECT username FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()
    book = db.execute("SELECT title FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    # Check if user has submitted review previously
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


@app.route("/api/<isbn>")
def api(isbn):

    # Make sure isbn exists
    row = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if not row:
        return jsonify({"error": "Invalid isbn"}), 404

    book_details = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    review_count = db.execute("SELECT review FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).rowcount

    # Check if any ratings given so far, if none round function will not work
    try:
        average_score_RowProxy = db.execute("SELECT AVG(rating) FROM reviews WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

        # Must convert average_score to dict lest its type is RoxProxy which is not JSON serializable
        d = dict(average_score_RowProxy)

        # Round to 2 decimal places, but still must convert to float lest type Decimal is not JSON serializable
        average_score = float(round((d['avg']), 2))
    except:
        average_score = 0

    return jsonify({
            "title": book_details["title"],
            "author": book_details["author"],
            "year": book_details["year"],
            "isbn": book_details["isbn"],
            "review_count": review_count,
            "average_score": average_score
    })

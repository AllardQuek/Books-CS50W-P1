import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, tit, aut, yr in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": tit, "author": aut, "year": yr})
        print(f"Added book {isbn}: {tit} by {aut} in year {yr}.")
    db.commit()

if __name__ == "__main__":
    main()


# Changed the data type of isbn column in books table: ALTER TABLE assets ALTER COLUMN name TYPE VARCHAR;

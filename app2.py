from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import difflib
import pickle
import numpy as np

# Load the datasets
popular_df = pickle.load(open('popular.pkl', 'rb'))
pt = pickle.load(open('pt.pkl', 'rb'))
books = pickle.load(open('books.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper function to check for similar usernames
def find_similar_usernames(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    usernames = [row[0] for row in c.fetchall()]
    conn.close()
    return difflib.get_close_matches(username, usernames)

@app.route('/')
def index():
    if 'username' in session:
        featured_books = popular_df.head(5)
        featured_titles = list(featured_books['Book-Title'])
        featured_authors = list(featured_books['Book-Author'])
        featured_images = list(featured_books['Image-URL-M'])

        return render_template('index.html',
                               featured_titles=featured_titles,
                               featured_authors=featured_authors,
                               featured_images=featured_images,
                               book_name=list(popular_df['Book-Title'].values),
                               author=list(popular_df['Book-Author'].values),
                               image=list(popular_df['Image-URL-M'].values),
                               votes=list(popular_df['num_ratings'].values),
                               rating=list(popular_df['avg_rating'].values)
                               )
    else:
        return redirect(url_for('login'))

@app.route('/recommend1')
def recommend_ui():
    if 'username' in session:
        return render_template('recommend1.html')
    else:
        return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/recommend_books', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input')
    if user_input in pt.index:
        index = np.where(pt.index == user_input)[0][0]
        similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:5]

        data = []
        for i in similar_items:
            item = []
            temp_df = books[books['Book-Title'] == pt.index[i[0]]]
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Title'].values))
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Author'].values))
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Image-URL-M'].values))

            data.append(item)

        return render_template('recommend1.html', data=data)
    else:
        similar_books = difflib.get_close_matches(user_input, pt.index)
        return render_template('recommend1.html', data=[], error="The book was not found.", similar_books=similar_books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        existing_user = c.fetchone()
        
        if existing_user:
            similar_usernames = find_similar_usernames(username)
            flash('Username already taken. Here are some suggestions: ' + ', '.join(similar_usernames), 'warning')
            return redirect(url_for('signup'))
        
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        
        session['username'] = username
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

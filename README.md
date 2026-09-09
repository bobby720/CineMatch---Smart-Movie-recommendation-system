# 🎬 CineMatch — Smart Movie Recommendation System

> **Discover movies that match your mood, interests, and preferences.**

CineMatch is a **smart movie recommendation web application** built with Python and Streamlit. It combines **mood-based NLP, movie metadata, rating-based scoring, genre preferences, language, platform, and release-year filters** to recommend movies tailored to the user's interests.

The application features a modern **glassmorphism interface inspired by streaming platforms**, with movie posters, descriptions, cast information, trailers, ratings, and detailed movie preview pages.

---

## ✨ Features

* 🎯 **Smart Movie Recommendations**
* 🧠 **Mood-Based Recommendation**
* 💭 **Natural Language Mood Input**
* 🎭 **Genre-Based Preferences**
* ⭐ **Rating-Based Scoring**
* 🌎 **Language Filtering**
* 📺 **Streaming Platform Filtering**
* 📅 **Release Year Filtering**
* 🎬 **Movie Posters & Details**
* 👥 **Cast Information**
* 🎞️ **Trailer Support**
* 🔎 **Movie Search & Discovery**
* 🎨 **Glassmorphism UI**
* 📱 **Interactive Streamlit Interface**
* 🗃️ **SQL Server Database Integration**

---

## 🧠 How CineMatch Works

CineMatch doesn't simply display a fixed list of movies.

It takes multiple user preferences and calculates a recommendation score for each movie.

### 🔄 Recommendation Pipeline

```text
                 👤 USER
                    │
                    ▼
          ┌─────────────────────┐
          │   User Preferences  │
          │                     │
          │ • Mood              │
          │ • Interests         │
          │ • Genre             │
          │ • Language          │
          │ • Platform          │
          │ • Rating            │
          │ • Release Year      │
          └──────────┬──────────┘
                     │
                     ▼
             🔍 HARD FILTERS
                     │
                     ▼
          ┌──────────────────────┐
          │    Movie Database    │
          │      SQL Server      │
          └──────────┬───────────┘
                     │
                     ▼
             🧠 SCORE MOVIES
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
     Genre        Mood/          Rating
     Score        Description    Score
                  Score
        │            │            │
        └────────────┼────────────┘
                     ▼
             📊 FINAL SCORE
                     │
                     ▼
           🏆 TOP RECOMMENDATIONS
                     │
                     ▼
              🎬 CINE MATCH
```

---

## 🧮 Recommendation Algorithm

CineMatch calculates a score using multiple factors.

### 1. Genre Match

The system checks how well the movie's genres match the user's selected interests.

### 2. Mood Match

The user's mood input is analyzed using predefined mood keywords and compared against movie descriptions.

For example:

```text
User Input:
"I want something exciting and adventurous"

        ↓

Detected Mood:
Adventure / Excitement

        ↓

Movie Description Analysis

        ↓

Mood Score
```

### 3. Rating Score

Movie ratings contribute to the final recommendation score.

Higher-rated movies receive a stronger rating contribution.

### 4. Interest Genre Bonus

Additional points are awarded when a movie matches the user's preferred genres.

### 5. Final Score

The different components are combined and normalized to produce a recommendation score between **0 and 100**.

```text
Genre Score
     +
Mood / Description Score
     +
Rating Score
     +
Interest Genre Bonus
     ↓
Final Recommendation Score
```

The implementation then ranks movies by their calculated score and returns the highest-ranked results.

---

## 🖥️ User Experience

CineMatch is designed to feel more like a modern streaming platform than a traditional machine-learning demo.

### 🎨 Glassmorphism Interface

The application uses a custom glassmorphism-inspired visual design with modern cards, gradients, animations, and a cinematic layout.

### 🎬 Movie Preview

Each movie can contain information such as:

* Movie title
* Genre
* Language
* Rating
* Platform
* Description
* Release year
* Poster
* Trailer
* Cast

The application models these movie attributes directly in Python and retrieves them from the database.

---

## 🛠️ Tech Stack

| Technology                    | Purpose                      |
| ----------------------------- | ---------------------------- |
| 🐍 **Python**                 | Core application logic       |
| 🎈 **Streamlit**              | Web application framework    |
| 🗄️ **Microsoft SQL Server**  | Movie database               |
| 🔌 **PyODBC**                 | Python–SQL Server connection |
| 🧠 **NLP / Keyword Matching** | Mood detection               |
| 🎨 **Custom CSS**             | Glassmorphism UI             |
| 📦 **Dataclasses**            | Movie and cast data models   |

The application uses `pyodbc` to connect to a SQL Server database named `MovieDB`, while Streamlit handles the interactive web interface.

---

## 🏗️ Architecture

```text
┌──────────────────────────────────────────┐
│              STREAMLIT UI                │
│                                          │
│  Search • Filters • Mood • Preferences  │
└───────────────────┬──────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│         RECOMMENDATION ENGINE            │
│                                          │
│  Mood Detection                          │
│  Genre Matching                          │
│  Rating Scoring                          │
│  Preference Matching                     │
│  Movie Ranking                            │
└───────────────────┬──────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│             DATA LAYER                   │
│                                          │
│             SQL Server                   │
│              MovieDB                     │
└───────────────────┬──────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│          MOVIE INFORMATION               │
│                                          │
│ Posters • Cast • Trailers • Ratings     │
│ Genres • Languages • Platforms • Years  │
└──────────────────────────────────────────┘
```

---

## 🗃️ Database

CineMatch uses **Microsoft SQL Server** as its primary data layer.

The application connects to:

```text
Server: localhost
Database: MovieDB
Authentication: Windows Trusted Connection
```

The database stores movie information such as:

```text
Movie
├── ID
├── Title
├── Genre
├── Language
├── Rating
├── Platform
├── Description
├── Poster URL
├── Release Year
└── Trailer URL
```

Additional database structures are used for information such as:

```text
Cast
Movie Images
```

The application also creates required supporting tables when they do not already exist.

---

# 🚀 Getting Started

## 📋 Prerequisites

Before running CineMatch, make sure you have:

* Python 3.9+
* Microsoft SQL Server
* ODBC Driver for SQL Server
* A configured `MovieDB` database
* Movie data populated in the database

---

## 📥 Installation

### 1. Clone the repository

```bash
git clone https://github.com/bobby720/CineMatch---Smart-Movie-recommendation-system.git
```

### 2. Enter the project directory

```bash
cd CineMatch---Smart-Movie-recommendation-system
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the environment

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install streamlit pyodbc
```

If you have a `requirements.txt` file, use:

```bash
pip install -r requirements.txt
```

---

# 🗄️ SQL Server Configuration

CineMatch expects a SQL Server database called:

```text
MovieDB
```

By default, the application uses:

```text
SERVER=localhost
DATABASE=MovieDB
Trusted_Connection=yes
```

The server can also be configured using the environment variable:

```text
DB_SERVER
```

Example:

```bash
set DB_SERVER=localhost
```

The connection configuration is handled through `pyodbc`.

---

# ▶️ Run the Application

Start CineMatch with:

```bash
streamlit run App.py
```

Then open the Streamlit URL shown in your terminal, typically:

```text
http://localhost:8501
```

---

# 🎯 Using CineMatch

### Step 1 — Choose your preferences

Select or enter your:

* Mood
* Movie interests
* Preferred genres
* Language
* Streaming platform
* Minimum rating
* Release year range

### Step 2 — Get recommendations

CineMatch applies the selected filters and calculates recommendation scores.

### Step 3 — Explore

Browse the recommended movies and explore:

* 🎬 Movie information
* ⭐ Ratings
* 👥 Cast
* 📝 Description
* 🖼️ Posters
* 🎞️ Trailers

---

# 📁 Project Structure

```text
CineMatch---Smart-Movie-recommendation-system/
│
├── App.py
│
└── README.md
```

The current repository keeps the application logic primarily inside `App.py`.

---

# 💡 Why CineMatch?

Traditional movie browsing makes users scroll through hundreds of titles.

CineMatch focuses on a different question:

> **"What kind of movie do I feel like watching right now?"**

Instead of relying only on movie titles or genres, the system allows users to describe their mood and preferences and combines those signals with movie metadata and ratings.

---

# 🔮 Future Enhancements

Potential improvements include:

* [ ] User accounts and profiles
* [ ] Personalized watch history
* [ ] Collaborative filtering
* [ ] Hybrid recommendation system
* [ ] Deep-learning recommendation models
* [ ] Better NLP-based mood classification
* [ ] Movie similarity embeddings
* [ ] TMDB API integration
* [ ] Real-time streaming availability
* [ ] Watchlist functionality
* [ ] User ratings and feedback
* [ ] Recommendation explanations
* [ ] Cloud deployment
* [ ] Mobile-responsive improvements

---

# 📊 Recommendation System Evolution

The current system provides a strong rule-based/content-scoring foundation.

A future version could evolve into:

```text
                 CineMatch 1.0
                      │
                      ▼
              Rule-Based Scoring
                      │
                      ▼
             NLP Mood Detection
                      │
                      ▼
              Content Features
                      │
                      ▼
          ┌──────────────────────┐
          │    Future Hybrid     │
          │ Recommendation Model │
          └──────────┬───────────┘
                     │
             ┌───────┴────────┐
             ▼                ▼
       Content-Based    Collaborative
        Filtering         Filtering
             │                │
             └───────┬────────┘
                     ▼
              🧠 Hybrid Model
                     │
                     ▼
            🎬 Better Recommendations
```

---

# 🎓 Key Concepts Demonstrated

This project demonstrates practical concepts in:

* Recommendation Systems
* Content-Based Filtering
* Natural Language Processing
* Keyword-Based Mood Detection
* Scoring & Ranking
* Database Integration
* SQL Server
* Python Data Modeling
* Streamlit Application Development
* UI/UX Design
* Full-Stack Data Flow

---

# 👨‍💻 Author

**Bobby**

GitHub: [@bobby720](https://github.com/bobby720)

---

## ⭐ Support

If you like CineMatch, consider giving the repository a ⭐ on GitHub.

---

## 📜 License

This project is created for **educational and experimental purposes**.

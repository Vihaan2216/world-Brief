import os
import secrets
import sqlite3
from typing import Any

from ddgs import DDGS
from flask import (
    Flask,
    jsonify,
    render_template_string,
    request,
    redirect,
    url_for,
    session,
)
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)

# IMPORTANT:
# For a real public deployment, set SECRET_KEY as an environment variable.
SECRET_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "worldbrief.secret"
)

def get_secret_key():
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key

    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key

    key = secrets.token_hex(32)
    with open(SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    return key

app.config["SECRET_KEY"] = get_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "worldbrief.db"
)

DEFAULT_QUERY = "latest India news"
MAX_RESULTS = 50

CATEGORIES = [
    ("Home", "latest India news"),
    ("World", "latest world news"),
    ("Technology", "latest technology news"),
    ("Science", "latest science news"),
    ("Sports", "latest sports news"),
    ("Business", "latest business news"),
    ("Health", "latest health news"),
    ("Entertainment", "latest entertainment news"),
]


# ============================================================
# DATABASE
# ============================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.commit()
    db.close()


# Create the database automatically when the program starts.
init_db()


# ============================================================
# HTML
# ============================================================

PAGE = r"""<!doctype html>
<html lang="en">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>worldBrief</title>

<style>

:root {
    --red: #e60000;
    --red-dark: #b90000;
    --ink: #17191c;
    --muted: #74808c;
    --line: #e8ebef;
    --surface: #ffffff;
    --page: #f4f6f8;
    --shadow: 0 12px 35px rgba(18, 29, 40, .09);
    color-scheme: light;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--page);
    color: var(--ink);
    font: 15px/1.5 Arial, sans-serif;
}

button,
input {
    font: inherit;
}


/* ============================================================
   TOP BAR
   ============================================================ */

.topbar {
    background: var(--ink);
    color: #fff;
}

.topbar-inner {
    max-width: 1240px;
    margin: auto;
    padding: 18px 24px;
    display: flex;
    align-items: center;
    gap: 22px;
}

.brand {
    color: #fff;
    text-decoration: none;
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -.8px;
    white-space: nowrap;
}

.brand span {
    color: var(--red);
}

.search {
    display: flex;
    flex: 1;
    max-width: 620px;
    margin-left: auto;
}

.search input {
    width: 100%;
    border: 0;
    padding: 12px 15px;
    border-radius: 7px 0 0 7px;
    outline: 0;
}

.search button {
    border: 0;
    color: #fff;
    background: var(--red);
    font-weight: 700;
    cursor: pointer;
    padding: 0 19px;
    border-radius: 0 7px 7px 0;
}

.search button:hover {
    background: var(--red-dark);
}


/* ============================================================
   ACCOUNT BUTTON
   ============================================================ */

.account-area {
    display: flex;
    align-items: center;
    gap: 9px;
    white-space: nowrap;
}

.account-user {
    color: #cbd0d5;
    font-size: 14px;
}

.account-button {
    color: white;
    text-decoration: none;
    border: 1px solid #555;
    border-radius: 7px;
    padding: 8px 13px;
    font-weight: 700;
    transition: .15s;
}

.account-button:hover {
    border-color: #fff;
    background: #2d3136;
}

.account-button.primary {
    background: var(--red);
    border-color: var(--red);
}

.account-button.primary:hover {
    background: var(--red-dark);
}


/* ============================================================
   NAVIGATION
   ============================================================ */

.nav {
    background: #222529;
    border-top: 1px solid #34383d;
}

.nav-inner {
    max-width: 1240px;
    margin: auto;
    padding: 0 24px;
    display: flex;
    gap: 4px;
    overflow-x: auto;
}

.nav button {
    border: 0;
    background: transparent;
    color: #cbd0d5;
    cursor: pointer;
    padding: 12px 14px;
    white-space: nowrap;
    font-weight: 600;
}

.nav button:hover,
.nav button.active {
    color: #fff;
    background: var(--red);
}


/* ============================================================
   LAYOUT
   ============================================================ */

.layout {
    max-width: 1240px;
    margin: 28px auto;
    padding: 0 24px;
    display: grid;
    grid-template-columns: 230px 1fr;
    gap: 28px;
}

aside {
    background: var(--surface);
    border-radius: 12px;
    padding: 20px;
    height: max-content;
    box-shadow: var(--shadow);
    position: sticky;
    top: 18px;
}

aside h3 {
    margin: 0 0 14px;
    font-size: 12px;
    color: var(--red);
    letter-spacing: 1.4px;
}

.side-link {
    display: block;
    width: 100%;
    border: 0;
    background: transparent;
    text-align: left;
    padding: 10px 8px;
    border-radius: 6px;
    cursor: pointer;
    color: #39434d;
}

.side-link:hover,
.side-link.active {
    color: var(--red);
    background: #fff0f0;
}


/* ============================================================
   SETTINGS
   ============================================================ */

.setting {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 8px;
    color: #39434d;
}

.switch {
    width: 38px;
    height: 21px;
    border-radius: 20px;
    border: 0;
    background: #cbd1d6;
    cursor: pointer;
    position: relative;
}

.switch:after {
    content: "";
    position: absolute;
    width: 17px;
    height: 17px;
    top: 2px;
    left: 2px;
    background: white;
    border-radius: 50%;
    transition: .2s;
}

.switch.on {
    background: var(--red);
}

.switch.on:after {
    left: 19px;
}


/* ============================================================
   HEADINGS
   ============================================================ */

.heading {
    display: flex;
    justify-content: space-between;
    align-items: end;
    margin-bottom: 20px;
}

.heading h1 {
    margin: 0;
    font-size: 30px;
    letter-spacing: -.8px;
}

#status {
    color: var(--muted);
    margin-top: 4px;
}


/* ============================================================
   HERO
   ============================================================ */

.hero {
    background: var(--ink);
    border-radius: 13px;
    color: white;
    padding: 28px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}

.hero .eyebrow {
    color: #ff7777;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    font-weight: 700;
}

.hero h2 {
    max-width: 700px;
    margin: 8px 0 10px;
    font-size: 28px;
    line-height: 1.15;
}

.hero p {
    max-width: 720px;
    color: #c5cbd1;
    margin: 0 0 18px;
}

.hero a {
    color: #fff;
    text-decoration: none;
    font-weight: 700;
}


/* ============================================================
   NEWS GRID
   ============================================================ */

.grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
}

article {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 11px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(18, 29, 40, .04);
    transition: transform .18s, box-shadow .18s;
}

article:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow);
}

article img {
    width: 100%;
    height: 175px;
    object-fit: cover;
    background: #e9edf0;
}

.content {
    padding: 17px;
}

h2 {
    font-size: 18px;
    line-height: 1.3;
    margin: 0 0 8px;
}

h2 a {
    color: var(--ink);
    text-decoration: none;
}

h2 a:hover {
    color: var(--red);
}

.meta {
    color: var(--muted);
    font-size: 12px;
}

article p {
    color: #56616c;
    margin: 10px 0 0;
}


/* ============================================================
   ADVERTISEMENTS
   ============================================================ */

.ad-card {
    grid-column: 1 / -1;
    background: linear-gradient(
        135deg,
        #ffffff,
        #f8f9fa
    );
    border: 1px solid #dfe3e7;
    border-radius: 11px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
}

.ad-card:before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 5px;
    background: var(--red);
}

.ad-label {
    color: #8b9299;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 7px;
}

.ad-title {
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 5px;
}

.ad-text {
    color: #59636d;
    margin-bottom: 13px;
}

.ad-button {
    display: inline-block;
    background: var(--red);
    color: white;
    text-decoration: none;
    padding: 8px 14px;
    border-radius: 6px;
    font-weight: 700;
}

.ad-button:hover {
    background: var(--red-dark);
}

.ad-mini {
    grid-column: 1 / -1;
    min-height: 90px;
    border-radius: 10px;
    background: #fff;
    border: 1px solid var(--line);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 15px 20px;
}

.ad-mini-left {
    display: flex;
    align-items: center;
    gap: 14px;
}

.ad-badge {
    background: #17191c;
    color: white;
    padding: 7px 9px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 800;
}

.ad-mini strong {
    display: block;
}

.ad-mini span {
    color: var(--muted);
    font-size: 13px;
}

.ad-mini a {
    color: var(--red);
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
}


/* ============================================================
   EMPTY / ERROR
   ============================================================ */

.empty,
.error {
    grid-column: 1 / -1;
    padding: 22px;
    border-radius: 9px;
}

.empty {
    background: #fff;
    color: var(--muted);
}

.error {
    color: #9b001d;
    background: #ffecef;
}


/* ============================================================
   LOADER
   ============================================================ */

.loader {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid #ddd;
    border-top-color: var(--red);
    border-radius: 50%;
    vertical-align: -3px;
    animation: spin .7s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}


/* ============================================================
   LOAD MORE
   ============================================================ */

.load-more {
    display: block;
    margin: 24px auto 0;
    padding: 12px 25px;
    border: 1px solid #d9dfe4;
    border-radius: 7px;
    background: #fff;
    cursor: pointer;
    font-weight: 700;
    color: #39434d;
}

.load-more:hover {
    border-color: var(--red);
    color: var(--red);
}


/* ============================================================
   GAMES
   ============================================================ */

.game-link {
    display: block;
    width: 100%;
    border: 0;
    background: #fff4f4;
    color: #8d0000;
    text-align: left;
    padding: 10px 8px;
    border-radius: 6px;
    cursor: pointer;
    margin-bottom: 6px;
    font-weight: 600;
}

.game-link:hover {
    background: #ffe0e0;
    color: var(--red);
}

.game-modal {
    position: fixed;
    inset: 0;
    z-index: 10;
    display: grid;
    place-items: center;
    padding: 20px;
    background: #0009;
}

.game-modal[hidden] {
    display: none;
}

.game-box {
    width: min(560px, 100%);
    max-height: 90vh;
    overflow: auto;
    background: #111;
    color: #fff;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 20px 60px #0008;
}

.game-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.game-head h2 {
    color: #fff;
    margin: 0;
}

.close-game {
    border: 0;
    background: #333;
    color: #fff;
    border-radius: 5px;
    padding: 7px 11px;
    cursor: pointer;
}

.game-canvas {
    display: block;
    width: min(500px, 100%);
    height: auto;
    margin: 18px auto 10px;
    background: #000;
    border: 2px solid #333;
}

.game-score {
    text-align: center;
    color: #ff7474;
    font-weight: 700;
}

.game-controls {
    text-align: center;
    margin-top: 12px;
}

.game-controls button {
    border: 0;
    background: var(--red);
    color: #fff;
    padding: 9px 14px;
    border-radius: 5px;
    cursor: pointer;
    margin: 3px;
}

.tiles {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    max-width: 360px;
    margin: 18px auto;
    background: #776e65;
    padding: 8px;
    border-radius: 6px;
}

.tile {
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    border-radius: 4px;
    background: #cdc1b4;
    color: #776e65;
    font-size: 25px;
    font-weight: 800;
}

.tile:not(:empty) {
    background: #eee4da;
}


/* ============================================================
   MOBILE
   ============================================================ */

.menu-button {
    display: none;
    border: 1px solid #555;
    background: transparent;
    color: #fff;
    border-radius: 5px;
    padding: 8px 10px;
}

@media (max-width: 850px) {

    .menu-button {
        display: block;
        order: -1;
    }

    .topbar-inner {
        flex-wrap: wrap;
        gap: 13px;
    }

    .brand {
        margin-right: auto;
    }

    .search {
        flex-basis: 100%;
        max-width: none;
        order: 5;
    }

    .account-area {
        margin-left: auto;
    }

    .layout {
        grid-template-columns: 1fr;
    }

    aside {
        display: none;
        position: static;
    }

    aside.open {
        display: block;
    }

}

@media (max-width: 600px) {

    .topbar-inner,
    .nav-inner,
    .layout {
        padding-left: 15px;
        padding-right: 15px;
    }

    .layout {
        margin-top: 18px;
    }

    .grid {
        grid-template-columns: 1fr;
    }

    .hero h2 {
        font-size: 23px;
    }

    .heading h1 {
        font-size: 25px;
    }

    .account-user {
        display: none;
    }

    .ad-mini {
        align-items: flex-start;
        flex-direction: column;
    }

}


/* ============================================================
   AUTH PAGES
   ============================================================ */

.auth-page {
    min-height: 100vh;
    background:
        radial-gradient(
            circle at top right,
            #ffe1e1,
            transparent 35%
        ),
        var(--page);
}

.auth-header {
    background: var(--ink);
    padding: 20px 25px;
}

.auth-header a {
    color: white;
    text-decoration: none;
    font-size: 26px;
    font-weight: 800;
}

.auth-header span {
    color: var(--red);
}

.auth-wrap {
    min-height: calc(100vh - 80px);
    display: grid;
    place-items: center;
    padding: 30px 20px;
}

.auth-box {
    width: min(430px, 100%);
    background: white;
    border-radius: 16px;
    padding: 32px;
    box-shadow: var(--shadow);
    border: 1px solid var(--line);
}

.auth-box h1 {
    margin: 0 0 7px;
    font-size: 29px;
}

.auth-subtitle {
    color: var(--muted);
    margin: 0 0 25px;
}

.auth-label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    margin: 15px 0 7px;
}

.auth-input {
    width: 100%;
    border: 1px solid #d9dfe4;
    border-radius: 7px;
    padding: 12px;
    outline: none;
}

.auth-input:focus {
    border-color: var(--red);
    box-shadow: 0 0 0 3px #ffe4e4;
}

.auth-submit {
    width: 100%;
    border: 0;
    border-radius: 7px;
    padding: 13px;
    margin-top: 20px;
    background: var(--red);
    color: white;
    font-weight: 800;
    cursor: pointer;
}

.auth-submit:hover {
    background: var(--red-dark);
}

.auth-switch {
    text-align: center;
    margin-top: 20px;
    color: var(--muted);
}

.auth-switch a {
    color: var(--red);
    font-weight: 700;
    text-decoration: none;
}

.auth-error {
    background: #ffecef;
    color: #9b001d;
    border-radius: 7px;
    padding: 10px 12px;
    margin-bottom: 12px;
}

.auth-success {
    background: #e9f8ee;
    color: #176b36;
    border-radius: 7px;
    padding: 10px 12px;
    margin-bottom: 12px;
}

</style>
</head>


<body>

{% if auth_page %}

<div class="auth-page">

    <header class="auth-header">
        <a href="/">world<span>Brief</span></a>
    </header>

    <div class="auth-wrap">

        <div class="auth-box">

            {% if auth_mode == "login" %}

                <h1>Welcome back</h1>

                <p class="auth-subtitle">
                    Sign in to your worldBrief account.
                </p>

                {% if error %}
                    <div class="auth-error">{{ error }}</div>
                {% endif %}

                <form method="POST" action="/login">

                    <label class="auth-label">
                        Username
                    </label>

                    <input
                        class="auth-input"
                        name="username"
                        autocomplete="username"
                        required
                    >

                    <label class="auth-label">
                        Password
                    </label>

                    <input
                        class="auth-input"
                        type="password"
                        name="password"
                        autocomplete="current-password"
                        required
                    >

                    <button class="auth-submit" type="submit">
                        Sign In
                    </button>

                </form>

                <div class="auth-switch">
                    Don't have an account?
                    <a href="/register">Create one</a>
                </div>

            {% else %}

                <h1>Create account</h1>

                <p class="auth-subtitle">
                    Join worldBrief and personalize your news experience.
                </p>

                {% if error %}
                    <div class="auth-error">{{ error }}</div>
                {% endif %}

                <form method="POST" action="/register">

                    <label class="auth-label">
                        Username
                    </label>

                    <input
                        class="auth-input"
                        name="username"
                        autocomplete="username"
                        minlength="3"
                        maxlength="30"
                        required
                    >

                    <label class="auth-label">
                        Password
                    </label>

                    <input
                        class="auth-input"
                        type="password"
                        name="password"
                        autocomplete="new-password"
                        minlength="6"
                        required
                    >

                    <label class="auth-label">
                        Confirm password
                    </label>

                    <input
                        class="auth-input"
                        type="password"
                        name="confirm_password"
                        autocomplete="new-password"
                        minlength="6"
                        required
                    >

                    <button class="auth-submit" type="submit">
                        Create Account
                    </button>

                </form>

                <div class="auth-switch">
                    Already have an account?
                    <a href="/login">Sign in</a>
                </div>

            {% endif %}

        </div>

    </div>

</div>

{% else %}

<header class="topbar">

    <div class="topbar-inner">

        <button
            class="menu-button"
            id="menu-button"
            aria-label="Open menu"
        >
            ☰
        </button>

        <a class="brand" href="/">
            world<span>Brief</span>
        </a>

        <form class="search" id="search-form">

            <input
                id="query"
                name="q"
                value="{{ query }}"
                placeholder="Search the latest news"
                required
            >

            <button type="submit">
                Search
            </button>

        </form>

        <div class="account-area">

            {% if logged_in %}

                <span class="account-user">
                    {{ username }}
                </span>

                <a class="account-button" href="/logout">
                    Logout
                </a>

            {% else %}

                <a class="account-button primary" href="/login">
                    Sign In
                </a>

            {% endif %}

        </div>

    </div>


    <nav class="nav">

        <div class="nav-inner" id="category-nav">

            {% for name, value in categories %}

                <button data-query="{{ value }}">
                    {{ name }}
                </button>

            {% endfor %}

        </div>

    </nav>

</header>


<div class="layout">


    <aside id="sidebar">

        <h3>SECTIONS</h3>

        {% for name, value in categories %}

            <button
                class="side-link"
                data-query="{{ value }}"
            >
                {{ name }}
            </button>

        {% endfor %}


        <h3 style="margin-top:24px">
            OPTIONS
        </h3>

        <div class="setting">

            <span>Images</span>

            <button
                class="switch on"
                id="images-toggle"
                aria-label="Toggle images"
            ></button>

        </div>


        <div class="setting">

            <span>Ads</span>

            <button
                class="switch on"
                id="ads-toggle"
                aria-label="Toggle advertisements"
            ></button>

        </div>


        <h3 style="margin-top:24px">
            GAMES
        </h3>

        <button class="game-link" data-game="snake">
            🐍 Snake
        </button>

        <button class="game-link" data-game="breakout">
            🧱 Breakout
        </button>

        <button class="game-link" data-game="2048">
            🔢 2048 Infinite Edition
        </button>

    </aside>


    <main>

        <div class="heading">

            <div>

                <h1>
                    Latest stories
                </h1>

                <div id="status">
                    Loading news...
                </div>

            </div>

        </div>


        <section
            id="hero"
            class="hero"
            hidden
        ></section>


        <section
            id="results"
            class="grid"
        ></section>


        <button
            id="load-more"
            class="load-more"
            hidden
        >
            Load more stories
        </button>

    </main>

</div>


<div
    class="game-modal"
    id="game-modal"
    hidden
>

    <div class="game-box">

        <div class="game-head">

            <h2 id="game-title"></h2>

            <button
                class="close-game"
                id="close-game"
            >
                ✕
            </button>

        </div>

        <div id="game-content"></div>

    </div>

</div>


<script>

const status = document.querySelector("#status");
const results = document.querySelector("#results");
const hero = document.querySelector("#hero");
const queryInput = document.querySelector("#query");
const loadMore = document.querySelector("#load-more");

let currentQuery = queryInput.value;
let allItems = [];

let showImages = true;
let showAds = true;

let gameTimer;


/* ============================================================
   SECURITY
   ============================================================ */

function escapeHtml(value) {

    const node = document.createElement("div");

    node.textContent = value || "";

    return node.innerHTML;
}


/* ============================================================
   ADS
   ============================================================ */

const advertisements = [

    {
        title: "Stay informed. Stay curious.",
        text: "worldBrief brings stories from around the world into one simple news experience.",
        button: "Explore worldBrief",
        url: "/"
    },

    {
        title: "Your news, your way.",
        text: "Search technology, science, business, sports and more from one place.",
        button: "Browse sections",
        url: "/"
    },

    {
        title: "Discover something new.",
        text: "Use worldBrief search to explore today's latest stories.",
        button: "Search stories",
        url: "#"
    }

];


function adCard(index) {

    const ad =
        advertisements[
            index % advertisements.length
        ];

    return `

        <div class="ad-card">

            <div class="ad-label">
                Sponsored
            </div>

            <div class="ad-title">
                ${escapeHtml(ad.title)}
            </div>

            <div class="ad-text">
                ${escapeHtml(ad.text)}
            </div>

            <a
                class="ad-button"
                href="${escapeHtml(ad.url)}"
            >
                ${escapeHtml(ad.button)} →
            </a>

        </div>

    `;
}


function miniAd(index) {

    const ad =
        advertisements[
            index % advertisements.length
        ];

    return `

        <div class="ad-mini">

            <div class="ad-mini-left">

                <div class="ad-badge">
                    AD
                </div>

                <div>

                    <strong>
                        ${escapeHtml(ad.title)}
                    </strong>

                    <span>
                        ${escapeHtml(ad.text)}
                    </span>

                </div>

            </div>

            <a href="${escapeHtml(ad.url)}">
                Learn more →
            </a>

        </div>

    `;
}


/* ============================================================
   NEWS CARD
   ============================================================ */

function card(item) {

    return `

        <article>

            ${
                showImages && item.image
                ?
                `
                <img
                    src="${escapeHtml(item.image)}"
                    alt=""
                    loading="lazy"
                >
                `
                :
                ""
            }

            <div class="content">

                <h2>

                    <a
                        href="${escapeHtml(item.url)}"
                        target="_blank"
                        rel="noopener"
                    >
                        ${escapeHtml(item.title)}
                    </a>

                </h2>

                <div class="meta">

                    ${escapeHtml(item.source || "News")}

                    ${
                        item.date
                        ?
                        ` · ${escapeHtml(item.date)}`
                        :
                        ""
                    }

                </div>

                <p>
                    ${escapeHtml(
                        item.body ||
                        "Open the article to read more."
                    )}
                </p>

            </div>

        </article>

    `;
}


/* ============================================================
   RENDER NEWS
   ============================================================ */

function render() {

    const lead = allItems[0];

    hero.hidden = !lead;

    if (lead) {

        hero.innerHTML = `

            <div class="eyebrow">
                Top story
            </div>

            <h2>
                ${escapeHtml(lead.title)}
            </h2>

            <p>
                ${escapeHtml(
                    lead.body ||
                    "Read the latest details from this story."
                )}
            </p>

            <a
                href="${escapeHtml(lead.url)}"
                target="_blank"
                rel="noopener"
            >
                Read full story →
            </a>

        `;

    }


    const visible =
        allItems.slice(1, 11);


    if (!visible.length) {

        results.innerHTML =
            `<div class="empty">
                No stories found. Try another search.
            </div>`;

        loadMore.hidden = true;

        return;
    }


    let html = "";


    visible.forEach((item, index) => {

        html += card(item);


        /*
         * Insert advertisements between stories.
         */

        if (showAds) {

            if (index === 2) {
                html += adCard(0);
            }

            if (index === 6) {
                html += miniAd(1);
            }

            if (index === 9) {
                html += adCard(2);
            }

        }

    });


    results.innerHTML = html;


    loadMore.hidden =
        allItems.length <= 11;

}


/* ============================================================
   GAMES
   ============================================================ */

function openGame(name) {

    clearInterval(gameTimer);

    const modal =
        document.querySelector("#game-modal");

    const title =
        document.querySelector("#game-title");

    const content =
        document.querySelector("#game-content");


    modal.hidden = false;


    title.textContent =
        name === "2048"
        ?
        "2048 Infinite Edition"
        :
        name[0].toUpperCase() +
        name.slice(1);


    if (name === "2048") {

        start2048(content);

    } else {

        startCanvasGame(content, name);

    }

}


function startCanvasGame(content, type) {

    content.innerHTML = `

        <canvas
            class="game-canvas"
            width="500"
            height="500"
        ></canvas>

        <div
            class="game-score"
            id="game-score"
        >
            Score: 0
        </div>

        <div class="game-controls">
            Use arrow keys to play
        </div>

    `;


    const canvas =
        content.querySelector("canvas");

    const ctx =
        canvas.getContext("2d");


    let score = 0;
    let over = false;


    /* ========================================================
       SNAKE
       ======================================================== */

    if (type === "snake") {

        const size = 20;
        const cells = 25;

        let snake = [
            [12, 12],
            [11, 12],
            [10, 12]
        ];

        let dir = [1, 0];

        let food = [
            Math.floor(Math.random() * cells),
            Math.floor(Math.random() * cells)
        ];


        function draw() {

            ctx.fillStyle = "#000";

            ctx.fillRect(
                0,
                0,
                500,
                500
            );


            ctx.fillStyle = "#e60000";

            ctx.fillRect(
                food[0] * size,
                food[1] * size,
                size - 1,
                size - 1
            );


            ctx.fillStyle = "#55d66b";

            snake.forEach(
                ([x, y]) => {

                    ctx.fillRect(
                        x * size,
                        y * size,
                        size - 1,
                        size - 1
                    );

                }
            );

        }


        function tick() {

            if (over) return;


            const head = [
                snake[0][0] + dir[0],
                snake[0][1] + dir[1]
            ];


            if (
                head[0] < 0 ||
                head[0] >= cells ||
                head[1] < 0 ||
                head[1] >= cells ||
                snake.some(
                    ([x, y]) =>
                        x === head[0] &&
                        y === head[1]
                )
            ) {

                over = true;

                document.querySelector(
                    "#game-score"
                ).textContent =
                    `Game over — Score: ${score}`;

                return;

            }


            snake.unshift(head);


            if (
                head[0] === food[0] &&
                head[1] === food[1]
            ) {

                score++;

                food = [
                    Math.floor(
                        Math.random() * cells
                    ),
                    Math.floor(
                        Math.random() * cells
                    )
                ];


                document.querySelector(
                    "#game-score"
                ).textContent =
                    `Score: ${score}`;

            } else {

                snake.pop();

            }


            draw();

        }


        window.onkeydown =
            event => {

                const keys = {

                    ArrowUp: [0, -1],
                    ArrowDown: [0, 1],
                    ArrowLeft: [-1, 0],
                    ArrowRight: [1, 0]

                };


                const next =
                    keys[event.key];


                if (
                    next &&
                    next[0] !== -dir[0] &&
                    next[1] !== -dir[1]
                ) {

                    dir = next;

                }

            };


        gameTimer =
            setInterval(tick, 110);


        draw();

    }


    /* ========================================================
       BREAKOUT
       ======================================================== */

    else {

        let paddle = 210;

        let ball = {
            x: 250,
            y: 450,
            dx: 3,
            dy: -3
        };


        let bricks = [];


        for (
            let row = 0;
            row < 5;
            row++
        ) {

            for (
                let col = 0;
                col < 8;
                col++
            ) {

                bricks.push({

                    x: 17 + col * 61,
                    y: 35 + row * 25,
                    hit: true

                });

            }

        }


        function draw() {

            ctx.fillStyle = "#000";

            ctx.fillRect(
                0,
                0,
                500,
                500
            );


            ctx.fillStyle = "#e60000";


            bricks
                .filter(b => b.hit)
                .forEach(b => {

                    ctx.fillRect(
                        b.x,
                        b.y,
                        54,
                        17
                    );

                });


            ctx.fillStyle = "#fff";

            ctx.fillRect(
                paddle,
                480,
                80,
                10
            );


            ctx.beginPath();

            ctx.arc(
                ball.x,
                ball.y,
                7,
                0,
                Math.PI * 2
            );

            ctx.fill();

        }


        function tick() {

            if (over) return;


            ball.x += ball.dx;
            ball.y += ball.dy;


            if (
                ball.x < 7 ||
                ball.x > 493
            ) {

                ball.dx *= -1;

            }


            if (ball.y < 7) {

                ball.dy *= -1;

            }


            if (
                ball.y > 470 &&
                ball.x > paddle &&
                ball.x < paddle + 80
            ) {

                ball.dy =
                    -Math.abs(ball.dy);

            }


            const brick =
                bricks.find(
                    b =>
                        b.hit &&
                        ball.x > b.x &&
                        ball.x < b.x + 54 &&
                        ball.y > b.y &&
                        ball.y < b.y + 17
                );


            if (brick) {

                brick.hit = false;

                ball.dy *= -1;

                score++;


                document.querySelector(
                    "#game-score"
                ).textContent =
                    `Score: ${score}`;

            }


            if (ball.y > 510) {

                over = true;

                document.querySelector(
                    "#game-score"
                ).textContent =
                    `Game over — Score: ${score}`;

            }


            draw();

        }


        window.onkeydown =
            event => {

                if (
                    event.key === "ArrowLeft"
                ) {

                    paddle =
                        Math.max(
                            0,
                            paddle - 25
                        );

                }


                if (
                    event.key === "ArrowRight"
                ) {

                    paddle =
                        Math.min(
                            420,
                            paddle + 25
                        );

                }

            };


        gameTimer =
            setInterval(tick, 16);


        draw();

    }

}


/* ============================================================
   2048
   ============================================================ */

function start2048(content) {

    content.innerHTML = `

        <div
            class="game-score"
            id="game-score"
        >
            Score: 0
        </div>

        <div
            class="tiles"
            id="tiles"
        ></div>

        <div class="game-controls">
            Use arrow keys to move tiles
        </div>

    `;


    let board =
        Array(16).fill(0);

    let score = 0;


    const tiles =
        content.querySelector("#tiles");


    function addTile() {

        const free =
            board
                .map(
                    (v, i) =>
                        v ? -1 : i
                )
                .filter(
                    v => v >= 0
                );


        if (free.length) {

            board[
                free[
                    Math.floor(
                        Math.random() *
                        free.length
                    )
                ]
            ] =
                Math.random() < .9
                ? 2
                : 4;

        }

    }


    function draw() {

        tiles.innerHTML =
            board
                .map(
                    v =>
                        `<div class="tile">${
                            v || ""
                        }</div>`
                )
                .join("");


        document.querySelector(
            "#game-score"
        ).textContent =
            `Score: ${score}`;

    }


    function move(direction) {

        let lines = [];


        for (
            let i = 0;
            i < 4;
            i++
        ) {

            lines.push(

                direction === "left" ||
                direction === "right"

                ?

                board.slice(
                    i * 4,
                    i * 4 + 4
                )

                :

                [
                    board[i],
                    board[i + 4],
                    board[i + 8],
                    board[i + 12]
                ]

            );

        }


        lines =
            lines.map(line => {

                if (
                    direction === "right" ||
                    direction === "down"
                ) {

                    line.reverse();

                }


                line =
                    line.filter(Boolean);


                for (
                    let i = 0;
                    i < line.length - 1;
                    i++
                ) {

                    if (
                        line[i] ===
                        line[i + 1]
                    ) {

                        line[i] *= 2;

                        score +=
                            line[i];

                        line.splice(
                            i + 1,
                            1
                        );

                    }

                }


                while (
                    line.length < 4
                ) {

                    line.push(0);

                }


                if (
                    direction === "right" ||
                    direction === "down"
                ) {

                    line.reverse();

                }


                return line;

            });


        lines.forEach(
            (line, i) => {

                line.forEach(
                    (v, j) => {

                        if (
                            direction === "left" ||
                            direction === "right"
                        ) {

                            board[
                                i * 4 + j
                            ] = v;

                        } else {

                            board[
                                i + j * 4
                            ] = v;

                        }

                    }
                );

            }
        );


        addTile();

        draw();

    }


    window.onkeydown =
        event => {

            const map = {

                ArrowLeft: "left",
                ArrowRight: "right",
                ArrowUp: "up",
                ArrowDown: "down"

            };


            if (map[event.key]) {

                move(
                    map[event.key]
                );

            }

        };


    addTile();
    addTile();

    draw();

}


/* ============================================================
   NEWS API
   ============================================================ */

async function loadNews(query) {

    currentQuery = query;

    queryInput.value = query;


    status.innerHTML =
        '<span class="loader"></span> Loading fresh stories...';


    results.innerHTML = "";

    hero.hidden = true;

    loadMore.hidden = true;


    document
        .querySelectorAll("[data-query]")
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.query === query
            );

        });


    try {

        const response =
            await fetch(
                `/api/news?q=${encodeURIComponent(query)}`
            );


        const payload =
            await response.json();


        if (!response.ok) {

            throw new Error(
                payload.error ||
                "Unable to load news"
            );

        }


        allItems =
            payload.results;


        render();


        status.textContent =
            `${allItems.length} stories for "${query}"`;

    }


    catch (error) {

        status.textContent =
            "Unable to load stories";


        results.innerHTML =
            `<div class="error">
                ${escapeHtml(error.message)}
            </div>`;

    }

}


/* ============================================================
   UI EVENTS
   ============================================================ */

document
    .querySelector("#search-form")
    .addEventListener(
        "submit",
        event => {

            event.preventDefault();


            const query =
                queryInput.value.trim();


            if (query) {

                loadNews(query);

            }

        }
    );


document
    .querySelectorAll("[data-query]")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                loadNews(
                    button.dataset.query
                );

            }
        );

    });


document
    .querySelector("#menu-button")
    .addEventListener(
        "click",
        () => {

            document
                .querySelector("#sidebar")
                .classList.toggle("open");

        }
    );


document
    .querySelector("#images-toggle")
    .addEventListener(
        "click",
        event => {

            showImages =
                !showImages;


            event.currentTarget
                .classList.toggle(
                    "on",
                    showImages
                );


            render();

        }
    );


document
    .querySelector("#ads-toggle")
    .addEventListener(
        "click",
        event => {

            showAds =
                !showAds;


            event.currentTarget
                .classList.toggle(
                    "on",
                    showAds
                );


            render();

        }
    );


document
    .querySelectorAll("[data-game]")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                openGame(
                    button.dataset.game
                );

            }
        );

    });


document
    .querySelector("#close-game")
    .addEventListener(
        "click",
        () => {

            clearInterval(gameTimer);

            document
                .querySelector("#game-modal")
                .hidden = true;

            window.onkeydown = null;

        }
    );


loadMore.addEventListener(
    "click",
    () => {

        results.innerHTML =
            allItems
                .slice(1)
                .map(card)
                .join("");


        /*
         * Put another ad after the extra stories.
         */

        if (showAds) {

            results.innerHTML +=
                adCard(1);

        }


        loadMore.hidden = true;

    }
);


/* ============================================================
   INITIAL NEWS LOAD
   ============================================================ */

loadNews(currentQuery);

</script>

{% endif %}

</body>
</html>
"""


# ============================================================
# AUTH PAGE HELPER
# ============================================================

def render_auth(mode, error=None):
    return render_template_string(
        PAGE,
        auth_page=True,
        auth_mode=mode,
        error=error,
        query=DEFAULT_QUERY,
        categories=CATEGORIES,
        logged_in=("username" in session),
        username=session.get("username")
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        if "username" in session:
            return redirect(url_for("index"))

        return render_auth("login")


    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    if not username or not password:

        return render_auth(
            "login",
            "Please enter your username and password."
        )


    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    db.close()


    if user is None or not check_password_hash(
        user["password"],
        password
    ):

        return render_auth(
            "login",
            "Incorrect username or password."
        )


    session.clear()

    session["user_id"] = user["id"]
    session["username"] = user["username"]


    return redirect(url_for("index"))


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":

        if "username" in session:
            return redirect(url_for("index"))

        return render_auth("register")


    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    if len(username) < 3:

        return render_auth(
            "register",
            "Username must be at least 3 characters."
        )


    if len(username) > 30:

        return render_auth(
            "register",
            "Username must be 30 characters or fewer."
        )


    if len(password) < 6:

        return render_auth(
            "register",
            "Password must be at least 6 characters."
        )


    if password != confirm_password:

        return render_auth(
            "register",
            "The passwords do not match."
        )


    db = get_db()


    existing = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()


    if existing:

        db.close()

        return render_auth(
            "register",
            "That username is already taken."
        )


    password_hash = generate_password_hash(
        password
    )


    db.execute(
        """
        INSERT INTO users (username, password)
        VALUES (?, ?)
        """,
        (username, password_hash)
    )


    db.commit()


    user = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()


    db.close()


    session.clear()

    session["user_id"] = user["id"]
    session["username"] = username


    return redirect(url_for("index"))


# ============================================================
# LOGOUT
# ============================================================

@app.get("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# ============================================================
# HOME
# ============================================================

@app.get("/")
def index():

    query = request.args.get(
        "q",
        DEFAULT_QUERY
    ).strip() or DEFAULT_QUERY


    return render_template_string(
        PAGE,
        query=query,
        categories=CATEGORIES,
        auth_page=False,
        auth_mode=None,
        error=None,
        logged_in=("username" in session),
        username=session.get("username")
    )


# ============================================================
# NEWS SEARCH
# ============================================================

def search_news(
    query: str
) -> list[dict[str, Any]]:

    with DDGS() as ddgs:

        raw_results = ddgs.news(
            query=query,
            region="in-en",
            safesearch="moderate",
            timelimit="d",
            max_results=MAX_RESULTS,
            backend="auto",
        )


        results = []


        for item in raw_results or []:

            if not isinstance(
                item,
                dict
            ):
                continue


            title = str(
                item.get("title")
                or item.get("headline")
                or ""
            ).strip()


            url = str(
                item.get("url")
                or item.get("link")
                or ""
            ).strip()


            if not title or not url:
                continue


            results.append({

                "title": title,

                "url": url,

                "body": str(
                    item.get("body")
                    or item.get("description")
                    or item.get("snippet")
                    or ""
                ).strip(),

                "source": str(
                    item.get("source")
                    or ""
                ).strip(),

                "date": str(
                    item.get("date")
                    or ""
                ).strip(),

                "image": str(
                    item.get("image")
                    or ""
                ).strip(),

            })


        return results


# ============================================================
# NEWS API
# ============================================================

@app.get("/api/news")
def news():

    query = request.args.get(
        "q",
        DEFAULT_QUERY
    ).strip()


    if not query:

        return jsonify({
            "error":
                "Search query cannot be empty"
        }), 400


    try:

        return jsonify({

            "query": query,

            "results":
                search_news(query)

        })


    except Exception:

        app.logger.exception(
            "News search failed for query %r",
            query
        )


        return jsonify({
            "error":
                "News search is temporarily unavailable"
        }), 502


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))

    print("\nworldBrief is running!")
    print(f"Local:   http://127.0.0.1:{port}")
    print(f"Network: http://0.0.0.0:{port}")

    app.run(
        host=host,
        port=port,
        debug=False
    )

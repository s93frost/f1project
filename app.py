import os, urllib.request

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import (
    login_required,
    lookup,
    drivers_lookup,
    teams_lookup,
    drivers_for_team,
    driver_standings,
    team_standings,
    next_race,
    previous_race,
    result,
    result_default,
    fastest,
    seasons_history,
    picture,
    track_pic,
)

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# global variables - dictionaries etc - reset at login &
drivers_and_teams = {}
drivers_dict = {}
teams_dict = {}
names_dict = {}
team_pics = False
current_season = ""


@app.context_processor
def inject_user():
    """to create dict of user session to make user available before templates are rendered"""
    try:
        x = session["user_id"]
    except:
        return {}
    else:
        username = db.execute(
            "SELECT username FROM users WHERE id = ?", session["user_id"]
        )[0]["username"].capitalize()
        return dict(user=username)


@app.after_request
def after_request(response):
    """This is to ensure that responses are not cached - caching responses
    is the default for Flask but may mean changes are not picked up by browser"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET"])
@login_required  # decorator to ensure logged in
def index():
    """Show's main page including upcoming race info"""
    username = (
        db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    )[0]["username"]
    last_race = previous_race()  # variable for the most recent completed race
    global current_season
    current_season = last_race["season"]
    next = next_race(1)
    next_plus_one = next_race(2)

    # calling wiki picture api functions for each track if not already exists
    if last_race != None and last_race != False:  # checks if there is a last race returned by the API
        if not os.path.isfile(
            f'/home/s93frost/f1project-main/static/track_pics/{last_race["Circuit"]["circuitName"]}.jpg'
        ):
            track_pic(last_race)

    if next != None and next != False: # checks if next race returned by the API (for end of season)
        if not os.path.isfile(
            f'/home/s93frost/f1project-main/static/track_pics/{next["Circuit"]["circuitName"]}.jpg'
        ):
            track_pic(next)

    if next_plus_one != None and next_plus_one != False:  # checks if next plus one race returned by the API (for end of season)
        if not os.path.isfile(
            f'/home/s93frost/f1project-main/static/track_pics/{next_plus_one["Circuit"]["circuitName"]}.jpg'
        ):
            track_pic(next_plus_one)

    # for dict of all teams in currrent year - this isn't required - only to preload so wait time isn't too long once clicking on /drivers route
    if not teams_dict:
        global teams  # specifies global so can be used by render template once already created and teams_dict already made
        teams = teams_lookup()
        for team in teams:
            name = team["constructorId"]
            teams_dict[name] = team

    return render_template(
        "index.html",
        username=username,
        next=next,
        next_plus_one=next_plus_one,
        last_race=last_race,
        current_season=current_season,
    )


@app.route("/drivers", methods=["GET"])
@login_required  # decorator to ensure logged in
def drivers():
    """Gets info for current drivers and displays their info in order of season standings"""

    # for dict of all teams in currrent year
    if not teams_dict:
        global teams  # specifies global so can be used by render template once already created and teams_dict already made
        teams = teams_lookup()
        for team in teams:
            name = team["constructorId"]
            teams_dict[name] = team

    # for dict of all drivers in currrent year
    if not drivers_dict:
        global drivers  # specifies global so can be used by render template once already created and teams_dict already made
        drivers = drivers_lookup()
        for driver in drivers:
            drivers_dict[driver["driverId"]] = driver

    # for dictionary of all teams and their drivers in current year
    if not drivers_and_teams:
        for team in teams_dict:
            team_name = team
            drivers_and_teams[team_name] = []
            for driver in drivers_for_team(team):
                d = driver["driverId"]
                drivers_and_teams[team].append(d)

    # to pull all pictures for drivers from their wikipedia url if file not already exists
    for x in drivers_dict.values():
        if os.path.isfile(
            f'/home/s93frost/f1project-main/static/driver_pics/{x["givenName"]}{x["familyName"]}.jpg'
        ):
            continue
        else:
            wiki_url = x["url"]
            # splits out page title from wiki page for API search
            wiki_search_title = wiki_url.split("/")[-1]
            # uses title for API function search tp pull picture
            url = picture(wiki_search_title)
            # if API call returns data, retrieve the URL and save it to my workspace
            if url:
                urllib.request.urlretrieve(
                    url,
                    f'/home/s93frost/f1project-main/static/driver_pics/{x["givenName"]}{x["familyName"]}.jpg',
                )

    driver_standing = driver_standings()

    return render_template(
        "drivers.html", driver_standing=driver_standing, current_season=current_season
    )


@app.route("/teams", methods=["GET"])
@login_required  # decorator to ensure logged in
def teams():
    """Gets info for current teams and displays their info in order of season standings"""

    # for dict  of all teams in currrent year
    if not teams_dict:
        global teams  # specifies global so can be used by render template once already created and teams_dict already made
        teams = teams_lookup()
        for team in teams:
            name = team["constructorId"]
            teams_dict[name] = team

    # to pull all pictures for teams from their wikipedia url if file not already exists
    global team_pics
    if team_pics == False:
        for x in teams_dict.values():
            if os.path.isfile(
                f'/home/s93frost/f1project-main/static/team_pics/{x["constructorId"]}.jpg'
            ):
                continue
            else:
                wiki_url = x["url"]
                # splits out page title from wiki page for API search
                wiki_search_title = wiki_url.split("/")[-1]
                # uses title for API function search tp pull picture
                url = picture(wiki_search_title)
                if url:
                    urllib.request.urlretrieve(
                        url,
                        f'/home/s93frost/f1project-main/static/team_pics/{x["constructorId"]}.jpg',
                    )
        # sets variable as true after loop run so doesn't check again if already pulled
        team_pics = True

    # for dict of all drivers in currrent year
    if not drivers_dict:
        global drivers  # specifies global so can be used by render template once already created and drivers_dict already made
        drivers = drivers_lookup()
        for driver in drivers:
            drivers_dict[driver["driverId"]] = driver

    # for dictionary of all teams and their drivers in current year
    if not drivers_and_teams:
        for team in teams_dict:
            team_name = team
            drivers_and_teams[team_name] = []
            for driver in drivers_for_team(team):
                d = driver["driverId"]
                drivers_and_teams[team].append(d)

    team_standing = team_standings()

    return render_template(
        "teams.html",
        drivers_dict=drivers_dict,
        drivers_and_teams=drivers_and_teams,
        team_standing=team_standing,
        current_season=current_season,
    )


@app.route("/results", methods=["GET", "POST"])
@login_required  # decorator to ensure logged in
def results():
    """Show's results of current race and allows users to select historical races to view"""

    seasons_and_rounds = {}  # dict for storing seasons and round combinations
    all_rounds = seasons_history()
    # to get list of all seasons being pulled by APi (offset due to size so starts in later year)
    for x in all_rounds:
        seasons_and_rounds[x["season"]] = []
    # to get all the rounds and add them to the season key in the dict
    for x in all_rounds:
        seasons_and_rounds[x["season"]].append(x["round"])

    data = result_default()

    # to pull picture for specific race loaded on page
    wiki_url = data["Races"][0]["Circuit"]["url"]
    # splits out page title from wiki page for API search
    wiki_search_title = wiki_url.split("/")[-1]
    # uses title for API function search tp pull picture
    url = picture(wiki_search_title)
    if url:
        urllib.request.urlretrieve(
            url,
            f'/home/s93frost/f1project-main/static/race_pics/{data["Races"][0]["raceName"]}.jpg',
        )

    current_year = data["season"]
    current_round = data["round"]
    # for getting fastest lap of last race
    fastest_lap = fastest(current_year, current_round)
    result_data = data["Races"][0]["Results"]

    if request.method == "POST":
        year = request.form.get("year")
        round = request.form.get("round")

        # if no constructor or driver entered on submit or doesnt exist
        if not year:
            link = "/results"
            message = "Please select a year in the dropdown"
            return render_template("error_message.html", message=message, link=link)
        if not round:
            link = "/results"
            message = "Please select a round in the dropdown"
            return render_template("error_message.html", message=message, link=link)

        fastest_lap = fastest(year, round)  # for getting fastest lap of selected race
        selected_data = result(year, round)  # for getting data for selected race

        if selected_data["Races"]:
            result_data = selected_data["Races"][0]["Results"]
            # to pull picture for race
            wiki_url = selected_data["Races"][0]["Circuit"]["url"]
            # splits out page title from wiki page for API search
            wiki_search_title = wiki_url.split("/")[-1]
            # uses title for API function search tp pull picture
            url = picture(wiki_search_title)
            if url:
                urllib.request.urlretrieve(
                    url,
                    f'/home/s93frost/f1project-main/static/race_pics/{selected_data["Races"][0]["raceName"]}.jpg',
                )
        else:
            # if no result data from API (may not be needed now i've limited to only valid seasons & rounds)
            result_data = None

        return render_template(
            "results.html",
            seasons_and_rounds=seasons_and_rounds,
            fastest_lap=fastest_lap,
            data=selected_data,
            result_data=result_data,
        )

    # if not post but get method
    else:
        return render_template(
            "results.html",
            seasons_and_rounds=seasons_and_rounds,
            fastest_lap=fastest_lap,
            data=data,
            result_data=result_data,
        )


@app.route("/driver_history", methods=["GET", "POST"])
@login_required  # decorator to ensure logged in
def driver_history():
    """allows user to pick drivers from current teams and list all the seasons that they've been with that team"""

    # for dict of all teams in currrent year
    if not teams_dict:
        global teams  # specifies global so can be used by render template once already created and teams_dict already made
        teams = teams_lookup()
        for team in teams:
            name = team["constructorId"]
            teams_dict[name] = team

    # for dict of all drivers in currrent year
    if not drivers_dict:
        global drivers  # specifies global so can be used by render template once already created and drivers_dict already made
        drivers = drivers_lookup()
        for driver in drivers:
            drivers_dict[driver["driverId"]] = driver

    # dict for proper names for select drop-down instead of driver ids and constructor_ids
    if not names_dict:
        for team in teams_dict.values():
            team_name = team["name"]
            names_dict[team_name] = []
            for driver in drivers_for_team(team["constructorId"]):
                d = driver["givenName"] + " " + driver["familyName"]
                names_dict[team_name].append(d)

    # dict to store vaues of driver ids and names
    driver_names = {}
    for driver in drivers_dict.values():
        drivername = driver["givenName"] + " " + driver["familyName"]
        driver_names[drivername] = driver["driverId"]

    # dict to store vaues of driver ids and names
    team_names = {}
    for team in teams_dict.values():
        tname = team["name"]
        team_names[tname] = team["constructorId"]

    if request.method == "POST":
        drivers_name = request.form.get("driver_name")
        constructor_name = request.form.get("constructor_name")
        # if no constructor or driver entered on submit or doesnt exist
        if not constructor_name:
            link = "/driver_history"
            message = "Please select a team name"
            return render_template("error_message.html", message=message, link=link)
        if not drivers_name:
            link = "/driver_history"
            message = "Please select a driver name"
            return render_template("error_message.html", message=message, link=link)

        # pulls corresponding driver_id for the name selected on form held in drivers_name variable
        driver_id = driver_names[drivers_name]
        # pulls corresponding constructor_id for the name selected on form held in constructor_name variable
        constructor_id = team_names[constructor_name]
        # my driver and constructor info API function
        info = lookup(driver_id, constructor_id)
        seasons = info["MRData"]["SeasonTable"]["Seasons"]

        return render_template(
            "driver_history.html",
            names_dict=names_dict,
            drivers_name=drivers_name,
            seasons=seasons,
            constructor_name=constructor_name,
            current_season=current_season,
        )

    # if method = GET
    else:
        seasons = ""
        constructor_name = ""
        drivers_name = ""

        return render_template(
            "driver_history.html",
            names_dict=names_dict,
            drivers_name=drivers_name,
            seasons=seasons,
            constructor_name=constructor_name,
            current_season=current_season,
        )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # resets these global variables if not already done
    global drivers_and_teams
    global teams_dict
    global drivers_dict
    global names_dict
    global team_pics
    global current_season
    drivers_and_teams = {}
    drivers_dict = {}
    teams_dict = {}
    names_dict = {}
    team_pics = False
    current_season = ""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            link = "/login"
            message = "Please provide a username"
            return render_template("error_message.html", message=message, link=link)

        # Ensure password was submitted
        elif not request.form.get("password"):
            link = "/login"
            message = "Please provide a password"
            return render_template("error_message.html", message=message, link=link)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            link = "/login"
            message = "Your username and password combination was incorrect"
            return render_template("error_message.html", message=message, link=link)

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

    session.clear()  # Forget any user_id

    # resets these global variables
    global drivers_and_teams
    global teams_dict
    global drivers_dict
    global names_dict
    global team_pics
    global current_season
    drivers_and_teams = {}
    drivers_dict = {}
    teams_dict = {}
    names_dict = {}
    team_pics = False
    current_season = ""

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Validate submission
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        hash_password = generate_password_hash(password)

        # if no username
        if not username:
            link = "/register"
            message = "Please enter a username in order to sign up"
            return render_template("error_message.html", message=message, link=link)

        already_exists = db.execute(
            "SELECT username FROM users WHERE username = ?", username
        )

        if already_exists:
            already_exists = already_exists[0]["username"]

        if username == already_exists:
            link = "/register"
            message = "That username already exists"
            return render_template("error_message.html", message=message, link=link)

        # if no password or password not match confirmation
        if not password or password != confirmation:
            link = "/register"
            message = "Please enter a password and make sure it matches the password confirmation"
            return render_template("error_message.html", message=message, link=link)
        # Remember registrant
        db.execute(
            "INSERT INTO users (username, hash) VALUES(?, ?)", username, hash_password
        )
        # once submitted it redirects to home
        return redirect("/")

    # if post not detected (i.e if GET) ask user to register
    else:
        return render_template("register.html")


@app.route("/deregister", methods=["GET", "POST"])
@login_required  # decorator to ensure logged in
def deregister():
    """deregister user"""

    if request.method == "POST":
        # Delete user from user table
        db.execute("DELETE FROM users WHERE id = ?", session["user_id"])
        # once submitted it redirects to home
        return redirect("/logout")

    else:
        return render_template("deregister.html")

# Internal Recruitment System      

## Tech Stack 
- Python 3.10.6
- Postgres
- test

**These are the minimum required version in order to run this project**


## Initial Setup
Clone the code, Install the required technologies with required version and do following in sequence

### Python Setup
- Install pip using [guide](https://pip.pypa.io/en/stable/installation/)
- Install virtual enviornment using this [guide](https://virtualenv.pypa.io/en/latest/index.html)
- Create and Activate virtual envoirnment
- Run `pip install -r requirements.txt`
- Run `python manage.py migrate`

The application should be accessible at (http://localhost:8000) when we run the command `python manage.py runserver`

### Install Pre-Commit hook
These hooks are for project wide code quality checks.
To install do following
- `pre-commit install --hook-type pre-commit`

### To populate database
- Run migrations if needed `python manage.py migrate`
- Flush database if needed `python manage.py flush`
- Run `python manage.py populate` to add fake data to database
- just a litte changes in readme files. 